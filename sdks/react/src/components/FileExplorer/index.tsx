/**
 * FileExplorer — public interface.
 *
 * Re-exports the component and all public prop types. Import from
 * "@filenest/react" — do not import from this file directly.
 *
 * @module
 */

import type React from "react";
import type { FileRecord, Folder } from "@filenest/core";
import type { ViewMode, SortField } from "./useExplorerState.js";

export interface FileExplorerProps {
  rootFolderId?: string | null;
  defaultView?: ViewMode;
  defaultSort?: SortField;
  height?: number | string;
  onFileClick?: (file: FileRecord) => void;
  onFolderClick?: (folder: Folder) => void;
  onFileDelete?: (file: FileRecord) => Promise<void>;
  onFolderDelete?: (folder: Folder) => Promise<void>;
  onFileDownload?: (file: FileRecord) => void;
  onFolderCreate?: (name: string, parentId: string | null) => Promise<void>;
  onFileRename?: (id: string, name: string) => Promise<void>;
  onFolderRename?: (id: string, name: string) => Promise<void>;
  onFileMove?: (fileId: string, targetFolderId: string | null) => Promise<void>;
  onFolderMove?: (folderId: string, targetFolderId: string | null) => Promise<void>;
  onSelectionChange?: (ids: string[]) => void;
  className?: string;
  style?: React.CSSProperties;
}

export { FileExplorer } from "./FileExplorer.js";
export type { ViewMode, SortField } from "./useExplorerState.js";
