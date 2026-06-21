/**
 * FileExplorer/ExplorerContextMenu — Radix ContextMenu rendered on right-click.
 *
 * Wraps any trigger (file card, list row, folder chip) with a Drive-style
 * context menu: Open, Download, Organize (star, move), Rename, Delete.
 *
 * @module
 */

import React from "react";
import * as CM from "@radix-ui/react-context-menu";
import type { FileRecord, Folder } from "@filenest/core";
import { useExplorer } from "./context.js";
import { isFile } from "./utils.js";
import {
  IDownload, ITrash, IRename, IMove, IStar, IStarFilled, IInfo, IChevRight,
} from "./icons.js";

interface Props {
  item: FileRecord | Folder;
  children: React.ReactNode;
}

export function ExplorerContextMenu({ item, children }: Props) {
  const {
    onFileDownload, openModal, showInfoPanel, toggleStar, starredIds,
    onFileDelete, onFolderDelete,
  } = useExplorer();

  const file   = isFile(item) ? item : null;
  const folder = !isFile(item) ? item : null;
  const name   = file ? file.filename : folder!.name;
  const starred = starredIds.has(item.id);

  const handleDelete = () => {
    openModal("delete", { type: file ? "file" : "folder", id: item.id, name, item });
  };

  const handleRename = () => {
    openModal("rename", { type: file ? "file" : "folder", id: item.id, name, item });
  };

  const handleMove = () => {
    openModal("move", { type: file ? "file" : "folder", id: item.id, name, item });
  };

  return (
    <CM.Root>
      <CM.Trigger asChild>{children}</CM.Trigger>
      <CM.Portal>
        <CM.Content className="fn-ex-menu-content">
          {file && (
            <CM.Item
              className="fn-ex-menu-item"
              onSelect={() => onFileDownload?.(file)}
            >
              <IDownload size={16} className="icon" />
              Download
            </CM.Item>
          )}

          <CM.Item
            className="fn-ex-menu-item"
            onSelect={() => showInfoPanel(item.id)}
          >
            <IInfo size={16} className="icon" />
            File information
          </CM.Item>

          <CM.Separator className="fn-ex-menu-sep" />

          <CM.Sub>
            <CM.SubTrigger className="fn-ex-menu-item fn-ex-menu-sub-trigger">
              <span style={{ display: "flex", alignItems: "center", gap: 14 }}>
                <IMove size={16} className="icon" />
                Organize
              </span>
              <IChevRight size={14} className="icon" />
            </CM.SubTrigger>
            <CM.Portal>
              <CM.SubContent className="fn-ex-menu-sub-content">
                <CM.Item
                  className="fn-ex-menu-item"
                  onSelect={() => toggleStar(item.id)}
                >
                  {starred
                    ? <><IStarFilled size={16} className="icon" /> Remove from Starred</>
                    : <><IStar size={16} className="icon" /> Add to Starred</>}
                </CM.Item>
                <CM.Item className="fn-ex-menu-item" onSelect={handleMove}>
                  <IMove size={16} className="icon" /> Move to
                </CM.Item>
              </CM.SubContent>
            </CM.Portal>
          </CM.Sub>

          <CM.Separator className="fn-ex-menu-sep" />

          <CM.Item className="fn-ex-menu-item" onSelect={handleRename}>
            <IRename size={16} className="icon" />
            Rename
          </CM.Item>

          <CM.Separator className="fn-ex-menu-sep" />

          <CM.Item className="fn-ex-menu-item danger" onSelect={handleDelete}>
            <ITrash size={16} className="icon" />
            Move to trash
          </CM.Item>
        </CM.Content>
      </CM.Portal>
    </CM.Root>
  );
}
