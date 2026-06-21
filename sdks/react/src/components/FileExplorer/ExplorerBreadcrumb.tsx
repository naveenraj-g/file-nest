/**
 * FileExplorer/ExplorerBreadcrumb — clickable path trail.
 *
 * Shows "My Drive › Folder › Sub-folder". All segments except the
 * last are clickable and navigate to that folder.
 *
 * @module
 */

import React from "react";
import { useExplorer } from "./context.js";
import { IChevRight } from "./icons.js";

export function ExplorerBreadcrumb() {
  const { breadcrumbs, section, navigateTo } = useExplorer();

  const sectionLabel: Record<string, string> = {
    "my-drive": "My Drive",
    recent:     "Recent",
    starred:    "Starred",
    trash:      "Trash",
  };

  const label = sectionLabel[section] ?? "My Drive";

  return (
    <nav className="fn-ex-breadcrumb" aria-label="breadcrumb">
      <button
        type="button"
        className="fn-ex-crumb-btn"
        onClick={() => navigateTo(null)}
        style={breadcrumbs.length <= 1 ? { fontWeight: 500, fontSize: 16 } : {}}
      >
        {label}
      </button>

      {breadcrumbs.slice(1).map((crumb, i) => {
        const isLast = i === breadcrumbs.length - 2;
        return (
          <React.Fragment key={crumb.id ?? `crumb-${i}`}>
            <span className="fn-ex-crumb-sep" aria-hidden>
              <IChevRight size={16} />
            </span>
            <button
              type="button"
              className="fn-ex-crumb-btn"
              onClick={() => !isLast && navigateTo(crumb.id)}
              style={isLast ? { fontWeight: 500, fontSize: 16, cursor: "default" } : {}}
              aria-current={isLast ? "page" : undefined}
            >
              {crumb.name}
            </button>
          </React.Fragment>
        );
      })}
    </nav>
  );
}
