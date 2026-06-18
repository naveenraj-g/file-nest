# FileNest — Client-Side Component Skill

## Purpose
Build and scaffold **client-side (browser) components** for the FileNest platform.
Covers: React SDK (`@filenest/react`), Next.js client components, upload token flow,
hooks, and TanStack Query integration.

## When to invoke
- User asks to add/build a file upload UI, file browser, file viewer, or search UI
- User asks to wire up `@filenest/react` components or hooks
- User asks how client-side upload tokens work
- User asks to build a Next.js page that uploads or displays files client-side

---

## Modules Folder Structure — `modules/client/`

All browser components and hooks live under `modules/client/`. Follow this layout:

```
modules/client/
├── (marketing)/               # Landing / feature pages (no auth required)
│   ├── components/            # Section components: Hero, Features, SdkSection, Footer, …
│   └── pages/                 # Full-page components used by app/[locale]/(marketing)/ routes
├── auth/                      # Login/callback/signup UI components
├── dashboard/                 # Dashboard widgets + hooks
├── projects/                  # Projects list + project detail client components
├── files/                     # FileUpload, FileExplorer, FilePreview wrappers + hooks
├── onboarding/                # Onboarding wizard step components
├── settings/                  # Settings sub-page components (Appearance, Profile, …)
└── shared/                    # Shared cross-feature UI
    └── components/
        ├── layout/            # AppSidebar, Header, OrgSwitcher, ThemeSwitcher
        └── tables/            # TanStack Table shared column helpers
```

### Rules for `modules/client/`

- **Mark with `'use client'`** at the top of any file that uses hooks, event handlers, or browser APIs.
- **Never import from `modules/server/`** in client files — this breaks server-only boundaries.
- **Import from `modules/entities/schemas/`** for Zod types — those are safe in both environments.
- **Split large components** — if JSX exceeds ~120 lines, extract sub-sections into co-located files.
- **Feature sub-folders** (`dashboard/`, `projects/`, `files/`) contain components *and* hooks for that feature.
- **`(marketing)/` mirrors the `(marketing)` route group** — keeps landing-page code isolated from the product UI.
- **Reference:** `E:\work\code\drgodly` for folder conventions and the compound `data-theme` theme system.

---

## Architecture Rule: Client Never Holds API Key

The browser **never** gets the API key (`fn_live_...` / `fn_test_...`).
The flow is always:

```
Browser → POST /api/filenest-token (your server)
        ← { token: "fn_upload_token_...", expiresAt }
Browser → Upload directly to storage using the token
```

The `<FileNestProvider>` handles this automatically via `tokenEndpoint`.

---

## Step 1 — Provider Setup (once per app)

```tsx
// app/layout.tsx  (Next.js App Router)
import { FileNestProvider } from '@filenest/react';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html>
      <body>
        <FileNestProvider
          tokenEndpoint="/api/filenest-token"
          projectId={process.env.NEXT_PUBLIC_FILENEST_PROJECT_ID!}
          options={{ environment: 'production', debug: process.env.NODE_ENV === 'development' }}
        >
          {children}
        </FileNestProvider>
      </body>
    </html>
  );
}
```

Token endpoint (server-side — see `filenest-server` skill for full implementation):
```typescript
// app/api/filenest-token/route.ts
import { createUploadToken } from '@filenest/nextjs/server';
export async function POST(req: Request) {
  // ... auth check ...
  const token = await createUploadToken({ apiKey, projectId, constraints, metadata, expiresIn: 3600 });
  return Response.json(token);
}
```

---

## Step 2 — Choose the right component

| Need | Component / Hook |
|------|-----------------|
| Drag-and-drop upload | `<FileUpload variant="dropzone">` |
| Button-triggered upload | `<FileUpload variant="button">` |
| Browse files & folders | `<FileExplorer>` |
| Inline file preview | `<FilePreview>` |
| Full-page document viewer | `<FileViewer>` |
| Programmatic upload | `useUpload()` |
| List files with filters | `useFiles()` |
| Search across files | `useSearch()` |
| Single file detail | `useFile()` |
| Folder navigation | `useFolder()` |
| Imperative API access | `useFileNest()` |

---

