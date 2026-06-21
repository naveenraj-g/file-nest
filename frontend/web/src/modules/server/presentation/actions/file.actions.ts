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
  setTagsController,
  addTagsController,
  updateMetadataController,
  mergeMetadataController,
  type TListFilesControllerOutput,
  type TDeleteFileControllerOutput,
  type TGetFileDownloadUrlControllerOutput,
  type TSetTagsControllerOutput,
  type TAddTagsControllerOutput,
  type TUpdateMetadataControllerOutput,
  type TMergeMetadataControllerOutput,
} from "@/modules/server/core/file/interface-adapters/controllers";
import {
  ListFilesActionSchema,
  DeleteFileActionSchema,
  GetFileDownloadUrlActionSchema,
  SetTagsActionSchema,
  AddTagsActionSchema,
  UpdateMetadataActionSchema,
  MergeMetadataActionSchema,
  type TListFilesAction,
  type TDeleteFileAction,
  type TGetFileDownloadUrlAction,
  type TSetTagsAction,
  type TAddTagsAction,
  type TUpdateMetadataAction,
  type TMergeMetadataAction,
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

export const setTagsAction = authenticatedProcedure
  .createServerAction()
  .input(SetTagsActionSchema, { skipInputParsing: true })
  .handler(async ({ input }: { input: TSetTagsAction }) => {
    return await runWithTransport<TSetTagsControllerOutput>(async () => {
      const data = await setTagsController(input.payload);
      return { result: data, transport: input.transportOptions };
    });
  });

export const addTagsAction = authenticatedProcedure
  .createServerAction()
  .input(AddTagsActionSchema, { skipInputParsing: true })
  .handler(async ({ input }: { input: TAddTagsAction }) => {
    return await runWithTransport<TAddTagsControllerOutput>(async () => {
      const data = await addTagsController(input.payload);
      return { result: data, transport: input.transportOptions };
    });
  });

export const updateMetadataAction = authenticatedProcedure
  .createServerAction()
  .input(UpdateMetadataActionSchema, { skipInputParsing: true })
  .handler(async ({ input }: { input: TUpdateMetadataAction }) => {
    return await runWithTransport<TUpdateMetadataControllerOutput>(async () => {
      const data = await updateMetadataController(input.payload);
      return { result: data, transport: input.transportOptions };
    });
  });

export const mergeMetadataAction = authenticatedProcedure
  .createServerAction()
  .input(MergeMetadataActionSchema, { skipInputParsing: true })
  .handler(async ({ input }: { input: TMergeMetadataAction }) => {
    return await runWithTransport<TMergeMetadataControllerOutput>(async () => {
      const data = await mergeMetadataController(input.payload);
      return { result: data, transport: input.transportOptions };
    });
  });
