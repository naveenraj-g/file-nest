/**
 * server/di/types — DI symbol registry and return type map.
 *
 * DI_SYMBOLS maps each interface name to a unique Symbol.
 * DI_RETURN_TYPES maps the same keys to their concrete TypeScript interface.
 * Together they give getInjection() full return-type inference.
 *
 * Add a new entry here whenever a new domain module is registered.
 *
 * @module
 */
import type { IProjectService } from "../core/project/domain/interfaces/project.service.interface";
import type { IStorageConfigService } from "../core/storage-config/domain/interfaces/storage-config.service.interface";

export const DI_SYMBOLS = {
  IProjectService: Symbol.for("IProjectService"),
  IStorageConfigService: Symbol.for("IStorageConfigService"),
} as const;

export interface DI_RETURN_TYPES {
  IProjectService: IProjectService;
  IStorageConfigService: IStorageConfigService;
}
