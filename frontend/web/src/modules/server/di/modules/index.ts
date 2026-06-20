/**
 * Barrel export for all DI module registration functions.
 * Import from here in container.ts to keep it tidy as new domains are added.
 */
export { registerProjectModule } from "./project/project.module";
export { registerStorageConfigModule } from "./storage-config/storage-config.module";
export { registerProjectConfigModule } from "./project-config/project-config.module";
export { registerApiKeyModule } from "./api-key/api-key.module";
export { registerFileModule } from "./file/file.module";
