"use client";

import { Sidebar } from "@/components/sidebar";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <main className="ml-[264px] min-h-screen">
        <div className="p-8">{children}</div>
      </main>
    </div>
  );
}
