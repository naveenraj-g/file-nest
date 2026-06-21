/**
 * FileExplorer/utils — pure helpers shared across all explorer sub-components.
 * @module
 */

import type { FileRecord, Folder } from "@filenest/core";

export function formatBytes(b: number): string {
  if (!b) return "—";
  if (b < 1024) return `${b} B`;
  if (b < 1024 ** 2) return `${(b / 1024).toFixed(1)} KB`;
  if (b < 1024 ** 3) return `${(b / 1024 ** 2).toFixed(1)} MB`;
  return `${(b / 1024 ** 3).toFixed(2)} GB`;
}

export function relativeDate(d: string | Date): string {
  const date = typeof d === "string" ? new Date(d) : d;
  const diff = (Date.now() - date.getTime()) / 1000;
  if (diff < 60) return "Just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 86400 * 2) return "Yesterday";
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)} days ago`;
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: diff > 86400 * 365 ? "numeric" : undefined,
  });
}

export type MimeGroup =
  | "folder"
  | "image"
  | "video"
  | "audio"
  | "pdf"
  | "spreadsheet"
  | "presentation"
  | "document"
  | "text"
  | "archive"
  | "code"
  | "file";

export function getMimeGroup(mimeType: string): MimeGroup {
  if (mimeType.startsWith("image/")) return "image";
  if (mimeType.startsWith("video/")) return "video";
  if (mimeType.startsWith("audio/")) return "audio";
  if (mimeType === "application/pdf") return "pdf";
  if (mimeType.includes("spreadsheet") || mimeType === "text/csv") return "spreadsheet";
  if (mimeType.includes("presentation") || mimeType.includes("powerpoint")) return "presentation";
  if (mimeType.includes("word") || mimeType === "application/msword") return "document";
  if (["text/javascript","text/typescript","application/json","text/html","text/css"].includes(mimeType))
    return "code";
  if (mimeType.startsWith("text/")) return "text";
  if (mimeType.includes("zip") || mimeType.includes("tar") || mimeType.includes("gzip"))
    return "archive";
  return "file";
}

export const MIME_COLOR: Record<MimeGroup, string> = {
  folder:       "#FBBC04",
  image:        "#4285F4",
  video:        "#AF5CF7",
  audio:        "#FF6D00",
  pdf:          "#EA4335",
  spreadsheet:  "#0F9D58",
  presentation: "#F4B400",
  document:     "#4285F4",
  text:         "#5F6368",
  archive:      "#78909C",
  code:         "#5C6BC0",
  file:         "#80868B",
};

export const MIME_LABEL: Record<MimeGroup, string> = {
  folder:       "Folder",
  image:        "Image",
  video:        "Video",
  audio:        "Audio",
  pdf:          "PDF",
  spreadsheet:  "Spreadsheet",
  presentation: "Presentation",
  document:     "Document",
  text:         "Text",
  archive:      "Archive",
  code:         "Code",
  file:         "File",
};

export function isFile(item: FileRecord | Folder): item is FileRecord {
  return "filename" in item;
}

export function itemId(item: FileRecord | Folder): string {
  return item.id;
}

export function itemName(item: FileRecord | Folder): string {
  return isFile(item) ? item.filename : item.name;
}
