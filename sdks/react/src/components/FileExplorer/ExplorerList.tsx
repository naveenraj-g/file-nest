/**
 * FileExplorer/ExplorerList — Drive-style table list view.
 *
 * Columns: checkbox · name · owner · modified · size · actions.
 * Sortable columns call setSort(); checkboxes support shift-range select.
 *
 * @module
 */

import React, { useCallback } from "react";
import type { FileRecord, Folder } from "@filenest/core";
import { useExplorer } from "./context.js";
import { ExplorerContextMenu } from "./ExplorerContextMenu.js";
import { ExplorerEmpty } from "./ExplorerEmpty.js";
import { MIME_COLOR, getMimeGroup, formatBytes, relativeDate, isFile } from "./utils.js";
import {
  IFolder, IStar, IStarFilled, ICheck, IMore,
  IChevDown, IChevUp, IDownload, IRename, ITrash,
} from "./icons.js";

function SortTh({
  field, label, width,
}: { field: string; label: string; width?: string }) {
  const { sortBy, sortOrder, setSort } = useExplorer();
  const active = sortBy === field;
  return (
    <th style={{ width }}>
      <button
        type="button"
        className={`fn-ex-sort-col-btn${active ? " active" : ""}`}
        onClick={() => setSort(field as never)}
      >
        {label}
        {active && (sortOrder === "asc" ? <IChevUp size={14} /> : <IChevDown size={14} />)}
      </button>
    </th>
  );
}

function Checkbox({ checked, onClick }: { checked: boolean; onClick: (e: React.MouseEvent) => void }) {
  return (
    <div
      role="checkbox"
      aria-checked={checked}
      className={`fn-ex-checkbox${checked ? " checked" : ""}`}
      onClick={onClick}
    >
      <ICheck size={12} />
    </div>
  );
}

function FolderRow({ folder, allIds }: { folder: Folder; allIds: string[] }) {
  const { selectedIds, toggleSelect, navigateTo, onFolderClick, starredIds, toggleStar, openModal } = useExplorer();
  const selected = selectedIds.has(folder.id);
  const starred  = starredIds.has(folder.id);

  const handleRowClick = useCallback((e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest(".fn-ex-row-actions, .fn-ex-cb-wrap, .fn-ex-star-btn")) return;
    if (e.detail === 2) { navigateTo(folder.id); onFolderClick?.(folder); return; }
    toggleSelect(folder.id, e.shiftKey, allIds);
  }, [folder, toggleSelect, navigateTo, onFolderClick, allIds]);

  return (
    <ExplorerContextMenu item={folder}>
      <tr
        role="option"
        aria-selected={selected}
        className={`fn-ex-list-row${selected ? " selected" : ""}`}
        onClick={handleRowClick}
      >
        <td style={{ width: 40 }}>
          <div className="fn-ex-cb-wrap">
            <Checkbox
              checked={selected}
              onClick={(e) => { e.stopPropagation(); toggleSelect(folder.id, e.shiftKey, allIds); }}
            />
          </div>
        </td>
        <td>
          <div className="fn-ex-list-name">
            <IFolder size={20} style={{ color: "#FBBC04", flexShrink: 0 }} />
            <span className="fn-ex-list-name-text">{folder.name}</span>
          </div>
        </td>
        <td style={{ color: "#5f6368", fontSize: 13 }}>me</td>
        <td style={{ color: "#5f6368", fontSize: 13 }}>{relativeDate(folder.createdAt)}</td>
        <td style={{ color: "#5f6368", fontSize: 13 }}>—</td>
        <td style={{ width: 120 }}>
          <div className="fn-ex-row-actions">
            <button
              type="button"
              className="fn-ex-icon-btn"
              style={{ width: 32, height: 32 }}
              onClick={(e) => { e.stopPropagation(); toggleStar(folder.id); }}
              aria-label={starred ? "Unstar" : "Star"}
            >
              {starred ? <IStarFilled size={16} style={{ color: "#FBBC04" }} /> : <IStar size={16} />}
            </button>
            <button
              type="button"
              className="fn-ex-icon-btn"
              style={{ width: 32, height: 32 }}
              onClick={(e) => { e.stopPropagation(); openModal("delete", { type: "folder", id: folder.id, name: folder.name, item: folder }); }}
              aria-label="More"
            >
              <IMore size={16} />
            </button>
          </div>
        </td>
      </tr>
    </ExplorerContextMenu>
  );
}

