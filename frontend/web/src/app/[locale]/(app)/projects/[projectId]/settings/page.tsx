/**
 * Project settings page — storage configuration.
 *
 * Server component: loads current storage config via server action. Passes
 * it to StorageConfigForm which handles the BYOB credential update flow and
 * the verify-connection probe.
 *
 * Managed-mode projects see an info banner (no credentials to configure).
 *
 * @module
 */
import { notFound } from "next/navigation";
import { getStorageConfigAction } from "@/modules/server/presentation/actions/storage-config.actions";
import { StorageConfigForm } from "@/modules/client/projects/forms/StorageConfigForm";

interface Props {
  params: Promise<{ projectId: string }>;
}

export default async function ProjectSettingsPage({ params }: Props) {
  const { projectId } = await params;

  const [config, err] = await getStorageConfigAction({ payload: { projectId } });

  if (err || !config) {
    notFound();
  }

  return (
    <div className="max-w-xl space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Storage</h2>
        <p className="text-sm text-muted-foreground mt-0.5">
          Configure where this project&apos;s files are stored.
        </p>
      </div>

      <StorageConfigForm projectId={projectId} config={config} />
    </div>
  );
}
