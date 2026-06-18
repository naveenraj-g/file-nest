/**
 * AppSidebar — collapsible left navigation for the FileNest Console.
 *
 * Uses the shadcn Sidebar primitive. When expanded shows icon + label;
 * when collapsed shows icon only with tooltip. State persists via the
 * sidebar_state cookie managed by SidebarProvider.
 *
 * @module
 */
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  FolderOpen,
  LayoutDashboard,
  Settings,
  ShieldAlert,
  Users,
  BarChart2,
  HardDrive,
  Webhook,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar";

const NAV_ITEMS = [
  { href: "/dashboard",   label: "Dashboard",  icon: LayoutDashboard },
  { href: "/projects",    label: "Projects",   icon: FolderOpen },
  { href: "/org/team",    label: "Team",       icon: Users },
  { href: "/org/usage",   label: "Usage",      icon: BarChart2 },
  { href: "/settings",    label: "Settings",   icon: Settings },
] as const;

interface AppSidebarProps {
  userRole?: string | null;
}

export function AppSidebar({ userRole }: AppSidebarProps) {
  const pathname = usePathname();

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild className="pointer-events-none">
              <div>
                <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground shrink-0">
                  <HardDrive className="h-4 w-4" />
                </div>
                <span className="font-semibold truncate">FileNest</span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
                const active = pathname === href || pathname.startsWith(`${href}/`);
                return (
                  <SidebarMenuItem key={href}>
                    <SidebarMenuButton asChild isActive={active} tooltip={label}>
                      <Link href={href}>
                        <Icon />
                        <span>{label}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {userRole === "superadmin" && (
          <SidebarGroup className="mt-auto">
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    asChild
                    tooltip="Admin"
                    className="text-muted-foreground hover:text-destructive"
                  >
                    <Link href="/admin/users">
                      <ShieldAlert />
                      <span>Admin</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>

      <SidebarFooter>
        <p className="px-2 py-1 text-xs text-muted-foreground group-data-[collapsible=icon]:hidden">
          v0.1.0 · Phase 1
        </p>
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>
  );
}
