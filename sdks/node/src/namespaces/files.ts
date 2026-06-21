/**
 * @filenest/node namespaces/files — FilesNamespace implementation.
 *
 * Provides all file operations: upload (single + auto-multipart), download,
 * list, get, update metadata/tags, soft delete, restore, and version management.
 *
 * @module
 */

import { createHmac } from "crypto";
import type { Readable } from "stream";
import type { FileNestHttpClient } from "@filenest/core";
import type {
  DownloadUrlResponse,
  FileRecord,
  FileVersion,
  ListResponse,
  UploadProgress,
} from "@filenest/core";

const MULTIPART_THRESHOLD = 5 * 1024 * 1024; // 5 MB

export interface UploadOptions {
  filename: string;
  data: Buffer | Readable | Uint8Array;
  mimeType?: string;
  size?: number;
  folderId?: string;
  metadata?: Record<string, unknown>;
  tags?: string[];
  onProgress?: (progress: UploadProgress) => void;
}

export interface FileListFilters {
  folderId?: string;
  mimeType?: string;
  status?: string;
  tags?: string[];
  limit?: number;
  offset?: number;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
  metadata?: Record<string, string>;
}

export interface FileUpdateOptions {
  tags?: string[];
  metadata?: Record<string, unknown>;
  filename?: string;
}

export interface VersionCreateOptions {
  data: Buffer | Readable;
  size?: number;
  mimeType?: string;
  changeNote?: string;
}

export interface GetDownloadUrlOptions {
  ttl?: number;
  disposition?: "inline" | "attachment";
}

class FileVersionsNamespace {
  constructor(
    private readonly http: FileNestHttpClient,
    private readonly projectId: string
  ) {}

  async list(fileId: string): Promise<ListResponse<FileVersion>> {
    return this.http.get(`/v1/projects/${this.projectId}/files/${fileId}/versions`);
  }

  async create(fileId: string, options: VersionCreateOptions): Promise<FileRecord> {
    const body = Buffer.isBuffer(options.data)
      ? options.data
      : await streamToBuffer(options.data as Readable);

    const form = new FormData();
    form.append("file", new Blob([body], { type: options.mimeType ?? "application/octet-stream" }), options.mimeType);
    if (options.changeNote) form.append("change_note", options.changeNote);

    return this.http.rawFetch(`/v1/projects/${this.projectId}/files/${fileId}/versions`, {
      method: "POST",
      body: form,
    }).then((r) => r.json() as Promise<FileRecord>);
  }

  async rollback(fileId: string, versionNumber: number, options?: { changeNote?: string }): Promise<FileRecord> {
    return this.http.post(`/v1/projects/${this.projectId}/files/${fileId}/versions/${versionNumber}/restore`, options);
  }
}

async function streamToBuffer(stream: Readable): Promise<Buffer> {
  const chunks: Buffer[] = [];
  for await (const chunk of stream) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk as Uint8Array));
  }
  return Buffer.concat(chunks);
}

export class FilesNamespace {
  readonly versions: FileVersionsNamespace;

  constructor(
    private readonly http: FileNestHttpClient,
    private readonly projectId: string
  ) {
    this.versions = new FileVersionsNamespace(http, projectId);
  }

  async upload(options: UploadOptions): Promise<FileRecord> {
    let data: Buffer;
    if (Buffer.isBuffer(options.data) || options.data instanceof Uint8Array) {
      data = Buffer.from(options.data);
    } else {
      data = await streamToBuffer(options.data as Readable);
    }

    if (data.length >= MULTIPART_THRESHOLD) {
      return this._multipartUpload(data, options);
    }
    return this._singleUpload(data, options);
  }