## FileUpload Component

```tsx
'use client';
import { FileUpload } from '@filenest/react';

export function DocumentUploader() {
  return (
    <FileUpload
      accept={['application/pdf', 'image/jpeg', 'image/png']}
      maxSize={50 * 1024 * 1024}   // 50 MB
      maxFiles={10}
      multiple={true}
      folderId="folder_abc"
      metadata={{ documentType: 'LabReport', uploadedBy: 'user_id_here' }}
      metadataForm={{
        fields: [
          { name: 'documentType', label: 'Document Type', type: 'select',
            options: ['LabReport', 'Discharge', 'Consent'], required: true },
          { name: 'notes', label: 'Notes', type: 'textarea' },
        ],
      }}
      variant="dropzone"
      placeholder="Drag and drop clinical documents here"
      showProgress={true}
      showPreview={true}
      onComplete={(files) => console.log('Uploaded', files)}
      onError={(error, file) => console.error(`Failed to upload ${file.filename}: ${error.message}`)}
      onValidationError={(errors) => errors.forEach(e => console.warn(e.message))}
    />
  );
}
```

---

## FileExplorer Component

```tsx
'use client';
import { FileExplorer } from '@filenest/react';
import { useState } from 'react';

export function DocumentBrowser() {
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);

  return (
    <FileExplorer
      rootFolderId={null}
      defaultView="grid"
      showFolders={true}
      showSearch={true}
      showFilters={true}
      showUploadButton={true}
      columns={['filename', 'size', 'mimeType', 'metadata.documentType', 'createdAt']}
      searchFacets={['documentType', 'tags']}
      selectable={true}
      multiSelect={true}
      selectedIds={selectedFiles}
      onSelectionChange={setSelectedFiles}
      actions={['download', 'delete', 'move', 'rename']}
      onFileClick={(file) => console.log('Clicked', file)}
      metadataColumns={[
        { field: 'metadata.patientId', header: 'Patient ID' },
        { field: 'metadata.documentType', header: 'Type' },
      ]}
      emptyState={<div>No documents found.</div>}
    />
  );
}
```

---

## FilePreview Component

```tsx
'use client';
import { FilePreview } from '@filenest/react';

export function PreviewPanel({ fileId, onClose }: { fileId: string; onClose: () => void }) {
  return (
    <FilePreview
      fileId={fileId}
      showMetadata={true}
      showVersionHistory={true}
      showProcessingResults={true}
      allowDownload={true}
      downloadTtl={3600}
      height="600px"
      width="100%"
      onClose={onClose}
      onDownload={(url) => window.open(url)}
      onVersionSelect={(version) => console.log('Version selected', version)}
    />
  );
}
```

---

## FileViewer Component

```tsx
'use client';
import { FileViewer } from '@filenest/react';

export function FullPageViewer({ fileId }: { fileId: string }) {
  return (
    <FileViewer
      fileId={fileId}
      showToolbar={true}
      showSidebar={true}
      pdf={{ showPageNumbers: true, enableSearch: true, enableZoom: true, defaultZoom: 'fit-width' }}
      image={{ enableZoom: true, enableRotate: true }}
      layout="fullscreen"
      onClose={() => history.back()}
    />
  );
}
```

---

## Hooks

### useUpload — programmatic upload with progress state

```tsx
'use client';
import { useUpload } from '@filenest/react';

function UploadButton() {
  const { upload, uploads, isUploading, cancel, retry } = useUpload({
    metadata: { uploadedBy: 'user_id' },
    folderId: 'folder_abc',
    onComplete: (file) => console.log('Uploaded', file.id),
  });

  return (
    <div>
      <input type="file" multiple onChange={e => upload(Array.from(e.target.files || []))} />
      {uploads.map(u => (
        <div key={u.id}>
          {u.filename}: {u.status === 'uploading' ? `${u.progress}%` : u.status}
          {u.status === 'failed' && <button onClick={() => retry(u.id)}>Retry</button>}
        </div>
      ))}
    </div>
  );
}
```

### useFiles — list with filters and infinite scroll

