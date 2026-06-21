/**
 * @filenest/node namespaces/upload-tokens — UploadTokensNamespace implementation.
 *
 * Generates short-lived upload tokens for use by browser clients.
 * The token is passed to `<FileNestProvider tokenEndpoint>` or used directly
 * in the `Authorization: Bearer` header by `@filenest/react`.
 *
 * @module
 */

import type { FileNestHttpClient, UploadToken } from "@filenest/core";

export interface CreateUploadTokenOptions {
  maxSize?: number;
  allowedMimeTypes?: string[];
  maxFiles?: number;
  folderId?: string;
  metadata?: Record<string, unknown>;
  expiresIn?: number;
}

export class UploadTokensNamespace {
  constructor(
    private readonly http: FileNestHttpClient,
    private readonly projectId: string
  ) {}

  async create(options: CreateUploadTokenOptions = {}): Promise<UploadToken> {
    return this.http.post(`/v1/projects/${this.projectId}/upload-tokens`, options);
  }
}
