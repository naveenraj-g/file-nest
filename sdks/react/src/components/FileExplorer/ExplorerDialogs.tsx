/**
 * FileExplorer/ExplorerDialogs — Radix Dialog modals for CRUD operations.
 *
 * Four dialogs rendered in one component (only one open at a time):
 *   new-folder · rename · delete · move
 *
 * Each dialog reads `modal` + `modalTarget` from context and calls the
 * appropriate external callback (onFolderCreate, onFileRename, etc.).
 * Falls back to a console warning when no callback is provided.
 *
 * @module
 */

import React, { useRef, useEffect } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { useExplorer } from "./context.js";
import { INewFolder } from "./icons.js";

function Overlay() {
  return <Dialog.Overlay className="fn-ex-overlay" />;
}

/* ── New Folder ─────────────────────────────────────────── */
function NewFolderDialog() {
  const { modal, closeModal, currentFolderId, onFolderCreate, newFolderName, setNewFolderName } = useExplorer();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (modal === "new-folder") {
      setTimeout(() => { inputRef.current?.select(); }, 50);
    }
  }, [modal]);

  const confirm = async () => {
    const name = newFolderName.trim() || "Untitled folder";
    await onFolderCreate?.(name, currentFolderId);
    closeModal();
  };

  return (
    <Dialog.Root open={modal === "new-folder"} onOpenChange={(o) => !o && closeModal()}>
      <Dialog.Portal>
        <Overlay />
        <Dialog.Content className="fn-ex-dialog">
          <Dialog.Title className="fn-ex-dialog-title">New folder</Dialog.Title>
          <input
            ref={inputRef}
            className="fn-ex-dialog-input"
            value={newFolderName}
            onChange={(e) => setNewFolderName(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") confirm(); if (e.key === "Escape") closeModal(); }}
            aria-label="Folder name"
          />
          <div className="fn-ex-dialog-actions">
            <button type="button" className="fn-ex-dialog-btn cancel" onClick={closeModal}>Cancel</button>
            <button type="button" className="fn-ex-dialog-btn confirm" onClick={confirm}>Create</button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/* ── Rename ─────────────────────────────────────────────── */
function RenameDialog() {
  const { modal, modalTarget, closeModal, onFileRename, onFolderRename, renameValue, setRenameValue } = useExplorer();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (modal === "rename") setTimeout(() => { inputRef.current?.select(); }, 50);
  }, [modal]);

  const confirm = async () => {
    if (!modalTarget) return;
    const name = renameValue.trim() || modalTarget.name;
    if (modalTarget.type === "file") await onFileRename?.(modalTarget.id, name);
    else await onFolderRename?.(modalTarget.id, name);
    closeModal();
  };

  return (
    <Dialog.Root open={modal === "rename"} onOpenChange={(o) => !o && closeModal()}>
      <Dialog.Portal>
        <Overlay />
        <Dialog.Content className="fn-ex-dialog">
          <Dialog.Title className="fn-ex-dialog-title">Rename</Dialog.Title>
          <input
            ref={inputRef}
            className="fn-ex-dialog-input"
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") confirm(); if (e.key === "Escape") closeModal(); }}
            aria-label="New name"
          />
          <div className="fn-ex-dialog-actions">
            <button type="button" className="fn-ex-dialog-btn cancel" onClick={closeModal}>Cancel</button>
            <button type="button" className="fn-ex-dialog-btn confirm" onClick={confirm}>OK</button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/* ── Delete ─────────────────────────────────────────────── */
function DeleteDialog() {
  const { modal, modalTarget, closeModal, onFileDelete, onFolderDelete } = useExplorer();

  const confirm = async () => {
    if (!modalTarget) return;
    if (modalTarget.type === "file" && "filename" in modalTarget.item) {
      await onFileDelete?.(modalTarget.item as never);
    } else if (modalTarget.type === "folder" && "name" in modalTarget.item) {
      await onFolderDelete?.(modalTarget.item as never);
    }
    closeModal();
  };

  return (
    <Dialog.Root open={modal === "delete"} onOpenChange={(o) => !o && closeModal()}>
      <Dialog.Portal>
        <Overlay />
        <Dialog.Content className="fn-ex-dialog">
          <Dialog.Title className="fn-ex-dialog-title">Move to trash?</Dialog.Title>
          <Dialog.Description className="fn-ex-dialog-desc">
            "{modalTarget?.name}" will be moved to Trash. Items in Trash are
            deleted after 30 days.
          </Dialog.Description>
          <div className="fn-ex-dialog-actions">
            <button type="button" className="fn-ex-dialog-btn cancel" onClick={closeModal}>Cancel</button>
            <button type="button" className="fn-ex-dialog-btn danger" onClick={confirm}>Move to trash</button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/* ── Move to ────────────────────────────────────────────── */
function MoveDialog() {
  const { modal, modalTarget, closeModal, onFileMove, onFolderMove, folders, navigateTo } = useExplorer();
  const [targetId, setTargetId] = React.useState<string | null>(null);

  const confirm = async () => {
    if (!modalTarget) return;
    if (modalTarget.type === "file") await onFileMove?.(modalTarget.id, targetId);
    else await onFolderMove?.(modalTarget.id, targetId);
    closeModal();
  };

  return (
    <Dialog.Root open={modal === "move"} onOpenChange={(o) => !o && closeModal()}>
      <Dialog.Portal>
        <Overlay />
        <Dialog.Content className="fn-ex-dialog">
          <Dialog.Title className="fn-ex-dialog-title">Move "{modalTarget?.name}"</Dialog.Title>
          <Dialog.Description className="fn-ex-dialog-desc">
            Choose a destination folder.
          </Dialog.Description>

          <div style={{
            border: "1px solid #e0e0e0", borderRadius: 8,
            maxHeight: 240, overflowY: "auto", marginBottom: 20,
          }}>
            <div
              role="option"
              aria-selected={targetId === null}
              style={{
                padding: "10px 16px", cursor: "pointer", fontSize: 14,
                background: targetId === null ? "#d3e2fd" : "transparent",
                transition: "background 0.1s",
              }}
              onClick={() => setTargetId(null)}
            >
              📁 My Drive (root)
            </div>
            {folders
              .filter((f) => f.id !== modalTarget?.id)
              .map((f) => (
                <div
                  key={f.id}
                  role="option"
                  aria-selected={targetId === f.id}
                  style={{
                    padding: "10px 16px", cursor: "pointer", fontSize: 14,
                    background: targetId === f.id ? "#d3e2fd" : "transparent",
                    transition: "background 0.1s",
                  }}
                  onClick={() => setTargetId(f.id)}
                >
                  📁 {f.name}
                </div>
              ))}
            {folders.length === 0 && (
              <div style={{ padding: "10px 16px", color: "#5f6368", fontSize: 13 }}>
                No folders in this location.
              </div>
            )}
          </div>

          <div className="fn-ex-dialog-actions">
            <button type="button" className="fn-ex-dialog-btn cancel" onClick={closeModal}>Cancel</button>
            <button type="button" className="fn-ex-dialog-btn confirm" onClick={confirm}>Move here</button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/* ── Composite ──────────────────────────────────────────── */
export function ExplorerDialogs() {
  return (
    <>
      <NewFolderDialog />
      <RenameDialog />
      <DeleteDialog />
      <MoveDialog />
    </>
  );
}
