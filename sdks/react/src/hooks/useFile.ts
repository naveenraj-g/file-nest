/**
 * @filenest/react hooks/useFile — single file detail with revalidation.
 * @module
 */

import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { FileRecord } from "@filenest/core";
import { useFileNest } from "../context/FileNestContext.js";

export interface UseFileOptions {
  includeVersions?: boolean;
  includeProcessing?: boolean;
  enabled?: boolean;
}

export function useFile(fileId: string, options: UseFileOptions = {}) {
  const { projectId, baseUrl, getToken } = useFileNest();
  const queryClient = useQueryClient();
  const queryKey = ["filenest", "file", projectId, fileId, options];

  const fetcher = useCallback(async (): Promise<FileRecord> => {
    const token = await getToken();
    const params = new URLSearchParams();
    if (options.includeVersions) params.set("include_versions", "true");
    if (options.includeProcessing) params.set("include_processing", "true");

    const res = await fetch(`${baseUrl}/v1/projects/${projectId}/files/${fileId}?${params}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error(`Failed to fetch file ${fileId}: ${res.statusText}`);
    return res.json() as Promise<FileRecord>;
  }, [projectId, fileId, getToken, options]);

  const { data, isLoading, isError, error } = useQuery({
    queryKey,
    queryFn: fetcher,
    enabled: !!fileId && options.enabled !== false,
  });

  const mutate = useCallback(() => {
    queryClient.invalidateQueries({ queryKey });
  }, [queryClient, queryKey]);

  return {
    file: data ?? null,
    isLoading,
    isError,
    error: error as Error | null,
    mutate,
  };
}
