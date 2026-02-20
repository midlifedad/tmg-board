"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { Card, CardContent } from "@/components/ui/card";
import {
  BarChart3,
  FileText,
  Download,
  Loader2,
  Calendar,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { documentsApi, api, type Document as ApiDocument } from "@/lib/api";

export default function ReportsPage() {
  const { data: session } = useSession();
  const [documents, setDocuments] = useState<ApiDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReports = async () => {
      try {
        setLoading(true);
        const email = session?.user?.email;
        if (email) {
          api.setUserEmail(email);
        }

        const data = await documentsApi.list({ archived: false });
        // Filter to report-type documents shareholders can see
        const reportDocs = Array.isArray(data)
          ? data
          : (data as { items?: ApiDocument[] }).items || [];
        setDocuments(reportDocs);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load reports");
      } finally {
        setLoading(false);
      }
    };

    if (session?.user?.email) {
      fetchReports();
    }
  }, [session?.user?.email]);

  if (loading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <div className="font-mono text-[10px] tracking-[0.2em] uppercase text-[var(--gold)] mb-2 flex items-center gap-3"><span>Shareholder Resources</span><div className="flex-1 h-px bg-border" /></div>
          <h1 className="text-3xl font-light">Reports & Documents</h1>
          <p className="text-sm font-light text-muted-foreground mt-1">
            Published reports, financial documents, and shareholder resources
          </p>
        </div>

        {/* Error */}
        {error && (
          <div className="p-4 rounded-md bg-destructive/10 text-destructive">
            {error}
          </div>
        )}

        {/* Reports List */}
        {documents.length === 0 ? (
          <Card>
            <CardContent className="py-12">
              <div className="text-center text-muted-foreground">
                <BarChart3 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p className="text-lg font-medium">No reports available</p>
                <p className="text-sm mt-1">
                  Reports and documents will appear here when published.
                </p>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {documents.map((doc) => (
              <Card key={doc.id} className="hover:bg-muted/20 transition-colors">
                <CardContent className="py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                        <FileText className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <Link
                          href={`/documents/${doc.id}`}
                          className="font-medium hover:text-primary transition-colors"
                        >
                          {doc.title}
                        </Link>
                        <div className="flex items-center gap-3 mt-1">
                          {doc.type && (
                            <span className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground capitalize">
                              {doc.type}
                            </span>
                          )}
                          <span className="text-xs text-muted-foreground flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {new Date(doc.created_at).toLocaleDateString("en-US", {
                              month: "short",
                              day: "numeric",
                              year: "numeric",
                            })}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button variant="ghost" size="sm" asChild>
                        <Link href={`/documents/${doc.id}`}>View</Link>
                      </Button>
                      {doc.file_path && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            window.open(`/api/proxy/documents/${doc.id}/download`, "_blank");
                          }}
                        >
                          <Download className="h-4 w-4 mr-2" />
                          Download
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
