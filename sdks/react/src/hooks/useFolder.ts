/**
 * @filenest/react hooks/useFolder — folder navigation with breadcrumbs.
 * @module
 */

import { useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import type { FileRecord, Folder } from "@filenest/core";
import { useFileNest } from "../context/FileNestContext.js";

export interface Breadcrumb {
  id: string | null;
  name: string;
}

export interface UseFolderResult {
  folder: Folder | null;
  files: FileRecord[];
  subfolders: Folder[];
  isLoading: boolean;
  breadcrumbs: Breadcrumb[];
}

export function useFolder(folderId: string | null): UseFolderResult {
  const { projectId, getToken } = useFileNest();

  const fetcher = useCallback(async () => {
    const token = await getToken();
    const headers = { Authorization: `Bearer ${token}` };

    const [folderRes, filesRes, subfoldersRes] = await Promise.all([
      folderId
        ? fetch(`/v1/projects/${projectId}/folders/${folderId}`, { headers }).then((r) => r.json() as Promise<Folder>)
        : Promise.resolve(null),
      fetch(`/v1/projects/${projectId}/files?folder_id=${folderId ?? "root"}&limit=100`, { headers }).then(
        (r) => r.json() as Promise<{ data: FileRecord[] }>
      ),
      fetch(`/v1/projects/${projectId}/folders?parent_folder_id=${folderId ?? ""}`, { headers }).then(
        (r) => r.json() as Promise<{ data: Folder[] }>
      ),
    ]);

    return {
      folder: folderRes,
      files: filesRes.data,
      subfolders: subfoldersRes.data,
    };
  }, [projectId, getToken, folderId]);

  const { data, isLoading } = useQuery({
    queryKey: ["filenest", "folder", projectId, folderId],
    queryFn: fetcher,
  });

  const buildBreadcrumbs = (): Breadcrumb[] => {
    const crumbs: Breadcrumb[] = [{ id: null, name: "Root" }];
    if (data?.folder) {
      // Parse materialized path: "parent/current" → ["parent", "current"]
      const parts = data.folder.path.split("/").filter(Boolean);
      parts.forEach((name, i) => {
        crumbs.push({ id: i < parts.length - 1 ? `path-${i}` : data.folder!.id, name });
      });
    }
    return crumbs;
  };

  return {
    folder: data?.folder ?? null,
    files: data?.files ?? [],
    subfolders: data?.subfolders ?? [],
    isLoading,
    breadcrumbs: buildBreadcrumbs(),
  };
}
