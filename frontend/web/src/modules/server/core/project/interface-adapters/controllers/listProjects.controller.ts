/**
 * listProjects.controller — interface adapter for listing projects.
 *
 * Layer: core / project / interface-adapters / controllers
 * Operation: list
 *
 * No input validation needed — list takes no arguments. Calls the use
 * case and passes the result through the presenter.
 *
 * @module
 */
"server-only";

import { listProjectsUseCase } from "../../application/usecases/listProjects.usecase";
import type { TProjectList } from "@/modules/entities/schemas/project";

function presenter(data: TProjectList): TProjectList {
  return data;
}

export type TListProjectsControllerOutput = ReturnType<typeof presenter>;

/**
 * Lists all active projects in the caller's organisation.
 *
 * @returns Paginated project list { items, total }.
 */
export async function listProjectsController(): Promise<TListProjectsControllerOutput> {
  const data = await listProjectsUseCase();
  return presenter(data);
}
