/**
 * CreateProjectForm — client form for creating a new project.
 *
 * Uses react-hook-form + zodResolver for local validation and
 * useServerAction(createProjectAction) for submission. Field-level server
 * errors (InputParseError) are applied back to the form via handleZSAError.
 * On success redirects to the new project's file explorer, or calls the
 * optional onSuccess callback (used in the onboarding wizard).
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
import {
  FormInput,
  FormTextarea,
  FormSelect,
  FormSelectOption,
} from "@/modules/client/shared/custom-form-fields";
import { createProjectAction } from "@/modules/server/presentation/actions/project.actions";
import {
  CreateProjectFormSchema,
  type TCreateProjectForm,
} from "@/modules/entities/schemas/project";
import { handleZSAError } from "@/modules/client/shared/error/handle-zsa-error";
import type { TProject } from "@/modules/entities/schemas/project";

interface CreateProjectFormProps {
  onSuccess?: (data: TProject) => void;
}

function toSlug(name: string) {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .slice(0, 48);
}

export function CreateProjectForm({ onSuccess }: CreateProjectFormProps = {}) {
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
      if (onSuccess) {
        onSuccess(data);
      } else {
        toast.success("Project created");
        router.push(`/projects/${data.id}/files`);
      }
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
  const storageMode = form.watch("storage_mode");

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
      <FormInput
        name="name"
        control={form.control}
        label="Project name"
        placeholder="My Project"
        autoFocus
        onChangeSideEffect={(e) => {
          if (!slugEdited) {
            form.setValue("slug", toSlug(e.target.value), { shouldValidate: false });
          }
        }}
      />

      <FormInput
        name="slug"
        control={form.control}
        label="Slug"
        description={`Used in API calls: ${slug || "my-project"}`}
        placeholder="my-project"
        onChangeSideEffect={(e) => {
          setSlugEdited(true);
          form.setValue("slug", toSlug(e.target.value), { shouldValidate: false });
        }}
      />

      <FormTextarea
        name="description"
        control={form.control}
        label="Description (optional)"
        placeholder="A short description of this project"
      />

      <FormSelect
        name="storage_mode"
        control={form.control}
        label="Storage mode"
      >
        <FormSelectOption value="managed">
          Managed — FileNest provisions storage for you
        </FormSelectOption>
        <FormSelectOption value="byob">
          BYOB — Bring your own bucket
        </FormSelectOption>
      </FormSelect>

      {storageMode === "byob" && (
        <p className="text-xs text-muted-foreground">
          You&apos;ll enter bucket credentials in{" "}
          <strong className="text-foreground">Project Settings → Storage</strong>{" "}
          after creation.
        </p>
      )}

      <FormSelect
        name="storage_provider"
        control={form.control}
        label="Storage provider"
      >
        <FormSelectOption value="s3">Amazon S3</FormSelectOption>
        <FormSelectOption value="azure_blob">Azure Blob Storage</FormSelectOption>
        <FormSelectOption value="gcs">Google Cloud Storage</FormSelectOption>
        <FormSelectOption value="minio">MinIO</FormSelectOption>
        <FormSelectOption value="r2">Cloudflare R2</FormSelectOption>
        <FormSelectOption value="restfs">RestFS</FormSelectOption>
      </FormSelect>

      <Button type="submit" className="w-full" disabled={isPending}>
        {isPending ? "Creating…" : "Create project"}
      </Button>
    </form>
  );
}
