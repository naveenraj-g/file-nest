/**
 * @filenest/react hooks/useInfiniteFiles — infinite-scroll file list via useInfiniteQuery.
 *
 * Feeds the FileExplorer's scroll-to-load pattern. Each page is fetched
 * automatically as the user scrolls to the sentinel element at the bottom of
 * the list. Call `fetchMore()` when the sentinel enters the viewport.
 *
 * @module
 */

import { useCallback } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import type { FileRecord, ListResponse } from "@filenest/core";
import { useFileNest } from "../context/FileNestContext.js";

export interface UseInfiniteFilesOptions {
  folderId?: string | null;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
  searchQuery?: string;
  limit?: number;
  enabled?: boolean;
}

export function useInfiniteFiles(opts: UseInfiniteFilesOptions = {}) {
  const { projectId, baseUrl, getToken } = useFileNest();
  const limit = opts.limit ?? 50;

  const fetcher = useCallback(
    async ({ pageParam = 0 }: { pageParam?: number }): Promise<ListResponse<FileRecord>> => {
      const token = await getToken();
      const params = new URLSearchParams();
      params.set("limit", String(limit));
      params.set("offset", String(pageParam));
      if (opts.folderId) params.set("folder_id", opts.folderId);
      if (opts.sortBy) params.set("sort_by", opts.sortBy);
      if (opts.sortOrder) params.set("sort_order", opts.sortOrder);
      if (opts.searchQuery) params.set("q", opts.searchQuery);

      const res = await fetch(`${baseUrl}/v1/projects/${projectId}/files?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Failed to fetch files: ${res.statusText}`);
      return res.json() as Promise<ListResponse<FileRecord>>;
    },
    [projectId, baseUrl, getToken, opts.folderId, opts.sortBy, opts.sortOrder, opts.searchQuery, limit]
  );

  const query = useInfiniteQuery({
    queryKey: [
      "filenest",
      "files-infinite",
      projectId,
      opts.folderId ?? "root",
      opts.sortBy,
      opts.sortOrder,
      opts.searchQuery,
    ],
    queryFn: fetcher,
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      const next = lastPage.offset + lastPage.limit;
      return next < lastPage.total ? next : undefined;
    },
    enabled: opts.enabled !== false,
  });

  return {
    files: query.data?.pages.flatMap((p) => p.items) ?? [],
    totalCount: query.data?.pages[0]?.total ?? 0,
    hasMore: query.hasNextPage,
    isLoading: query.isLoading,
    isFetchingMore: query.isFetchingNextPage,
    fetchMore: query.fetchNextPage,
    refresh: query.refetch,
  };
}
