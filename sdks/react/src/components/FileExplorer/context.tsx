/**
 * FileExplorer/context — React context that threads state + data through all sub-components.
 *
 * FileExplorer.tsx creates and provides this context. Every child component reads
 * it via useExplorer() rather than accepting props directly.
 *
 * @module
 */

import { createContext, useContext } from "react";
import type React from "react";
import type { FileRecord, Folder } from "@filenest/core";
import type { Breadcrumb } from "../../hooks/useFolder.js";
import type { ExplorerState } from "./useExplorerState.js";

export interface ExplorerCallbacks {
  onFileClick?: (file: FileRecord) => void;
  onFolderClick?: (folder: Folder) => void;
  onFileDelete?: (file: FileRecord) => Promise<void>;
  onFolderDelete?: (folder: Folder) => Promise<void>;
  onFileDownload?: (file: FileRecord) => void;
  onFolderCreate?: (name: string, parentId: string | null) => Promise<void>;
  onFileRename?: (id: string, name: string) => Promise<void>;
  onFolderRename?: (id: string, name: string) => Promise<void>;
  onFileMove?: (fileId: string, folderId: string | null) => Promise<void>;
  onFolderMove?: (folderId: string, folderId2: string | null) => Promise<void>;
  onSelectionChange?: (ids: string[]) => void;
}

export interface ExplorerData {
  files: FileRecord[];
  folders: Folder[];
  breadcrumbs: Breadcrumb[];
  isLoading: boolean;
  isFetchingMore: boolean;
  hasMore: boolean;
  totalCount: number;
  sentinelRef: React.RefObject<HTMLDivElement | null>;
}

export type ExplorerContextValue = ExplorerState & ExplorerData & ExplorerCallbacks;

const ExplorerCtx = createContext<ExplorerContextValue | null>(null);

export const ExplorerProvider = ExplorerCtx.Provider;

export function useExplorer(): ExplorerContextValue {
  const ctx = useContext(ExplorerCtx);
  if (!ctx) throw new Error("useExplorer must be called inside <FileExplorer>");
  return ctx;
}
