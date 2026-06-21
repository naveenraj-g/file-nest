# FileNest — Phase 3 Implementation Plan

**Phase:** 3 — Metadata, Search & Folders  
**Status:** 🔄 In Progress  
**Source:** `dev-docs/plan/00_Implementation_Roadmap.md` — Phase 3 section  
**Goal:** Files are searchable. Custom metadata schemas work. OCR extracts text from PDFs. Folders organise files.

**Docs to read before implementing:** `10_Search_Architecture`, `03_Database_Design`, `05_API_Specification`, `13_Processing_Pipelines`

**Exit criteria:**
- Upload a PDF containing "discharge" → `POST /search { q: "discharge" }` → file in results with highlight
- Custom metadata schema defined → upload file with missing required field → HTTP 422 with field path
- Files organised in folders → `GET /folders/{id}/files` returns correct subset
- Search across `tags`, `metadata.patientId`, and `ocr_text` in a single query

> **Completed steps** get a `✅ COMPLETED` tag on the heading — never deleted, kept as history.  
> When all steps are done → rename this file to `completed-plan-phase-3.md` and create `current-plan.md` for Phase 4.

---

## Step 1 — Tags on files

Tags are the simplest Phase 3 feature and a prerequisite for search filtering. Add `tags` to the `files` table first so all later steps can index and filter by them.

**Database:**
- Add `tags` column to `files` table: `ARRAY` of `TEXT`, not null, default `{}`
- Alembic migration: `just migration "add_tags_to_files"`

**API endpoints:**
- `PUT /v1/projects/{id}/files/{file_id}/tags` — replace full tag set; body: `{ tags: ["tag1", "tag2"] }`
- `POST /v1/projects/{id}/files/{file_id}/tags` — add tags (union, no duplicates); body: `{ tags: ["tag3"] }`

**Backend files:**
- `backend/app/models/file.py` — add `tags = Column(ARRAY(String), nullable=False, server_default="{}")`
- `backend/app/schemas/file.py` — add `TagsUpdateRequest`, `TagsAddRequest`; add `tags` field to `FileResponse`
- `backend/app/repositories/file.py` — add `set_tags(file_id, tags)`, `add_tags(file_id, tags)`
- `backend/app/services/file.py` — add `set_tags`, `add_tags` methods
- `backend/app/routers/files.py` — two new endpoints under `files:update_metadata` scope

---

## Step 2 — Custom metadata

Per-file key-value metadata stored as JSONB, validated against a project-scoped JSON Schema when `enforce_schema=true`.

**Database:**
- `metadata_schemas` table: `id`, `project_id`, `organization_id`, `version`, `schema_json` (JSONB), `is_active` (bool), `created_at`
- The `files.metadata_json` column already exists (added in Phase 1 initial migration)
- Alembic migration: `just migration "add_metadata_schemas"`

**API endpoints:**
- `POST /v1/projects/{id}/metadata-schemas` — define schema; body: `{ schema: { ... } }`; marks previous version inactive
- `GET /v1/projects/{id}/metadata-schemas` — list schemas (with `is_active` flag)
- `PUT /v1/projects/{id}/files/{file_id}/metadata` — update file metadata; validates against active schema if `enforce_schema=true` on project config; raises `MetadataValidationError` (HTTP 422) on violation

**Backend files:**
- `backend/app/models/metadata_schema.py` — `MetadataSchema` ORM model
- `backend/app/schemas/metadata.py` — Pydantic DTOs
- `backend/app/repositories/metadata_schema.py` — `MetadataSchemaRepository`
- `backend/app/services/metadata.py` — `MetadataService`: schema create, list, validate-and-update
- `backend/app/routers/metadata.py` — 3 endpoints
- `backend/app/routers/__init__.py` — register `metadata_router`

---

## Step 3 — Folder hierarchy

Folders let clients organise files into a tree structure. Files can be moved between folders.

