/**
 * FilesTable — file list table with status filtering and row actions.
 *
 * Initial data is SSR-fetched by the RSC page and passed as a prop, avoiding
 * any client-side fetch on first render. After a delete mutation the store
 * trigger increments, which fires a useServerAction execute() to refresh rows.
 * No React Query / useServerActionQuery — keeps hydration simple and avoids
 * the "state update before mount" error that async query initialisation causes.
 *
 * @module
 */
"use client";

import * as React from "react";
import { useServerAction } from "zsa-react";
import { Trash2, Upload, FileX } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
  EmptyDescription,
} from "@/components/ui/empty";
import {
  DataTableWithViews,
  DataTableToolbar,
  DataTableGlobalSearch,
  DataTableSelectionBar,
  useDataTable,
} from "@/modules/client/shared/components/tables";
import { listFilesAction } from "@/modules/server/presentation/actions/file.actions";
import { useFileStore } from "@/modules/client/files/stores/file.store";
import { filesTableColumns } from "./FilesTableColumn";
import type { TFile, TFileList } from "@/modules/entities/schemas/file";

interface FilesTableProps {
  projectId: string;
  /** SSR-fetched first page — seeds the table to avoid a loading flash. */
  initialData: TFileList;
}

export function FilesTable({ projectId, initialData }: FilesTableProps) {
  const { onOpen, trigger } = useFileStore();

  const [rows, setRows] = React.useState<TFile[]>(initialData.items ?? []);
  const [isFetching, setIsFetching] = React.useState(false);

  const columns = React.useMemo(() => filesTableColumns(), []);

  const { table } = useDataTable({
    columns,
    data: rows,
    initialSorting: [{ id: "created_at", desc: true }],
    initialPageSize: 50,
  });

  const { execute } = useServerAction(listFilesAction);

  // Re-fetch rows after any mutation (trigger increments in file store)
  React.useEffect(() => {
    if (trigger === 0) return;
    setIsFetching(true);
    execute({ payload: { projectId, limit: 200 } })
      .then(([data]) => {
        if (data) setRows(data.items ?? []);
      })
      .finally(() => setIsFetching(false));
  }, [trigger, projectId]);  // eslint-disable-line react-hooks/exhaustive-deps

  const selectedRows = table.getFilteredSelectedRowModel().rows;

  const emptyState = (
    <Empty>
      <EmptyHeader>
        <EmptyMedia>
          <FileX className="h-8 w-8 text-muted-foreground" />
        </EmptyMedia>
        <EmptyTitle>No files yet</EmptyTitle>
        <EmptyDescription>
          Upload files using the FileNest SDK or API to see them here.
        </EmptyDescription>
      </EmptyHeader>
    </Empty>
  );

  const toolbar = (
    <DataTableToolbar table={table}>
      <DataTableGlobalSearch table={table} placeholder="Search files…" />
      <Button size="default" variant="outline" disabled>
        <Upload className="h-4 w-4 mr-1.5" />
        Upload
      </Button>
    </DataTableToolbar>
  );

  return (
    <>
      <DataTableWithViews
        table={table}
        toolbar={toolbar}
        defaultView="table"
        loading={isFetching}
        emptyState={emptyState}
      />

      <DataTableSelectionBar table={table} filename="files">
        {selectedRows.length > 0 && (
          <Button
            variant="destructive"
            size="sm"
            className="h-7 gap-1.5 text-xs"
            onClick={() => {
              if (selectedRows.length === 1) {
                onOpen("deleteFile", selectedRows[0].original);
              }
            }}
          >
            <Trash2 className="size-3.5" />
            Delete
          </Button>
        )}
      </DataTableSelectionBar>
    </>
  );
}