```tsx
'use client';
import { useFiles } from '@filenest/react';

function FileList({ patientId }: { patientId: string }) {
  const { files, isLoading, isError, error, hasMore, loadMore, totalCount } = useFiles({
    filters: { metadata: { patientId }, tags: ['clinical'] },
    sortBy: 'created_at',
    sortOrder: 'desc',
    limit: 20,
  });

  if (isLoading) return <div>Loading...</div>;
  if (isError) return <div>Error: {error.message}</div>;

  return (
    <div>
      <p>{totalCount} documents</p>
      {files.map(file => <div key={file.id}>{file.filename}</div>)}
      {hasMore && <button onClick={loadMore}>Load more</button>}
    </div>
  );
}
```

### useSearch — debounced full-text + faceted search

```tsx
'use client';
import { useSearch } from '@filenest/react';
import { useState } from 'react';

function SearchBox() {
  const [query, setQuery] = useState('');
  const { results, facets, isLoading, totalCount, queryTimeMs, search } = useSearch({
    debounceMs: 300,
    facets: ['documentType', 'tags'],
  });

  return (
    <div>
      <input
        value={query}
        onChange={e => { setQuery(e.target.value); search({ q: e.target.value }); }}
        placeholder="Search documents..."
      />
      {!isLoading && <p>{totalCount} results in {queryTimeMs}ms</p>}
      {results.map(f => <div key={f.id}>{f.filename}</div>)}
    </div>
  );
}
```

### useFile — single file detail with revalidation

```tsx
'use client';
import { useFile } from '@filenest/react';

function FileDetail({ fileId }: { fileId: string }) {
  const { file, isLoading, mutate } = useFile(fileId, {
    includeVersions: true,
    includeProcessing: true,
  });

  if (!file) return null;
  return <div>{file.filename} — {file.status}</div>;
}
```

### useFolder — folder navigation with breadcrumbs

```tsx
'use client';
import { useFolder } from '@filenest/react';

function FolderView({ folderId }: { folderId: string | null }) {
  const { folder, files, subfolders, isLoading, breadcrumbs } = useFolder(folderId);

  return (
    <div>
      <nav>{breadcrumbs.map(b => <span key={b.id}>{b.name} / </span>)}</nav>
      {subfolders.map(f => <div key={f.id}>{f.name}/</div>)}
      {files.map(f => <div key={f.id}>{f.filename}</div>)}
    </div>
  );
}
```

### useFileNest — imperative API for custom flows

```tsx
'use client';
import { useFileNest } from '@filenest/react';

function CustomUpload() {
  const filenest = useFileNest();

  const handleFile = async (file: File) => {
    const result = await filenest.upload(file, {
      metadata: { uploadedBy: 'user_abc' },
      onProgress: (p) => console.log(`${p.percentage}%`),
    });
    console.log('Uploaded:', result.id);
  };

  return <button onClick={() => document.querySelector<HTMLInputElement>('input')?.click()}>Upload</button>;
}
```

---

## Error Handling (client-side)

```typescript
import { FileNestError, WORMViolationError, MetadataValidationError, LegalHoldError } from '@filenest/react';

try {
  await filenest.files.delete('file_xyz789');
} catch (error) {
  if (error instanceof WORMViolationError) {
    toast.error('Cannot delete WORM-committed file');
  } else if (error instanceof LegalHoldError) {
    toast.error(`File under legal hold: ${error.reason}`);
  } else if (error instanceof MetadataValidationError) {
    error.validationErrors.forEach(e => toast.warning(`${e.field}: ${e.message}`));
  } else if (error instanceof FileNestError) {
    toast.error(`Error ${error.code}: ${error.message}`);
  }
}
```

---

## Key rules

1. **Always mark client components with `'use client'`** — FileNest React components use hooks and state.
2. **Never put `FILENEST_API_KEY` in client code** — only `NEXT_PUBLIC_*` env vars are safe in the browser.
3. **Token endpoint must auth-gate itself** — verify the user session before calling `createUploadToken`.
4. **`useFiles` and `useSearch` are TanStack Query-backed** — call `refresh()` or `mutate()` after mutations.
5. **`metadata` in component props is merged with token-level constraints** — no need to duplicate fields.
6. **Use `onComplete` for post-upload side effects** — `revalidatePath`, state updates, notifications.
