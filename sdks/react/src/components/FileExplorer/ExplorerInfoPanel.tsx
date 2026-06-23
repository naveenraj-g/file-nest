/**
 * FileExplorer/ExplorerInfoPanel — right-side details panel.
 *
 * Shows file/folder name, type thumbnail, metadata rows (size, type,
 * location, modified), tags, and quick actions (Download, Star).
 * Panel is toggled via the ℹ button in the top bar.
 *
 * @module
 */

import React from "react";
import { useExplorer } from "./context.js";
import { MIME_COLOR, getMimeGroup, MIME_LABEL, formatBytes, relativeDate } from "./utils.js";
import { FileTypeIcon } from "./icons.js";
import { IDownload, IStarFilled, IStar, IClose } from "./icons.js";

export function ExplorerInfoPanel() {
  const {
    infoPanelItemId, files, folders, setInfoPanelOpen,
    onFileDownload, starredIds, toggleStar,
  } = useExplorer();

  const file   = files.find((f) => f.id === infoPanelItemId);
  const folder = folders.find((f) => f.id === infoPanelItemId);
  const item   = file ?? folder;

  const isImage = file && getMimeGroup(file.contentType) === "image";
  const starred = infoPanelItemId ? starredIds.has(infoPanelItemId) : false;

  return (
    <aside className="fn-ex-info" aria-label="File details">
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: "#5f6368", textTransform: "uppercase", letterSpacing: "0.05em" }}>
          Details
        </span>
        <button
          type="button"
          className="fn-ex-icon-btn"
          style={{ width: 28, height: 28 }}
          onClick={() => setInfoPanelOpen(false)}
          aria-label="Close details"
        >
          <IClose size={16} />
        </button>
      </div>

      {!item ? (
        <div style={{ color: "#5f6368", fontSize: 13, textAlign: "center", marginTop: 24 }}>
          Select a file or folder to see its details.
        </div>
      ) : (
        <>
          {/* Thumbnail */}
          <div className="fn-ex-info-thumb">
            {isImage && file?.metadata?.thumbnailUrl ? (
              <img src={file.metadata.thumbnailUrl as string} alt={file.filename} />
            ) : file ? (
              <FileTypeIcon mimeType={file.contentType} size={64} />
            ) : (
              <span style={{ fontSize: 64 }}>📁</span>
            )}
          </div>

          {/* Name */}
          <div className="fn-ex-info-name">
            {file ? file.filename : folder!.name}
          </div>

          <div className="fn-ex-info-divider" />

          {/* Details rows */}
          {file && (
            <>
              <Row label="Type" value={MIME_LABEL[getMimeGroup(file.contentType)]} />
              <Row label="Size" value={formatBytes(file.sizeBytes)} />
              <Row label="Status" value={file.status} />
            </>
          )}
          <Row label="Location" value="My Drive" />
          <Row
            label="Modified"
            value={relativeDate((file?.updatedAt ?? folder?.createdAt) as string)}
          />
          <Row
            label="Created"
            value={relativeDate((file?.createdAt ?? folder?.createdAt) as string)}
          />

          {file?.tags && file.tags.length > 0 && (
            <>
              <div className="fn-ex-info-divider" />
              <div style={{ fontSize: 12, color: "#5f6368", fontWeight: 600, marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Tags
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {file.tags.map((tag) => (
                  <span
                    key={tag}
                    style={{ padding: "2px 10px", borderRadius: 12, background: "#e8f0fe", color: "#0b57d0", fontSize: 12 }}
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </>
          )}

          {file?.metadata && Object.keys(file.metadata).length > 0 && (
            <>
              <div className="fn-ex-info-divider" />
              <div style={{ fontSize: 12, color: "#5f6368", fontWeight: 600, marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Metadata
              </div>
              {Object.entries(file.metadata).map(([k, v]) => (
                <Row key={k} label={k} value={String(v)} />
              ))}
            </>
          )}

          <div className="fn-ex-info-divider" />

          {/* Action buttons */}
          <div className="fn-ex-info-action-row">
            {file && onFileDownload && (
              <button
                type="button"
                className="fn-ex-info-action"
                onClick={() => onFileDownload(file)}
              >
                <IDownload size={16} /> Download
              </button>
            )}
            {infoPanelItemId && (
              <button
                type="button"
                className="fn-ex-info-action"
                onClick={() => toggleStar(infoPanelItemId)}
              >
                {starred
                  ? <><IStarFilled size={16} style={{ color: "#FBBC04" }} /> Unstar</>
                  : <><IStar size={16} /> Star</>}
              </button>
            )}
          </div>
        </>
      )}
    </aside>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="fn-ex-info-row">
      <span className="fn-ex-info-label">{label}</span>
      <span className="fn-ex-info-value">{value}</span>
    </div>
  );
}
