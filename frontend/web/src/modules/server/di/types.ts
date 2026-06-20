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
import type { IProjectConfigService } from "../core/project-config/domain/interfaces/project-config.service.interface";
import type { IApiKeyService } from "../core/api-key/domain/interfaces/api-key.service.interface";
import type { IFileService } from "../core/file/domain/interfaces/file.service.interface";

export const DI_SYMBOLS = {
  IProjectService: Symbol.for("IProjectService"),
  IStorageConfigService: Symbol.for("IStorageConfigService"),
  IProjectConfigService: Symbol.for("IProjectConfigService"),
  IApiKeyService: Symbol.for("IApiKeyService"),
  IFileService: Symbol.for("IFileService"),
} as const;

export interface DI_RETURN_TYPES {
  IProjectService: IProjectService;
  IStorageConfigService: IStorageConfigService;
  IProjectConfigService: IProjectConfigService;
  IApiKeyService: IApiKeyService;
  IFileService: IFileService;
}
