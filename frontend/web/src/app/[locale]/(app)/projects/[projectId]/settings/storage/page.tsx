/**
 * Project settings › Storage — BYOB storage credentials and connection status.
 *
 * Server component: loads current storage config via server action. Passes
 * it to StorageConfigForm which handles the BYOB credential update flow and
 * the verify-connection probe.
 *
 * Managed-mode projects see an info banner (no credentials to configure).
 *
 * @module
 */
import { getStorageConfigAction } from "@/modules/server/presentation/actions/storage-config.actions";
import { StorageConfigForm } from "@/modules/client/projects/forms/StorageConfigForm";
import { ConfigUnavailable } from "@/modules/client/projects/components/settings/ConfigUnavailable";

interface Props {
  params: Promise<{ projectId: string }>;
}

export default async function ProjectSettingsStoragePage({ params }: Props) {
  const { projectId } = await params;

  const [config, err] = await getStorageConfigAction({ payload: { projectId } });

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Storage</h2>
        <p className="text-sm text-muted-foreground mt-0.5">
          Configure where this project&apos;s files are stored.
        </p>
      </div>

      {err || !config ? (
        <ConfigUnavailable />
      ) : (
        <StorageConfigForm projectId={projectId} config={config} />
      )}
    </div>
  );
}
