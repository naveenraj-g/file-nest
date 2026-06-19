/**
 * CreateProjectForm — client form for creating a new project.
 *
 * Uses react-hook-form + zodResolver for local validation and
 * useServerAction(createProjectAction) for submission. Field-level server
 * errors (InputParseError) are applied back to the form via handleZSAError.
 * On success the user is redirected to the new project's file explorer.
 *
 * @module
 */
"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useServerAction } from "zsa-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { FieldError } from "@/components/ui/field";
import { createProjectAction } from "@/modules/server/presentation/actions/project.actions";
import {
  CreateProjectFormSchema,
  type TCreateProjectForm,
} from "@/modules/entities/schemas/project";
import { handleZSAError } from "@/modules/client/shared/error/handle-zsa-error";

function toSlug(name: string) {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .slice(0, 48);
}

export function CreateProjectForm() {
  const router = useRouter();
  const [slugEdited, setSlugEdited] = React.useState(false);

  const form = useForm<TCreateProjectForm>({
    resolver: zodResolver(CreateProjectFormSchema),
    defaultValues: {
      name: "",
      slug: "",
      description: "",
      storage_mode: "managed",
      storage_provider: "s3",
    },
  });

  const { execute, isPending } = useServerAction(createProjectAction, {
    onSuccess: ({ data }) => {
      toast.success("Project created");
      router.push(`/projects/${data.id}/files`);
    },
    onError: ({ err }) =>
      handleZSAError({ err, form, fallbackMessage: "Failed to create project" }),
  });

  async function onSubmit(values: TCreateProjectForm) {
    await execute({
      payload: values,
      transportOptions: { shouldRevalidate: true, url: "/projects" },
    });
  }

  const slug = form.watch("slug");
  const errors = form.formState.errors;

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
      {/* Name */}
      <div className="space-y-1.5">
        <Label htmlFor="name">Project name</Label>
        <Input
          id="name"
          placeholder="My Project"
          autoFocus
          aria-invalid={!!errors.name}
          {...form.register("name", {
            onChange: (e: React.ChangeEvent<HTMLInputElement>) => {
              if (!slugEdited) {
                form.setValue("slug", toSlug(e.target.value), {
                  shouldValidate: false,
                });
              }
            },
          })}
        />
        {errors.name && <FieldError errors={[errors.name]} />}
      </div>

      {/* Slug */}
      <div className="space-y-1.5">
        <Label htmlFor="slug">
          Slug
          <span className="ml-2 text-xs text-muted-foreground font-normal">
            Used in API calls:{" "}
            <span className="font-mono text-foreground">
              {slug || "my-project"}
            </span>
          </span>
        </Label>
        <Input
          id="slug"
          placeholder="my-project"
          aria-invalid={!!errors.slug}
          {...form.register("slug", {
            onChange: (e: React.ChangeEvent<HTMLInputElement>) => {
              setSlugEdited(true);
              form.setValue("slug", toSlug(e.target.value), {
                shouldValidate: false,
              });
            },
          })}
        />
        {errors.slug && <FieldError errors={[errors.slug]} />}
      </div>

      {/* Description */}
      <div className="space-y-1.5">
        <Label htmlFor="description">
          Description{" "}
          <span className="font-normal text-muted-foreground">(optional)</span>
        </Label>
        <Textarea
          id="description"
          placeholder="A short description of this project"
          aria-invalid={!!errors.description}
          {...form.register("description")}
        />
        {errors.description && <FieldError errors={[errors.description]} />}
      </div>

      {/* Storage mode */}
      <div className="space-y-1.5">
        <Label htmlFor="storage_mode">Storage mode</Label>
        <NativeSelect
          id="storage_mode"
          className="w-full"
          aria-invalid={!!errors.storage_mode}
          {...form.register("storage_mode")}
        >
          <NativeSelectOption value="managed">
            Managed — FileNest provisions storage for you
          </NativeSelectOption>
          <NativeSelectOption value="byob">
            BYOB — Bring your own bucket
          </NativeSelectOption>
        </NativeSelect>
        {errors.storage_mode && <FieldError errors={[errors.storage_mode]} />}
      </div>

      {/* Storage provider */}
      <div className="space-y-1.5">
        <Label htmlFor="storage_provider">Storage provider</Label>
        <NativeSelect
          id="storage_provider"
          className="w-full"
          aria-invalid={!!errors.storage_provider}
          {...form.register("storage_provider")}
        >
          <NativeSelectOption value="s3">Amazon S3</NativeSelectOption>
          <NativeSelectOption value="azure_blob">
            Azure Blob Storage
          </NativeSelectOption>
          <NativeSelectOption value="gcs">
            Google Cloud Storage
          </NativeSelectOption>
          <NativeSelectOption value="minio">MinIO</NativeSelectOption>
          <NativeSelectOption value="r2">Cloudflare R2</NativeSelectOption>
          <NativeSelectOption value="restfs">RestFS</NativeSelectOption>
        </NativeSelect>
        {errors.storage_provider && (
          <FieldError errors={[errors.storage_provider]} />
        )}
      </div>

      <Button type="submit" className="w-full" disabled={isPending}>
        {isPending ? "Creating…" : "Create project"}
      </Button>
    </form>
  );
}
