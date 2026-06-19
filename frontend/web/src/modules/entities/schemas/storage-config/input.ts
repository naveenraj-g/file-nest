/**
 * entities/schemas/storage-config/input — mutation schemas for storage config.
 *
 * Used by the controller (server-side validation) and the client form resolver.
 * No Next.js or React imports here — safe in both environments.
 *
 * @module
 */
import { z } from "zod";

export const UpdateStorageConfigSchema = z.object({
  projectId: z.string().min(1),
  bucket_name: z.string().min(1, "Bucket name is required"),
  region: z.string().optional(),
  endpoint_url: z.string().optional(),
  access_key_id: z.string().min(1, "Access key ID is required"),
  secret_access_key: z.string().min(1, "Secret access key is required"),
  server_side_encryption: z.enum(["AES256", "aws:kms"]).default("AES256"),
  kms_key_id: z.string().optional(),
});

export type TUpdateStorageConfig = z.infer<typeof UpdateStorageConfigSchema>;

export const VerifyStorageSchema = z.object({
  projectId: z.string().min(1),
});

export type TVerifyStorage = z.infer<typeof VerifyStorageSchema>;
