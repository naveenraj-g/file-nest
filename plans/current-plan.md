# FileNest — Phase 4 Implementation Plan

**Phase:** 4 — Console App  
**Status:** 🔄 In Progress  
**Source:** `dev-docs/plan/00_Implementation_Roadmap.md` — Phase 4 section  
**Goal:** Developers and org admins can manage everything through a UI without touching the raw API.

**Docs to read before implementing:** `24_Admin_Dashboard`, `06_SDK_Specification` (React SDK usage)

**Exit criteria:**
- New user signs up → completes onboarding → uploads a file → downloads it — all within the UI, no terminal
- Admin creates API key with specific scopes → key works in `curl`
- Team member invited by email → accepts → sees project with correct permissions
- Webhook configured → file uploaded → delivery visible in history table within 10 seconds

> **Completed steps** get a `✅ COMPLETED` tag on the heading — never deleted, kept as history.  
> When all steps are done → rename this file to `completed-plan-phase-4.md` and create `current-plan.md` for Phase 5.

---

## Already built (carried over from Phases 1–3)

These Phase 4 deliverables are done — no further work needed:

- ✅ **Auth** — OAuth 2.1 PKCE flow (login, callback, session cookie, `getServerSession`)
- ✅ **Onboarding wizard** — create org → generate API key → install SDK → dashboard
- ✅ **Layout & navigation** — `AppSidebar`, `OrgSwitcher`, `ThemeSwitcher`, `(app)/` route guard
- ✅ **Projects page** — list, grid view, create modal, delete modal, row selection
- ✅ **Project Settings → Storage tab** — provider selector, BYOB credential form, SSE toggle, verify connection
- ✅ **Files page** — file table, status badges, download, delete, folder sidebar, metadata side panel, tag editing
- ✅ **API Keys page** — list keys, create (scopes + expiry), revoke with confirmation
- ✅ **Webhooks page** — list, add (URL + events + auto-secret), enable/disable toggle, delivery history
- ✅ **Console Settings** — appearance, theme switcher

---

## Step 1 — Dashboard page (`/dashboard`) ✅ COMPLETED

The landing page after login. Shows a snapshot of the active org's usage and quick-access actions.

**Backend:**
- `GET /v1/organizations/{org_id}/usage` — returns `{ storage_bytes_used, api_requests_30d, files_uploaded_30d, processing_jobs_30d }` (Phase 6 adds Redis metering; for now return live counts from DB aggregates)
- `GET /v1/projects/{id}/files?limit=10&sort=created_at:desc` — already exists; used for recent files list

**Frontend files:**
- `frontend/web/src/app/[locale]/(app)/dashboard/page.tsx` — server component; fetches usage + recent files in parallel
- `frontend/web/src/modules/client/dashboard/components/UsageCards.tsx` — 4 stat cards (storage, requests, uploads, jobs) using shadcn/ui `Card`
- `frontend/web/src/modules/client/dashboard/components/RecentFilesList.tsx` — last 10 files across all projects; filename, project name, status badge, relative timestamp
- `frontend/web/src/modules/client/dashboard/components/QuickActions.tsx` — "Upload file", "Create project", "Generate API key" buttons (link/modal openers)
- `frontend/web/src/modules/server/core/usage/` — clean-arch stack: domain interface → REST service → use case → controller
- `frontend/web/src/modules/server/presentation/actions/usage.actions.ts` — `getOrgUsageAction`
- `frontend/web/src/modules/entities/schemas/usage/` — `OrgUsageSchema`, `UsageActionSchema`

---

## Step 2 — File upload UI ✅ COMPLETED

The **Upload** button in the files page toolbar is currently disabled. Wire it to a real upload flow.

**Approach:** Presigned URL flow — console calls `POST /files/upload` to get a presigned S3 URL, PUTs the bytes directly, then calls `POST /files/{id}/confirm`. No SDK dependency.

