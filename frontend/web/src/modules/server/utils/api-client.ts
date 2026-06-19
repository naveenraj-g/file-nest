/**
 * server/utils/api-client — typed fetch wrapper for the FileNest backend.
 *
 * Reads FILENEST_API_URL and FILENEST_API_KEY from the server environment,
 * attaches the Authorization header, and throws ApiError on non-2xx responses
 * so callers never need to inspect res.ok themselves.
 *
 * @module
 */
"server-only";

import { ApiError } from "@/modules/server/shared/errors/mappers/map-error-to-zsa";

const API_URL = process.env.FILENEST_API_URL ?? "http://localhost:8000";
const API_KEY = process.env.FILENEST_API_KEY ?? "";

export async function filenestApi<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${API_KEY}`,
      ...(options.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = body?.detail?.message ?? body?.detail ?? body?.message ?? message;
    } catch {
      // leave message as statusText
    }
    throw new ApiError(res.status, message);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}
