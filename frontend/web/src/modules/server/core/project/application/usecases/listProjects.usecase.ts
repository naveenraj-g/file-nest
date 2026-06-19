/**
 * listProjects.usecase — application layer use case.
 *
 * Layer: core / project / application / usecases
 * Operation: list all projects in the caller's organisation
 *
 * @module
 */
"server-only";

import { getInjection } from "@/modules/server/di/container";
import type { TProjectList } from "@/modules/entities/schemas/project";

/**
 * Returns all active projects for the caller's organisation.
 *
 * @returns Paginated project list { items, total }.
 * @throws ApiError propagated from the service.
 */
export async function listProjectsUseCase(): Promise<TProjectList> {
  const service = getInjection("IProjectService");
  return service.list();
}
