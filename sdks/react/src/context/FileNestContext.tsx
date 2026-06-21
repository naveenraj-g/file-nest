/**
 * @filenest/react context/FileNestContext — provider and context for the React SDK.
 *
 * `FileNestProvider` fetches upload tokens from the host app's token endpoint
 * and makes them available to all hooks and components. Tokens are cached and
 * refreshed 60 seconds before expiry.
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
  options?: {
    environment?: "production" | "test";
    debug?: boolean;
  };
  children: React.ReactNode;
}

const internalQueryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 2 } },
});

export function FileNestProvider({ tokenEndpoint, projectId, options, children }: FileNestProviderProps) {
  const [isReady, setIsReady] = useState(false);
  const tokenRef = useRef<{ token: string; expiresAt: number } | null>(null);
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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
    // Schedule refresh 60 s before expiry
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
      const form = new FormData();
      form.append("file", file, file.name);
      if (opts.folderId) form.append("folder_id", opts.folderId);
      if (opts.metadata) form.append("metadata", JSON.stringify(opts.metadata));
      if (opts.tags) form.append("tags", JSON.stringify(opts.tags));

      // Prefer XHR for progress reporting; fall back to fetch
      if (opts.onProgress) {
        return new Promise((resolve, reject) => {
          const xhr = new XMLHttpRequest();
          xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
              opts.onProgress!({
                bytesUploaded: e.loaded,
                totalBytes: e.total,
                percentage: Math.round((e.loaded / e.total) * 100),
                chunkNumber: 1,
                totalChunks: 1,
              });
            }
          };
          xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              resolve(JSON.parse(xhr.responseText) as FileRecord);
            } else {
              reject(new Error(`Upload failed with status ${xhr.status}`));
            }
          };
          xhr.onerror = () => reject(new Error("Network error during upload"));
          const apiUrl = `/v1/projects/${projectId}/files/upload`;
          xhr.open("POST", apiUrl);
          xhr.setRequestHeader("Authorization", `Bearer ${token}`);
          xhr.send(form);
        });
      }

      const res = await fetch(`/v1/projects/${projectId}/files/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
      return res.json() as Promise<FileRecord>;
    },
    [getToken, projectId]
  );

  return (
    <QueryClientProvider client={internalQueryClient}>
      <FileNestContext.Provider value={{ projectId, tokenEndpoint, getToken, upload, isReady }}>
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
