/**
 * @filenest/react context/FileNestContext — provider and context for the React SDK.
 *
 * `FileNestProvider` fetches upload tokens from the host app's token endpoint
 * and makes them available to all hooks and components. Tokens are cached and
 * refreshed 60 seconds before expiry.
 *
 * Upload flow (three-step presigned URL pattern):
 *   1. POST JSON to backend init endpoint → receive presigned storage URL + file_id
 *   2. PUT file bytes to presigned URL (XHR for progress, fetch otherwise)
 *   3. POST /confirm → triggers the processing pipeline
 *
 * @module
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { FileRecord, UploadProgress } from "@filenest/core";

export interface FileNestContextValue {
  projectId: string;
  baseUrl: string;
  tokenEndpoint: string;
  getToken: () => Promise<string>;
  upload: (
    file: File,
    options?: { folderId?: string; metadata?: Record<string, unknown>; tags?: string[]; onProgress?: (p: UploadProgress) => void }
  ) => Promise<FileRecord>;
  isReady: boolean;
}

const FileNestContext = createContext<FileNestContextValue | null>(null);

export interface FileNestProviderProps {
  tokenEndpoint: string;
  projectId: string;
  /**
   * Base URL of the FileNest backend, e.g. "https://api.filenest.io".
   * Defaults to "" (same origin). Set this when the backend is at a different origin.
   */
  baseUrl?: string;
  options?: {
    environment?: "production" | "test";
    debug?: boolean;
  };
  children: React.ReactNode;
}

const internalQueryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 2 } },
});

export function FileNestProvider({ tokenEndpoint, projectId, baseUrl = "", options, children }: FileNestProviderProps) {
  const [isReady, setIsReady] = useState(false);
  const tokenRef = useRef<{ token: string; expiresAt: number } | null>(null);
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const api = baseUrl.replace(/\/$/, "");

  const fetchToken = useCallback(async (): Promise<string> => {
    const res = await fetch(tokenEndpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    if (!res.ok) throw new Error(`Token endpoint returned ${res.status}`);
    const data = (await res.json()) as { token: string; expiresAt: string };
    const expiresAt = new Date(data.expiresAt).getTime();
    tokenRef.current = { token: data.token, expiresAt };
    const ttl = expiresAt - Date.now() - 60_000;
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    if (ttl > 0) {
      refreshTimerRef.current = setTimeout(() => fetchToken().catch(console.error), ttl);
    }
    return data.token;
  }, [tokenEndpoint]);

  const getToken = useCallback(async (): Promise<string> => {
    if (tokenRef.current && tokenRef.current.expiresAt - Date.now() > 60_000) {
      return tokenRef.current.token;
    }
    return fetchToken();
  }, [fetchToken]);

  useEffect(() => {
    fetchToken()
      .then(() => setIsReady(true))
      .catch((err) => {
        if (options?.debug) console.error("[FileNest] Failed to fetch initial token:", err);
      });
    return () => {
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    };
  }, [fetchToken, options?.debug]);

  const upload = useCallback(
    async (
      file: File,
      opts: { folderId?: string; metadata?: Record<string, unknown>; tags?: string[]; onProgress?: (p: UploadProgress) => void } = {}
    ): Promise<FileRecord> => {
      const token = await getToken();
      const authHeader = { Authorization: `Bearer ${token}` };

      // 1. Init: tell backend about the file, get a presigned PUT URL
      const initRes = await fetch(`${api}/v1/projects/${projectId}/files/upload`, {
        method: "POST",
        headers: { ...authHeader, "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: file.name,
          content_type: file.type || "application/octet-stream",
          size_bytes: file.size,
          folder_id: opts.folderId ?? null,
          metadata: opts.metadata ?? {},
          tags: opts.tags ?? [],
        }),
      });
      if (!initRes.ok) throw new Error(`Upload init failed: ${initRes.statusText}`);
      const initData = (await initRes.json()) as { file_id: string; upload_url: string };

      // 2. PUT file bytes to presigned storage URL (XHR enables upload progress events)
      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable && opts.onProgress) {
            opts.onProgress({
              bytesUploaded: e.loaded,
              totalBytes: e.total,
              percentage: Math.round((e.loaded / e.total) * 100),
              chunkNumber: 1,
              totalChunks: 1,
            });
          }
        };
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) resolve();
          else reject(new Error(`Storage upload failed with status ${xhr.status}`));
        };
        xhr.onerror = () => reject(new Error("Network error during storage upload"));
        xhr.open("PUT", initData.upload_url);
        xhr.setRequestHeader("Content-Type", file.type || "application/octet-stream");
        xhr.send(file);
      });

      // 3. Confirm — triggers the virus scan + processing pipeline
      const confirmRes = await fetch(`${api}/v1/projects/${projectId}/files/${initData.file_id}/confirm`, {
        method: "POST",
        headers: authHeader,
      });
      if (!confirmRes.ok) throw new Error(`Upload confirm failed: ${confirmRes.statusText}`);

      // 4. Return full file record
      const fileRes = await fetch(`${api}/v1/projects/${projectId}/files/${initData.file_id}`, {
        headers: authHeader,
      });
      if (!fileRes.ok) throw new Error(`Failed to fetch file record: ${fileRes.statusText}`);
      return fileRes.json() as Promise<FileRecord>;
    },
    [getToken, projectId, api]
  );

  return (
    <QueryClientProvider client={internalQueryClient}>
      <FileNestContext.Provider value={{ projectId, baseUrl: api, tokenEndpoint, getToken, upload, isReady }}>
        {children}
      </FileNestContext.Provider>
    </QueryClientProvider>
  );
}

export function useFileNest(): FileNestContextValue {
  const ctx = useContext(FileNestContext);
  if (!ctx) {
    throw new Error("useFileNest must be used inside <FileNestProvider>");
  }
  return ctx;
}
