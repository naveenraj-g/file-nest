"use client";

/**
 * /file-explorer — Full Google Drive-inspired FileExplorer demo.
 *
 * Uses the rebuilt @filenest/react FileExplorer: infinite scroll,
 * grid/list views, right-click context menu, selection toolbar,
 * drag-and-drop folders, info panel, and keyboard shortcuts.
 */

import { FileExplorer } from "@filenest/react";
import { useState } from "react";

export default function FileExplorerPage() {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 0px)", gap: 0 }}>
      {/* Page header — above the explorer */}
      <div
        style={{
          padding: "16px 24px 12px",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexShrink: 0,
          background: "var(--surface)",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <h1 style={{ margin: 0, fontSize: 20, fontWeight: 600 }}>FileExplorer</h1>
            <span className="badge badge-green">@filenest/react</span>
          </div>
          <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--text-muted)" }}>
            Google Drive-inspired browser — infinite scroll · grid/list · multi-select ·
            context menu · info panel · keyboard shortcuts
          </p>
        </div>
        {selectedIds.length > 0 && (
          <span className="badge badge-blue">{selectedIds.length} selected</span>
        )}
      </div>

      {/* Feature badges */}
      <div
        style={{
          display: "flex",
          gap: 8,
          padding: "8px 24px",
          flexWrap: "wrap",
          borderBottom: "1px solid var(--border)",
          flexShrink: 0,
        }}
      >
        {[
          "Infinite scroll (useInfiniteQuery)",
          "Grid + List views",
          "Shift/Ctrl multi-select",
          "Right-click context menu",
          "Keyboard shortcuts (n, Del, ⌘A)",
          "Details info panel",
          "Star / Unstar",
          "New folder · Rename · Delete · Move",
        ].map((f) => (
          <span key={f} className="badge badge-gray" style={{ fontSize: 11 }}>
            {f}
          </span>
        ))}
      </div>

      {/* The explorer fills all remaining space */}
      <div style={{ flex: 1, overflow: "hidden" }}>
        <FileExplorer
          rootFolderId={null}
          defaultView="grid"
          defaultSort="name"
          height="100%"
          onSelectionChange={setSelectedIds}
          onFileClick={(file) => console.log("[explorer] open file:", file.id)}
          onFolderClick={(folder) => console.log("[explorer] open folder:", folder.id)}
          onFileDownload={(file) => {
            console.log("[explorer] download:", file.filename);
            window.open(`/v1/files/${file.id}/download`, "_blank");
          }}
          onFileDelete={async (file) => {
            console.log("[explorer] delete file:", file.id);
          }}
          onFolderDelete={async (folder) => {
            console.log("[explorer] delete folder:", folder.id);
          }}
          onFolderCreate={async (name, parentId) => {
            console.log("[explorer] create folder:", name, "in", parentId);
          }}
          onFileRename={async (id, name) => {
            console.log("[explorer] rename file:", id, "→", name);
          }}
          onFolderRename={async (id, name) => {
            console.log("[explorer] rename folder:", id, "→", name);
          }}
          onFileMove={async (fileId, targetFolderId) => {
            console.log("[explorer] move file:", fileId, "→", targetFolderId);
          }}
          onFolderMove={async (folderId, targetFolderId) => {
            console.log("[explorer] move folder:", folderId, "→", targetFolderId);
          }}
        />
      </div>

      {/* Keyboard shortcuts reference */}
      <div
        style={{
          padding: "6px 24px",
          borderTop: "1px solid var(--border)",
          background: "var(--surface)",
          display: "flex",
          gap: 16,
          fontSize: 11,
          color: "var(--text-muted)",
          flexShrink: 0,
          flexWrap: "wrap",
        }}
      >
        {[
          ["n", "New folder"],
          ["Del", "Move to trash"],
          ["⌘A", "Select all"],
          ["Esc", "Clear selection"],
          ["Double-click", "Open / navigate"],
          ["Right-click", "Context menu"],
        ].map(([key, label]) => (
          <span key={key}>
            <kbd
              style={{
                padding: "1px 5px", borderRadius: 3,
                border: "1px solid var(--border)", fontSize: 10,
                background: "var(--bg)", fontFamily: "monospace",
              }}
            >
              {key}
            </kbd>{" "}
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}
