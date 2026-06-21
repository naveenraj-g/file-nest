/**
 * folder.service.interface — domain contract for folder API access.
 *
 * @module
 */
import type { TFolderList } from "@/modules/entities/schemas/folder";

export interface IFolderService {
  /** Returns all active folders in the project, ordered by path. */
  list(projectId: string): Promise<TFolderList>;
}