**Database:**
- `folders` table: `id`, `organization_id`, `project_id`, `parent_folder_id` (nullable FK → `folders.id`), `name`, `path` (materialized text, e.g. `/invoices/2026`), `created_at`, `deleted_at`
- Alembic migration: `just migration "add_folders"`

**API endpoints:**
- `POST /v1/projects/{id}/folders` — create folder; body: `{ name, parent_folder_id? }`
- `GET /v1/projects/{id}/folders` — list folders (top-level + subtree, breadth-first)
- `GET /v1/projects/{id}/folders/{folder_id}/files` — list files in folder (same pagination as `GET /files`)
- `POST /v1/projects/{id}/files/{file_id}/move` — move file to folder; body: `{ folder_id: string | null }`
- `DELETE /v1/projects/{id}/folders/{folder_id}` — soft delete; fails with 409 if folder has files or subfolders

**Backend files:**
- `backend/app/models/folder.py` — `Folder` ORM model with self-referential FK
- `backend/app/schemas/folder.py` — Pydantic DTOs: `FolderCreateRequest`, `FolderResponse`, `FolderListResponse`
- `backend/app/repositories/folder.py` — `FolderRepository`: create, list, get, soft_delete; path materialisation on create
- `backend/app/services/folder.py` — `FolderService`: CRUD + empty-check before delete
- `backend/app/routers/folders.py` — 5 endpoints
- `backend/app/routers/__init__.py` — register `folders_router`
- `backend/app/services/file.py` — add `move_file(file_id, folder_id)` method

---

## Step 4 — OpenSearch client + index management

Before the indexing stage and search API can work, the OpenSearch client must be initialised and the per-project index created when a project is created.

**Infrastructure:**
- OpenSearch already in the roadmap (Phase 3); add `opensearch-py` dependency to `pyproject.toml`
- One index per project: `filenest-{project_id}` (lowercase, hyphenated)
- Mapping fields: `filename`, `content_type`, `size_bytes`, `tags`, `metadata` (object), `ocr_text`, `category`, `folder_id`, `status`, `created_at`

**Backend files:**
- `backend/app/core/search.py` — async OpenSearch client singleton: `get_search_client()`, `close_search_client()`; reads `OPENSEARCH_URL` from settings
- `backend/app/core/config.py` — add `opensearch_url: str` setting (default `http://localhost:9200`)
- `backend/app/services/project.py` — call `create_project_index(project_id)` after project creation; call `delete_project_index(project_id)` on soft delete
- `backend/app/main.py` — connect OpenSearch client in lifespan; close on shutdown
- `docker-compose.yml` — add OpenSearch service (port 9200)

---

## Step 5 — IndexingStage + re-index on metadata/tag update

The processing pipeline needs an `IndexingStage` that runs after `ClassificationStage` and indexes the file into OpenSearch when it reaches `ready` status. Metadata and tag updates must also keep the index in sync.

**Backend files:**
- `backend/app/processing/stages/indexing.py` — `IndexingStage`: builds the document from the `File` ORM object + fetches `ocr_text` (if present) → `client.index(index=f"filenest-{project_id}", id=file_id, body={...})`
- `backend/app/processing/pipeline.py` — append `IndexingStage` after `ClassificationStage` (always runs, not gated by a project_config flag)
- `backend/app/services/file.py` — after `set_tags` and metadata `PUT`: call `IndexingStage` directly (or re-use the client) to update the document in place (`client.update(...)`)
- `backend/app/routers/files.py` — `DELETE` handler: call `client.delete(index=..., id=file_id)` after soft-delete to remove from index

---

## Step 6 — OCR stage ⏸ DEFERRED

> **Deferred — not included in Phase 3 / v1.0.** OCR will be implemented in a later release after the core search infrastructure (Steps 4, 5, 7) is stable. The `ocr_enabled` toggle in the console Settings → Processing tab is visible but disabled with a "Coming soon" badge. The `ocr_texts` table and `IndexingStage` are designed to accommodate the `ocr_text` field when OCR is added — no schema changes will be needed.

