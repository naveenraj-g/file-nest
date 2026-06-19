/**
 * NewProjectPage — server shell for the create-project form.
 *
 * Renders a constrained-width layout with a back link and delegates all
 * interactivity to the CreateProjectForm client component. No data fetching
 * needed here — the form submits directly via a server action.
 *
 * @module
 */
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CreateProjectForm } from "@/modules/client/projects/components/CreateProjectForm";

export default function NewProjectPage() {
  return (
    <div className="max-w-lg space-y-6">
      <div>
        <Button variant="ghost" size="sm" asChild className="-ml-2 mb-2">
          <Link href="/projects">
            <ChevronLeft className="h-4 w-4 mr-1" />
            Projects
          </Link>
        </Button>
        <h1 className="text-2xl font-semibold">New project</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Configure storage and start uploading files.
        </p>
      </div>

      <CreateProjectForm />
    </div>
  );
}
