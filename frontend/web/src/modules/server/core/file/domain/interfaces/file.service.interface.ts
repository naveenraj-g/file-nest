/**
 * file.service.interface — domain contract for file API access.
 *
 * Layer: core / file / domain / interfaces
 *
 * Use cases depend on this interface, not the concrete REST implementation.
 * Swap the implementation via the DI module without touching use cases or controllers.
 *
 * @module
 */
import type {
  TFileList,
  TFileDownloadUrl,
  TListFilesParams,
} from "@/modules/entities/schemas/file";

export interface IFileService {
  /**
   * Returns a page of files for the given project.
   * @param projectId - Target project ID.
   * @param params    - Optional limit, cursor, folder_id filter.
   * @throws ApiError on backend failure.
   */
  list(projectId: string, params?: Omit<TListFilesParams, "projectId">): Promise<TFileList>;

  /**
   * Generates a presigned download URL for a file.
   * @param projectId - Target project ID.
   * @param fileId    - Target file ID.
   * @param ttl       - URL TTL in seconds (default: 3600).
   * @throws ApiError on backend failure.
   */
  getDownloadUrl(projectId: string, fileId: string, ttl?: number): Promise<TFileDownloadUrl>;

  /**
   * Soft-deletes a file. Bytes are removed asynchronously via background event.
   * @param projectId - Target project ID.
   * @param fileId    - Target file ID.
   * @throws ApiError on backend failure.
   */
  delete(projectId: string, fileId: string): Promise<void>;
}
