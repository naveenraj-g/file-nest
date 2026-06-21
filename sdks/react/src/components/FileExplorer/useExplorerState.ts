/**
 * FileExplorer/useExplorerState — central state management for the explorer.
 *
 * Holds all UI state (section, view, sort, selection, modals, panels).
 * Data (files, folders) lives in the parent FileExplorer component and is
 * passed through context separately.
 *
 * @module
 */

import { useState, useCallback, useRef } from "react";
import type { FileRecord, Folder } from "@filenest/core";

export type SectionId   = "my-drive" | "recent" | "starred" | "trash";
export type ViewMode    = "grid" | "list";
export type SortField   = "name" | "modified" | "size" | "kind";
export type ModalType   = "none" | "new-folder" | "rename" | "delete" | "move";

export interface ModalTarget {
  type: "file" | "folder";
  id: string;
  name: string;
  item: FileRecord | Folder;
}

export function useExplorerState(opts: {
  rootFolderId?: string | null;
  defaultView?: ViewMode;
  defaultSort?: SortField;
} = {}) {
  const [section, setSection]               = useState<SectionId>("my-drive");
  const [currentFolderId, _setCurrentFolder] = useState<string | null>(opts.rootFolderId ?? null);
  const [view, setView]                     = useState<ViewMode>(opts.defaultView ?? "grid");
  const [sortBy, setSortBy]                 = useState<SortField>(opts.defaultSort ?? "name");
  const [sortOrder, setSortOrder]           = useState<"asc" | "desc">("asc");
  const [selectedIds, setSelectedIds]       = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery]       = useState("");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [infoPanelOpen, setInfoPanelOpen]   = useState(false);
  const [infoPanelItemId, setInfoPanelItemId] = useState<string | null>(null);
  const [modal, setModal]                   = useState<ModalType>("none");
  const [modalTarget, setModalTarget]       = useState<ModalTarget | null>(null);
  const [starredIds, setStarredIds]         = useState<Set<string>>(new Set());
  const [newFolderName, setNewFolderName]   = useState("Untitled folder");
  const [renameValue, setRenameValue]       = useState("");

  const lastSelectedRef = useRef<string | null>(null);

  const navigateTo = useCallback((folderId: string | null) => {
    _setCurrentFolder(folderId);
    setSelectedIds(new Set());
    setSearchQuery("");
    setInfoPanelItemId(null);
    setInfoPanelOpen(false);
  }, []);

  const toggleSelect = useCallback(
    (id: string, shiftHeld = false, orderedIds: string[] = []) => {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        if (shiftHeld && lastSelectedRef.current && orderedIds.length > 0) {
          const a = orderedIds.indexOf(lastSelectedRef.current);
          const b = orderedIds.indexOf(id);
          if (a !== -1 && b !== -1) {
            const [lo, hi] = a < b ? [a, b] : [b, a];
            orderedIds.slice(lo, hi + 1).forEach((i) => next.add(i));
            return next;
          }
        }
        if (next.has(id)) next.delete(id);
        else next.add(id);
        lastSelectedRef.current = id;
        return next;
      });
    },
    []
  );

  const selectAll = useCallback((ids: string[]) => {
    setSelectedIds(new Set(ids));
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
    lastSelectedRef.current = null;
  }, []);

  const setSort = useCallback((field: SortField) => {
    setSortBy((prev) => {
      if (prev === field) {
        setSortOrder((o) => (o === "asc" ? "desc" : "asc"));
        return prev;
      }
      setSortOrder("asc");
      return field;
    });
  }, []);

  const toggleStar = useCallback((id: string) => {
    setStarredIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const showInfoPanel = useCallback((itemId: string) => {
    setInfoPanelItemId(itemId);
    setInfoPanelOpen(true);
  }, []);

  const openModal = useCallback((type: ModalType, target?: ModalTarget) => {
    setModal(type);
    setModalTarget(target ?? null);
    if (type === "rename" && target) setRenameValue(target.name);
    if (type === "new-folder") setNewFolderName("Untitled folder");
  }, []);

  const closeModal = useCallback(() => {
    setModal("none");
    setModalTarget(null);
  }, []);

  return {
    section, setSection,
    currentFolderId, navigateTo,
    view, setView,
    sortBy, sortOrder, setSort,
    selectedIds, toggleSelect, selectAll, clearSelection,
    searchQuery, setSearchQuery,
    sidebarCollapsed, setSidebarCollapsed,
    infoPanelOpen, setInfoPanelOpen, infoPanelItemId, showInfoPanel,
    modal, modalTarget, openModal, closeModal,
    starredIds, toggleStar,
    newFolderName, setNewFolderName,
    renameValue, setRenameValue,
  };
}

export type ExplorerState = ReturnType<typeof useExplorerState>;
