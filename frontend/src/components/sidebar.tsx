"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import {
  LayoutDashboard,
  FileText,
  Calendar,
  CheckSquare,
  Stamp,
  Lightbulb,
  Users,
  Settings,
  LogOut,
  BarChart3,
  ClipboardList,
  Bot,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { isBoardOrAbove, isAdmin, type Role } from "@/lib/permissions";
import { useBranding } from "@/contexts/branding-context";

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

interface NavGroup {
  label: string;
  items: NavItem[];
  visibleTo: "all" | "board" | "admin";
}

const boardNavGroups: NavGroup[] = [
  {
    label: "Main",
    visibleTo: "board",
    items: [
      { label: "Dashboard", href: "/", icon: LayoutDashboard },
      { label: "Documents", href: "/documents", icon: FileText },
      { label: "Meetings", href: "/meetings", icon: Calendar },
      { label: "Decisions", href: "/decisions", icon: CheckSquare },
      { label: "Resolutions", href: "/resolutions", icon: Stamp },
      { label: "Ideas", href: "/ideas", icon: Lightbulb },
    ],
  },
  {
    label: "Admin",
    visibleTo: "admin",
    items: [
      { label: "Users", href: "/admin/users", icon: Users },
      { label: "Templates", href: "/admin/templates", icon: ClipboardList },
      { label: "Agents", href: "/admin/agents", icon: Bot },
      { label: "Settings", href: "/admin/settings", icon: Settings },
    ],
  },
];

const shareholderNavGroups: NavGroup[] = [
  {
    label: "Shareholder",
    visibleTo: "all",
    items: [
      { label: "Reports", href: "/reports", icon: BarChart3 },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { data: session } = useSession();
  const { branding } = useBranding();

  const userRole = (session?.user as { role?: Role })?.role;
  const isBoardLevel = isBoardOrAbove(userRole);
  const isAdminUser = isAdmin(userRole);

  // Board+ users see everything; shareholders see only their section
  const navGroups = isBoardLevel
    ? [...boardNavGroups, ...shareholderNavGroups]
    : shareholderNavGroups;

  const handleSignOut = () => {
    signOut({ callbackUrl: "/login" });
  };

  return (
    <aside className="fixed left-0 top-0 h-full w-[264px] bg-[#0a0a0f] border-r border-[#1e2030] flex flex-col">
      {/* Logo Header */}
      <div className="h-16 flex items-center px-5 border-b border-[#1e2030]">
        <Link href="/" className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-gold/10 border border-gold/30 flex items-center justify-center">
            <span className="font-mono text-xs font-medium text-gold">{branding.app_name?.[0]?.toUpperCase() || "B"}</span>
          </div>
          <div>
            <span className="font-serif text-lg font-light tracking-tight text-[var(--paper)]">
              {branding.app_name}
            </span>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-6 px-3 space-y-6">
        {navGroups
          .filter((group) => {
            if (group.visibleTo === "admin") return isAdminUser;
            if (group.visibleTo === "board") return isBoardLevel;
            return true;
          })
          .map((group) => (
            <div key={group.label}>
              <div className="font-mono text-[10px] tracking-[0.2em] uppercase text-[var(--mist)] mb-3 px-3 flex items-center gap-2">
                <span>{group.label}</span>
                <div className="flex-1 h-px bg-[#1e2030]" />
              </div>
              <ul className="space-y-0.5">
                {group.items.map((item) => {
                  const isActive =
                    pathname === item.href ||
                    (item.href !== "/" && pathname.startsWith(item.href));
                  const Icon = item.icon;

                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        className={cn(
                          "flex items-center gap-3 px-3 py-2.5 rounded text-sm transition-all",
                          isActive
                            ? "bg-gold/10 text-gold border-l-2 border-gold ml-0 pl-2.5"
                            : "text-[var(--mist)] hover:text-[var(--paper)] hover:bg-[#12121a]"
                        )}
                      >
                        <Icon className={cn("h-4 w-4", isActive ? "text-gold" : "")} />
                        <span className={cn(isActive ? "font-medium" : "font-light")}>
                          {item.label}
                        </span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
      </nav>

      {/* User Section */}
      <div className="p-4 border-t border-[#1e2030]">
        <div className="flex items-center gap-3">
          {session?.user?.image ? (
            <img
              src={session.user.image}
              alt={session.user.name || "User"}
              className="w-8 h-8 rounded-full"
            />
          ) : (
            <div className="w-8 h-8 rounded-full bg-[var(--steel)] flex items-center justify-center">
              <span className="text-xs font-medium text-[var(--paper)]">
                {session?.user?.name?.[0] || "?"}
              </span>
            </div>
          )}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <p className="text-sm font-medium truncate text-[var(--paper)]">
                {session?.user?.name || "User"}
              </p>
              {userRole && (
                <span className="font-mono text-[9px] tracking-wider px-1.5 py-0.5 rounded bg-gold/10 text-gold uppercase">
                  {userRole}
                </span>
              )}
            </div>
            <p className="text-xs text-[var(--mist)] truncate">
              {session?.user?.email}
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleSignOut}
            title="Sign out"
            className="text-[var(--mist)] hover:text-[var(--paper)]"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </aside>
  );
}