OCR extracts text from PDFs and scanned images, stores it separately, and feeds it into OpenSearch for full-text search.

**Database:**
- `ocr_texts` table: `id`, `file_id` (unique FK → `files.id`), `project_id`, `organization_id`, `text` (Text), `page_count` (int), `word_count` (int), `created_at`
- Alembic migration: `just migration "add_ocr_texts"`

**Dependencies:**
- `PyMuPDF` (fitz) — fast PDF text extraction
- `pytesseract` + `Pillow` — fallback for scanned images (requires `tesseract-ocr` in Docker image)

**Backend files:**
- `backend/app/models/ocr_text.py` — `OCRText` ORM model
- `backend/app/processing/stages/ocr.py` — `OCRStage`:
  - Only runs when `ocr_enabled=true` on project config AND file is PDF or image (`category` in `["document", "image"]`)
  - PDF path: PyMuPDF `fitz.open()` → extract text per page → join
  - Image fallback: pytesseract
  - Creates `OcrText` row in DB; `IndexingStage` (Step 5) reads it for OpenSearch
- `backend/app/processing/pipeline.py` — insert `OCRStage` after `MimeValidationStage`, before `ClassificationStage`
- `backend/app/repositories/ocr_text.py` — `OCRTextRepository`: `create`, `get_by_file_id`

---

## Step 7 — Search API

The main search endpoint. Queries OpenSearch with the given parameters and returns ranked results with highlights.

**API endpoint:**
- `POST /v1/projects/{id}/search`
- Request body:
  ```json
  {
    "q": "string",
    "filters": { "content_type": "...", "category": "...", "status": "..." },
    "tags": ["tag1"],
    "date_from": "ISO8601",
    "date_to": "ISO8601",
    "size_min": 0,
    "size_max": 0,
    "folder_id": "string",
    "sort_by": "created_at | size_bytes | filename",
    "sort_order": "asc | desc",
    "limit": 20,
    "offset": 0
  }
  ```
- Response:
  ```json
  {
    "hits": [{ "file_id": "...", "filename": "...", "score": 1.0, "highlights": { "ocr_text": ["..."] } }],
    "total": 42,
    "facets": { "content_type": { "application/pdf": 10 }, "category": { "document": 12 }, "tags": { "invoice": 5 } }
  }
  ```

**Backend files:**
- `backend/app/schemas/search.py` — `SearchRequest`, `SearchHit`, `SearchResponse`, `SearchFacets`
- `backend/app/services/search.py` — `SearchService`: builds OpenSearch bool query from request params; `multi_match` on `filename` + `ocr_text` + `metadata.*`; aggregations for facets; highlight on `ocr_text`, `filename`
- `backend/app/routers/search.py` — single `POST /v1/projects/{id}/search` endpoint under `files:read` scope
- `backend/app/routers/__init__.py` — register `search_router`

---

## Step 8 — Console: Metadata & Tags UI

Wire the new backend APIs into the file explorer — metadata side panel and tag editing.

**Files:**
- `frontend/web/src/modules/entities/schemas/metadata/` — Zod schemas (response, input, actions)
- `frontend/web/src/modules/server/core/metadata/` — clean-arch stack: interface → REST service → use cases → controllers
- `frontend/web/src/modules/server/presentation/actions/metadata.actions.ts` — `updateFileMetadataAction`, `setFileTagsAction`
- `frontend/web/src/modules/client/files/components/FileMetadataPanel.tsx` — side drawer showing metadata key-values + tag chips with edit capability
- `frontend/web/src/app/[locale]/(app)/projects/[projectId]/files/page.tsx` — wire metadata panel into file row click

---

## Step 9 — Console: Folders UI

