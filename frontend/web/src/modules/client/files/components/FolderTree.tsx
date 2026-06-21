/**
 * FolderTree — read-only folder sidebar for the files page.
 *
 * Displays a hierarchical tree built from the flat folder list returned by
 * the API (materialized-path model). Clicking a folder pushes `?folder_id=xxx`
 * to the URL so the state is shareable and back-button safe. Clicking the
 * active folder (or "All files") clears the filter.
 *
 * No create/delete — those operations are SDK/API only. This is purely a
 * navigation aid for browsing the project's folder structure.
 *
 * @module
 */
"use client";

import * as React from "react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { ChevronRight, Folder, FolderOpen, Files } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TFolder, TFolderList } from "@/modules/entities/schemas/folder";

interface FolderNode extends TFolder {
  children: FolderNode[];
}

function buildTree(folders: TFolder[]): FolderNode[] {
  const nodeMap = new Map<string, FolderNode>();
  for (const f of folders) {
    nodeMap.set(f.id, { ...f, children: [] });
  }
  const roots: FolderNode[] = [];
  for (const node of nodeMap.values()) {
    if (node.parent_folder_id && nodeMap.has(node.parent_folder_id)) {
      nodeMap.get(node.parent_folder_id)!.children.push(node);
    } else {
      roots.push(node);
    }
  }
  const sort = (nodes: FolderNode[]) => {
    nodes.sort((a, b) => a.name.localeCompare(b.name));
    for (const n of nodes) sort(n.children);
  };
  sort(roots);
  return roots;
}

interface FolderNodeItemProps {
  node: FolderNode;
  activeFolderId: string | null;
  depth: number;
  onSelect: (id: string) => void;
}

function FolderNodeItem({ node, activeFolderId, depth, onSelect }: FolderNodeItemProps) {
  const isActive = activeFolderId === node.id;
  const hasChildren = node.children.length > 0;
  const [expanded, setExpanded] = React.useState(false);

  // Auto-expand if a descendant is active
  const isAncestorOfActive = React.useMemo(() => {
    if (!activeFolderId) return false;
    const isDescendant = (n: FolderNode): boolean =>
      n.id === activeFolderId || n.children.some(isDescendant);
    return node.children.some(isDescendant);
  }, [activeFolderId, node]);

  React.useEffect(() => {
    if (isAncestorOfActive) setExpanded(true);
  }, [isAncestorOfActive]);

  return (
    <li>
      <button
        type="button"
        className={cn(
          "w-full flex items-center gap-1.5 px-2 py-1 rounded-md text-sm transition-colors text-left",
          isActive
            ? "bg-accent text-accent-foreground font-medium"
            : "hover:bg-muted/60 text-muted-foreground hover:text-foreground",
        )}
        style={{ paddingLeft: `${(depth + 1) * 12}px` }}
        onClick={() => onSelect(node.id)}
      >
        {hasChildren ? (
          <span
            className="shrink-0 text-muted-foreground"
            onClick={(e) => {
              e.stopPropagation();
              setExpanded((p) => !p);
            }}
          >
            <ChevronRight
              className={cn("h-3.5 w-3.5 transition-transform", expanded && "rotate-90")}
            />
          </span>
        ) : (
          <span className="w-3.5 shrink-0" />
        )}
        {isActive ? (
          <FolderOpen className="h-3.5 w-3.5 shrink-0" />
        ) : (
          <Folder className="h-3.5 w-3.5 shrink-0" />
        )}
        <span className="truncate">{node.name}</span>
      </button>

      {hasChildren && expanded && (
        <ul className="mt-0.5 space-y-0.5">
          {node.children.map((child) => (
            <FolderNodeItem
              key={child.id}
              node={child}
              activeFolderId={activeFolderId}
              depth={depth + 1}
              onSelect={onSelect}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

interface FolderTreeProps {
  folderList: TFolderList;
  /** Current folder_id from URL search params — null means "all files". */
  activeFolderId: string | null;
}

export function FolderTree({ folderList, activeFolderId }: FolderTreeProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const tree = React.useMemo(() => buildTree(folderList.items), [folderList.items]);

  const navigate = React.useCallback(
    (folderId: string | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (folderId) {
        params.set("folder_id", folderId);
      } else {
        params.delete("folder_id");
      }
      router.push(`${pathname}?${params.toString()}`);
    },
    [router, pathname, searchParams],
  );

  if (folderList.items.length === 0) return null;

  return (
    <nav className="w-52 shrink-0">
      <p className="text-xs font-medium text-muted-foreground px-2 mb-1.5 uppercase tracking-wide">
        Folders
      </p>
      <ul className="space-y-0.5">
        {/* "All files" root entry */}
        <li>
          <button
            type="button"
            className={cn(
              "w-full flex items-center gap-1.5 px-2 py-1 rounded-md text-sm transition-colors text-left",
              activeFolderId === null
                ? "bg-accent text-accent-foreground font-medium"
                : "hover:bg-muted/60 text-muted-foreground hover:text-foreground",
            )}
            onClick={() => navigate(null)}
          >
            <span className="w-3.5 shrink-0" />
            <Files className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">All files</span>
          </button>
        </li>

        {tree.map((node) => (
          <FolderNodeItem
            key={node.id}
            node={node}
            activeFolderId={activeFolderId}
            depth={0}
            onSelect={(id) => navigate(id === activeFolderId ? null : id)}
          />
        ))}
      </ul>
    </nav>
  );
}
