/**
 * @filenest/react hooks/useFolder — folder navigation with breadcrumbs.
 * @module
 */

import { useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import type { FileRecord, Folder, ListResponse } from "@filenest/core";
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
  const { projectId, baseUrl, getToken } = useFileNest();

  const fetcher = useCallback(async () => {
    const token = await getToken();
    const headers = { Authorization: `Bearer ${token}` };

    const [folderRes, filesRes, subfoldersRes] = await Promise.all([
      folderId
        ? fetch(`${baseUrl}/v1/projects/${projectId}/folders/${folderId}`, { headers }).then((r) => r.json() as Promise<Folder>)
        : Promise.resolve(null),
      fetch(`${baseUrl}/v1/projects/${projectId}/files?folder_id=${folderId ?? "root"}&limit=100`, { headers }).then(
        (r) => r.json() as Promise<ListResponse<FileRecord>>
      ),
      fetch(`${baseUrl}/v1/projects/${projectId}/folders?parent_folder_id=${folderId ?? ""}`, { headers }).then(
        (r) => r.json() as Promise<{ items: Folder[] }>
      ),
    ]);

    return {
      folder: folderRes,
      files: filesRes.items,
      subfolders: subfoldersRes.items,
    };
  }, [projectId, baseUrl, getToken, folderId]);

  const { data, isLoading } = useQuery({
    queryKey: ["filenest", "folder", projectId, folderId],
    queryFn: fetcher,
  });

  const buildBreadcrumbs = (): Breadcrumb[] => {
    const crumbs: Breadcrumb[] = [{ id: null, name: "Root" }];
    if (data?.folder) {
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
