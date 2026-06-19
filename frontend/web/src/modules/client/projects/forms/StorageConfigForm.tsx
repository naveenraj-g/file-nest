/**
 * StorageConfigForm — dynamic BYOB storage credentials form.
 *
 * Fields shown/hidden based on the project's storage provider:
 *   - endpoint_url: required for MinIO, R2, RustFS; hidden for S3/Azure/GCS
 *   - region:       shown for S3, Azure Blob, GCS
 *   - server_side_encryption + kms_key_id: S3 only
 *
 * Managed-mode projects render an info banner instead of the form.
 * Credentials are never returned by the API after save (stored encrypted).
 *
 * @module
 */
"use client";

import * as React from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useServerAction } from "zsa-react";
import { toast } from "sonner";
import { CheckCircle2, AlertCircle, Clock, RefreshCw, Save } from "lucide-react";
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
import { cn } from "@/lib/utils";
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

interface StorageConfigFormProps {
  projectId: string;
  config: TStorageConfig;
}

const STATUS_CONFIG = {
  active: { icon: CheckCircle2, label: "Active", className: "text-green-600" },
  pending_verification: {
    icon: Clock,
    label: "Pending verification",
    className: "text-yellow-600",
  },
  verification_failed: {
    icon: AlertCircle,
    label: "Verification failed",
    className: "text-destructive",
  },
} as const;

const PROVIDER_LABELS: Record<TStorageConfig["provider"], string> = {
  s3: "Amazon S3",
  azure_blob: "Azure Blob Storage",
  gcs: "Google Cloud Storage",
  minio: "MinIO",
  r2: "Cloudflare R2",
  rustfs: "RustFS",
};

export function StorageConfigForm({ projectId, config }: StorageConfigFormProps) {
  const provider = config.provider;
  const needsEndpoint = (PROVIDERS_REQUIRING_ENDPOINT as readonly string[]).includes(provider);
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
        toast.success("Storage configuration saved — run Verify to activate it"),
      onError: ({ err }) =>
        handleZSAError({ err, form, fallbackMessage: "Failed to save storage config" }),
    }
  );

  const { execute: verify, isPending: isVerifying } = useServerAction(
    verifyStorageAction,
    {
      onSuccess: ({ data }) => {
        if (data?.ok) {
          toast.success(
            `Connection verified — latency ${data.latency_ms?.toFixed(0) ?? "?"}ms`
          );
        } else {
          toast.error(`Verification failed: ${data?.error ?? "Unknown error"}`);
        }
      },
      onError: ({ err }) =>
        handleZSAError({ err, fallbackMessage: "Verification request failed" }),
    }
  );

  async function onSubmit(values: TStorageConfigForm) {
    const { provider: _p, ...rest } = values;
    await save({
      payload: { projectId, ...rest },
      transportOptions: {
        shouldRevalidate: true,
        url: `/projects/${projectId}/settings`,
      },
    });
  }

  async function onVerify() {
    await verify({
      payload: { projectId },
      transportOptions: {
        shouldRevalidate: true,
        url: `/projects/${projectId}/settings`,
      },
    });
  }

  if (config.storage_mode === "managed") {
    return (
      <div className="rounded-lg border bg-muted/40 p-5 text-sm text-muted-foreground">
        This project uses{" "}
        <strong className="text-foreground">managed storage</strong> — FileNest
        provisions and manages the bucket. No credentials are required.
      </div>
    );
  }

  const statusCfg = STATUS_CONFIG[config.status];
  const StatusIcon = statusCfg.icon;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div
          className={cn(
            "flex items-center gap-2 text-sm font-medium",
            statusCfg.className
          )}
        >
          <StatusIcon className="h-4 w-4" />
          {statusCfg.label}
          {config.last_verified_at && (
            <span className="text-xs font-normal text-muted-foreground">
              · last verified{" "}
              {new Date(config.last_verified_at).toLocaleString()}
            </span>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={onVerify}
          disabled={isVerifying}
        >
          <RefreshCw
            className={cn("h-3.5 w-3.5 mr-1.5", isVerifying && "animate-spin")}
          />
          {isVerifying ? "Verifying…" : "Verify connection"}
        </Button>
      </div>

      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
        <FieldGroup>
          <Controller
            name="bucket_name"
            control={form.control}
            render={({ field, fieldState }) => (
              <Field data-invalid={fieldState.invalid}>
                <FieldLabel htmlFor={field.name}>
                  {provider === "azure_blob" ? "Container name" : "Bucket name"}
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
                  <FieldDescription>Required for this provider</FieldDescription>
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
                <FieldDescription>
                  Stored encrypted — never returned by the API after save.
                </FieldDescription>
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
                    <NativeSelectOption value="AES256">AES-256 (default)</NativeSelectOption>
                    <NativeSelectOption value="aws:kms">AWS KMS</NativeSelectOption>
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

        <div className="pt-1">
          <p className="text-xs text-muted-foreground mb-4">
            Provider:{" "}
            <span className="font-medium text-foreground">
              {PROVIDER_LABELS[provider]}
            </span>
            . After saving, click <strong>Verify connection</strong> to confirm
            access.
          </p>
          <Button type="submit" disabled={isSaving}>
            <Save className="h-4 w-4 mr-1.5" />
            {isSaving ? "Saving…" : "Save credentials"}
          </Button>
        </div>
      </form>
    </div>
  );
}
