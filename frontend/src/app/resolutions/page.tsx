"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Stamp,
  CheckCircle,
  Clock,
  ChevronRight,
  Loader2,
  PenLine,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { resolutionsApi, api, type ResolutionListItem } from "@/lib/api";

const statusConfig: Record<string, { label: string; color: string; icon: React.ComponentType<{ className?: string }> }> = {
  pending: { label: "Pending", color: "bg-muted text-muted-foreground", icon: Clock },
  open: { label: "Open", color: "bg-blue-500/20 text-blue-400", icon: Stamp },
  closed: { label: "Closed", color: "bg-muted text-muted-foreground", icon: CheckCircle },
};

export default function ResolutionsPage() {
  const { data: session } = useSession();
  const [filter, setFilter] = useState<"all" | "open" | "closed">("all");
  const [resolutions, setResolutions] = useState<ResolutionListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const email = session?.user?.email;
    if (!email) return;

    const fetchResolutions = async () => {
      try {
        setLoading(true);
        api.setUserEmail(email);
        const data = await resolutionsApi.list();
        setResolutions(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load resolutions");
      } finally {
        setLoading(false);
      }
    };

    fetchResolutions();
  }, [session?.user?.email]);

  const filteredResolutions = resolutions.filter((r) => {
    if (filter === "all") return true;
    return r.status === filter;
  });

  const openResolutions = resolutions.filter((r) => r.status === "open");
  const closedResolutions = resolutions.filter((r) => r.status === "closed");

  if (loading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <p className="text-destructive">{error}</p>
          <Button onClick={() => window.location.reload()}>Retry</Button>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <div className="font-mono text-[10px] tracking-[0.2em] uppercase text-[var(--gold)] mb-2 flex items-center gap-3">
            <span>Governance</span>
            <div className="flex-1 h-px bg-border" />
          </div>
          <h1 className="text-3xl font-light">Resolutions</h1>
          <p className="text-sm font-light text-muted-foreground mt-1">
            Board resolutions and digital signatures
          </p>
        </div>

        {/* Filter Tabs */}
        <div className="flex gap-2">
          {[
            { key: "all", label: `All (${resolutions.length})` },
            { key: "open", label: `Open (${openResolutions.length})` },
            { key: "closed", label: `Closed (${closedResolutions.length})` },
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setFilter(key as typeof filter)}
              className={cn(
                "px-4 py-2 rounded-md text-sm font-medium transition-colors",
                filter === key
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted hover:bg-muted/80"
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Resolution Cards */}
        <div className="space-y-3">
          {filteredResolutions.map((resolution) => (
            <ResolutionCard key={resolution.id} resolution={resolution} />
          ))}
        </div>

        {filteredResolutions.length === 0 && (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              No resolutions found.
            </CardContent>
          </Card>
        )}
      </div>
    </AppShell>
  );
}

function ResolutionCard({ resolution }: { resolution: ResolutionListItem }) {
  const statusInfo = statusConfig[resolution.status] || statusConfig.pending;
  const StatusIcon = statusInfo.icon;
  const sigProgress = `${resolution.signature_count}/${resolution.total_signers}`;

  return (
    <Card className="hover:bg-muted/20 transition-colors">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-500/20 text-blue-400">
                Resolution
              </span>
              <span className={cn("px-2 py-0.5 rounded text-xs font-medium", statusInfo.color)}>
                {statusInfo.label}
              </span>
              {resolution.resolution_number && (
                <span className="text-xs text-muted-foreground font-mono">
                  {resolution.resolution_number}
                </span>
              )}
            </div>
            <Link
              href={`/resolutions/${resolution.id}`}
              className="font-medium hover:text-primary transition-colors"
            >
              {resolution.title}
            </Link>
            {resolution.description && (
              <p className="text-sm text-muted-foreground mt-1 line-clamp-1">
                {resolution.description}
              </p>
            )}

            {/* Signature Progress */}
            <div className="flex items-center gap-2 mt-3">
              <PenLine className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                {sigProgress} signed
              </span>
              {resolution.signature_count > 0 && (
                <div className="flex-1 max-w-[120px] h-1.5 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-green-500 rounded-full transition-all"
                    style={{
                      width: `${resolution.total_signers > 0 ? (resolution.signature_count / resolution.total_signers) * 100 : 0}%`,
                    }}
                  />
                </div>
              )}
            </div>
          </div>

          <Button variant="ghost" size="sm" asChild>
            <Link href={`/resolutions/${resolution.id}`}>
              <ChevronRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
