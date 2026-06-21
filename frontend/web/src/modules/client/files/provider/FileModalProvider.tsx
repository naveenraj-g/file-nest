/**
 * FileModalProvider — mounts all file modals once, client-only.
 *
 * The mount guard (isMounted) ensures modals are never rendered during SSR.
 * Render <FileModalProvider /> once in the files page alongside the table.
 *
 * @module
 */
"use client";

import { useEffect, useState } from "react";
import { DeleteFileModal } from "@/modules/client/files/modals/DeleteFileModal";
import { FileMetadataPanel } from "@/modules/client/files/components/FileMetadataPanel";

export function FileModalProvider() {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  if (!isMounted) return null;

  return (
    <>
      <DeleteFileModal />
      <FileMetadataPanel />
    </>
  );
}
