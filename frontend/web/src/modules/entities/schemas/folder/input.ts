/**
 * entities/schemas/folder/input — validation schemas for folder operations.
 *
 * @module
 */
import { z } from "zod";

export const ListFoldersParamsSchema = z.object({
  projectId: z.string().min(1),
});

export type TListFoldersParams = z.infer<typeof ListFoldersParamsSchema>;
