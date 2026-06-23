/**
 * FileExplorer/ExplorerGrid — Google Drive-style card grid.
 *
 * Renders folders first (compact chips) then files (tall cards with thumbnail).
 * Each item is wrapped in ExplorerContextMenu for right-click actions.
 * Checkboxes appear on hover / when any item is selected.
 * Shift+click performs range selection.
 *
 * @module
 */

import React, { useCallback } from "react";
import type { FileRecord, Folder } from "@filenest/core";
import { useExplorer } from "./context.js";
import { ExplorerContextMenu } from "./ExplorerContextMenu.js";
import { ExplorerEmpty } from "./ExplorerEmpty.js";
import { MIME_COLOR, getMimeGroup, formatBytes, relativeDate, isFile } from "./utils.js";
import { IFolder, IStar, IStarFilled, ICheck, IMore } from "./icons.js";

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

function StarBtn({ id }: { id: string }) {
  const { starredIds, toggleStar } = useExplorer();
  const starred = starredIds.has(id);
  return (
    <button
      type="button"
      className={`fn-ex-star-btn${starred ? " starred" : ""}`}
      onClick={(e) => { e.stopPropagation(); toggleStar(id); }}
      aria-label={starred ? "Remove from Starred" : "Add to Starred"}
    >
      {starred ? <IStarFilled size={16} /> : <IStar size={16} />}
    </button>
  );
}

function FolderCard({ folder, allIds }: { folder: Folder; allIds: string[] }) {
  const { selectedIds, toggleSelect, navigateTo, onFolderClick } = useExplorer();
  const selected = selectedIds.has(folder.id);

  const handleClick = useCallback((e: React.MouseEvent) => {
    if (e.detail === 2) {
      navigateTo(folder.id);
      onFolderClick?.(folder);
    } else {
      toggleSelect(folder.id, e.shiftKey, allIds);
    }
  }, [folder, toggleSelect, navigateTo, onFolderClick, allIds]);

  return (
    <ExplorerContextMenu item={folder}>
      <div
        role="option"
        aria-selected={selected}
        className={`fn-ex-grid-folder${selected ? " selected" : ""}`}
        onClick={handleClick}
      >
        <div className="fn-ex-grid-check-wrap">
          <Checkbox
            checked={selected}
            onClick={(e) => { e.stopPropagation(); toggleSelect(folder.id, e.shiftKey, allIds); }}
          />
        </div>
        <IFolder size={20} style={{ color: "#FBBC04", flexShrink: 0 }} />
        <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontSize: 13 }}>
          {folder.name}
        </span>
        <StarBtn id={folder.id} />
      </div>
    </ExplorerContextMenu>
  );
}

function FileCard({ file, allIds }: { file: FileRecord; allIds: string[] }) {
  const { selectedIds, toggleSelect, onFileClick, showInfoPanel } = useExplorer();
  const selected = selectedIds.has(file.id);
  const group = getMimeGroup(file.contentType);
  const color = MIME_COLOR[group];
  const isImage = group === "image";

  const handleClick = useCallback((e: React.MouseEvent) => {
    if (e.detail === 2) {
      onFileClick?.(file);
    } else {
      toggleSelect(file.id, e.shiftKey, allIds);
    }
  }, [file, toggleSelect, onFileClick, allIds]);

  return (
    <ExplorerContextMenu item={file}>
      <div
        role="option"
        aria-selected={selected}
        className={`fn-ex-grid-item${selected ? " selected" : ""}`}
        onClick={handleClick}
      >
        {/* Thumbnail */}
        <div className="fn-ex-grid-thumb">
          {isImage && file.metadata?.thumbnailUrl ? (
            <img src={file.metadata.thumbnailUrl as string} alt={file.filename} />
          ) : (
            <div style={{
              width: 56, height: 56, borderRadius: 8,
              background: color, display: "flex", alignItems: "center", justifyContent: "center",
              color: "#fff", fontWeight: 700, fontSize: 18, letterSpacing: -0.5,
            }}>
              {group === "pdf" ? "PDF"
               : group === "spreadsheet" ? "XLS"
               : group === "presentation" ? "PPT"
               : group === "document" ? "DOC"
               : group.slice(0, 3).toUpperCase()}
            </div>
          )}
        </div>

        {/* Hover actions */}
        <div className="fn-ex-grid-actions">
          <StarBtn id={file.id} />
          <button
            type="button"
            className="fn-ex-star-btn"
            onClick={(e) => { e.stopPropagation(); showInfoPanel(file.id); }}
            aria-label="More options"
          >
            <IMore size={16} />
          </button>
        </div>

        {/* Checkbox */}
        <div className="fn-ex-grid-check-wrap">
          <Checkbox
            checked={selected}
            onClick={(e) => { e.stopPropagation(); toggleSelect(file.id, e.shiftKey, allIds); }}
          />
        </div>

        {/* Name + size */}
        <div className="fn-ex-grid-info">
          <div className="fn-ex-grid-name" title={file.filename}>
            {file.filename}
          </div>
        </div>
        <div style={{ padding: "0 10px 8px", fontSize: 11, color: "#5f6368" }}>
          {relativeDate(file.createdAt)} · {formatBytes(file.sizeBytes)}
        </div>
      </div>
    </ExplorerContextMenu>
  );
}

export function ExplorerGrid() {
  const { files, folders, isLoading, hasMore, isFetchingMore, sentinelRef, searchQuery } = useExplorer();

  const allIds = [
    ...folders.map((f) => f.id),
    ...files.map((f) => f.id),
  ];

  const isEmpty = !isLoading && files.length === 0 && folders.length === 0;

  return (
    <div className="fn-ex-content" role="listbox" aria-multiselectable>
      {/* Folders */}
      {folders.length > 0 && !searchQuery && (
        <>
          <div className="fn-ex-group-label">Folders</div>
          <div className="fn-ex-grid">
            {folders.map((f) => (
              <FolderCard key={f.id} folder={f} allIds={allIds} />
            ))}
          </div>
        </>
      )}

      {/* Files */}
      {files.length > 0 && (
        <>
          {folders.length > 0 && !searchQuery && (
            <div className="fn-ex-group-label" style={{ marginTop: 8 }}>Files</div>
          )}
          <div className="fn-ex-grid">
            {files.map((f) => (
              <FileCard key={f.id} file={f} allIds={allIds} />
            ))}
          </div>
        </>
      )}

      {/* Empty state */}
      {isEmpty && <ExplorerEmpty isSearch={!!searchQuery} />}

      {/* Loading skeleton on first load */}
      {isLoading && !files.length && (
        <div className="fn-ex-grid" style={{ padding: "4px 24px 16px" }}>
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} style={{
              borderRadius: 12, background: "#f0f4f9",
              height: 168, animation: `fn-ex-pulse 1.4s ease ${(i % 4) * 0.1}s infinite`,
            }} />
          ))}
          <style>{`
            @keyframes fn-ex-pulse {
              0%,100% { opacity: 1 } 50% { opacity: 0.55 }
            }
          `}</style>
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
