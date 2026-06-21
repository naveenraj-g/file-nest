/**
 * entities/schemas/folder/actions — ZSA action envelope schemas for folders.
 *
 * @module
 */
import { z } from "zod";
import { TransportOptionsSchema } from "../transport";
import { ListFoldersParamsSchema } from "./input";

export const ListFoldersActionSchema = z.object({
  payload: ListFoldersParamsSchema,
  transportOptions: TransportOptionsSchema.optional(),
});

export type TListFoldersAction = z.infer<typeof ListFoldersActionSchema>;
