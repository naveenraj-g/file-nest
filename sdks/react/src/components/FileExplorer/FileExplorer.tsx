/**
 * FileExplorer/FileExplorer — Google Drive-inspired file browser component.
 *
 * Three-pane layout: sidebar (sections + storage) · content (grid or list) ·
 * info panel (file details). Infinite scroll via useInfiniteQuery +
 * IntersectionObserver — no pagination buttons.
 *
 * Data flow:
 *   useInfiniteFiles → files (auto-loads next page as sentinel enters viewport)
 *   useFolder        → subfolders + breadcrumbs for current folder
 *   useSearch        → search results (replaces file list when query is set)
 *
 * @module
 */

import React, { useEffect, useRef, useMemo } from "react";
import type { FileRecord, Folder } from "@filenest/core";
import { useInfiniteFiles }     from "../../hooks/useInfiniteFiles.js";
import { useFolder }            from "../../hooks/useFolder.js";
import { useSearch }            from "../../hooks/useSearch.js";
import { useExplorerState }     from "./useExplorerState.js";
import { ExplorerProvider }     from "./context.js";
import { ExplorerStyles }       from "./ExplorerStyles.js";
import { ExplorerSidebar }      from "./ExplorerSidebar.js";
import { ExplorerTopBar }       from "./ExplorerTopBar.js";
import { ExplorerBreadcrumb }   from "./ExplorerBreadcrumb.js";
import { ExplorerGrid }         from "./ExplorerGrid.js";
import { ExplorerList }         from "./ExplorerList.js";
import { ExplorerInfoPanel }    from "./ExplorerInfoPanel.js";
import { ExplorerDialogs }      from "./ExplorerDialogs.js";
import type { FileExplorerProps } from "./index.js";

export function FileExplorer({
  rootFolderId = null,
  defaultView  = "grid",
  defaultSort  = "name",
  height       = "100%",
  onFileClick,
  onFolderClick,
  onFileDelete,
  onFolderDelete,
  onFileDownload,
  onFolderCreate,
  onFileRename,
  onFolderRename,
  onFileMove,
  onFolderMove,
  onSelectionChange,
  className,
  style,
}: FileExplorerProps) {
  const state = useExplorerState({ rootFolderId, defaultView, defaultSort });
  const sentinelRef = useRef<HTMLDivElement>(null);

  // ── Data fetching ────────────────────────────────────────
  const sortField = state.sortBy === "modified" ? "updated_at"
    : state.sortBy === "size" ? "size"
    : state.sortBy === "kind" ? "mime_type"
    : "filename";

  const infiniteFiles = useInfiniteFiles({
    folderId:    state.currentFolderId,
    sortBy:      sortField,
    sortOrder:   state.sortOrder,
    searchQuery: state.section !== "my-drive" ? undefined : (state.searchQuery || undefined),
    enabled:     state.section === "my-drive",
  });

  const folderData = useFolder(state.currentFolderId);
  const { results, search } = useSearch({ debounceMs: 300 });

  // Kick off search when query changes
  useEffect(() => {
    if (state.searchQuery) search({ q: state.searchQuery });
  }, [state.searchQuery, search]);

  // ── Infinite scroll via IntersectionObserver ─────────────
  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && infiniteFiles.hasMore && !infiniteFiles.isFetchingMore) {
          infiniteFiles.fetchMore();
        }
      },
      { threshold: 0.1 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [infiniteFiles.hasMore, infiniteFiles.isFetchingMore, infiniteFiles.fetchMore]);

  // ── Keyboard shortcuts ───────────────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      const inInput = tag === "INPUT" || tag === "TEXTAREA";
      if (e.key === "Escape") { state.clearSelection(); state.closeModal(); }
      if (e.key === "a" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        const ids = [...folderData.subfolders.map((f) => f.id), ...infiniteFiles.files.map((f) => f.id)];
        state.selectAll(ids);
      }
      if (!inInput && e.key === "n") state.openModal("new-folder");
      if (!inInput && (e.key === "Delete" || e.key === "Backspace") && state.selectedIds.size > 0) {
        const id = Array.from(state.selectedIds)[0];
        const file = infiniteFiles.files.find((f) => f.id === id);
        const folder = folderData.subfolders.find((f) => f.id === id);
        if (file) state.openModal("delete", { type: "file", id, name: file.filename, item: file });
        else if (folder) state.openModal("delete", { type: "folder", id, name: folder.name, item: folder });
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [state, infiniteFiles.files, folderData.subfolders]);

  // ── Notify parent of selection changes ───────────────────
  useEffect(() => {
    onSelectionChange?.(Array.from(state.selectedIds));
  }, [state.selectedIds, onSelectionChange]);

  // ── Compute files + folders to display ──────────────────
  const displayFiles: FileRecord[] = state.searchQuery
    ? results.map((h) => h.file)
    : state.section === "starred"
    ? infiniteFiles.files.filter((f) => state.starredIds.has(f.id))
    : infiniteFiles.files;

  const displayFolders: Folder[] = state.searchQuery ? [] : folderData.subfolders;

  // ── Build context value ──────────────────────────────────
  const ctxValue = useMemo(
    () => ({
      ...state,
      files:           displayFiles,
      folders:         displayFolders,
      breadcrumbs:     folderData.breadcrumbs,
      isLoading:       infiniteFiles.isLoading || folderData.isLoading,
      isFetchingMore:  infiniteFiles.isFetchingMore,
      hasMore:         infiniteFiles.hasMore,
      totalCount:      infiniteFiles.totalCount,
      sentinelRef,
      onFileClick,
      onFolderClick,
      onFileDelete,
      onFolderDelete,
      onFileDownload,
      onFolderCreate,
      onFileRename,
      onFolderRename,
      onFileMove,
      onFolderMove,
      onSelectionChange,
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [state, displayFiles, displayFolders, folderData, infiniteFiles]
  );

  return (
    <ExplorerProvider value={ctxValue}>
      <ExplorerStyles />
      <div
        className={`fn-ex${className ? ` ${className}` : ""}`}
        style={{ height, ...style }}
      >
        {/* Top bar */}
        <ExplorerTopBar />

        {/* Body */}
        <div className="fn-ex-body">
          {/* Sidebar */}
          <ExplorerSidebar />

          {/* Main content */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
            <ExplorerBreadcrumb />
            {state.view === "grid" ? <ExplorerGrid /> : <ExplorerList />}
          </div>

          {/* Info panel */}
          {state.infoPanelOpen && <ExplorerInfoPanel />}
        </div>

        {/* Dialogs (portaled, rendered once) */}
        <ExplorerDialogs />
      </div>
    </ExplorerProvider>
  );
}
