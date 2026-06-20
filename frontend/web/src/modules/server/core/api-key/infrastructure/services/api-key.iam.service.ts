/**
 * api-key.iam.service — IAM implementation of IApiKeyService.
 *
 * Layer: core / api-key / infrastructure / services
 *
 * Calls the BetterAuth IAM REST API via iamApi. All key management
 * (create / list / revoke) lives in the IAM — the FileNest backend
 * validates keys but does not manage them.
 *
 * Bound in the DI container by registerApiKeyModule().
 *
 * @module
 */
"server-only";

import { iamApi } from "@/modules/server/utils/iam-api-client";
import {
  ApiKeyListSchema,
  CreatedApiKeySchema,
  type TApiKeyList,
  type TCreatedApiKey,
  type TCreateApiKey,
  type TListApiKeys,
  type TRevokeApiKey,
} from "@/modules/entities/schemas/api-key";
import { OutputParseError } from "@/modules/server/shared/errors/schema-parse-error";
import type { IApiKeyService } from "../../domain/interfaces/api-key.service.interface";

export class ApiKeyIamService implements IApiKeyService {
  async list(params: TListApiKeys): Promise<TApiKeyList> {
    const qs = new URLSearchParams({ organizationId: params.organizationId });
    const raw = await iamApi<unknown>(`/api/auth/api-key/list?${qs}`);
    const parsed = ApiKeyListSchema.safeParse(raw);
    if (!parsed.success) throw new OutputParseError(parsed.error);
    const { organizationId, projectId } = params;
    // Filter to keys that belong to this org and project (stored in metadata)
    const filtered = parsed.data.apiKeys.filter((k) => {
      if (k.organizationId && k.organizationId !== organizationId) return false;
      if (
        projectId &&
        k.metadata?.projectId &&
        k.metadata.projectId !== projectId
      )
        return false;
      return true;
    });
    return { apiKeys: filtered };
  }

  async create(dto: TCreateApiKey): Promise<TCreatedApiKey> {
    const body: Record<string, unknown> = {
      name: dto.name,
      organizationId: dto.organizationId,
      metadata: {
        organizationId: dto.organizationId,
        projectId: dto.projectId ?? null,
        scopes: dto.scopes,
      },
    };
    if (dto.expiresInDays) {
      body.expiresIn = dto.expiresInDays * 86400;
    }
    const raw = await iamApi<unknown>("/api/auth/api-key/create", {
      method: "POST",
      body: JSON.stringify(body),
    });
    const parsed = CreatedApiKeySchema.safeParse(raw);
    if (!parsed.success) throw new OutputParseError(parsed.error);
    return parsed.data;
  }

  async revoke(params: TRevokeApiKey): Promise<void> {
    await iamApi<void>("/api/auth/api-key/delete", {
      method: "POST",
      body: JSON.stringify({ keyId: params.keyId }),
    });
  }
}
