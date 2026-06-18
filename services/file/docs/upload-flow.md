# File Service — Upload Flow

## Phase 1: Single-file presigned upload

The upload flow keeps file bytes off the service entirely. The service only manages metadata; the client streams bytes directly to object storage.

```
Client                    File Service              MinIO / S3
  │                            │                        │
  │  POST /v1/files/upload     │                        │
  │  { filename, content_type, │                        │
  │    size_bytes, metadata }  │                        │
  │ ─────────────────────────► │                        │
  │                            │                        │
  │                            │ INSERT files row       │
  │                            │ (status=pending)       │
  │                            │                        │
  │                            │ INSERT outbox_messages │
  │                            │ (file.upload.initiated)│
  │                            │                        │
  │                            │ COMMIT                 │
  │                            │                        │
  │                            │ Generate presigned PUT │
  │                            │ URL (1-hour expiry)    │
  │                            │ ──────────────────────►│
  │                            │ ◄──────────────────────│
  │  201 { file_id,            │                        │
  │        upload_url,         │                        │
  │        expires_at }        │                        │
  │ ◄───────────────────────── │                        │
  │                            │                        │
  │  PUT <upload_url>          │                        │
  │  Content-Type: image/png   │                        │
  │  [file bytes]              │                        │
  │ ───────────────────────────────────────────────────►│
  │  200 OK                    │                        │
  │ ◄───────────────────────────────────────────────────│
```

## Phase 2 additions (not yet implemented)

After the client's PUT succeeds, it notifies the service, which triggers the processing pipeline:

```
Client             File Service         NATS / Processing
  │                     │                      │
  │ POST /v1/files/{id}/confirm                │
  │ ────────────────── ►│                      │
  │                     │ UPDATE status        │
  │                     │  = processing        │
  │                     │                      │
  │                     │ Publish via outbox   │
  │                     │ file.processing.start│
  │                     │ ─────────────────────►
  │                     │                      │ ClamAV scan
  │                     │                      │ MIME validate
  │                     │                      │ ...
  │                     │ ◄─────────────────────
  │                     │ UPDATE status=ready  │
```

## Upload URL expiry

Presigned URLs expire after **1 hour**. If the client's PUT to the upload URL returns 403 (URL expired), it must call `POST /v1/files/upload` again to get a new URL. The existing file record (status=pending) will be reused.

## File size limits (Phase 1)

| Size | Behaviour |
|------|----------|
| ≤ 100 MB | Single presigned PUT |
| > 100 MB | Rejected with 413 until Phase 2 multipart is implemented |

The 100 MB threshold is set by `MULTIPART_THRESHOLD_BYTES` in settings.

## Status lifecycle

```
pending ──► processing ──► ready
              │
              ├──► failed
              └──► quarantined   (virus detected by ClamAV)
```

Files in `pending` state are not downloadable. Files in `ready` state are.
Files in `quarantined` state return 409 on any access attempt.
