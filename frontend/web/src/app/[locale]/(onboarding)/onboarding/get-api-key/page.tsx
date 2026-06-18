/**
 * Get-API-key onboarding step.
 *
 * Generates an org-scoped API key via the IAM authClient. The key is shown
 * once and must be copied before proceeding. The raw key is stored in
 * sessionStorage for the install-sdk step's code snippets.
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

// authClient is the browser-side Better Auth client — imported from the
// console app's lib/auth.ts (create this file pointing at the IAM URL).
// For now we call the IAM directly via fetch to avoid a dependency gap.
export default function GetApiKeyPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const orgId = searchParams.get("orgId") ?? "";

  const [apiKey, setApiKey] = React.useState<string | null>(null);
  const [copied, setCopied] = React.useState(false);
  const [hasCopied, setHasCopied] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [generated, setGenerated] = React.useState(false);

  async function generateKey() {
    setLoading(true);

    const res = await fetch(
      `${process.env.NEXT_PUBLIC_BETTER_AUTH_URL}/api/auth/api-key/create`,
      {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "Default",
          ...(orgId ? { referenceId: orgId } : {}),
        }),
      },
    );

    const data = await res.json();

    if (!res.ok) {
      toast.error(data.message ?? "Failed to generate API key");
      setLoading(false);
      return;
    }

    const rawKey = (data as { key: string }).key;
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
          This key authenticates your application with FileNest. It will only
          be shown once — copy it now and store it securely.
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
              Store this key as{" "}
              <code className="rounded bg-muted px-1 py-0.5 font-mono">
                FILENEST_API_KEY
              </code>{" "}
              in your environment variables. You can create additional keys in
              Settings → API Keys.
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
