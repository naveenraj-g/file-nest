/**
 * entities/schemas/api-key/input — validation schemas for API key mutations.
 *
 * @module
 */
import { z } from "zod";

export const AVAILABLE_SCOPES = [
  "files:upload",
  "files:download",
  "files:read",
  "files:delete",
  "files:update_metadata",
  "projects:read",
  "projects:update",
] as const;

export type TScope = (typeof AVAILABLE_SCOPES)[number];

export const CreateApiKeySchema = z.object({
  name: z.string().min(1, "Name is required").max(100),
  organizationId: z.string().min(1),
  projectId: z.string().optional(),
  scopes: z.array(z.enum(AVAILABLE_SCOPES)).min(1, "Select at least one scope"),
  expiresInDays: z.number().int().min(1).max(365).optional(),
});

export type TCreateApiKey = z.infer<typeof CreateApiKeySchema>;

export const ListApiKeysSchema = z.object({
  organizationId: z.string().min(1),
  projectId: z.string().optional(),
});

export type TListApiKeys = z.infer<typeof ListApiKeysSchema>;

export const RevokeApiKeySchema = z.object({
  keyId: z.string().min(1),
});

export type TRevokeApiKey = z.infer<typeof RevokeApiKeySchema>;
