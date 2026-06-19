/**
 * ProjectsPage — lists all projects in the active organisation.
 *
 * Server component: fetches projects via listProjectsAction and passes the
 * result to the client ProjectsTable (TanStack Table + filters + row actions).
 * ProjectModalProvider mounts the Create and Delete modals client-side once.
 *
 * @module
 */
import { listProjectsAction } from "@/modules/server/presentation/actions/project.actions";
import { ProjectsTable } from "@/modules/client/projects/components/ProjectsTable";
import { ProjectModalProvider } from "@/modules/client/projects/provider/ProjectModalProvider";

export default async function ProjectsPage() {
  const [data, err] = await listProjectsAction({});
  const projects = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Projects</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          {total} project{total !== 1 ? "s" : ""} in this organisation
        </p>
      </div>

      <ProjectsTable
        projects={projects}
        error={err ? String(err) : null}
      />

      <ProjectModalProvider />
    </div>
  );
}