  private async _singleUpload(data: Buffer, options: UploadOptions): Promise<FileRecord> {
    const form = new FormData();
    form.append(
      "file",
      new Blob([data], { type: options.mimeType ?? "application/octet-stream" }),
      options.filename
    );
    if (options.folderId) form.append("folder_id", options.folderId);
    if (options.metadata) form.append("metadata", JSON.stringify(options.metadata));
    if (options.tags) form.append("tags", JSON.stringify(options.tags));

    const res = await this.http.rawFetch(`/v1/projects/${this.projectId}/files/upload`, {
      method: "POST",
      body: form,
    });
    return res.json() as Promise<FileRecord>;
  }

  private async _multipartUpload(data: Buffer, options: UploadOptions): Promise<FileRecord> {
    // Start multipart session
    const session = await this.http.post<{ upload_id: string; file_id: string }>(
      `/v1/projects/${this.projectId}/files/upload/multipart/start`,
      {
        filename: options.filename,
        size: data.length,
        mime_type: options.mimeType ?? "application/octet-stream",
        folder_id: options.folderId,
        metadata: options.metadata,
        tags: options.tags,
      }
    );

    const CHUNK_SIZE = 5 * 1024 * 1024;
    const totalChunks = Math.ceil(data.length / CHUNK_SIZE);
    const etags: { partNumber: number; etag: string }[] = [];

    for (let i = 0; i < totalChunks; i++) {
      const start = i * CHUNK_SIZE;
      const chunk = data.slice(start, start + CHUNK_SIZE);

      // Get presigned URL for this part
      const { url } = await this.http.get<{ url: string }>(
        `/v1/projects/${this.projectId}/files/upload/multipart/${session.upload_id}/part-url`,
        { part: i + 1 }
      );

      // Upload part directly to storage
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

    // Complete multipart upload
    return this.http.post(`/v1/projects/${this.projectId}/files/upload/multipart/${session.upload_id}/complete`, {
      parts: etags,
    });
  }

  async download(fileId: string): Promise<Readable> {
    const res = await this.http.rawFetch(`/v1/projects/${this.projectId}/files/${fileId}/download`, {
      method: "GET",
    });
    // In Node 18+ ReadableStream is available; convert to Node Readable
    const { Readable } = await import("stream");
    return Readable.fromWeb(res.body as unknown as ReadableStream<Uint8Array>);
  }

  async downloadToBuffer(fileId: string): Promise<Buffer> {
    const stream = await this.download(fileId);
    return streamToBuffer(stream);
  }

  async getDownloadUrl(fileId: string, options: GetDownloadUrlOptions = {}): Promise<DownloadUrlResponse> {
    return this.http.get(`/v1/projects/${this.projectId}/files/${fileId}/download-url`, {
      ttl: options.ttl,
      disposition: options.disposition,
    });
  }

  async list(filters: FileListFilters = {}): Promise<ListResponse<FileRecord>> {
    const { metadata, tags, ...rest } = filters;
    return this.http.get(`/v1/projects/${this.projectId}/files`, {
      ...rest,
      ...(metadata ? { metadata: JSON.stringify(metadata) } : {}),
      ...(tags ? { tags: tags.join(",") } : {}),
    } as Record<string, string | number | boolean | undefined>);
  }

  async get(fileId: string): Promise<FileRecord> {
    return this.http.get(`/v1/projects/${this.projectId}/files/${fileId}`);
  }

  async update(fileId: string, options: FileUpdateOptions): Promise<FileRecord> {
    return this.http.patch(`/v1/projects/${this.projectId}/files/${fileId}`, options);
  }

  async delete(fileId: string): Promise<void> {
    return this.http.delete(`/v1/projects/${this.projectId}/files/${fileId}`);
  }

  async restore(fileId: string): Promise<FileRecord> {
    return this.http.post(`/v1/projects/${this.projectId}/files/${fileId}/restore`);
  }

  /** Verify an HMAC-SHA256 webhook signature. */
  static verifyWebhookSignature(rawBody: Buffer, signature: string, secret: string): boolean {
    const expected = createHmac("sha256", secret).update(rawBody).digest("hex");
    const received = signature.replace("sha256=", "");
    return expected === received;
  }
}
