/**
 * FileExplorer/ExplorerStyles — scoped CSS injected as a <style> element.
 *
 * Uses a fn-ex- prefix on every class to avoid collisions with host app CSS.
 * Designed to match Google Drive's Material Design 3 aesthetic.
 *
 * @module
 */

import React from "react";

export function ExplorerStyles() {
  return <style>{CSS}</style>;
}

const CSS = `
/* ── Root layout ─────────────────────────────────────────── */
.fn-ex {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  font-family: 'Google Sans', Roboto, Arial, sans-serif;
  font-size: 14px;
  color: #1f1f1f;
  background: #fff;
  position: relative;
}

.fn-ex-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ── Top bar ─────────────────────────────────────────────── */
.fn-ex-topbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
  height: 64px;
  border-bottom: 1px solid #e0e0e0;
  flex-shrink: 0;
  background: #fff;
}

.fn-ex-search-wrap {
  flex: 1;
  max-width: 720px;
  position: relative;
}

.fn-ex-search {
  width: 100%;
  height: 40px;
  padding: 0 16px 0 44px;
  border: none;
  border-radius: 24px;
  background: #f0f4f9;
  font-size: 14px;
  color: #1f1f1f;
  outline: none;
  transition: background 0.15s, box-shadow 0.15s;
  box-sizing: border-box;
}
.fn-ex-search:focus {
  background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2), 0 0 0 2px #0b57d0;
}
.fn-ex-search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #5f6368;
  pointer-events: none;
}

.fn-ex-icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: #444746;
  cursor: pointer;
  transition: background 0.12s;
  flex-shrink: 0;
}
.fn-ex-icon-btn:hover { background: #f0f4f9; }
.fn-ex-icon-btn.active { color: #0b57d0; background: #d3e2fd; }

.fn-ex-new-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 18px 0 14px;
  height: 40px;
  border-radius: 20px;
  border: 1px solid #c4c7c5;
  background: #fff;
  font-size: 14px;
  font-weight: 500;
  color: #1f1f1f;
  cursor: pointer;
  transition: background 0.12s, box-shadow 0.12s;
  white-space: nowrap;
  flex-shrink: 0;
}
.fn-ex-new-btn:hover { background: #f9f9f9; box-shadow: 0 1px 3px rgba(0,0,0,.15); }

/* ── Selection toolbar ───────────────────────────────────── */
.fn-ex-sel-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
}
.fn-ex-sel-count {
  font-size: 14px;
  font-weight: 500;
  color: #0b57d0;
  margin-right: 8px;
  white-space: nowrap;
}
.fn-ex-sel-action {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 12px;
  height: 36px;
  border-radius: 18px;
  border: none;
  background: transparent;
  font-size: 13px;
  color: #1f1f1f;
  cursor: pointer;
  transition: background 0.12s;
  white-space: nowrap;
}
.fn-ex-sel-action:hover { background: #f0f4f9; }
.fn-ex-sel-action.danger:hover { background: #fce8e6; color: #c5221f; }

/* ── Sidebar ─────────────────────────────────────────────── */
.fn-ex-sidebar {
  width: 256px;
  min-width: 256px;
  height: 100%;
  overflow-y: auto;
  padding: 8px 0 16px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e0e0e0;
  background: #fff;
  transition: width 0.2s, min-width 0.2s;
  flex-shrink: 0;
}
.fn-ex-sidebar.collapsed { width: 0; min-width: 0; overflow: hidden; border-right: none; }

.fn-ex-section-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: #5f6368;
  padding: 12px 28px 4px;
  text-transform: uppercase;
}

.fn-ex-nav-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 14px 0 14px;
  height: 40px;
  border-radius: 0 24px 24px 0;
  margin-right: 14px;
  color: #1f1f1f;
  font-size: 14px;
  cursor: pointer;
  border: none;
  background: transparent;
  width: calc(100% - 14px);
  text-align: left;
  transition: background 0.12s;
}
.fn-ex-nav-item:hover { background: #e8eaed; }
.fn-ex-nav-item.active { background: #d3e2fd; font-weight: 500; }
.fn-ex-nav-item .icon { color: #444746; }
.fn-ex-nav-item.active .icon { color: #0b57d0; }

.fn-ex-storage {
  margin: auto 16px 0;
  padding-top: 16px;
}
.fn-ex-storage-bar {
  height: 4px;
  border-radius: 2px;
  background: #e0e0e0;
  overflow: hidden;
  margin: 6px 0;
}
.fn-ex-storage-fill {
  height: 100%;
  border-radius: 2px;
  background: #0b57d0;
  transition: width 0.4s;
}
.fn-ex-storage-label { font-size: 12px; color: #5f6368; }

/* ── Content area ────────────────────────────────────────── */
.fn-ex-content {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.fn-ex-breadcrumb {
  display: flex;
  align-items: center;
  padding: 12px 24px 4px;
  gap: 2px;
  flex-shrink: 0;
}
.fn-ex-crumb-btn {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 4px 8px;
  border: none;
  background: transparent;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 500;
  color: #1f1f1f;
  cursor: pointer;
  transition: background 0.1s;
}
.fn-ex-crumb-btn:not(:last-child) { font-weight: 400; font-size: 14px; color: #444746; }
.fn-ex-crumb-btn:not(:last-child):hover { background: #f0f4f9; }
.fn-ex-crumb-sep { color: #5f6368; }

.fn-ex-section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 24px 4px;
  font-size: 12px;
  font-weight: 600;
  color: #5f6368;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.fn-ex-sort-col-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: transparent;
  font-size: 12px;
  font-weight: 600;
  color: #5f6368;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  transition: background 0.1s;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.fn-ex-sort-col-btn:hover { background: #f0f4f9; color: #1f1f1f; }
.fn-ex-sort-col-btn.active { color: #0b57d0; }

/* ── Folders section header ──────────────────────────────── */
.fn-ex-group-label {
  padding: 8px 24px 4px;
  font-size: 12px;
  color: #5f6368;
  font-weight: 600;
  letter-spacing: 0.05em;
}

/* ── Grid view ───────────────────────────────────────────── */
.fn-ex-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 4px;
  padding: 4px 24px 16px;
}

.fn-ex-grid-item {
  position: relative;
  border-radius: 12px;
  border: 1px solid transparent;
  cursor: pointer;
  transition: background 0.1s, border-color 0.1s, box-shadow 0.1s;
  user-select: none;
  overflow: hidden;
  background: #fff;
}
.fn-ex-grid-item:hover { background: #f0f4f9; border-color: #e0e0e0; }
.fn-ex-grid-item.selected { background: #d3e2fd; border-color: #a8c5f8; }
.fn-ex-grid-item.selected:hover { background: #c2d7ff; }

.fn-ex-grid-thumb {
  height: 112px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8f9fa;
  border-radius: 12px 12px 0 0;
  overflow: hidden;
}
.fn-ex-grid-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.fn-ex-grid-info {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
}
.fn-ex-grid-name {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  word-break: break-word;
}
.fn-ex-grid-actions {
  position: absolute;
  top: 6px;
  right: 6px;
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.1s;
}
.fn-ex-grid-item:hover .fn-ex-grid-actions,
.fn-ex-grid-item.selected .fn-ex-grid-actions { opacity: 1; }

.fn-ex-grid-check-wrap {
  position: absolute;
  top: 6px;
  left: 6px;
  opacity: 0;
  transition: opacity 0.1s;
}
.fn-ex-grid-item:hover .fn-ex-grid-check-wrap,
.fn-ex-grid-item.selected .fn-ex-grid-check-wrap { opacity: 1; }

/* ── Folder grid card ────────────────────────────────────── */
.fn-ex-grid-folder {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid transparent;
  cursor: pointer;
  transition: background 0.1s, border-color 0.1s;
  user-select: none;
  background: #fff;
  position: relative;
}
.fn-ex-grid-folder:hover { background: #f0f4f9; border-color: #e0e0e0; }
.fn-ex-grid-folder.selected { background: #d3e2fd; border-color: #a8c5f8; }

/* ── List view ───────────────────────────────────────────── */
.fn-ex-list {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
.fn-ex-list th {
  padding: 8px 12px;
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: #5f6368;
  border-bottom: 1px solid #e0e0e0;
  white-space: nowrap;
  position: sticky;
  top: 0;
  background: #fff;
  z-index: 1;
}
.fn-ex-list td {
  padding: 6px 12px;
  vertical-align: middle;
  border-bottom: 1px solid #f8f9fa;
}

.fn-ex-list-row {
  cursor: pointer;
  transition: background 0.08s;
}
.fn-ex-list-row:hover { background: #f0f4f9; }
.fn-ex-list-row.selected { background: #d3e2fd; }
.fn-ex-list-row.selected:hover { background: #c2d7ff; }

.fn-ex-list-name {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.fn-ex-list-name-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fn-ex-row-actions {
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.1s;
  justify-content: flex-end;
}
.fn-ex-list-row:hover .fn-ex-row-actions,
.fn-ex-list-row.selected .fn-ex-row-actions { opacity: 1; }

.fn-ex-cb-wrap { opacity: 0; transition: opacity 0.1s; }
.fn-ex-list-row:hover .fn-ex-cb-wrap,
.fn-ex-list-row.selected .fn-ex-cb-wrap { opacity: 1; }

/* ── Custom checkbox ─────────────────────────────────────── */
.fn-ex-checkbox {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid #5f6368;
  background: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: border-color 0.1s, background 0.1s;
}
.fn-ex-checkbox.checked { border-color: #0b57d0; background: #0b57d0; }
.fn-ex-checkbox.checked svg { opacity: 1; }
.fn-ex-checkbox svg { opacity: 0; color: #fff; transition: opacity 0.1s; }
.fn-ex-checkbox:hover:not(.checked) { border-color: #0b57d0; }

/* ── Star button ─────────────────────────────────────────── */
.fn-ex-star-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 4px;
  border-radius: 50%;
  color: #5f6368;
  display: flex;
  align-items: center;
  transition: background 0.1s, color 0.1s;
}
.fn-ex-star-btn:hover { background: rgba(0,0,0,0.06); }
.fn-ex-star-btn.starred { color: #FBBC04; }

/* ── Info panel ──────────────────────────────────────────── */
.fn-ex-info {
  width: 304px;
  min-width: 304px;
  border-left: 1px solid #e0e0e0;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex-shrink: 0;
}
.fn-ex-info-thumb {
  width: 100%;
  aspect-ratio: 4/3;
  background: #f8f9fa;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.fn-ex-info-thumb img { width: 100%; height: 100%; object-fit: cover; }
.fn-ex-info-name { font-size: 15px; font-weight: 500; word-break: break-word; }
.fn-ex-info-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
}
.fn-ex-info-label { color: #5f6368; white-space: nowrap; }
.fn-ex-info-value { color: #1f1f1f; text-align: right; word-break: break-all; }
.fn-ex-info-divider { height: 1px; background: #e0e0e0; margin: 4px 0; }
.fn-ex-info-action-row { display: flex; gap: 8px; }
.fn-ex-info-action {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px;
  border-radius: 8px;
  border: 1px solid #c4c7c5;
  background: #fff;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.1s;
}
.fn-ex-info-action:hover { background: #f0f4f9; }

/* ── Radix dropdown / context menu ───────────────────────── */
.fn-ex-menu-content {
  min-width: 220px;
  background: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,.2), 0 0 1px rgba(0,0,0,.1);
  padding: 4px 0;
  z-index: 9999;
  animation: fn-ex-fade-in 0.1s ease;
}
@keyframes fn-ex-fade-in {
  from { opacity: 0; transform: scale(0.97); }
  to   { opacity: 1; transform: scale(1); }
}

.fn-ex-menu-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 8px 16px;
  font-size: 14px;
  color: #1f1f1f;
  cursor: pointer;
  border: none;
  background: transparent;
  width: 100%;
  text-align: left;
  transition: background 0.08s;
  outline: none;
}
.fn-ex-menu-item:hover, .fn-ex-menu-item[data-highlighted] { background: #f0f4f9; }
.fn-ex-menu-item.danger { color: #c5221f; }
.fn-ex-menu-item.danger:hover { background: #fce8e6; }
.fn-ex-menu-item .icon { color: #5f6368; }
.fn-ex-menu-item.danger .icon { color: #c5221f; }
.fn-ex-menu-sep { height: 1px; background: #e0e0e0; margin: 4px 0; }
.fn-ex-menu-sub-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.fn-ex-menu-sub-content {
  min-width: 160px;
  background: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,.2);
  padding: 4px 0;
  z-index: 9999;
}

/* ── Radix dialog ────────────────────────────────────────── */
.fn-ex-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  z-index: 9998;
  animation: fn-ex-fade-in 0.15s ease;
}
.fn-ex-dialog {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  min-width: 360px;
  max-width: 480px;
  z-index: 9999;
  box-shadow: 0 8px 32px rgba(0,0,0,.2);
  animation: fn-ex-dialog-in 0.15s ease;
}
@keyframes fn-ex-dialog-in {
  from { opacity: 0; transform: translate(-50%, -52%); }
  to   { opacity: 1; transform: translate(-50%, -50%); }
}
.fn-ex-dialog-title { font-size: 22px; font-weight: 400; margin: 0 0 20px; }
.fn-ex-dialog-desc { font-size: 14px; color: #5f6368; margin: 0 0 20px; }
.fn-ex-dialog-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #c4c7c5;
  border-radius: 4px;
  font-size: 14px;
  color: #1f1f1f;
  outline: none;
  box-sizing: border-box;
  margin-bottom: 20px;
}
.fn-ex-dialog-input:focus { border-color: #0b57d0; box-shadow: 0 0 0 2px rgba(11,87,208,.2); }
.fn-ex-dialog-actions { display: flex; justify-content: flex-end; gap: 8px; }
.fn-ex-dialog-btn {
  padding: 8px 20px;
  border-radius: 20px;
  border: none;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.12s;
}
.fn-ex-dialog-btn.cancel { background: transparent; color: #0b57d0; }
.fn-ex-dialog-btn.cancel:hover { background: #e8f0fe; }
.fn-ex-dialog-btn.confirm { background: #0b57d0; color: #fff; }
.fn-ex-dialog-btn.confirm:hover { background: #0842a0; }
.fn-ex-dialog-btn.danger  { background: #c5221f; color: #fff; }
.fn-ex-dialog-btn.danger:hover  { background: #a50e0e; }

/* ── Dropdown menu ───────────────────────────────────────── */
.fn-ex-dropdown-content {
  min-width: 200px;
  background: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,.2);
  padding: 4px 0;
  z-index: 9999;
  animation: fn-ex-fade-in 0.1s ease;
}
.fn-ex-dropdown-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 16px;
  font-size: 14px;
  color: #1f1f1f;
  cursor: pointer;
  transition: background 0.08s;
  outline: none;
}
.fn-ex-dropdown-item:hover,
.fn-ex-dropdown-item[data-highlighted] { background: #f0f4f9; }
.fn-ex-dropdown-item .icon { color: #5f6368; }
.fn-ex-dropdown-sep { height: 1px; background: #e0e0e0; margin: 4px 0; }
.fn-ex-dropdown-label {
  padding: 6px 16px;
  font-size: 12px;
  color: #5f6368;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.fn-ex-dropdown-check {
  margin-left: auto;
  color: #0b57d0;
}

/* ── Loading / empty ─────────────────────────────────────── */
.fn-ex-spinner-row {
  display: flex;
  justify-content: center;
  padding: 24px;
}
.fn-ex-spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #e0e0e0;
  border-top-color: #0b57d0;
  border-radius: 50%;
  animation: fn-ex-spin 0.7s linear infinite;
}
@keyframes fn-ex-spin { to { transform: rotate(360deg); } }

.fn-ex-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 64px 24px;
  color: #5f6368;
  text-align: center;
}
.fn-ex-empty-icon { font-size: 64px; line-height: 1; opacity: 0.5; }
.fn-ex-empty-title { font-size: 22px; font-weight: 400; color: #1f1f1f; }
.fn-ex-empty-desc  { font-size: 14px; color: #5f6368; max-width: 320px; }

/* ── Sentinel (infinite scroll trigger) ──────────────────── */
.fn-ex-sentinel { height: 1px; width: 100%; }
`;
