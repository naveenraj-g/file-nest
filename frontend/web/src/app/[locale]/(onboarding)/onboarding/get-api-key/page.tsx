/**
 * Get-API-key onboarding step.
 *
 * Generates a project-scoped API key via the IAM. The key carries both
 * organizationId (as referenceId, for org-level listing) and projectId
 * (in metadata) so the FileNest backend can build the full tenant context
 * from a single key verification call.
 *
 * The key is shown once — copy it before proceeding. The raw key and the
 * project ID are stored in sessionStorage for the install-sdk step's snippets.
 *
 * @module
 */

"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Check, Copy, KeyRound } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { authClient } from "@/modules/client/auth/auth-client";

const DEFAULT_SCOPES = [
  "files:upload",
  "files:download",
  "files:read",
  "files:delete",
  "files:update_metadata",
  "projects:read",
  "projects:update",
];

export default function GetApiKeyPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const orgId = searchParams.get("orgId") ?? "";

  const [projectId, setProjectId] = React.useState("");
  const [apiKey, setApiKey] = React.useState<string | null>(null);
  const [copied, setCopied] = React.useState(false);
  const [hasCopied, setHasCopied] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [generated, setGenerated] = React.useState(false);

  React.useEffect(() => {
    const stored = sessionStorage.getItem("fn_onboarding_project_id");
    if (stored) setProjectId(stored);
  }, []);

  async function generateKey() {
    setLoading(true);

    const { data, error } = await authClient.apiKey.create({
      name: "default",
      organizationId: orgId,
      metadata: {
        organizationId: orgId,
        projectId: projectId || null,
        scopes: DEFAULT_SCOPES,
      },
    });

    if (error || !data) {
      toast.error(error?.message ?? "Failed to generate API key");
      setLoading(false);
      return;
    }

    const rawKey = data.key;
    setApiKey(rawKey);
    setGenerated(true);
    sessionStorage.setItem("fn_onboarding_key", rawKey);
    setLoading(false);
  }

  async function copyKey() {
    if (!apiKey) return;
    await navigator.clipboard.writeText(apiKey);
    setCopied(true);
    setHasCopied(true);
    toast.success("API key copied");
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Your API key</CardTitle>
        <CardDescription>
          This key authenticates your application with FileNest and is scoped to
          your project. It will only be shown once — copy it now and store it
          securely.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!generated ? (
          <Button onClick={generateKey} disabled={loading} className="w-full">
            <KeyRound className="mr-2 h-4 w-4" />
            {loading ? "Generating…" : "Generate API key"}
          </Button>
        ) : (
          <>
            <div className="flex items-center gap-2 rounded-md border bg-muted/50 p-3">
              <code className="flex-1 break-all font-mono text-sm select-all">
                {apiKey}
              </code>
              <Button
                variant="ghost"
                size="icon"
                className="shrink-0"
                onClick={copyKey}
              >
                {copied ? (
                  <Check className="h-4 w-4 text-green-500" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Store this as{" "}
              <code className="rounded bg-muted px-1 py-0.5 font-mono">
                FILENEST_API_KEY
              </code>{" "}
              in your environment. You can create additional project-scoped keys
              in Project Settings → API Keys.
            </p>
            <Button
              className="w-full"
              onClick={() => router.push("/onboarding/install-sdk")}
              disabled={!hasCopied}
            >
              {hasCopied ? "Continue to install SDK" : "Copy your key to continue"}
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  );
}
