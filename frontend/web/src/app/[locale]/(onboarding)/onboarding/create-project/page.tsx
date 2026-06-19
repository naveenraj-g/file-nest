/**
 * Create-project onboarding step.
 *
 * Creates the user's first FileNest project with managed S3 storage.
 * Only the project name is required — slug is auto-derived and storage
 * defaults to managed/s3 so there's nothing else to configure here.
 *
 * On success the project ID is saved to sessionStorage so the next step
 * (get-api-key) can bind the generated key to this specific project.
 *
 * @module
 */

"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useServerAction } from "zsa-react";
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
import { createProjectAction } from "@/modules/server/presentation/actions/project.actions";

function toSlug(name: string) {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .slice(0, 48);
}

export default function CreateProjectPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const orgId = searchParams.get("orgId") ?? "";

  const [name, setName] = React.useState("");
  const [slug, setSlug] = React.useState("");
  const [slugEdited, setSlugEdited] = React.useState(false);

  function handleNameChange(value: string) {
    setName(value);
    if (!slugEdited) setSlug(toSlug(value));
  }

  function handleSlugChange(value: string) {
    setSlugEdited(true);
    setSlug(toSlug(value));
  }

  const { execute, isPending } = useServerAction(createProjectAction, {
    onSuccess: ({ data }) => {
      sessionStorage.setItem("fn_onboarding_project_id", data.id);
      sessionStorage.setItem("fn_onboarding_project_slug", data.slug);
      router.push(`/onboarding/get-api-key?orgId=${orgId}`);
    },
    onError: ({ err }) => {
      toast.error(err.message || "Failed to create project. Please try again.");
    },
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;

    await execute({
      payload: {
        name: name.trim(),
        slug: slug.trim() || toSlug(name.trim()),
        storage_mode: "managed",
        storage_provider: "s3",
      },
    });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create your first project</CardTitle>
        <CardDescription>
          A project is where your files live. You can create more projects later
          from the dashboard.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Project name</Label>
            <Input
              id="name"
              placeholder="My App"
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
              autoFocus
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="slug">
              Slug
              <span className="ml-2 text-xs text-muted-foreground font-normal">
                Used in API calls:{" "}
                <span className="font-mono text-foreground">
                  {slug || "my-app"}
                </span>
              </span>
            </Label>
            <Input
              id="slug"
              placeholder="my-app"
              value={slug}
              onChange={(e) => handleSlugChange(e.target.value)}
              pattern="[a-z0-9-]+"
              title="Lowercase letters, numbers, and hyphens only"
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Storage: Managed S3 — FileNest handles everything for you. You can
            switch to your own bucket in project settings later.
          </p>
          <Button
            type="submit"
            className="w-full"
            disabled={isPending || !name.trim()}
          >
            {isPending ? "Creating…" : "Create project"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
