/**
 * file.rest.service — REST implementation of IFileService.
 *
 * Layer: core / file / infrastructure / services
 *
 * Calls the FileNest FastAPI backend via filenestApi. Validates every
 * response against canonical Zod schemas before returning so schema
 * drift between backend and frontend is caught at the boundary.
 *
 * Bound in the DI container by registerFileModule().
 *
 * @module
 */
"server-only";

import { filenestApi } from "@/modules/server/utils/api-client";
import {
  FileListSchema,
  FileDownloadUrlSchema,
  TagsResponseSchema,
  MetadataResponseSchema,
  type TFileList,
  type TFileDownloadUrl,
  type TListFilesParams,
  type TTagsResponse,
  type TMetadataResponse,
} from "@/modules/entities/schemas/file";
import { OutputParseError } from "@/modules/server/shared/errors/schema-parse-error";
import type { IFileService } from "../../domain/interfaces/file.service.interface";

export class FileRestService implements IFileService {
  async list(
    projectId: string,
    params?: Omit<TListFilesParams, "projectId">,
  ): Promise<TFileList> {
    let qs = "";
    if (params) {
      const parts: string[] = [];
      for (const [k, v] of Object.entries(params)) {
        if (v === undefined || v === null || v === "") continue;
        if (Array.isArray(v)) {
          // tags: repeat the param — ?tags=a&tags=b
          for (const item of v) {
            parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(item))}`);
          }
        } else {
          parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
        }
      }
      if (parts.length > 0) qs = "?" + parts.join("&");
    }
    const raw = await filenestApi<unknown>(`/v1/projects/${projectId}/files${qs}`);
    const parsed = FileListSchema.safeParse(raw);
    if (!parsed.success) throw new OutputParseError(parsed.error);
    return parsed.data;
  }

  async getDownloadUrl(
    projectId: string,
    fileId: string,
    ttl?: number,
  ): Promise<TFileDownloadUrl> {
    const qs = ttl ? `?ttl=${ttl}` : "";
    const raw = await filenestApi<unknown>(
      `/v1/projects/${projectId}/files/${fileId}/download${qs}`,
    );
    const parsed = FileDownloadUrlSchema.safeParse(raw);
    if (!parsed.success) throw new OutputParseError(parsed.error);
    return parsed.data;
  }

  async delete(projectId: string, fileId: string): Promise<void> {
    await filenestApi<void>(`/v1/projects/${projectId}/files/${fileId}`, {
      method: "DELETE",
    });
  }

  async setTags(projectId: string, fileId: string, tags: string[]): Promise<TTagsResponse> {
    const raw = await filenestApi<unknown>(
      `/v1/projects/${projectId}/files/${fileId}/tags`,
      { method: "PUT", body: JSON.stringify({ tags }) },
    );
    const parsed = TagsResponseSchema.safeParse(raw);
    if (!parsed.success) throw new OutputParseError(parsed.error);
    return parsed.data;
  }

  async addTags(projectId: string, fileId: string, tags: string[]): Promise<TTagsResponse> {
    const raw = await filenestApi<unknown>(
      `/v1/projects/${projectId}/files/${fileId}/tags`,
      { method: "POST", body: JSON.stringify({ tags }) },
    );
    const parsed = TagsResponseSchema.safeParse(raw);
    if (!parsed.success) throw new OutputParseError(parsed.error);
    return parsed.data;
  }

  async updateMetadata(projectId: string, fileId: string, metadata: Record<string, unknown>): Promise<TMetadataResponse> {
    const raw = await filenestApi<unknown>(
      `/v1/projects/${projectId}/files/${fileId}/metadata`,
      { method: "PUT", body: JSON.stringify({ metadata }) },
    );
    const parsed = MetadataResponseSchema.safeParse(raw);
    if (!parsed.success) throw new OutputParseError(parsed.error);
    return parsed.data;
  }

  async mergeMetadata(projectId: string, fileId: string, metadata: Record<string, unknown>): Promise<TMetadataResponse> {
    const raw = await filenestApi<unknown>(
      `/v1/projects/${projectId}/files/${fileId}/metadata`,
      { method: "PATCH", body: JSON.stringify({ metadata }) },
    );
    const parsed = MetadataResponseSchema.safeParse(raw);
    if (!parsed.success) throw new OutputParseError(parsed.error);
    return parsed.data;
  }
}
