/**
 * entities/schemas/file/actions — ZSA action envelope schemas for files.
 *
 * Every action schema carries transportOptions so any action can trigger
 * revalidation or redirect after it completes.
 *
 * @module
 */
import { z } from "zod";
import { TransportOptionsSchema } from "../transport";
import {
  ListFilesParamsSchema,
  DeleteFileSchema,
  GetFileDownloadUrlSchema,
} from "./input";

export const ListFilesActionSchema = z.object({
  payload: ListFilesParamsSchema,
  transportOptions: TransportOptionsSchema.optional(),
});

export type TListFilesAction = z.infer<typeof ListFilesActionSchema>;

export const DeleteFileActionSchema = z.object({
  payload: DeleteFileSchema,
  transportOptions: TransportOptionsSchema.optional(),
});

export type TDeleteFileAction = z.infer<typeof DeleteFileActionSchema>;

export const GetFileDownloadUrlActionSchema = z.object({
  payload: GetFileDownloadUrlSchema,
  transportOptions: TransportOptionsSchema.optional(),
});

export type TGetFileDownloadUrlAction = z.infer<typeof GetFileDownloadUrlActionSchema>;