**Frontend files:**
- `frontend/web/src/modules/client/files/components/FileUploadModal.tsx` — `Dialog` wrapping a drag-and-drop zone (`react-dropzone`). Shows per-file progress bars. Calls `initiateUploadAction` → PUT to presigned URL → `confirmUploadAction`. Closes on all complete; `incrementTrigger()` to refresh the table.
- `frontend/web/src/modules/client/files/forms/UploadFileForm.tsx` — file picker + optional metadata JSON field
- `frontend/web/src/modules/entities/schemas/file/` — add `InitiateUploadSchema`, `ConfirmUploadSchema`, `InitiateUploadActionSchema`, `ConfirmUploadActionSchema`
- `frontend/web/src/modules/server/core/file/application/usecases/initiateUpload.usecase.ts`
- `frontend/web/src/modules/server/core/file/application/usecases/confirmUpload.usecase.ts`
- `frontend/web/src/modules/server/core/file/interface-adapters/controllers/initiateUpload.controller.ts`
- `frontend/web/src/modules/server/core/file/interface-adapters/controllers/confirmUpload.controller.ts`
- `frontend/web/src/modules/server/presentation/actions/file.actions.ts` — add `initiateUploadAction`, `confirmUploadAction`
- `frontend/web/src/modules/client/files/stores/file.store.ts` — add `"uploadFile"` to `FileModalType`
- `frontend/web/src/modules/client/files/provider/FileModalProvider.tsx` — mount `<FileUploadModal />`
- Update `FilesTable.tsx` toolbar — enable the Upload button, wire `onOpen("uploadFile")`

---

## Step 3 — File rename + move to folder

Two new row actions in the files table, both using the existing backend endpoints.

**Backend (already exists):**
- Rename: `PATCH /v1/projects/{id}/files/{file_id}` with `{ filename }` — if not already present, add this to `FileService.update()`
- Move: `POST /v1/projects/{id}/files/{file_id}/move` with `{ folder_id }` — already built in Phase 3

**Frontend files:**
- `frontend/web/src/modules/client/files/forms/RenameFileForm.tsx` — single `FormInput` pre-filled with current filename
- `frontend/web/src/modules/client/files/modals/RenameFileModal.tsx` — `Dialog` wrapping the form
- `frontend/web/src/modules/client/files/modals/MoveFileModal.tsx` — `Dialog` with a folder selector (flat `<select>` seeded from the folder list already fetched by the page)
- `frontend/web/src/modules/entities/schemas/file/` — add `RenameFileSchema`, `MoveFileSchema`, `RenameFileActionSchema`, `MoveFileActionSchema`
- `frontend/web/src/modules/server/core/file/application/usecases/renameFile.usecase.ts`
- `frontend/web/src/modules/server/core/file/application/usecases/moveFile.usecase.ts`
- `frontend/web/src/modules/server/core/file/interface-adapters/controllers/renameFile.controller.ts`
- `frontend/web/src/modules/server/core/file/interface-adapters/controllers/moveFile.controller.ts`
- `frontend/web/src/modules/server/presentation/actions/file.actions.ts` — add `renameFileAction`, `moveFileAction`
- `frontend/web/src/modules/client/files/stores/file.store.ts` — add `"renameFile"`, `"moveFile"` to `FileModalType`
- `frontend/web/src/modules/client/files/provider/FileModalProvider.tsx` — mount new modals
- `frontend/web/src/modules/client/files/components/FilesTableColumn.tsx` — add "Rename" and "Move to folder" row actions

---

## Step 4 — Team management (`/org/team`)

Invite members, assign roles, remove members. All operations call the **IAM API** (BetterAuth organization plugin), not the FileNest backend.

**IAM endpoints used (BetterAuth `organization` plugin):**
- `POST /api/auth/organization/invite-member` — invite by email + role
- `GET /api/auth/organization/list-members` — list current members
- `POST /api/auth/organization/update-member-role` — change role
- `POST /api/auth/organization/remove-member` — remove from org

**Frontend files:**
- `frontend/web/src/app/[locale]/(app)/org/team/page.tsx` — server component; fetches member list from IAM
- `frontend/web/src/modules/client/team/components/TeamTable.tsx` — member list: avatar, name, email, role badge, actions menu
- `frontend/web/src/modules/client/team/components/TeamTableColumn.tsx` — column defs
- `frontend/web/src/modules/client/team/forms/InviteMemberForm.tsx` — email + role select (`Owner` / `Admin` / `Member` / `Viewer`)
- `frontend/web/src/modules/client/team/modals/InviteMemberModal.tsx`
- `frontend/web/src/modules/client/team/modals/RemoveMemberModal.tsx` — `AlertDialog` (destructive)
- `frontend/web/src/modules/client/team/modals/ChangeRoleModal.tsx` — `Dialog` with role select
- `frontend/web/src/modules/client/team/provider/TeamModalProvider.tsx`
- `frontend/web/src/modules/client/team/stores/team.store.ts`
- `frontend/web/src/modules/entities/schemas/team/` — `MemberSchema`, `InviteMemberSchema`, `ChangeRoleSchema`, action schemas
- `frontend/web/src/modules/server/core/team/` — domain interface → IAM REST service → use cases → controllers
- `frontend/web/src/modules/server/presentation/actions/team.actions.ts` — `listMembersAction`, `inviteMemberAction`, `changeRoleAction`, `removeMemberAction`

