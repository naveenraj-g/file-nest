/**
 * Dashboard page — top-level landing page after sign-in.
 *
 * Phase 1: placeholder. Phase 4 will add usage summary, recent files,
 * and quick actions.
 *
 * @module
 */
import { getServerSession } from "@/modules/server/auth/get-session";

export default async function DashboardPage() {
  const session = await getServerSession();

  return (
    <main className="p-8">
      <h1 className="text-2xl font-semibold">Welcome, {session?.user.name}</h1>
      <p className="text-muted-foreground mt-1">FileNest Console — Phase 1 scaffold</p>
    </main>
  );
}
