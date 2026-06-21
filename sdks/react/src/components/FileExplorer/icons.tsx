/**
 * FileExplorer/icons — inline SVG icon set for the explorer UI.
 *
 * All icons share a `size` prop (default 18). Designed to match
 * Material Design / Google Drive aesthetics.
 *
 * @module
 */

import React from "react";

type P = { size?: number; className?: string; style?: React.CSSProperties };

const svg = (path: string, vb = "0 0 24 24") =>
  ({ size = 18, className, style }: P) => (
    <svg
      width={size}
      height={size}
      viewBox={vb}
      fill="currentColor"
      className={className}
      style={style}
      aria-hidden
    >
      <path d={path} />
    </svg>
  );

export const IGrid        = svg("M3 3h7v7H3zm0 11h7v7H3zm11-11h7v7h-7zm0 11h7v7h-7z");
export const IList        = svg("M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7v2zM7 7v2h14V7H7z");
export const ISearch      = svg("M15.5 14h-.79l-.28-.27A6.47 6.47 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z");
export const IClose       = svg("M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z");
export const IChevRight   = svg("M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z");
export const IChevDown    = svg("M16.59 8.59L12 13.17 7.41 8.59 6 10l6 6 6-6z");
export const IChevUp      = svg("M12 8l-6 6 1.41 1.41L12 10.83l4.59 4.58L18 14z");
export const IStar        = svg("M22 9.24l-7.19-.62L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21 12 17.27 18.18 21l-1.63-7.03L22 9.24zm-10 6.31L8.24 17.5l1.07-4.61L5.66 9.9l4.73-.41L12 5.37l1.61 4.12 4.73.41-3.65 2.99 1.07 4.61L12 15.55z");
export const IStarFilled  = svg("M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z");
export const ITrash       = svg("M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z");
export const IDownload    = svg("M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z");
export const IUpload      = svg("M9 16h6v-6h4l-7-7-7 7h4zm-4 2h14v2H5z");
export const INewFolder   = svg("M20 6h-8l-2-2H4c-1.11 0-1.99.89-1.99 2L2 18c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2zm-1 8h-3v3h-2v-3h-3v-2h3V9h2v3h3v2z");
export const ISort        = svg("M3 18h6v-2H3v2zM3 6v2h18V6H3zm0 7h12v-2H3v2z");
export const IInfo        = svg("M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z");
export const IMore        = svg("M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z");
export const IMove        = svg("M20 6h-2.18c.07-.44.18-.86.18-1 0-2.21-1.79-4-4-4s-4 1.79-4 4c0 .14.11.56.18 1H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-6-3c1.1 0 2 .9 2 2 0 .14-.11.56-.18 1h-3.64C12.11 5.56 12 5.14 12 5c0-1.1.9-2 2-2zm4 17H8V8h2v2h8V8h2v12z");
export const IRename      = svg("M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z");
export const ILink        = svg("M3.9 12c0-1.71 1.39-3.1 3.1-3.1h4V7H7c-2.76 0-5 2.24-5 5s2.24 5 5 5h4v-1.9H7c-1.71 0-3.1-1.39-3.1-3.1zM8 13h8v-2H8v2zm9-6h-4v1.9h4c1.71 0 3.1 1.39 3.1 3.1s-1.39 3.1-3.1 3.1h-4V17h4c2.76 0 5-2.24 5-5s-2.24-5-5-5z");
export const IDriveCloud  = svg("M10.35 17l1.08-4H7L12 3l5 10h-4.46L13.65 17H10.35zm-.35 2v2h4v-2h-4z");
export const IRecent      = svg("M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42A8.954 8.954 0 0 0 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z");
export const IStarred     = IStarFilled;
export const IStorage     = svg("M2 20h20v-4H2v4zm2-3h2v2H4v-2zM2 4v4h20V4H2zm4 3H4V5h2v2zm-4 7h20v-4H2v4zm2-3h2v2H4v-2z");
export const IShared      = svg("M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z");
export const ICheck       = svg("M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z");
export const IPlus        = svg("M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z");
export const IFolder      = svg("M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z");
export const IFile        = svg("M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z");

const _MIME_COLOR: Record<string, string> = {
  folder: "#FBBC04", image: "#4285F4", video: "#AF5CF7", audio: "#FF6D00",
  pdf: "#EA4335", spreadsheet: "#0F9D58", presentation: "#F4B400",
  document: "#4285F4", text: "#5F6368", archive: "#78909C", code: "#5C6BC0", file: "#80868B",
};

function _group(mime: string): string {
  if (mime.startsWith("image/")) return "image";
  if (mime.startsWith("video/")) return "video";
  if (mime.startsWith("audio/")) return "audio";
  if (mime === "application/pdf") return "pdf";
  if (mime.includes("spreadsheet") || mime === "text/csv") return "spreadsheet";
  if (mime.includes("presentation")) return "presentation";
  if (mime.includes("word")) return "document";
  if (mime.startsWith("text/")) return "text";
  if (mime.includes("zip") || mime.includes("tar")) return "archive";
  return "file";
}

const _SHORT: Record<string, string> = {
  pdf: "PDF", spreadsheet: "XLS", presentation: "PPT", document: "DOC",
  image: "IMG", video: "VID", audio: "AUD", archive: "ZIP", code: "COD",
};

export function FileTypeIcon({ mimeType, size = 40 }: { mimeType: string; size?: number }) {
  const group = _group(mimeType);
  return (
    <div
      aria-hidden
      style={{
        width: size, height: size, borderRadius: 6,
        background: _MIME_COLOR[group] ?? "#80868B",
        display: "flex", alignItems: "center", justifyContent: "center",
        flexShrink: 0, fontSize: size * 0.28, fontWeight: 700,
        color: "#fff", letterSpacing: -0.5, fontFamily: "monospace",
      }}
    >
      {(_SHORT[group] ?? group.slice(0, 3)).toUpperCase()}
    </div>
  );
}
