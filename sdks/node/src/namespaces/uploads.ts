/**
 * @filenest/node namespaces/uploads — UploadsNamespace for resumable multipart sessions.
 * @module
 */

import type { Readable } from "stream";
import type { FileNestHttpClient, FileRecord, UploadProgress, UploadSession } from "@filenest/core";

export interface UploadSessionCreateOptions {
  filename: string;
  size: number;
  mimeType?: string;
  folderId?: string;
  metadata?: Record<string, unknown>;
  tags?: string[];
}

export interface ResumeUploadOptions {
  data: Buffer | Readable;
  onProgress?: (progress: UploadProgress) => void;
}

export class UploadsNamespace {
  constructor(
    private readonly http: FileNestHttpClient,
    private readonly projectId: string
  ) {}

  async create(options: UploadSessionCreateOptions): Promise<UploadSession> {
    return this.http.post(`/v1/projects/${this.projectId}/files/upload/multipart/start`, {
      filename: options.filename,
      size: options.size,
      mime_type: options.mimeType ?? "application/octet-stream",
      folder_id: options.folderId,
      metadata: options.metadata,
      tags: options.tags,
    });
  }

  async resume(sessionId: string, options: ResumeUploadOptions): Promise<FileRecord> {
    let data: Buffer;
    if (Buffer.isBuffer(options.data)) {
      data = options.data;
    } else {
      const { default: streamToBuffer } = await import("../utils/stream-to-buffer.js");
      data = await streamToBuffer(options.data as Readable);
    }

    const CHUNK_SIZE = 5 * 1024 * 1024;
    const totalChunks = Math.ceil(data.length / CHUNK_SIZE);
    const etags: { partNumber: number; etag: string }[] = [];

    for (let i = 0; i < totalChunks; i++) {
      const start = i * CHUNK_SIZE;
      const chunk = data.slice(start, start + CHUNK_SIZE);

      const { url } = await this.http.get<{ url: string }>(
        `/v1/projects/${this.projectId}/files/upload/multipart/${sessionId}/part-url`,
        { part: i + 1 }
      );

      const partRes = await fetch(url, { method: "PUT", body: chunk });
      const etag = partRes.headers.get("etag") ?? "";
      etags.push({ partNumber: i + 1, etag });

      options.onProgress?.({
        bytesUploaded: Math.min((i + 1) * CHUNK_SIZE, data.length),
        totalBytes: data.length,
        percentage: Math.round(((i + 1) / totalChunks) * 100),
        chunkNumber: i + 1,
        totalChunks,
      });
    }

    return this.http.post(`/v1/projects/${this.projectId}/files/upload/multipart/${sessionId}/complete`, {
      parts: etags,
    });
  }
}
