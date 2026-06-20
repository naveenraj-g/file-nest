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
  type TFileList,
  type TFileDownloadUrl,
  type TListFilesParams,
} from "@/modules/entities/schemas/file";
import { OutputParseError } from "@/modules/server/shared/errors/schema-parse-error";
import type { IFileService } from "../../domain/interfaces/file.service.interface";

export class FileRestService implements IFileService {
  async list(
    projectId: string,
    params?: Omit<TListFilesParams, "projectId">,
  ): Promise<TFileList> {
    const qs = params
      ? "?" +
        new URLSearchParams(
          Object.entries(params)
            .filter(([, v]) => v !== undefined && v !== null && v !== "")
            .map(([k, v]) => [k, String(v)]),
        ).toString()
      : "";
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
}
