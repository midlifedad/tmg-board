"use client";

import { useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  ArrowLeft,
  Printer,
  CheckCircle,
  Clock,
  Stamp,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  resolutionsApi,
  authApi,
  api,
  type DecisionDetail,
  type SignatureStatus,
} from "@/lib/api";

/** Extended detail that includes resolution-specific fields from the backend */
interface ResolutionDetailResponse extends DecisionDetail {
  resolution_number?: string | null;
  document_id?: number | null;
}
import { isChairOrAbove, type Role } from "@/lib/permissions";
import { SignaturePanel } from "@/components/signature-panel";
import { ResolutionWriter } from "@/components/resolution-writer";

// ---------------------------------------------------------------------------
// Status config
// ---------------------------------------------------------------------------

const statusConfig: Record<string, { label: string; color: string; icon: React.ComponentType<{ className?: string }> }> = {
  pending: { label: "Pending", color: "bg-muted text-muted-foreground", icon: Clock },
  open: { label: "Open", color: "bg-blue-500/20 text-blue-400", icon: Stamp },
  closed: { label: "Closed", color: "bg-green-500/20 text-green-400", icon: CheckCircle },
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ResolutionDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const { data: session } = useSession();

  const [detail, setDetail] = useState<ResolutionDetailResponse | null>(null);
  const [sigStatus, setSigStatus] = useState<SignatureStatus | null>(null);
  const [currentUserId, setCurrentUserId] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [signing, setSigning] = useState(false);
  const [signSuccess, setSignSuccess] = useState(false);

  const userRole = (session?.user as { role?: Role })?.role;
  const userEmail = session?.user?.email || "";

  const fetchSignatures = useCallback(async () => {
    try {
      const sigs = await resolutionsApi.getSignatures(id);
      setSigStatus(sigs);
    } catch {
      // Signature fetch failure is non-fatal
    }
  }, [id]);

  useEffect(() => {
    const email = session?.user?.email;
    if (!email) return;

    const fetchData = async () => {
      try {
        setLoading(true);
        api.setUserEmail(email);

        const [resolutionData, sigsData] = await Promise.all([
          resolutionsApi.get(id) as Promise<ResolutionDetailResponse>,
          resolutionsApi.getSignatures(id),
        ]);

        setDetail(resolutionData);
        setSigStatus(sigsData);

        try {
          const me = await authApi.getCurrentUser();
          setCurrentUserId(Number(me.id));
        } catch {
          // User fetch failure is non-fatal
        }

        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load resolution");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [id, session?.user?.email, fetchSignatures]);

  const handleSign = async () => {
    try {
      setSigning(true);
      await resolutionsApi.sign(id);
      await fetchSignatures();
      setSignSuccess(true);
      setTimeout(() => setSignSuccess(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to sign resolution");
    } finally {
      setSigning(false);
    }
  };

  // -------------------------------------------------------------------------
  // Loading / Error states
  // -------------------------------------------------------------------------

  if (loading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppShell>
    );
  }

  if (error && !detail) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <p className="text-destructive">{error}</p>
          <Button onClick={() => window.location.reload()}>Retry</Button>
        </div>
      </AppShell>
    );
  }

  if (!detail) return null;

  const resolution = detail.decision;
  const resolutionNumber = detail.resolution_number ?? null;
  const statusInfo = statusConfig[resolution.status] || statusConfig.pending;

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <AppShell>
      {/* Print-only header */}
      <div className="hidden print:block print:mb-8">
        <h1 className="text-2xl font-bold text-black">{resolution.title}</h1>
        {resolutionNumber && (
          <p className="text-sm text-gray-600 mt-1">Resolution No. {resolutionNumber}</p>
        )}
        <p className="text-sm text-gray-600">
          Date: {new Date(resolution.created_at).toLocaleDateString()}
        </p>
        <hr className="my-4 border-gray-300" />
        {resolution.description && (
          <div
            className="prose prose-sm max-w-none text-black"
            dangerouslySetInnerHTML={{ __html: resolution.description }}
          />
        )}
        {sigStatus && sigStatus.signatures.filter((s) => s.signed_at).length > 0 && (
          <div className="mt-8">
            <h3 className="text-lg font-semibold text-black mb-2">Signatures</h3>
            <table className="w-full border-collapse border border-gray-300">
              <thead>
                <tr className="bg-gray-100">
                  <th className="border border-gray-300 px-3 py-2 text-left text-sm font-medium text-black">Name</th>
                  <th className="border border-gray-300 px-3 py-2 text-left text-sm font-medium text-black">Date</th>
                </tr>
              </thead>
              <tbody>
                {sigStatus.signatures
                  .filter((s) => s.signed_at)
                  .map((sig) => (
                    <tr key={sig.member_id}>
                      <td className="border border-gray-300 px-3 py-2 text-sm text-black">{sig.member_name}</td>
                      <td className="border border-gray-300 px-3 py-2 text-sm text-black">
                        {new Date(sig.signed_at!).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Screen-only UI */}
      <div className="print:hidden space-y-6">
        {/* Back link */}
        <Link
          href="/resolutions"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Resolutions
        </Link>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column */}
          <div className="lg:col-span-2 space-y-6">
            {/* Header */}
            <div>
              <div className="font-mono text-[10px] tracking-[0.2em] uppercase text-[var(--gold)] mb-2 flex items-center gap-3">
                <span>Resolution</span>
                <div className="flex-1 h-px bg-border" />
              </div>
              <h1 className="text-3xl font-light">{resolution.title}</h1>
              <div className="flex items-center gap-3 mt-3">
                <span className={cn("px-2 py-0.5 rounded text-xs font-medium", statusInfo.color)}>
                  {statusInfo.label}
                </span>
                {resolutionNumber && (
                  <span className="text-sm text-muted-foreground font-mono">
                    {resolutionNumber}
                  </span>
                )}
                <span className="text-sm text-muted-foreground">
                  Created {new Date(resolution.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>

            {/* Description */}
            {resolution.description && (
              <Card>
                <CardContent className="p-6">
                  <div
                    className="prose prose-invert prose-sm max-w-none prose-p:text-gray-300 prose-headings:text-white prose-strong:text-white prose-li:text-gray-300"
                    dangerouslySetInnerHTML={{ __html: resolution.description }}
                  />
                </CardContent>
              </Card>
            )}

            {/* Sign success feedback */}
            {signSuccess && (
              <div className="rounded-md border border-green-800/50 bg-green-900/20 px-4 py-3 text-sm text-green-400 flex items-center gap-2">
                <CheckCircle className="h-4 w-4" />
                Resolution signed successfully
              </div>
            )}

            {/* Error feedback */}
            {error && (
              <div className="rounded-md border border-red-800/50 bg-red-900/20 px-4 py-3 text-sm text-red-400">
                {error}
              </div>
            )}

            {/* Resolution Writer */}
            <ResolutionWriter
              resolutionId={id}
              resolutionTitle={resolution.title}
              userEmail={userEmail}
            />
          </div>

          {/* Right column */}
          <div className="space-y-6">
            {/* Signature Panel */}
            {sigStatus && (
              <SignaturePanel
                resolutionId={id}
                signatures={sigStatus.signatures}
                signedCount={sigStatus.signed_count}
                totalMembers={sigStatus.total_members}
                currentUserId={currentUserId}
                isClosed={resolution.status === "closed"}
                onSign={handleSign}
                signing={signing}
              />
            )}

            {/* Print button (chair/admin only) */}
            {isChairOrAbove(userRole) && (
              <Button
                variant="outline"
                className="w-full"
                onClick={() => window.print()}
              >
                <Printer className="h-4 w-4 mr-2" />
                Print Resolution
              </Button>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
