/**
 * FilesPage — lists all files in the active project.
 *
 * Server component: fetches the first 200 files via listFilesAction and passes
 * the result as initialData to FilesTable. The client table handles client-side
 * sorting and filtering; refetches after mutations via the file store trigger.
 *
 * @module
 */
import { listFilesAction } from "@/modules/server/presentation/actions/file.actions";
import { FilesTable } from "@/modules/client/files/components/FilesTable";
import { FileModalProvider } from "@/modules/client/files/provider/FileModalProvider";

interface FilesPageProps {
  params: Promise<{ projectId: string }>;
}

export default async function FilesPage({ params }: FilesPageProps) {
  const { projectId } = await params;

  const [data] = await listFilesAction({
    payload: { projectId, limit: 200 },
  });

  const initialData = data ?? { items: [], total: 0, cursor: null };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Files</h2>
        <p className="text-sm text-muted-foreground mt-0.5">
          {initialData.total} file{initialData.total !== 1 ? "s" : ""} in this project
        </p>
      </div>

      <FilesTable projectId={projectId} initialData={initialData} />

      <FileModalProvider />
    </div>
  );
}