Folder tree sidebar in the file explorer. Clicking a folder filters the file list.

**Files:**
- `frontend/web/src/modules/entities/schemas/folder/` — Zod schemas
- `frontend/web/src/modules/server/core/folder/` — clean-arch stack
- `frontend/web/src/modules/server/presentation/actions/folder.actions.ts` — `listFoldersAction`, `createFolderAction`, `deleteFolderAction`, `moveFileAction`
- `frontend/web/src/modules/client/files/components/FolderTree.tsx` — collapsible tree; clicking a folder sets `activeFolderId` in URL search param
- `frontend/web/src/app/[locale]/(app)/projects/[projectId]/files/page.tsx` — read `folder_id` from search params, pass to `FilesTable`, show `FolderTree` in sidebar

---

## Step 10 — Console: Search UI

Search bar above the file table. Calls the search API and shows results with highlights.

**Files:**
- `frontend/web/src/modules/entities/schemas/search/` — Zod schemas (`SearchRequestSchema`, `SearchResultSchema`)
- `frontend/web/src/modules/server/core/search/` — clean-arch stack
- `frontend/web/src/modules/server/presentation/actions/search.actions.ts` — `searchFilesAction`
- `frontend/web/src/modules/client/files/components/FileSearch.tsx` — debounced input (300 ms); calls `searchFilesAction`; shows result list with filename + highlight snippet; clicking a result opens the metadata panel
- `frontend/web/src/app/[locale]/(app)/projects/[projectId]/files/page.tsx` — add `FileSearch` above `FilesTable`; when a search is active, replace the table with search results

---

## Step 11 — Docs audit — Console app docs route

Review all Phase 3 features and ensure the docs route (`frontend/web/src/content/docs/`) reflects them.

**Checklist:**

- `api/search.mdx` — new file: `POST /v1/projects/{id}/search` request body, response shape with hits + facets + highlights, facet field list
- `api/files.mdx` — update: add tags endpoints (`PUT /files/{id}/tags`, `POST /files/{id}/tags`) and metadata endpoint (`PUT /files/{id}/metadata`)
- `api/metadata.mdx` — new file: metadata schemas (`POST/GET /v1/projects/{id}/metadata-schemas`), schema structure, `enforce_schema` flag, `MetadataValidationError` shape
- `api/folders.mdx` — new file: folder CRUD + file move endpoints, path materialisation, soft-delete 409 rules
- `concepts/files.mdx` — update: add tags, metadata, folder, OCR text, and search index to the file lifecycle section
- `console/files.mdx` — update: add metadata side panel, tag editing, folder sidebar, search bar
- `nav.ts` — add `{ title: "Search", href: "/docs/api/search" }`, `{ title: "Metadata", href: "/docs/api/metadata" }`, `{ title: "Folders", href: "/docs/api/folders" }` under API Reference; update Console Guide if new console pages added

---

## Summary

| Step | Description | Status |
|------|-------------|--------|
| 1 | Tags on files — DB column + set/add endpoints | ⬜ Not started |
| 2 | Custom metadata — schemas table + metadata update endpoint | ⬜ Not started |
| 3 | Folder hierarchy — table + CRUD + file move | ⬜ Not started |
| 4 | OpenSearch client + index management | ⬜ Not started |
| 5 | IndexingStage + sync on metadata/tag/delete | ⬜ Not started |
| 6 | OCR stage — PyMuPDF + pytesseract + ocr_texts table | ⏸ Deferred |
| 7 | Search API — POST /v1/projects/{id}/search | ⬜ Not started |
| 8 | Console: Metadata & Tags UI — side panel + tag editing | ⬜ Not started |
| 9 | Console: Folders UI — sidebar tree + URL-driven filter | ⬜ Not started |
| 10 | Console: Search UI — debounced search bar + result view | ⬜ Not started |
| 11 | Docs audit — Console app docs route | ⬜ Not started |
