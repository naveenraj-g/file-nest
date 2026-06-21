/**
 * FileExplorer/ExplorerSidebar — left navigation pane.
 *
 * Sections: My Drive, Recent, Starred, Trash (mirrors Google Drive).
 * Bottom: storage usage bar (reads from project metadata when available).
 *
 * @module
 */

import React from "react";
import { useExplorer } from "./context.js";
import type { SectionId } from "./useExplorerState.js";
import {
  IDriveCloud, IRecent, IStarFilled, ITrash, IStorage,
} from "./icons.js";

interface NavItemProps {
  id: SectionId;
  label: string;
  icon: React.ReactNode;
}

function NavItem({ id, label, icon }: NavItemProps) {
  const { section, setSection, navigateTo } = useExplorer();
  const active = section === id;
  return (
    <button
      type="button"
      className={`fn-ex-nav-item${active ? " active" : ""}`}
      onClick={() => { setSection(id); navigateTo(null); }}
      aria-current={active ? "page" : undefined}
    >
      <span className="icon">{icon}</span>
      {label}
    </button>
  );
}

export function ExplorerSidebar() {
  const { sidebarCollapsed } = useExplorer();

  return (
    <aside
      className={`fn-ex-sidebar${sidebarCollapsed ? " collapsed" : ""}`}
      aria-label="Navigation"
    >
      <nav style={{ flex: 1 }}>
        <NavItem id="my-drive" label="My Drive" icon={<IDriveCloud size={20} />} />
        <NavItem id="recent"   label="Recent"   icon={<IRecent     size={20} />} />
        <NavItem id="starred"  label="Starred"  icon={<IStarFilled size={20} style={{ color: "#FBBC04" }} />} />
        <NavItem id="trash"    label="Trash"    icon={<ITrash      size={20} />} />
      </nav>

      <StorageMeter />
    </aside>
  );
}

function StorageMeter() {
  // Phase 3: fetch real usage from project config.
  // For now, show a placeholder meter.
  const usedGb  = 2.4;
  const totalGb = 15;
  const pct     = Math.min((usedGb / totalGb) * 100, 100);

  return (
    <div className="fn-ex-storage">
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
        <IStorage size={16} style={{ color: "#5f6368" }} />
        <span className="fn-ex-storage-label">Storage</span>
      </div>
      <div className="fn-ex-storage-bar">
        <div className="fn-ex-storage-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="fn-ex-storage-label">
        {usedGb} GB of {totalGb} GB used
      </div>
    </div>
  );
}
