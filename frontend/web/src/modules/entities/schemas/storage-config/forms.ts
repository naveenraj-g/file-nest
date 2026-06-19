/**
 * entities/schemas/storage-config/forms — React Hook Form schema for the BYOB settings form.
 *
 * Adds cross-field validation on top of the input schema:
 *  - endpoint_url is required when provider is minio, r2, or restfs
 *  - kms_key_id is required when server_side_encryption is aws:kms
 *
 * @module
 */
import { z } from "zod";

export const PROVIDERS_REQUIRING_ENDPOINT = ["minio", "r2", "restfs"] as const;

export const StorageConfigFormSchema = z
  .object({
    bucket_name: z.string().min(1, "Bucket name is required"),
    region: z.string().optional(),
    endpoint_url: z.string().optional(),
    access_key_id: z.string().min(1, "Access key ID is required"),
    secret_access_key: z.string().min(1, "Secret access key is required"),
    server_side_encryption: z.enum(["AES256", "aws:kms"]).default("AES256"),
    kms_key_id: z.string().optional(),
    // provider is read-only (set at project creation), passed for conditional validation
    provider: z.enum(["s3", "azure_blob", "gcs", "minio", "r2", "restfs"]),
  })
  .superRefine((data, ctx) => {
    if (
      (PROVIDERS_REQUIRING_ENDPOINT as readonly string[]).includes(data.provider) &&
      !data.endpoint_url
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["endpoint_url"],
        message: "Endpoint URL is required for this provider",
      });
    }
    if (data.server_side_encryption === "aws:kms" && !data.kms_key_id) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["kms_key_id"],
        message: "KMS key ARN is required when using aws:kms encryption",
      });
    }
  });

export type TStorageConfigForm = z.infer<typeof StorageConfigFormSchema>;
