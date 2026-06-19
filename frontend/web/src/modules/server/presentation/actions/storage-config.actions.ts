/**
 * storage-config.actions — ZSA server actions for project storage configuration.
 *
 * getStorageConfigAction   — read; safe to call from RSC pages.
 * updateStorageConfigAction — mutation; saves BYOB credentials.
 * verifyStorageAction       — mutation; runs the connectivity probe.
 *
 * @module
 */
"use server";

import { authenticatedProcedure } from "./procedures";
import { runWithTransport } from "@/modules/server/utils/run-with-transport";
import {
  getStorageConfigController,
  updateStorageConfigController,
  verifyStorageConfigController,
  type TGetStorageConfigControllerOutput,
  type TUpdateStorageConfigControllerOutput,
  type TVerifyStorageConfigControllerOutput,
} from "@/modules/server/core/storage-config/interface-adapters/controllers";
import {
  GetStorageConfigActionSchema,
  UpdateStorageConfigActionSchema,
  VerifyStorageActionSchema,
  type TGetStorageConfigAction,
  type TUpdateStorageConfigAction,
  type TVerifyStorageAction,
} from "@/modules/entities/schemas/storage-config";

export const getStorageConfigAction = authenticatedProcedure
  .createServerAction()
  .input(GetStorageConfigActionSchema, { skipInputParsing: true })
  .handler(async ({ input }: { input: TGetStorageConfigAction }) => {
    return await runWithTransport<TGetStorageConfigControllerOutput>(async () => {
      const data = await getStorageConfigController(input.payload);
      return { result: data, transport: input.transportOptions };
    });
  });

export const updateStorageConfigAction = authenticatedProcedure
  .createServerAction()
  .input(UpdateStorageConfigActionSchema, { skipInputParsing: true })
  .handler(async ({ input }: { input: TUpdateStorageConfigAction }) => {
    return await runWithTransport<TUpdateStorageConfigControllerOutput>(async () => {
      const data = await updateStorageConfigController(input.payload);
      return { result: data, transport: input.transportOptions };
    });
  });

export const verifyStorageAction = authenticatedProcedure
  .createServerAction()
  .input(VerifyStorageActionSchema, { skipInputParsing: true })
  .handler(async ({ input }: { input: TVerifyStorageAction }) => {
    return await runWithTransport<TVerifyStorageConfigControllerOutput>(async () => {
      const data = await verifyStorageConfigController(input.payload);
      return { result: data, transport: input.transportOptions };
    });
  });