function FileRow({ file, allIds }: { file: FileRecord; allIds: string[] }) {
  const { selectedIds, toggleSelect, onFileClick, onFileDownload, starredIds, toggleStar, openModal } = useExplorer();
  const selected = selectedIds.has(file.id);
  const starred  = starredIds.has(file.id);
  const group    = getMimeGroup(file.contentType);
  const color    = MIME_COLOR[group];

  const handleRowClick = useCallback((e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest(".fn-ex-row-actions, .fn-ex-cb-wrap, .fn-ex-star-btn")) return;
    if (e.detail === 2) { onFileClick?.(file); return; }
    toggleSelect(file.id, e.shiftKey, allIds);
  }, [file, toggleSelect, onFileClick, allIds]);

  return (
    <ExplorerContextMenu item={file}>
      <tr
        role="option"
        aria-selected={selected}
        className={`fn-ex-list-row${selected ? " selected" : ""}`}
        onClick={handleRowClick}
      >
        <td style={{ width: 40 }}>
          <div className="fn-ex-cb-wrap">
            <Checkbox
              checked={selected}
              onClick={(e) => { e.stopPropagation(); toggleSelect(file.id, e.shiftKey, allIds); }}
            />
          </div>
        </td>
        <td>
          <div className="fn-ex-list-name">
            <div style={{
              width: 20, height: 20, borderRadius: 3, background: color, flexShrink: 0,
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "#fff", fontSize: 8, fontWeight: 700, letterSpacing: -0.3,
            }}>
              {group === "pdf" ? "PDF" : group.slice(0, 1).toUpperCase()}
            </div>
            <span className="fn-ex-list-name-text" title={file.filename}>{file.filename}</span>
          </div>
        </td>
        <td style={{ color: "#5f6368", fontSize: 13 }}>me</td>
        <td style={{ color: "#5f6368", fontSize: 13 }}>{relativeDate(file.updatedAt ?? file.createdAt)}</td>
        <td style={{ color: "#5f6368", fontSize: 13 }}>{formatBytes(file.sizeBytes)}</td>
        <td style={{ width: 120 }}>
          <div className="fn-ex-row-actions">
            <button
              type="button"
              className="fn-ex-icon-btn"
              style={{ width: 32, height: 32 }}
              onClick={(e) => { e.stopPropagation(); toggleStar(file.id); }}
              aria-label={starred ? "Unstar" : "Star"}
            >
              {starred ? <IStarFilled size={16} style={{ color: "#FBBC04" }} /> : <IStar size={16} />}
            </button>
            <button
              type="button"
              className="fn-ex-icon-btn"
              style={{ width: 32, height: 32 }}
              onClick={(e) => {
                e.stopPropagation();
                openModal("delete", { type: "file", id: file.id, name: file.filename, item: file });
              }}
              aria-label="More"
            >
              <IMore size={16} />
            </button>
          </div>
        </td>
      </tr>
    </ExplorerContextMenu>
  );
}

export function ExplorerList() {
  const { files, folders, isLoading, isFetchingMore, hasMore, sentinelRef, searchQuery, selectedIds, selectAll, clearSelection } = useExplorer();

  const allIds = [...folders.map((f) => f.id), ...files.map((f) => f.id)];
  const allSelected = allIds.length > 0 && allIds.every((id) => selectedIds.has(id));
  const isEmpty = !isLoading && files.length === 0 && folders.length === 0;

  return (
    <div className="fn-ex-content">
      {isEmpty ? (
        <ExplorerEmpty isSearch={!!searchQuery} />
      ) : (
        <table className="fn-ex-list" role="listbox" aria-multiselectable>
          <thead>
            <tr>
              <th style={{ width: 40 }}>
                <div
                  role="checkbox"
                  aria-checked={allSelected}
                  className={`fn-ex-checkbox${allSelected ? " checked" : ""}`}
                  style={{ opacity: allIds.length ? 1 : 0 }}
                  onClick={() => allSelected ? clearSelection() : selectAll(allIds)}
                >
                  <ICheck size={12} />
                </div>
              </th>
              <SortTh field="name"     label="Name" />
              <th style={{ width: 140, fontSize: 12, color: "#5f6368", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}>Owner</th>
              <SortTh field="modified" label="Last modified" width="160px" />
              <SortTh field="size"     label="File size"     width="110px" />
              <th style={{ width: 120 }} />
            </tr>
          </thead>
          <tbody>
            {folders.map((f) => <FolderRow key={f.id} folder={f} allIds={allIds} />)}
            {files.map((f)   => <FileRow   key={f.id} file={f}   allIds={allIds} />)}
          </tbody>
        </table>
      )}

      {/* Loading skeleton */}
      {isLoading && !files.length && (
        <div style={{ padding: "0 24px" }}>
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} style={{
              height: 40, borderRadius: 6, background: "#f0f4f9", marginBottom: 4,
              animation: `fn-ex-pulse 1.4s ease ${i * 0.07}s infinite`,
            }} />
          ))}
        </div>
      )}

      {/* Infinite scroll sentinel + spinner */}
      <div ref={sentinelRef} className="fn-ex-sentinel" />
      {isFetchingMore && (
        <div className="fn-ex-spinner-row">
          <div className="fn-ex-spinner" />
        </div>
      )}
    </div>
  );
}
