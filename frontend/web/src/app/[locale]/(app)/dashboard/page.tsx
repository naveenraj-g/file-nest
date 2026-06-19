/**
 * DashboardPage — entry point after sign-in.
 *
 * Fetches live project data via the project server action and renders a
 * summary stat card plus a recent-projects list. Quick actions guide new
 * users toward creating their first project.
 *
 * @module
 */
import Link from "next/link";
import { getServerSession } from "@/modules/server/auth/get-session";
import { listProjectsAction } from "@/modules/server/presentation/actions/project.actions";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FolderOpen, Plus } from "lucide-react";

export default async function DashboardPage() {
  const session = await getServerSession();

  const [data] = await listProjectsAction({});
  const projects = data?.items ?? [];
  const total = data?.total ?? 0;
  const recent = projects.slice(0, 3);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">
          Welcome back, {session?.user.name}
        </h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Here&apos;s what&apos;s happening in your organisation.
        </p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Projects
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{total}</p>
            <p className="text-xs text-muted-foreground mt-1">
              active in this organisation
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Recent projects */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">Recent projects</h2>
          {total > 3 && (
            <Button variant="ghost" size="sm" asChild>
              <Link href="/projects">View all</Link>
            </Button>
          )}
        </div>

        {recent.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed p-10 text-center">
            <FolderOpen className="h-8 w-8 text-muted-foreground mb-3" />
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
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {recent.map((project) => (
              <Link key={project.id} href={`/projects/${project.id}/files`}>
                <Card className="hover:border-foreground/20 transition-colors cursor-pointer h-full">
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between gap-2">
                      <CardTitle className="text-sm font-semibold leading-tight">
                        {project.name}
                      </CardTitle>
                      <Badge
                        variant="secondary"
                        className="shrink-0 text-xs capitalize"
                      >
                        {project.storage_provider}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground font-mono">
                      {project.slug}
                    </p>
                  </CardHeader>
                  <CardContent>
                    <p className="text-xs text-muted-foreground capitalize">
                      {project.storage_mode === "managed"
                        ? "Managed storage"
                        : "Custom storage"}
                    </p>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}

        {recent.length > 0 && (
          <div className="flex justify-end">
            <Button asChild size="sm" variant="outline">
              <Link href="/projects/new">
                <Plus className="h-4 w-4 mr-1.5" />
                New project
              </Link>
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
