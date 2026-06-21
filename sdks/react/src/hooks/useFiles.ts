/**
 * @filenest/react hooks/useFiles — TanStack Query-backed file list with pagination.
 * @module
 */

import { useCallback, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { FileRecord, ListResponse, SearchFilters } from "@filenest/core";
import { useFileNest } from "../context/FileNestContext.js";

export interface UseFilesOptions {
  folderId?: string;
  filters?: SearchFilters & { metadata?: Record<string, string> };
  tags?: string[];
  sortBy?: string;
  sortOrder?: "asc" | "desc";
  limit?: number;
  enabled?: boolean;
}

export function useFiles(options: UseFilesOptions = {}) {
  const { projectId, getToken } = useFileNest();
  const [offset, setOffset] = useState(0);
  const limit = options.limit ?? 20;

  const fetcher = useCallback(async (): Promise<ListResponse<FileRecord>> => {
    const token = await getToken();
    const params = new URLSearchParams();
    params.set("limit", String(limit));
    params.set("offset", String(offset));
    if (options.folderId) params.set("folder_id", options.folderId);
    if (options.sortBy) params.set("sort_by", options.sortBy);
    if (options.sortOrder) params.set("sort_order", options.sortOrder);
    if (options.tags?.length) params.set("tags", options.tags.join(","));
    if (options.filters?.metadata) params.set("metadata", JSON.stringify(options.filters.metadata));

    const res = await fetch(`/v1/projects/${projectId}/files?${params}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error(`Failed to fetch files: ${res.statusText}`);
    return res.json() as Promise<ListResponse<FileRecord>>;
  }, [projectId, getToken, options, offset, limit]);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["filenest", "files", projectId, options, offset],
    queryFn: fetcher,
    enabled: options.enabled !== false,
  });

  return {
    files: data?.data ?? [],
    totalCount: data?.pagination.total ?? 0,
    hasMore: data?.pagination.hasMore ?? false,
    isLoading,
    isError,
    error: error as Error | null,
    loadMore: () => setOffset((o) => o + limit),
    refresh: () => refetch(),
  };
}
