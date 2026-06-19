/**
 * ProjectsTable — renders the projects list with search, filters, and row actions.
 *
 * Follows the IAM UsersTable pattern: accepts pre-fetched data from the RSC page,
 * wires up useDataTable + DataTable + DataTableToolbar, and opens modals via the
 * project store. The "New project" button triggers the createProject modal.
 *
 * @module
 */
"use client";

import * as React from "react";
import { FolderOpen, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
  EmptyDescription,
  EmptyContent,
} from "@/components/ui/empty";
import {
  DataTable,
  DataTableToolbar,
  useDataTable,
} from "@/modules/client/shared/components/tables";
import { useProjectStore } from "@/modules/client/projects/stores/project.store";
import { projectsTableColumns } from "./ProjectsTableColumn";
import type { IProjectsTableProps } from "@/modules/client/projects/types/project.type";

export function ProjectsTable({ projects, error }: IProjectsTableProps) {
  const { onOpen } = useProjectStore();
  const columns = React.useMemo(() => projectsTableColumns(), []);

  const { table } = useDataTable({
    columns,
    data: projects,
    initialSorting: [{ id: "created_at", desc: true }],
    initialPageSize: 20,
  });

  if (error) {
    return (
      <Empty>
        <EmptyHeader>
          <EmptyTitle>Failed to load projects</EmptyTitle>
          <EmptyDescription>{error}</EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }

  return (
    <DataTable
      table={table}
      emptyState={
        <Empty>
          <EmptyHeader>
            <EmptyMedia><FolderOpen className="h-8 w-8 text-muted-foreground" /></EmptyMedia>
            <EmptyTitle>No projects yet</EmptyTitle>
            <EmptyDescription>
              Create your first project to start uploading files.
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Button size="sm" onClick={() => onOpen("createProject")}>
              <Plus className="h-4 w-4 mr-1.5" />
              New project
            </Button>
          </EmptyContent>
        </Empty>
      }
    >
      <DataTableToolbar table={table}>
        <Button size="sm" onClick={() => onOpen("createProject")}>
          <Plus className="h-4 w-4 mr-1.5" />
          New project
        </Button>
      </DataTableToolbar>
    </DataTable>
  );
}
