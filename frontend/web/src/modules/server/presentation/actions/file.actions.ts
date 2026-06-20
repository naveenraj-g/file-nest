/**
 * server/presentation/actions/file.actions — ZSA server actions for files.
 *
 * Layer: presentation / actions
 * Resource: File
 *
 * listFilesAction          — read; call from RSC pages or client components.
 * deleteFileAction         — mutation; revalidates the files page.
 * getFileDownloadUrlAction — read; returns presigned URL for client to open.
 *
 * @module
 */
"use server";

import { authenticatedProcedure } from "./procedures";
import { runWithTransport } from "@/modules/server/utils/run-with-transport";
import {
  listFilesController,
  deleteFileController,
  getFileDownloadUrlController,
  type TListFilesControllerOutput,
  type TDeleteFileControllerOutput,
  type TGetFileDownloadUrlControllerOutput,
} from "@/modules/server/core/file/interface-adapters/controllers";
import {
  ListFilesActionSchema,
  DeleteFileActionSchema,
  GetFileDownloadUrlActionSchema,
  type TListFilesAction,
  type TDeleteFileAction,
  type TGetFileDownloadUrlAction,
} from "@/modules/entities/schemas/file";

export const listFilesAction = authenticatedProcedure
  .createServerAction()
  .input(ListFilesActionSchema, { skipInputParsing: true })
  .handler(async ({ input }: { input: TListFilesAction }) => {
    return await runWithTransport<TListFilesControllerOutput>(async () => {
      const data = await listFilesController(input.payload);
      return { result: data, transport: input.transportOptions };
    });
  });

export const deleteFileAction = authenticatedProcedure
  .createServerAction()
  .input(DeleteFileActionSchema, { skipInputParsing: true })
  .handler(async ({ input }: { input: TDeleteFileAction }) => {
    return await runWithTransport<TDeleteFileControllerOutput>(async () => {
      await deleteFileController(input.payload);
      return { result: undefined, transport: input.transportOptions };
    });
  });

export const getFileDownloadUrlAction = authenticatedProcedure
  .createServerAction()
  .input(GetFileDownloadUrlActionSchema, { skipInputParsing: true })
  .handler(async ({ input }: { input: TGetFileDownloadUrlAction }) => {
    return await runWithTransport<TGetFileDownloadUrlControllerOutput>(async () => {
      const data = await getFileDownloadUrlController(input.payload);
      return { result: data, transport: input.transportOptions };
    });
  });
