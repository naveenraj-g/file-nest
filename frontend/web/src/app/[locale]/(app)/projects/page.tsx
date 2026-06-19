/**
 * ProjectsPage — lists all projects in the active organisation.
 *
 * Server component: fetches projects via the project server action.
 * Renders a card grid; empty state guides the user toward creating a project.
 *
 * @module
 */
import Link from "next/link";
import { listProjectsAction } from "@/modules/server/presentation/actions/project.actions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FolderOpen, Plus } from "lucide-react";

export default async function ProjectsPage() {
  const [data] = await listProjectsAction({});
  const projects = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Projects</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {total} project{total !== 1 ? "s" : ""} in this organisation
          </p>
        </div>
        <Button asChild size="sm">
          <Link href="/projects/new">
            <Plus className="h-4 w-4 mr-1.5" />
            New project
          </Link>
        </Button>
      </div>

      {projects.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed p-12 text-center">
          <FolderOpen className="h-10 w-10 text-muted-foreground mb-3" />
          <p className="text-sm font-medium">No projects yet</p>
          <p className="text-sm text-muted-foreground mt-1">
            Create your first project to start uploading files.
          </p>
          <Button asChild size="sm" className="mt-4">
            <Link href="/projects/new">
              <Plus className="h-4 w-4 mr-1.5" />
              New project
            </Link>
          </Button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <Link key={project.id} href={`/projects/${project.id}/files`}>
              <Card className="hover:border-foreground/20 transition-colors cursor-pointer h-full">
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <CardTitle className="text-base font-semibold leading-tight">
                      {project.name}
                    </CardTitle>
                    <Badge variant="secondary" className="shrink-0 text-xs capitalize">
                      {project.storage_provider}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground font-mono">{project.slug}</p>
                </CardHeader>
                <CardContent>
                  {project.description && (
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {project.description}
                    </p>
                  )}
                  <p className="text-xs text-muted-foreground mt-2 capitalize">
                    {project.storage_mode === "managed" ? "Managed storage" : "Custom storage"}
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
