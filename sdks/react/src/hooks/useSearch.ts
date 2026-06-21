/**
 * @filenest/react hooks/useSearch — debounced full-text + faceted search.
 * @module
 */

import { useCallback, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { SearchFilters, SearchFacets, SearchHit } from "@filenest/core";
import { useFileNest } from "../context/FileNestContext.js";

export interface SearchQuery {
  q?: string;
  filters?: SearchFilters;
  tags?: string[];
  limit?: number;
  offset?: number;
}

export interface UseSearchOptions {
  debounceMs?: number;
  facets?: string[];
  limit?: number;
}

export function useSearch(options: UseSearchOptions = {}) {
  const { projectId, getToken } = useFileNest();
  const queryClient = useQueryClient();
  const debounceMs = options.debounceMs ?? 300;
  const [currentQuery, setCurrentQuery] = useState<SearchQuery>({});
  const [queryTimeMs, setQueryTimeMs] = useState(0);
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const queryKey = ["filenest", "search", projectId, currentQuery, options.facets];

  const fetcher = useCallback(async () => {
    if (!currentQuery.q && !Object.keys(currentQuery.filters ?? {}).length) {
      return { hits: [], total: 0, queryTimeMs: 0, facets: undefined };
    }
    const token = await getToken();
    const t0 = Date.now();
    const res = await fetch(`/v1/projects/${projectId}/search`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ ...currentQuery, facets: options.facets, limit: options.limit ?? 20 }),
    });
    if (!res.ok) throw new Error(`Search failed: ${res.statusText}`);
    const data = (await res.json()) as { hits: SearchHit[]; total: number; facets?: SearchFacets };
    const elapsed = Date.now() - t0;
    setQueryTimeMs(elapsed);
    return { ...data, queryTimeMs: elapsed };
  }, [projectId, getToken, currentQuery, options.facets, options.limit]);

  const { data, isLoading } = useQuery({ queryKey, queryFn: fetcher, enabled: true });

  const search = useCallback(
    (query: SearchQuery) => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
      debounceTimer.current = setTimeout(() => {
        setCurrentQuery(query);
        queryClient.invalidateQueries({ queryKey: ["filenest", "search", projectId] });
      }, debounceMs);
    },
    [debounceMs, projectId, queryClient]
  );

  return {
    results: data?.hits ?? [],
    facets: data?.facets,
    isLoading,
    totalCount: data?.total ?? 0,
    queryTimeMs,
    search,
    hasMore: (data?.hits?.length ?? 0) < (data?.total ?? 0),
  };
}
