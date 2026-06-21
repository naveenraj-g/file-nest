/**
 * @filenest/core types — shared TypeScript types for all FileNest SDKs.
 *
 * These types mirror the Pydantic models in the FastAPI backend. All SDK
 * responses are typed with these interfaces.
 *
 * @module
 */

// ─── Files ───────────────────────────────────────────────────────────────────

export type FileStatus =
  | "uploading"
  | "processing"
  | "ready"
  | "failed"
  | "quarantined"
  | "deleted";

export interface FileRecord {
  id: string;
  projectId: string;
  organizationId: string;
  filename: string;
  mimeType: string;
  size: number;
  status: FileStatus;
  storageKey: string;
  folderId: string | null;
  tags: string[];
  metadata: Record<string, unknown>;
  versionCount: number;
  deletedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface FileVersion {
  id: string;
  fileId: string;
  versionNumber: number;
  size: number;
  storageKey: string;
  changeNote: string | null;
  createdAt: string;
}

// ─── Folders ─────────────────────────────────────────────────────────────────

export interface Folder {
  id: string;
  projectId: string;
  parentFolderId: string | null;
  name: string;
  path: string;
  fileCount?: number;
  totalSizeBytes?: number;
  createdAt: string;
}

// ─── Projects ────────────────────────────────────────────────────────────────

export type StorageMode = "managed" | "byob";
export type StorageProvider = "s3" | "azure_blob" | "gcs" | "minio" | "r2" | "rustfs";

export interface Project {
  id: string;
  organizationId: string;
  name: string;
  slug: string;
  description: string | null;
  storageMode: StorageMode;
  storageProvider: StorageProvider;
  createdAt: string;
  updatedAt: string;
}

// ─── Webhooks ────────────────────────────────────────────────────────────────

export type WebhookStatus = "active" | "disabled" | "failing";

export type WebhookEvent =
  | "file.uploaded"
  | "file.processed"
  | "file.deleted"
  | "file.virus_detected"
  | "file.quarantined"
  | "file.ready";

export interface Webhook {
  id: string;
  projectId: string;
  name: string;
  url: string;
  events: WebhookEvent[];
  status: WebhookStatus;
  signingSecret: string;
  createdAt: string;
  updatedAt: string;
}

export interface WebhookDelivery {
  id: string;
  webhookId: string;
  event: WebhookEvent;
  statusCode: number | null;
  success: boolean;
  attemptCount: number;
  responseBody: string | null;
  deliveredAt: string | null;
  createdAt: string;
}

// ─── Upload ──────────────────────────────────────────────────────────────────

export interface UploadProgress {
  bytesUploaded: number;
  totalBytes: number;
  percentage: number;
  chunkNumber: number;
  totalChunks: number;
}

export interface UploadSession {
  sessionId: string;
  fileId: string;
  filename: string;
  size: number;
  mimeType: string;
  uploadedParts: number;
  totalParts: number;
  expiresAt: string;
}

export interface UploadToken {
  token: string;
  expiresAt: string;
  constraints: {
    maxSize: number;
    allowedMimeTypes: string[];
    maxFiles: number;
  };
}

// ─── Download ────────────────────────────────────────────────────────────────

export interface DownloadUrlResponse {
  url: string;
  expiresAt: string;
  filename: string;
}

// ─── Search ──────────────────────────────────────────────────────────────────

export interface SearchFilters {
  metadata?: Record<string, string>;
  tags?: string[];
  mimeType?: string[];
  createdAfter?: Date | string;
  createdBefore?: Date | string;
  folderId?: string;
  sizeMin?: number;
  sizeMax?: number;
}

export interface SearchHit {
  fileId: string;
  filename: string;
  score: number;
  highlights: Record<string, string[]>;
  file: FileRecord;
}

export interface SearchFacets {
  mimeType?: { value: string; count: number }[];
  tags?: { value: string; count: number }[];
}

export interface SearchResults {
  hits: SearchHit[];
  total: number;
  queryTimeMs: number;
  facets?: SearchFacets;
}

// ─── Audit ───────────────────────────────────────────────────────────────────

export interface AuditLog {
  id: string;
  organizationId: string;
  projectId: string;
  fileId: string | null;
  actorType: "api_key" | "upload_token" | "service_account";
  actorId: string;
  eventType: string;
  metadata: Record<string, unknown>;
  createdAt: string;
}

// ─── Pagination ──────────────────────────────────────────────────────────────

export interface Pagination {
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
}

export interface ListResponse<T> {
  data: T[];
  pagination: Pagination;
}
