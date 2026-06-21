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
  TTagsResponse,
  TMetadataResponse,
} from "@/modules/entities/schemas/file";

export interface IFileService {
  list(projectId: string, params?: Omit<TListFilesParams, "projectId">): Promise<TFileList>;
  getDownloadUrl(projectId: string, fileId: string, ttl?: number): Promise<TFileDownloadUrl>;
  delete(projectId: string, fileId: string): Promise<void>;
  /** Replace the full tag list on a file (PUT). */
  setTags(projectId: string, fileId: string, tags: string[]): Promise<TTagsResponse>;
  /** Append tags not already present on the file (POST — union). */
  addTags(projectId: string, fileId: string, tags: string[]): Promise<TTagsResponse>;
  /** Replace the entire metadata object on a file (PUT). */
  updateMetadata(projectId: string, fileId: string, metadata: Record<string, unknown>): Promise<TMetadataResponse>;
  /** Merge specific keys into the file's existing metadata (PATCH). */
  mergeMetadata(projectId: string, fileId: string, metadata: Record<string, unknown>): Promise<TMetadataResponse>;
}
