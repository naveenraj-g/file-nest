/**
 * StorageConfigForm — storage configuration for a project.
 *
 * Renders two modes:
 *   managed — StorageInfoCard only (details + test button; no credentials to enter)
 *   byob    — StorageInfoCard (current status + details) + credential form below
 *
 * Credentials are never returned by the API after save (stored encrypted), so
 * access_key_id / secret_access_key fields are always empty on load.
 *
 * @module
 */
"use client";

import * as React from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useServerAction } from "zsa-react";
import { toast } from "sonner";
import { Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import {
  Field,
  FieldLabel,
  FieldDescription,
  FieldError,
  FieldGroup,
} from "@/components/ui/field";
import {
  updateStorageConfigAction,
  verifyStorageAction,
} from "@/modules/server/presentation/actions/storage-config.actions";
import {
  StorageConfigFormSchema,
  PROVIDERS_REQUIRING_ENDPOINT,
  type TStorageConfigForm,
  type TStorageConfig,
} from "@/modules/entities/schemas/storage-config";
import { handleZSAError } from "@/modules/client/shared/error/handle-zsa-error";
import { StorageInfoCard } from "@/modules/client/projects/components/settings/StorageInfoCard";

interface StorageConfigFormProps {
  projectId: string;
  config: TStorageConfig;
}

export function StorageConfigForm({
  projectId,
  config,
}: StorageConfigFormProps) {
  const provider = config.provider;
  const needsEndpoint = (
    PROVIDERS_REQUIRING_ENDPOINT as readonly string[]
  ).includes(provider);
  const isS3 = provider === "s3";

  const form = useForm<TStorageConfigForm>({
    resolver: zodResolver(StorageConfigFormSchema),
    defaultValues: {
      provider,
      bucket_name: config.bucket_name ?? "",
      region: config.region ?? "",
      endpoint_url: config.endpoint_url ?? "",
      access_key_id: "",
      secret_access_key: "",
      server_side_encryption:
        (config.server_side_encryption as "AES256" | "aws:kms") ?? "AES256",
      kms_key_id: "",
    },
  });

  const sse = form.watch("server_side_encryption");

  const { execute: save, isPending: isSaving } = useServerAction(
    updateStorageConfigAction,
    {
      onSuccess: () =>
        toast.success("Credentials saved — click Test connection to activate"),
      onError: ({ err }) =>
        handleZSAError({
          err,
          form,
          fallbackMessage: "Failed to save storage config",
        }),
    },
  );

  const { execute: verify, isPending: isVerifying } = useServerAction(
    verifyStorageAction,
    {
      onSuccess: ({ data }) => {
        if (data?.ok) {
          toast.success(
            `Connection verified — latency ${data.latency_ms?.toFixed(0) ?? "?"}ms`,
          );
        } else {
          toast.error(`Verification failed: ${data?.error ?? "Unknown error"}`);
        }
      },
      onError: ({ err }) =>
        handleZSAError({ err, fallbackMessage: "Verification request failed" }),
    },
  );

  async function onSubmit(values: TStorageConfigForm) {
    const { provider: _p, ...rest } = values;
    await save({
      payload: { projectId, ...rest },
      transportOptions: {
        shouldRevalidate: true,
        url: `/projects/${projectId}/settings/storage`,
      },
    });
  }

  async function onVerify() {
    await verify({
      payload: { projectId },
      transportOptions: {
        shouldRevalidate: true,
        url: `/projects/${projectId}/settings/storage`,
      },
    });
  }

  // Managed mode — show details card only; no credentials to configure
  if (config.storage_mode === "managed") {
    return (
      <StorageInfoCard
        config={config}
        onVerify={onVerify}
        isVerifying={isVerifying}
      />
    );
  }

  // BYOB mode — details card + credential form
  return (
    <div className="space-y-6">
      <StorageInfoCard
        config={config}
        onVerify={onVerify}
        isVerifying={isVerifying}
      />

      <div>
        <h3 className="text-sm font-medium mb-1">Credentials</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Stored encrypted — never returned by the API after save.
        </p>

        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
          <FieldGroup>
            <Controller
              name="bucket_name"
              control={form.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor={field.name}>
                    {provider === "azure_blob"
                      ? "Container name"
                      : "Bucket name"}
                  </FieldLabel>
                  <Input
                    {...field}
                    id={field.name}
                    placeholder={
                      provider === "azure_blob" ? "my-container" : "my-bucket"
                    }
                    aria-invalid={fieldState.invalid}
                  />
                  {fieldState.invalid && (
                    <FieldError errors={[fieldState.error]} />
                  )}
                </Field>
              )}
            />

            {needsEndpoint && (
              <Controller
                name="endpoint_url"
                control={form.control}
                render={({ field, fieldState }) => (
                  <Field data-invalid={fieldState.invalid}>
                    <FieldLabel htmlFor={field.name}>Endpoint URL</FieldLabel>
                    <FieldDescription>
                      Required for this provider
                    </FieldDescription>
                    <Input
                      {...field}
                      id={field.name}
                      placeholder={
                        provider === "r2"
                          ? "https://<account_id>.r2.cloudflarestorage.com"
                          : "http://localhost:9000"
                      }
                      aria-invalid={fieldState.invalid}
                    />
                    {fieldState.invalid && (
                      <FieldError errors={[fieldState.error]} />
                    )}
                  </Field>
                )}
              />
            )}

            {!needsEndpoint && (
              <Controller
                name="region"
                control={form.control}
                render={({ field, fieldState }) => (
                  <Field data-invalid={fieldState.invalid}>
                    <FieldLabel htmlFor={field.name}>Region</FieldLabel>
                    {provider !== "s3" && (
                      <FieldDescription>Optional</FieldDescription>
                    )}
                    <Input
                      {...field}
                      id={field.name}
                      placeholder="us-east-1"
                      aria-invalid={fieldState.invalid}
                    />
                    {fieldState.invalid && (
                      <FieldError errors={[fieldState.error]} />
                    )}
                  </Field>
                )}
              />
            )}

            <Controller
              name="access_key_id"
              control={form.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor={field.name}>
                    {provider === "azure_blob"
                      ? "Storage account name"
                      : "Access key ID"}
                  </FieldLabel>
                  <Input
                    {...field}
                    id={field.name}
                    placeholder={
                      provider === "azure_blob"
                        ? "mystorageaccount"
                        : "AKIAIOSFODNN7EXAMPLE"
                    }
                    autoComplete="off"
                    aria-invalid={fieldState.invalid}
                  />
                  {fieldState.invalid && (
                    <FieldError errors={[fieldState.error]} />
                  )}
                </Field>
              )}
            />

            <Controller
              name="secret_access_key"
              control={form.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor={field.name}>
                    {provider === "azure_blob"
                      ? "Storage access key"
                      : "Secret access key"}
                  </FieldLabel>
                  <Input
                    {...field}
                    id={field.name}
                    type="password"
                    placeholder="••••••••••••••••••••••••••••••••"
                    autoComplete="new-password"
                    aria-invalid={fieldState.invalid}
                  />
                  {fieldState.invalid && (
                    <FieldError errors={[fieldState.error]} />
                  )}
                </Field>
              )}
            />

            {isS3 && (
              <Controller
                name="server_side_encryption"
                control={form.control}
                render={({ field, fieldState }) => (
                  <Field data-invalid={fieldState.invalid}>
                    <FieldLabel htmlFor={field.name}>
                      Server-side encryption
                    </FieldLabel>
                    <NativeSelect
                      id={field.name}
                      value={field.value}
                      onChange={field.onChange}
                      onBlur={field.onBlur}
                      ref={field.ref}
                      aria-invalid={fieldState.invalid}
                      className="w-full"
                    >
                      <NativeSelectOption value="AES256">
                        AES-256 (default)
                      </NativeSelectOption>
                      <NativeSelectOption value="aws:kms">
                        AWS KMS
                      </NativeSelectOption>
                    </NativeSelect>
                    {fieldState.invalid && (
                      <FieldError errors={[fieldState.error]} />
                    )}
                  </Field>
                )}
              />
            )}

            {isS3 && sse === "aws:kms" && (
              <Controller
                name="kms_key_id"
                control={form.control}
                render={({ field, fieldState }) => (
                  <Field data-invalid={fieldState.invalid}>
                    <FieldLabel htmlFor={field.name}>KMS key ARN</FieldLabel>
                    <Input
                      {...field}
                      id={field.name}
                      placeholder="arn:aws:kms:us-east-1:123456789:key/…"
                      aria-invalid={fieldState.invalid}
                    />
                    {fieldState.invalid && (
                      <FieldError errors={[fieldState.error]} />
                    )}
                  </Field>
                )}
              />
            )}
          </FieldGroup>

          <Button type="submit" disabled={isSaving}>
            <Save className="h-4 w-4 mr-1.5" />
            {isSaving ? "Saving…" : "Save credentials"}
          </Button>
        </form>
      </div>
    </div>
  );
}
