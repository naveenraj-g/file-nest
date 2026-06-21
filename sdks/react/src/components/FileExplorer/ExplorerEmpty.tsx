/**
 * FileExplorer/ExplorerEmpty — empty-state views per section.
 * @module
 */

import React from "react";
import { useExplorer } from "./context.js";

export function ExplorerEmpty({ isSearch }: { isSearch: boolean }) {
  const { section, searchQuery, openModal } = useExplorer();

  if (isSearch) {
    return (
      <div className="fn-ex-empty">
        <div className="fn-ex-empty-icon">🔍</div>
        <div className="fn-ex-empty-title">No results for "{searchQuery}"</div>
        <div className="fn-ex-empty-desc">Try different keywords or check for typos.</div>
      </div>
    );
  }

  const configs: Record<string, { icon: string; title: string; desc: string; cta?: string }> = {
    "my-drive": {
      icon: "☁️",
      title: "Your Drive is empty",
      desc: "Upload files to get started, or create a folder to organize your work.",
      cta: "Upload files",
    },
    recent: {
      icon: "🕐",
      title: "No recently viewed files",
      desc: "Files you open will appear here.",
    },
    starred: {
      icon: "⭐",
      title: "No starred items",
      desc: "Add stars to things that you want to easily find later.",
    },
    trash: {
      icon: "🗑️",
      title: "Trash is empty",
      desc: "Items moved to Trash will be automatically deleted after 30 days.",
    },
  };

  const cfg = configs[section] ?? configs["my-drive"];

  return (
    <div className="fn-ex-empty">
      <div className="fn-ex-empty-icon">{cfg.icon}</div>
      <div className="fn-ex-empty-title">{cfg.title}</div>
      <div className="fn-ex-empty-desc">{cfg.desc}</div>
      {cfg.cta && (
        <button
          type="button"
          style={{
            marginTop: 8,
            padding: "10px 24px",
            borderRadius: 20,
            border: "1px solid #c4c7c5",
            background: "#fff",
            fontSize: 14,
            fontWeight: 500,
            cursor: "pointer",
            color: "#0b57d0",
          }}
          onClick={() => openModal("new-folder")}
        >
          {cfg.cta}
        </button>
      )}
    </div>
  );
}
