/**
 * @filenest/node namespaces/folders — FoldersNamespace implementation.
 * @module
 */

import type { FileNestHttpClient, Folder, ListResponse } from "@filenest/core";

export interface FolderCreateOptions {
  name: string;
  parentFolderId?: string;
  metadata?: Record<string, unknown>;
}

export interface FolderListOptions {
  parentFolderId?: string;
}

export interface FolderGetOptions {
  includeStats?: boolean;
}

export interface FolderDeleteOptions {
  force?: boolean;
}

export class FoldersNamespace {
  constructor(
    private readonly http: FileNestHttpClient,
    private readonly projectId: string
  ) {}

  async create(options: FolderCreateOptions): Promise<Folder> {
    return this.http.post(`/v1/projects/${this.projectId}/folders`, options);
  }

  async list(options: FolderListOptions = {}): Promise<ListResponse<Folder>> {
    return this.http.get(`/v1/projects/${this.projectId}/folders`, {
      parent_folder_id: options.parentFolderId,
    });
  }

  async get(folderId: string, options: FolderGetOptions = {}): Promise<Folder> {
    return this.http.get(`/v1/projects/${this.projectId}/folders/${folderId}`, {
      include_stats: options.includeStats,
    });
  }

  async delete(folderId: string, options: FolderDeleteOptions = {}): Promise<void> {
    return this.http.delete(`/v1/projects/${this.projectId}/folders/${folderId}?force=${options.force ?? false}`);
  }
}
