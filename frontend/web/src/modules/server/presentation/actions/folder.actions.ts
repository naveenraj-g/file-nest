/**
 * server/presentation/actions/folder.actions — ZSA server actions for folders.
 *
 * Layer: presentation / actions
 * Resource: Folder
 *
 * listFoldersAction — read; returns all folders in a project (flat list).
 *
 * @module
 */
"use server";

import { authenticatedProcedure } from "./procedures";
import { runWithTransport } from "@/modules/server/utils/run-with-transport";
import {
  listFoldersController,
  type TListFoldersControllerOutput,
} from "@/modules/server/core/folder/interface-adapters/controllers";
import {
  ListFoldersActionSchema,
  type TListFoldersAction,
} from "@/modules/entities/schemas/folder";

export const listFoldersAction = authenticatedProcedure
  .createServerAction()
  .input(ListFoldersActionSchema, { skipInputParsing: true })
  .handler(async ({ input }: { input: TListFoldersAction }) => {
    return await runWithTransport<TListFoldersControllerOutput>(async () => {
      const data = await listFoldersController(input.payload);
      return { result: data, transport: input.transportOptions };
    });
  });
