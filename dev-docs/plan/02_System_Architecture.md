# FileNest v1.0 — System Architecture

**Version:** 1.0.0
**Status:** Approved for Engineering
**Last Updated:** 2026-06-15

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Service Map](#2-service-map)
3. [Service Boundaries](#3-service-boundaries)
4. [Communication Patterns](#4-communication-patterns)
5. [Data Flow Diagrams](#5-data-flow-diagrams)
6. [Upload Architecture](#6-upload-architecture)
7. [Download Architecture](#7-download-architecture)
8. [Processing Architecture](#8-processing-architecture)
9. [Storage Architecture](#9-storage-architecture)
10. [Event Architecture](#10-event-architecture)
11. [Search Architecture](#11-search-architecture)
12. [Deployment Architecture](#12-deployment-architecture)
13. [Network Architecture](#13-network-architecture)
14. [Caching Architecture](#14-caching-architecture)
15. [Scalability Architecture](#15-scalability-architecture)
16. [Disaster Recovery Architecture](#16-disaster-recovery-architecture)

---

## 1. Architecture Overview

### 1.1 System Context

FileNest sits between client applications and cloud storage providers:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT APPLICATIONS                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │  Web App     │  │  Mobile App  │  │  Backend Svc │             │
│  │  (React SDK) │  │  (REST API)  │  │  (Node SDK)  │             │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘             │
└─────────┼─────────────────┼─────────────────┼───────────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         FILENEST PLATFORM                           │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                    API Gateway Layer                        │    │
│  │         Rate Limiting / Auth / Routing / Logging           │    │
│  └────────────────────────┬───────────────────────────────────┘    │
│                           │                                         │
│  ┌────────┐ ┌──────────┐ ┌┴──────────┐ ┌──────────┐ ┌──────────┐ │
│  │Identity│ │ Project  │ │   File    │ │  Search  │ │Processing│ │
│  │Service │ │ Service  │ │  Service  │ │  Service │ │ Service  │ │
│  └────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │
│                                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐│
│  │ Storage  │ │Metadata  │ │  Audit   │ │ Webhook  │ │Compliance││
│  │ Service  │ │ Service  │ │ Service  │ │ Service  │ │ Service  ││
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘│
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │               Healthcare Service (Optional Pack)             │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐
│  PostgreSQL  │  │   Redis      │  │   Object Storage             │
│  (Primary    │  │   (Cache)    │  │   S3 / Azure / GCS / MinIO   │
│   DB)        │  │              │  │                              │
└──────────────┘  └──────────────┘  └──────────────────────────────┘
          │                                   │
          ▼                                   ▼
┌──────────────┐                   ┌──────────────────────────────┐
│  OpenSearch  │                   │   NATS / RabbitMQ            │
│  (Search)    │                   │   (Message Broker)           │
└──────────────┘                   └──────────────────────────────┘
```

### 1.2 Architecture Principles

1. **Stateless Services** — All services are stateless. State lives in PostgreSQL, Redis, or storage providers.
2. **Async by Default** — File processing is always asynchronous. The upload API returns immediately after persisting the file record.
3. **Event-Driven** — Every significant state change emits an event via NATS. Services subscribe to relevant events.
4. **Fail-Safe** — Processing pipeline failures do not block file availability. Files are accessible after upload, before processing completes.
5. **Configuration-Driven** — No service contains industry-specific logic. Industry behavior comes from project configuration.
6. **Multi-Tenant by Construction** — Tenant ID is part of every data access path, not an afterthought.

---

## 2. Service Map

### 2.1 Core Services

| Service | Type | Protocol | Port | Replicas (prod) |
|---------|------|----------|------|-----------------|
| API Gateway | Stateless | HTTP/2, gRPC | 8000 | 5–20 |
| Identity Service | Stateless | HTTP | 8001 | 3–10 |
| Project Service | Stateless | HTTP | 8002 | 3–10 |
| File Service | Stateless | HTTP | 8003 | 5–50 |
| Storage Service | Stateless | HTTP | 8004 | 3–20 |
| Metadata Service | Stateless | HTTP | 8005 | 3–10 |
| Search Service | Stateless | HTTP | 8006 | 3–10 |
| Processing Service | Worker | NATS Subscriber | — | 5–50 |
| Audit Service | Stateless | HTTP | 8007 | 3–10 |
| Webhook Service | Worker | NATS Subscriber | — | 3–10 |
| Compliance Service | Stateless | HTTP | 8008 | 3–5 |
| Healthcare Service | Stateless | HTTP | 8009 | 2–10 |

### 2.2 Data Services

| Service | Technology | Version | Replication |
|---------|-----------|---------|-------------|
| Primary Database | PostgreSQL | 16 | Streaming replication (1 primary, 2 replicas) |
| Cache | Redis | 7.x | Redis Cluster (3 masters, 3 replicas) |
| Search | OpenSearch | 2.x | 3 master-eligible nodes, 3+ data nodes |
| Message Broker | NATS JetStream | 2.x | 3-node cluster |
| Object Storage | S3/Azure/GCS/MinIO | — | Provider-managed |

---

## 3. Service Boundaries

### 3.1 Identity Service

**Owns:**
- Organizations
- Users
- Roles and permissions
- API keys (creation, validation, rotation)
- Service accounts
- OAuth tokens

**Does NOT own:**
- Project configuration (Project Service)
- File metadata (Metadata Service)
- Audit logs (Audit Service)

**Boundary Rule:** Any service can call the Identity Service to validate a token. No service calls Identity Service to modify auth state (only Identity Service modifies its own data).

---

### 3.2 Project Service

**Owns:**
- Project CRUD
- Project configuration
- Compliance profile assignment
- Metadata schema definitions
- Storage configuration per project
- Capability pack activation

**Does NOT own:**
- Files within projects (File Service)
- Processing pipeline execution (Processing Service)
- User management (Identity Service)

**Boundary Rule:** Project Service is the source of truth for "what is this project configured to do?" All other services query Project Service (via cache) before processing any request.

---

### 3.3 File Service

**Owns:**
- Upload session lifecycle
- File record CRUD
- File version history
- Folder structure
- File-to-folder associations
- File soft delete and restore

**Does NOT own:**
- Actual bytes stored (Storage Service)
- Metadata validation (Metadata Service)
- Processing pipeline execution (Processing Service)
- Signed URL generation (Storage Service)

**Boundary Rule:** File Service orchestrates — it calls Storage Service for actual storage, Metadata Service for metadata, and emits events to trigger Processing Service.

---

### 3.4 Storage Service

**Owns:**
- Storage provider abstraction
- Provider credential management
- Signed URL generation
- File chunk management
- Storage path construction
- Provider health checking

**Does NOT own:**
- File records (File Service)
- Who can access which file (File Service + Identity Service)

**Boundary Rule:** Storage Service knows nothing about organizations, projects, or users. It receives a storage key and performs the operation. Authorization happens before Storage Service is called.

---

### 3.5 Processing Service

**Owns:**
- Processing job lifecycle
- Pipeline stage execution
- Worker pool management
- Processing result storage

**Does NOT own:**
- Files (File Service)
- Search indexing (Search Service — notified via event)
- PHI detection model (external service or library)

**Boundary Rule:** Processing Service is triggered by events, never by direct HTTP calls. It emits events when processing completes.

---

## 4. Communication Patterns

### 4.1 Synchronous Communication (HTTP)

Used for:
- Client-facing API requests
- Service-to-service calls where immediate response is needed
- Configuration lookups
- Auth validation

```
Client → API Gateway → File Service → Storage Service
                                    → Metadata Service
                                    → Identity Service (auth)
```

Pattern rules:
- Max 3 levels of synchronous chaining (to prevent distributed deadlocks)
- All inter-service HTTP calls use internal DNS: `http://file-service.filenest.svc.cluster.local`
- Circuit breaker on all inter-service calls (using `httpx` with retry + timeout)
- Timeout: 5 seconds for most calls, 30 seconds for storage operations

### 4.2 Asynchronous Communication (NATS JetStream)

Used for:
- Processing pipeline triggering
- Event delivery to webhook consumers
- Search index updates
- Audit log writes
- Inter-service notifications

```
File Service
  → Publishes: file.uploaded
     ↓
Processing Service (subscriber)
  → Runs: virus_scan, ocr, phi_detection
  → Publishes: file.processed
     ↓
Search Service (subscriber)
  → Indexes file content
  → Publishes: file.indexed
     ↓
Webhook Service (subscriber)
  → Delivers webhooks to customer endpoints
```

NATS Topic naming convention:
```
filenest.{organization_id}.{project_id}.{event_type}
filenest.*.*.file.uploaded        # Admin wildcard subscription
filenest.org_abc.proj_xyz.file.uploaded  # Project-specific subscription
```

### 4.3 Publish-Subscribe Patterns

| Publisher | Topic | Subscribers |
|-----------|-------|-------------|
| File Service | file.uploaded | Processing Service, Audit Service, Webhook Service |
| File Service | file.deleted | Search Service, Audit Service, Webhook Service |
| File Service | file.downloaded | Audit Service, Webhook Service |
| Processing Service | file.processed | Search Service, File Service (status update), Webhook Service |
| Processing Service | file.virus_detected | File Service (quarantine), Audit Service, Webhook Service |
| Search Service | file.indexed | Webhook Service |
| Identity Service | apikey.rotated | All services (cache invalidation) |
| Project Service | project.config_changed | All services (config cache invalidation) |

---

## 5. Data Flow Diagrams

### 5.1 Upload Flow — Complete Sequence

```
Client                 API GW          File Svc         Storage Svc      NATS
  │                      │                │                 │               │
  │ POST /v1/files/upload│                │                 │               │
  ├─────────────────────►│                │                 │               │
  │                      │ ValidateAPIKey │                 │               │
  │                      ├──────────────► │                 │               │
  │                      │ GetProjectConf │                 │               │
  │                      ├──────────────► │                 │               │
  │                      │ ValidateMetadata                 │               │
  │                      ├──────────────► │                 │               │
  │                      │                │ CreateFileRecord│               │
  │                      │                ├────────────────►│               │
  │                      │                │ GetUploadURL    │               │
  │                      │                ├────────────────►│               │
  │                      │                │◄────────────────┤               │
  │                      │                │ presignedPutURL │               │
  │◄─────────────────────┤                │                 │               │
  │ {fileId, uploadUrl}  │                │                 │               │
  │                      │                │                 │               │
  │ PUT bytes → Storage Provider (direct) │                 │               │
  ├───────────────────────────────────────────────────────►│               │
  │                                                         │               │
  │ POST /v1/files/{id}/complete          │                 │               │
  ├─────────────────────►│                │                 │               │
  │                      ├──────────────► │                 │               │
  │                      │                │ VerifyChecksum  │               │
  │                      │                ├────────────────►│               │
  │                      │                │ UpdateStatus=ready              │
  │                      │                │                 │               │
  │                      │                │ Publish: file.uploaded          │
  │                      │                ├────────────────────────────────►│
  │◄─────────────────────┤                │                 │               │
  │ {fileId, status}     │                │                 │               │
```

### 5.2 Download Flow — Complete Sequence

```
Client               API GW         File Svc        Storage Svc     Audit Svc
  │                    │               │                 │               │
  │ GET /v1/files/{id}/download        │                 │               │
  ├───────────────────►│               │                 │               │
  │                    │ ValidateAPIKey│                 │               │
  │                    ├─────────────► │                 │               │
  │                    │ CheckPermission                 │               │
  │                    ├─────────────► │                 │               │
  │                    │ CheckLegalHold│                 │               │
  │                    ├─────────────► │                 │               │
  │                    │ GetFileRecord │                 │               │
  │                    ├─────────────► │                 │               │
  │                    │               │ GenerateSignedURL               │
  │                    │               ├────────────────►│               │
  │                    │               │◄────────────────┤               │
  │                    │               │ signedUrl       │               │
  │                    │               │                 │               │
  │                    │               │ Publish: file.downloaded        │
  │                    │               ├─────────────────────────────────►
  │◄───────────────────┤               │                 │               │
  │ 302 → signedUrl    │               │                 │               │
  │                    │               │                 │               │
  │ GET signedUrl (direct to storage)  │                 │               │
  ├──────────────────────────────────────────────────────►               │
  │◄──────────────────────────────────────────────────────               │
  │ file bytes         │               │                 │               │
```

### 5.3 Processing Flow — Pipeline Sequence

```
NATS           Processing Svc    Virus Scanner    OCR Engine    PHI Detector   Search Svc
  │                  │                │               │               │              │
  │ file.uploaded    │                │               │               │              │
  ├─────────────────►│                │               │               │              │
  │                  │ CreateJob      │               │               │              │
  │                  ├──────────────► │               │               │              │
  │                  │                │ ScanFile      │               │              │
  │                  │                ├──────────────►│               │              │
  │                  │                │ virusResult   │               │              │
  │                  │                │◄──────────────┤               │              │
  │                  │                │               │               │              │
  │                  │ [if healthcare] │               │               │              │
  │                  ├─────────────────────────────────────────────► │              │
  │                  │                │               │  DetectPHI    │              │
  │                  │                │               │◄──────────────┤              │
  │                  │                │               │               │              │
  │                  │ [if ocr enabled]│               │               │              │
  │                  ├──────────────────────────────►│               │              │
  │                  │                │ ExtractText   │               │              │
  │                  │                │◄──────────────┤               │              │
  │                  │                │               │               │              │
  │                  │ UpdateFileRecord (processing results)          │              │
  │                  │                │               │               │              │
  │                  │ Publish: file.processed        │               │              │
  ├◄─────────────────┤                │               │               │              │
  │                  │                │               │               │              │
  │ file.processed ──────────────────────────────────────────────────────────────► │
  │                  │                │               │               │  IndexFile   │
  │                  │                │               │               │◄─────────────┤
```

---

## 6. Upload Architecture

### 6.1 Upload Types

| Type | Max Size | Use Case |
|------|----------|----------|
| Single Upload | 100 MB | Small files, simple integrations |
| Multipart Upload | 5 GB | Large files, parallel chunk upload |
| Resumable Upload | 5 GB | Unreliable networks, long uploads |
| Direct Browser Upload | 5 GB | Frontend SDK — direct to storage |
| Server-Side Upload | 5 GB | Backend-to-backend via SDK |

### 6.2 Multipart Upload Architecture

```
Client           File Svc         Storage Svc          DB
  │                 │                 │                  │
  │ CreateSession   │                 │                  │
  ├───────────────► │                 │                  │
  │                 │ InitMultipart   │                  │
  │                 ├───────────────► │                  │
  │                 │ uploadId        │                  │
  │                 │◄────────────────┤                  │
  │                 │ CreateUploadSession                │
  │                 ├──────────────────────────────────►│
  │ {sessionId, uploadId}             │                  │
  │◄────────────────┤                 │                  │
  │                 │                 │                  │
  │ [Repeat per chunk]                │                  │
  │ GetChunkURL(part N)               │                  │
  ├───────────────► │                 │                  │
  │                 │ PresignChunkPut │                  │
  │                 ├───────────────► │                  │
  │ {chunkUrl}      │◄────────────────┤                  │
  │◄────────────────┤                 │                  │
  │ PUT chunk → chunkUrl (direct)     │                  │
  ├──────────────────────────────────►│                  │
  │ {ETag}          │                 │                  │
  │◄────────────────────────────────-─┤                  │
  │                 │                 │                  │
  │ CompleteUpload({parts: [{n, etag}]})                │
  ├───────────────► │                 │                  │
  │                 │ CompleteMultipart                  │
  │                 ├───────────────► │                  │
  │                 │ VerifyChecksum  │                  │
  │                 ├──────────────────────────────────►│
  │                 │ PublishUploadedEvent               │
  │◄────────────────┤                 │                  │
  │ {fileId, status: processing}      │                  │
```

### 6.3 Resumable Upload Logic

Upload sessions are stored in Redis with TTL of 24 hours:

```
Key: upload_session:{session_id}
Value: {
  "sessionId": "sess_abc",
  "fileId": "file_xyz",
  "projectId": "proj_abc",
  "totalSize": 524288000,
  "chunkSize": 5242880,
  "totalChunks": 100,
  "uploadedChunks": [1,2,3,...,47],
  "startedAt": "2026-06-15T10:00:00Z",
  "expiresAt": "2026-06-16T10:00:00Z"
}
```

On resume:
1. Client calls `GET /v1/uploads/{sessionId}/status`
2. FileNest returns list of already-uploaded chunks
3. Client re-uploads only missing chunks
4. Complete when all chunks uploaded

---

## 7. Download Architecture

### 7.1 Download Flow

FileNest **never** exposes raw storage URLs. All downloads go through an authorization + signed URL redirect pattern.

```
GET /v1/files/{fileId}/download?ttl=3600
  ↓
1. Validate API key → get organization_id, project_id
2. Verify file belongs to project
3. Check user/service account has download permission
4. Check file is not under legal hold restriction
5. Check file is in "ready" or "available" state
6. Check IP allowlist (if configured on project)
7. Generate signed URL from Storage Service
8. Log audit event: file.downloaded
9. Return 302 redirect to signed URL
```

### 7.2 Signed URL Properties

```json
{
  "url": "https://s3.amazonaws.com/bucket/key?X-Amz-Signature=...",
  "expiresAt": "2026-06-15T11:00:00Z",
  "ttlSeconds": 3600,
  "singleUse": false,
  "ipRestricted": false,
  "downloadCount": 0,
  "maxDownloads": null
}
```

### 7.3 Direct Streaming (Enterprise)

For files where 302 redirect is problematic, FileNest supports streaming proxy:

```
GET /v1/files/{fileId}/stream
  → FileNest fetches from storage and streams bytes to client
  → Adds X-FileNest-FileId and X-FileNest-Checksum headers
  → Enables download count enforcement
  → Slower than signed URL redirect (extra hop)
  → Use only when client cannot follow redirects
```

---

## 8. Processing Architecture

### 8.1 Pipeline Orchestration

Processing pipelines are project-configured and executed asynchronously by the Processing Service.

```
Project Configuration:
  processing:
    stages: [virus_scan, phi_detection, ocr, classification, indexing]
    parallelStages: [virus_scan, phi_detection]  # Run in parallel
    sequentialStages: [ocr, classification, indexing]  # Run in order
```

### 8.2 Worker Architecture

```
NATS JetStream (file.uploaded)
  ↓
Processing Consumer Group
  ↓
Worker Pool (Celery/Dramatiq workers)
  ├── Virus Scan Worker
  ├── OCR Worker
  ├── PII/PHI Detection Worker
  ├── Classification Worker
  ├── Embedding Worker
  └── Indexing Worker
```

Workers are stateless and pull from a work queue. Dead letter queue captures permanently failed jobs.

### 8.3 Pipeline Stage Isolation

Each stage is isolated:
- Failure of one stage does not block other stages
- Stage results are stored independently
- File is available to download even if all processing stages fail
- Processing can be re-triggered manually

---

## 9. Storage Architecture

### 9.1 Storage Provider Abstraction

```python
class StorageProvider(Protocol):
    async def upload(self, key: str, data: BinaryIO, content_type: str) -> str: ...
    async def download(self, key: str) -> BinaryIO: ...
    async def delete(self, key: str) -> None: ...
    async def exists(self, key: str) -> bool: ...
    async def copy(self, source_key: str, dest_key: str) -> str: ...
    async def move(self, source_key: str, dest_key: str) -> str: ...
    async def generate_signed_url(
        self, key: str, ttl_seconds: int, method: str = "GET"
    ) -> str: ...
    async def generate_multipart_upload_id(self, key: str) -> str: ...
    async def generate_part_url(self, key: str, upload_id: str, part_number: int) -> str: ...
    async def complete_multipart(self, key: str, upload_id: str, parts: List[Part]) -> str: ...
    async def abort_multipart(self, key: str, upload_id: str) -> None: ...
```

### 9.2 Storage Key Construction

```python
def build_storage_key(
    organization_id: str,
    project_id: str,
    environment: str,
    file_id: str,
    version_id: str,
    filename: str,
) -> str:
    date_prefix = datetime.utcnow().strftime("%Y/%m")
    safe_filename = sanitize_filename(filename)
    return (
        f"{organization_id}/{project_id}/{environment}/"
        f"{date_prefix}/{file_id}/{version_id}/{safe_filename}"
    )
```

### 9.3 BYOB Architecture

```
Customer Setup:
  1. Customer creates S3 bucket in their AWS account
  2. Customer creates IAM role with trust policy allowing FileNest's AWS account
  3. Customer provides FileNest with role ARN
  4. FileNest assumes role via STS AssumeRole
  5. FileNest stores encrypted {roleArn, externalId} in project config

Runtime:
  1. File Service → Storage Service.getProviderForProject(project_id)
  2. Storage Service → reads project config → detects byob=true
  3. Storage Service → assumes customer role via STS
  4. Storage Service → creates S3 client with assumed credentials
  5. Storage Service → performs operation against customer bucket
  6. Credentials are cached in Redis for 15 minutes (STS session duration up to 1 hour)
```

---

## 10. Event Architecture

### 10.1 NATS JetStream Configuration

```
Stream: FILENEST_EVENTS
Subjects: filenest.>
Retention: WorkQueuePolicy (deleted on ack)
Storage: File (persisted to disk)
Replicas: 3
MaxAge: 7 days
MaxBytes: 50GB
```

### 10.2 Consumer Groups

| Consumer | Subject Filter | Durable | Deliver | Processing |
|----------|---------------|---------|---------|------------|
| processing-consumer | filenest.*.*.file.uploaded | processing-workers | New | Processing Service |
| search-consumer | filenest.*.*.file.processed | search-workers | New | Search Service |
| webhook-consumer | filenest.> | webhook-workers | New | Webhook Service |
| audit-consumer | filenest.> | audit-workers | New | Audit Service |

### 10.3 Event Schemas

```json
// file.uploaded
{
  "eventId": "evt_abc123",
  "eventType": "file.uploaded",
  "version": "1.0",
  "timestamp": "2026-06-15T10:30:00.000Z",
  "organizationId": "org_abc",
  "projectId": "proj_xyz",
  "environmentId": "env_prod",
  "payload": {
    "fileId": "file_abc",
    "filename": "discharge-summary.pdf",
    "mimeType": "application/pdf",
    "size": 524288,
    "storageKey": "org_abc/proj_xyz/prod/2026/06/file_abc/v1/discharge-summary.pdf",
    "storageProvider": "s3",
    "metadata": { "patientId": "P-12345", "documentType": "Discharge" },
    "uploadedBy": "sa_backend_worker",
    "uploadedAt": "2026-06-15T10:30:00.000Z"
  }
}
```

---

## 11. Search Architecture

### 11.1 OpenSearch Index Design

One index per project:
```
Index: filenest-{project_id}
Settings:
  shards: 3
  replicas: 1
  refresh_interval: 5s
```

### 11.2 Index Mapping

```json
{
  "mappings": {
    "properties": {
      "fileId": { "type": "keyword" },
      "projectId": { "type": "keyword" },
      "organizationId": { "type": "keyword" },
      "filename": {
        "type": "text",
        "analyzer": "standard",
        "fields": { "keyword": { "type": "keyword" } }
      },
      "mimeType": { "type": "keyword" },
      "size": { "type": "long" },
      "tags": { "type": "keyword" },
      "metadata": { "type": "object", "dynamic": true },
      "ocrContent": {
        "type": "text",
        "analyzer": "standard",
        "index_options": "positions"
      },
      "createdAt": { "type": "date" },
      "updatedAt": { "type": "date" },
      "status": { "type": "keyword" },
      "folderId": { "type": "keyword" },
      "processingResults": {
        "type": "object",
        "properties": {
          "phiDetected": { "type": "boolean" },
          "piiDetected": { "type": "boolean" },
          "classification": { "type": "keyword" }
        }
      }
    }
  }
}
```

---

## 12. Deployment Architecture

### 12.1 Kubernetes Cluster Topology

```
Production Cluster (per region)
├── Node Pool: API (c5.xlarge × 5–20 nodes, autoscaling)
│   ├── api-gateway (2–5 pods)
│   ├── identity-service (2–5 pods)
│   ├── project-service (2–5 pods)
│   ├── file-service (3–20 pods)
│   ├── storage-service (2–10 pods)
│   ├── metadata-service (2–5 pods)
│   ├── search-service (2–5 pods)
│   ├── audit-service (2–5 pods)
│   ├── webhook-service (2–5 pods)
│   ├── compliance-service (2–5 pods)
│   └── healthcare-service (2–5 pods)
│
├── Node Pool: Workers (c5.2xlarge × 5–50 nodes, autoscaling)
│   ├── processing-workers (3–50 pods)
│   └── webhook-workers (2–10 pods)
│
├── Node Pool: Data (r5.2xlarge × 3 nodes, fixed)
│   ├── PostgreSQL (via RDS or CloudNativePG)
│   ├── Redis Cluster (via ElastiCache or Redis Operator)
│   └── NATS Cluster (3 pods)
│
└── Node Pool: Search (r5.2xlarge × 3–6 nodes, autoscaling)
    └── OpenSearch Cluster (3–6 pods)
```

### 12.2 Helm Chart Structure

```
filenest/
├── Chart.yaml
├── values.yaml
├── values.production.yaml
├── values.staging.yaml
├── templates/
│   ├── _helpers.tpl
│   ├── api-gateway/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── hpa.yaml
│   │   └── configmap.yaml
│   ├── file-service/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── hpa.yaml
│   ├── ... (one directory per service)
│   ├── ingress.yaml
│   ├── namespace.yaml
│   └── rbac.yaml
```

### 12.3 Ingress Architecture

```
Internet
  ↓
AWS ALB / Azure Application Gateway / GCP GLB
  ↓
Nginx Ingress Controller (Kubernetes)
  ↓
Rules:
  api.filenest.io → api-gateway service (port 8000)
  app.filenest.io → dashboard-frontend service (port 3000)
  *.webhook.filenest.io → webhook-service (port 8007)

TLS:
  cert-manager with Let's Encrypt or customer-provided certificates
  Wildcard cert for *.filenest.io
```

---

## 13. Network Architecture

### 13.1 Network Segmentation

```
VPC
├── Public Subnet (AZ-a, AZ-b, AZ-c)
│   └── Load Balancers only
│
├── Private Subnet — Application Tier (AZ-a, AZ-b, AZ-c)
│   └── Kubernetes worker nodes
│       └── All application pods
│
├── Private Subnet — Data Tier (AZ-a, AZ-b, AZ-c)
│   ├── PostgreSQL
│   ├── Redis
│   └── NATS
│
└── Private Subnet — Search Tier (AZ-a, AZ-b, AZ-c)
    └── OpenSearch Cluster
```

### 13.2 Service-to-Service Communication

```yaml
NetworkPolicy:
  file-service:
    ingress:
      - from: api-gateway
      - from: processing-service
    egress:
      - to: storage-service
      - to: metadata-service
      - to: postgres (port 5432)
      - to: redis (port 6379)
      - to: nats (port 4222)
```

### 13.3 External Connectivity

| Direction | Traffic | Security |
|-----------|---------|----------|
| Inbound | Client API calls | TLS 1.3, WAF, DDoS protection |
| Inbound | Webhook callbacks (none — FileNest sends webhooks) | N/A |
| Outbound | Storage provider APIs | VPC endpoint where possible |
| Outbound | Customer webhook endpoints | Egress via NAT gateway |
| Outbound | OCR/PHI detection APIs (if external) | mTLS |

---

## 14. Caching Architecture

### 14.1 Cache Strategy

| Data | Cache Key | TTL | Invalidation |
|------|-----------|-----|--------------|
| Project config | `project_config:{project_id}` | 5 min | On config change event |
| API key validation | `apikey:{key_hash}` | 10 min | On rotation event |
| File metadata | `file_meta:{file_id}` | 1 min | On file update |
| Signed URLs | Not cached (generated per request) | — | — |
| Processing job status | `job_status:{job_id}` | 30 sec | On job update |
| Search results | `search:{hash}` | 30 sec | Not invalidated (eventual) |
| Storage credentials (BYOB) | `byob_creds:{project_id}` | 15 min | On rotation |

### 14.2 Redis Cluster Configuration

```
Redis Cluster: 3 masters, 3 replicas
Master 1: slots 0–5460    (organization data, project config)
Master 2: slots 5461–10922 (file metadata, API keys)
Master 3: slots 10923–16383 (processing, search cache)

Maxmemory: 8GB per master
Eviction: allkeys-lru
Persistence: AOF with fsync every second
```

### 14.3 Cache-Aside Pattern

```python
async def get_project_config(project_id: str) -> ProjectConfig:
    cache_key = f"project_config:{project_id}"

    cached = await redis.get(cache_key)
    if cached:
        return ProjectConfig.model_validate_json(cached)

    config = await db.query(ProjectConfig).filter_by(project_id=project_id).first()
    if not config:
        raise ProjectNotFoundError(project_id)

    await redis.setex(cache_key, 300, config.model_dump_json())
    return config
```

---

## 15. Scalability Architecture

### 15.1 Horizontal Scaling

| Service | Scaling Trigger | Min | Max |
|---------|----------------|-----|-----|
| API Gateway | CPU > 60% or RPS > 1000/pod | 2 | 20 |
| File Service | CPU > 60% or RPS > 500/pod | 3 | 50 |
| Processing Workers | Queue depth > 100 jobs/worker | 5 | 100 |
| Search Service | CPU > 70% | 2 | 10 |
| Storage Service | RPS > 500/pod | 2 | 20 |

### 15.2 Database Scaling

| Strategy | Implementation |
|----------|---------------|
| Connection pooling | PgBouncer (transaction pooling mode) |
| Read replicas | Route read queries to replicas via SQLAlchemy |
| Table partitioning | `audit_logs` and `files` partitioned by `created_at` monthly |
| Vertical scaling | Start on r5.2xlarge, scale to r5.8xlarge before sharding |
| Future sharding | Shard by `organization_id` when single instance saturates |

### 15.3 Processing Scaling

```
Job Queue Depth Metric → Prometheus → KEDA (Kubernetes Event-Driven Autoscaler)
  → Scale processing workers based on NATS consumer lag
  → Minimum: 5 workers
  → Maximum: 100 workers
  → Scale-up threshold: 50 pending jobs per worker
  → Scale-down: 3 minute stabilization window
```

---

## 16. Disaster Recovery Architecture

### 16.1 Backup Strategy

| Component | Backup Frequency | Retention | Method |
|-----------|-----------------|-----------|--------|
| PostgreSQL | Continuous WAL + daily snapshot | 30 days | pg_basebackup + WAL-G |
| Redis | Every 15 minutes RDB snapshot | 7 days | Redis persistence + S3 export |
| OpenSearch | Daily snapshots | 14 days | OpenSearch snapshot API to S3 |
| NATS | JetStream built-in replication | N/A | 3-node cluster |
| Object Storage | Provider-managed | Per project retention policy | Cross-region replication |

### 16.2 Multi-Region Architecture

```
Primary Region (US-East-1)
├── Active — all traffic
├── PostgreSQL primary
├── Redis cluster primary
└── OpenSearch primary

Secondary Region (US-West-2)
├── Standby — zero traffic
├── PostgreSQL replica (streaming replication, ~100ms lag)
├── Redis replica (async replication)
└── OpenSearch replica cluster
```

**Failover procedure:**
1. Primary region health check fails (Route53 health check)
2. Route53 DNS failover activates secondary region endpoint
3. Secondary PostgreSQL promoted to primary (pg_promote)
4. Redis secondary promoted (REPLICAOF NO ONE)
5. OpenSearch traffic shifted to secondary cluster
6. RTO target: 15 minutes, RPO target: 5 minutes

### 16.3 Recovery Testing

- Monthly automated failover test in staging environment
- Quarterly game day DR drill in production (with traffic shift to secondary)
- Annual full DR test
- All recovery procedures documented in runbooks
