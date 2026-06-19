/**
 * Create-org onboarding step.
 *
 * Pre-populates the org name from the user's display name so they can just
 * hit Continue without typing. Slug is derived automatically from the name
 * but is editable. Submits to /api/onboarding/org which calls the IAM.
 *
 * @module
 */

"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

function toSlug(name: string) {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .slice(0, 48);
}

interface CreateOrgPageProps {
  searchParams: Promise<{ name?: string }>;
}

export default function CreateOrgPage({ searchParams }: CreateOrgPageProps) {
  const router = useRouter();
  const [name, setName] = React.useState("");
  const [slug, setSlug] = React.useState("");
  const [slugEdited, setSlugEdited] = React.useState(false);
  const [loading, setLoading] = React.useState(false);

  // Pre-populate from ?name= query param (set by the app layout from session).
  React.useEffect(() => {
    searchParams.then(({ name: prefill }) => {
      if (prefill && !name) {
        setName(prefill);
        setSlug(toSlug(prefill));
      }
    });
  }, [searchParams]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleNameChange(value: string) {
    setName(value);
    if (!slugEdited) setSlug(toSlug(value));
  }

  function handleSlugChange(value: string) {
    setSlugEdited(true);
    setSlug(toSlug(value));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !slug.trim()) return;

    setLoading(true);

    const res = await fetch("/api/onboarding/org", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name.trim(), slug: slug.trim() }),
    });

    const data = await res.json();

    if (!res.ok) {
      toast.error(data.error ?? "Failed to create organisation");
      setLoading(false);
      return;
    }

    router.push(`/onboarding/create-project?orgId=${data.orgId}`);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Name your organisation</CardTitle>
        <CardDescription>
          This is your team or company workspace. You can change it later in
          settings.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Organisation name</Label>
            <Input
              id="name"
              placeholder="Acme Inc."
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
              autoFocus
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="slug">
              URL slug
              <span className="ml-2 text-xs text-muted-foreground font-normal">
                console.filenest.io/
                <span className="text-foreground">{slug || "your-org"}</span>
              </span>
            </Label>
            <Input
              id="slug"
              placeholder="acme-inc"
              value={slug}
              onChange={(e) => handleSlugChange(e.target.value)}
              pattern="[a-z0-9-]+"
              title="Lowercase letters, numbers, and hyphens only"
              required
            />
          </div>
          <Button
            type="submit"
            className="w-full"
            disabled={loading || !name.trim() || !slug.trim()}
          >
            {loading ? "Creating…" : "Create organisation"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
