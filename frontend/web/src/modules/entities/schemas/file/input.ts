/**
 * entities/schemas/file/input — validation schemas for file operations.
 *
 * Used by controllers (server-side Zod validation) and the client
 * for typed payloads. No Next.js or React imports here.
 *
 * @module
 */
import { z } from "zod";

export const ListFilesParamsSchema = z.object({
  projectId: z.string().min(1),
  folder_id: z.string().optional(),
  limit: z.number().int().min(1).max(200).optional(),
  cursor: z.string().optional(),
});

export type TListFilesParams = z.infer<typeof ListFilesParamsSchema>;

export const DeleteFileSchema = z.object({
  projectId: z.string().min(1),
  fileId: z.string().min(1),
});

export type TDeleteFile = z.infer<typeof DeleteFileSchema>;

export const GetFileDownloadUrlSchema = z.object({
  projectId: z.string().min(1),
  fileId: z.string().min(1),
  ttl: z.number().int().min(60).max(86400).optional(),
});

export type TGetFileDownloadUrl = z.infer<typeof GetFileDownloadUrlSchema>;
