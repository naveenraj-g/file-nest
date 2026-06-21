/**
 * FileExplorer/ExplorerTopBar — search bar + action toolbar.
 *
 * Normal mode: search · New▾ · grid/list toggle · sort▾ · ℹ
 * Selection mode: replaces entire bar with count + bulk action buttons.
 *
 * @module
 */

import React, { useRef } from "react";
import * as DD from "@radix-ui/react-dropdown-menu";
import { useExplorer } from "./context.js";
import {
  ISearch, IClose, IGrid, IList, ISort, IInfo, INewFolder, IUpload,
  IPlus, IDownload, ITrash, IMove, IStar, IStarFilled, IRename,
  ICheck, IChevDown,
} from "./icons.js";

export function ExplorerTopBar() {
  const {
    selectedIds, clearSelection, view, setView, sortBy, sortOrder, setSort,
    searchQuery, setSearchQuery, infoPanelOpen, setInfoPanelOpen,
    sidebarCollapsed, setSidebarCollapsed, openModal,
    files, onFileDownload, onFileDelete, starredIds, toggleStar,
  } = useExplorer();

  const count = selectedIds.size;
  const fileInputRef = useRef<HTMLInputElement>(null);

  const selectedFiles = files.filter((f) => selectedIds.has(f.id));
  const allStarred = selectedFiles.length > 0 && selectedFiles.every((f) => starredIds.has(f.id));

  if (count > 0) {
    return (
      <div className="fn-ex-topbar">
        <button
          type="button"
          className="fn-ex-icon-btn"
          onClick={clearSelection}
          aria-label="Clear selection"
        >
          <IClose size={20} />
        </button>
        <div className="fn-ex-sel-bar">
          <span className="fn-ex-sel-count">{count} selected</span>
          {selectedFiles.length > 0 && onFileDownload && (
            <button
              type="button"
              className="fn-ex-sel-action"
              onClick={() => selectedFiles.forEach((f) => onFileDownload(f))}
            >
              <IDownload size={16} /> Download
            </button>
          )}
          <button
            type="button"
            className="fn-ex-sel-action"
            onClick={() => toggleStar(Array.from(selectedIds)[0])}
          >
            {allStarred
              ? <><IStarFilled size={16} style={{ color: "#FBBC04" }} /> Unstar</>
              : <><IStar size={16} /> Add to Starred</>}
          </button>
          <button
            type="button"
            className="fn-ex-sel-action"
            onClick={() => {
              const id = Array.from(selectedIds)[0];
              const f = files.find((x) => x.id === id);
              if (f) openModal("move", { type: "file", id, name: f.filename, item: f });
            }}
          >
            <IMove size={16} /> Move to
          </button>
          {count === 1 && (
            <button
              type="button"
              className="fn-ex-sel-action"
              onClick={() => {
                const id = Array.from(selectedIds)[0];
                const f = files.find((x) => x.id === id);
                if (f) openModal("rename", { type: "file", id, name: f.filename, item: f });
              }}
            >
              <IRename size={16} /> Rename
            </button>
          )}
          <button
            type="button"
            className="fn-ex-sel-action danger"
            onClick={() => {
              const id = Array.from(selectedIds)[0];
              const f = files.find((x) => x.id === id);
              if (f) openModal("delete", { type: "file", id, name: f.filename, item: f });
            }}
          >
            <ITrash size={16} /> Move to trash
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fn-ex-topbar">
      {/* Sidebar toggle */}
      <button
        type="button"
        className="fn-ex-icon-btn"
        onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
        aria-label="Toggle sidebar"
        style={{ flexShrink: 0 }}
      >
        <svg width={20} height={20} viewBox="0 0 24 24" fill="currentColor" aria-hidden>
          <path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/>
        </svg>
      </button>

      {/* Search */}
      <div className="fn-ex-search-wrap">
        <span className="fn-ex-search-icon"><ISearch size={20} /></span>
        <input
          type="search"
          className="fn-ex-search"
          placeholder="Search in Drive"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          aria-label="Search files"
        />
        {searchQuery && (
          <button
            type="button"
            className="fn-ex-icon-btn"
            style={{ position: "absolute", right: 4, top: "50%", transform: "translateY(-50%)", width: 32, height: 32 }}
            onClick={() => setSearchQuery("")}
          >
            <IClose size={16} />
          </button>
        )}
      </div>

      {/* New button */}
      <input ref={fileInputRef} type="file" multiple style={{ display: "none" }} aria-hidden />
      <DD.Root>
        <DD.Trigger asChild>
          <button type="button" className="fn-ex-new-btn">
            <IPlus size={18} /> New <IChevDown size={14} />
          </button>
        </DD.Trigger>
        <DD.Portal>
          <DD.Content className="fn-ex-dropdown-content" align="start">
            <DD.Item
              className="fn-ex-dropdown-item"
              onSelect={() => fileInputRef.current?.click()}
            >
              <IUpload size={16} className="icon" /> Upload files
            </DD.Item>
            <DD.Separator className="fn-ex-dropdown-sep" />
            <DD.Item className="fn-ex-dropdown-item" onSelect={() => openModal("new-folder")}>
              <INewFolder size={16} className="icon" /> New folder
            </DD.Item>
          </DD.Content>
        </DD.Portal>
      </DD.Root>

      {/* View toggle */}
      <div style={{ display: "flex", gap: 2, marginLeft: 4 }}>
        <button
          type="button"
          className={`fn-ex-icon-btn${view === "grid" ? " active" : ""}`}
          onClick={() => setView("grid")}
          aria-label="Grid view"
          aria-pressed={view === "grid"}
        >
          <IGrid size={20} />
        </button>
        <button
          type="button"
          className={`fn-ex-icon-btn${view === "list" ? " active" : ""}`}
          onClick={() => setView("list")}
          aria-label="List view"
          aria-pressed={view === "list"}
        >
          <IList size={20} />
        </button>
      </div>

      {/* Sort dropdown */}
      <DD.Root>
        <DD.Trigger asChild>
          <button type="button" className="fn-ex-icon-btn" aria-label="Sort options">
            <ISort size={20} />
          </button>
        </DD.Trigger>
        <DD.Portal>
          <DD.Content className="fn-ex-dropdown-content" align="end">
            <div className="fn-ex-dropdown-label">Sort by</div>
            {(["name", "modified", "size", "kind"] as const).map((field) => (
              <DD.Item
                key={field}
                className="fn-ex-dropdown-item"
                onSelect={() => setSort(field)}
              >
                {{ name: "Name", modified: "Last modified", size: "File size", kind: "File type" }[field]}
                {sortBy === field && (
                  <span className="fn-ex-dropdown-check">
                    {sortOrder === "asc" ? "↑" : "↓"}
                  </span>
                )}
              </DD.Item>
            ))}
          </DD.Content>
        </DD.Portal>
      </DD.Root>

      {/* Info panel toggle */}
      <button
        type="button"
        className={`fn-ex-icon-btn${infoPanelOpen ? " active" : ""}`}
        onClick={() => setInfoPanelOpen(!infoPanelOpen)}
        aria-label="Toggle details panel"
        aria-pressed={infoPanelOpen}
      >
        <IInfo size={20} />
      </button>
    </div>
  );
}