---

## Step 5 — Usage page (`/org/usage`)

Shows org-level usage meters with a per-project breakdown table.

**Backend:**
- `GET /v1/organizations/{org_id}/usage` — already planned in Step 1; reuse the same endpoint
- `GET /v1/organizations/{org_id}/usage/projects` — per-project breakdown: `[{ project_id, name, storage_bytes, file_count, api_requests_30d }]`

**Frontend files:**
- `frontend/web/src/app/[locale]/(app)/org/usage/page.tsx` — server component; fetches org usage + project breakdown
- `frontend/web/src/modules/client/usage/components/UsageMeters.tsx` — storage, API requests, processing jobs; shadcn/ui `Progress` bar showing used vs. limit with percentage label
- `frontend/web/src/modules/client/usage/components/ProjectUsageTable.tsx` — per-project table: project name, storage used, file count, API requests; sortable columns
- `frontend/web/src/modules/server/core/usage/` — extend with `getProjectBreakdownUseCase` if not already added in Step 1
- `frontend/web/src/modules/entities/schemas/usage/` — `ProjectUsageSchema`, `ProjectUsageListSchema`

---

## Step 6 — Project Settings — General + Processing tabs

The Settings page already has the Storage tab. Complete the other two tabs.

**General tab** (update project name/description):
- `frontend/web/src/modules/client/settings/forms/UpdateProjectForm.tsx` — `FormInput` for name + `FormTextarea` for description; calls `updateProjectAction` (already exists)
- Wire into the existing `frontend/web/src/app/[locale]/(app)/projects/[projectId]/settings/page.tsx`

**Processing tab** (toggle pipeline stages):
- Virus scan toggle — always enabled, shown as read-only with a tooltip
- OCR toggle — shows "Coming soon" badge (deferred per Phase 3 plan)
- `frontend/web/src/modules/client/settings/components/ProcessingSettings.tsx`
- Calls `updateProjectConfigAction` (wire to `PATCH /v1/projects/{id}/config` if not yet built — adds `ocr_enabled`, `virus_scan_enabled` to `ProjectConfig`)

---

## Step 7 — Docs audit — Console app docs route

Review all Phase 4 features built in this phase and ensure the docs route reflects them.

**Checklist:**
- `console/dashboard.mdx` — new file: usage cards, recent files list, quick actions
- `console/files.mdx` — update: add file upload flow (drag-and-drop, progress), rename, move to folder
- `console/team.mdx` — new file: invite member, role assignment, remove member
- `console/usage.mdx` — new file: usage meters, per-project breakdown table
- `console/settings.mdx` — update: general tab (name/description), processing tab (OCR coming soon)
- `nav.ts` — add `{ title: "Dashboard", href: "/docs/console/dashboard" }`, `{ title: "Team", href: "/docs/console/team" }`, `{ title: "Usage", href: "/docs/console/usage" }` under Console Guide

---

## Summary

| Step | Description | Status |
|------|-------------|--------|
| — | Auth, onboarding, layout, projects, API keys, webhooks, settings | ✅ Carried over |
| 1 | Dashboard page — usage cards, recent files, quick actions | ✅ Completed |
| 2 | File upload UI — drag-and-drop, presigned URL flow, progress bars | ✅ Completed |
| 3 | File rename + move to folder — row actions + modals | ⬜ Not started |
| 4 | Team management — invite, role assignment, remove | ⬜ Not started |
| 5 | Usage page — org meters + per-project breakdown | ⬜ Not started |
| 6 | Project Settings — General + Processing tabs | ⬜ Not started |
| 7 | Docs audit — Console app docs route | ⬜ Not started |
