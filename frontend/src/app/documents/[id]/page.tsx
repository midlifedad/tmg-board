"use client";

import { use, useState, useEffect } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ArrowLeft,
  Download,
  PenLine,
  FileText,
  CheckCircle,
  Clock,
  User,
  Calendar,
  Tag,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { documentsApi, api, type Document as ApiDocument } from "@/lib/api";

interface DocumentDetail {
  id: string;
  title: string;
  type: string;
  description: string;
  fileUrl: string;
  uploadedBy: string;
  uploadedAt: string;
  signers: Array<{ name: string; email: string; signedAt: string | null }>;
  relatedDocuments: Array<{ id: string; title: string; type: string }>;
}

const typeColors: Record<string, string> = {
  resolution: "bg-blue-500/20 text-blue-400",
  minutes: "bg-green-500/20 text-green-400",
  financial: "bg-amber-500/20 text-amber-400",
  consent: "bg-purple-500/20 text-purple-400",
  legal: "bg-red-500/20 text-red-400",
};

export default function DocumentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: session } = useSession();
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDocument = async () => {
      try {
        setLoading(true);
        const email = session?.user?.email;
        if (email) {
          api.setUserEmail(email);
        }
        const docData = await documentsApi.get(id);

        // Fetch signing status if available
        let signers: Array<{ name: string; email: string; signedAt: string | null }> = [];
        if (docData.docusign_envelope_id) {
          try {
            const statusData = await documentsApi.getSigningStatus(id);
            signers = statusData.signers.map((s) => ({
              name: s.name,
              email: s.email,
              signedAt: s.signed_at || null,
            }));
          } catch {
            // Signing status not available
          }
        }

        setDocument({
          id: String(docData.id),
          title: docData.title,
          type: docData.type,
          description: "", // TODO: Get from API if available
          fileUrl: docData.file_path,
          uploadedBy: `User ${docData.uploaded_by_id}`, // TODO: Fetch user name
          uploadedAt: docData.created_at,
          signers: signers,
          relatedDocuments: [], // TODO: Fetch related documents
        });
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load document");
      } finally {
        setLoading(false);
      }
    };

    fetchDocument();
  }, [id, session?.user?.email]);

  const userEmail = session?.user?.email;
  const currentUserSigner = document?.signers.find(
    (s) => s.email === userEmail
  );
  const hasUserSigned = currentUserSigner?.signedAt != null;
  const pendingSigners = document?.signers.filter((s) => !s.signedAt) || [];
  const completedSigners = document?.signers.filter((s) => s.signedAt) || [];

  if (loading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppShell>
    );
  }

  if (error || !document) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <p className="text-destructive">{error || "Document not found"}</p>
          <Button asChild>
            <Link href="/documents">Back to Documents</Link>
          </Button>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Back Link */}
        <Link
          href="/documents"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Documents
        </Link>

        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{document.title}</h1>
              <span
                className={cn(
                  "inline-flex px-2 py-1 rounded text-xs font-medium capitalize",
                  typeColors[document.type] || "bg-muted text-muted-foreground"
                )}
              >
                {document.type}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <User className="h-4 w-4" />
                Uploaded by {document.uploadedBy}
              </div>
              <div className="flex items-center gap-1.5">
                <Calendar className="h-4 w-4" />
                {new Date(document.uploadedAt).toLocaleDateString("en-US", {
                  month: "long",
                  day: "numeric",
                  year: "numeric",
                })}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="outline">
              <Download className="h-4 w-4 mr-2" />
              Download PDF
            </Button>
            {currentUserSigner && !hasUserSigned && (
              <Button>
                <PenLine className="h-4 w-4 mr-2" />
                Sign Document
              </Button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* PDF Viewer */}
          <div className="lg:col-span-2">
            <Card>
              <CardContent className="p-0">
                <div className="aspect-[8.5/11] bg-muted/50 rounded-lg flex items-center justify-center">
                  <div className="text-center text-muted-foreground">
                    <FileText className="h-16 w-16 mx-auto mb-4 opacity-50" />
                    <p className="text-lg font-medium">PDF Viewer</p>
                    <p className="text-sm">
                      Document preview will be displayed here
                    </p>
                    <p className="text-xs mt-2">
                      (react-pdf integration pending)
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Description */}
            {document.description && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Description</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    {document.description}
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Signature Status */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Signature Status</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Completed */}
                {completedSigners.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Signed ({completedSigners.length})
                    </p>
                    {completedSigners.map((signer) => (
                      <div
                        key={signer.email}
                        className="flex items-center justify-between py-2"
                      >
                        <div className="flex items-center gap-2">
                          <CheckCircle className="h-4 w-4 text-green-500" />
                          <span className="text-sm">{signer.name}</span>
                        </div>
                        <span className="text-xs text-muted-foreground">
                          {new Date(signer.signedAt!).toLocaleDateString()}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Pending */}
                {pendingSigners.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Pending ({pendingSigners.length})
                    </p>
                    {pendingSigners.map((signer) => (
                      <div
                        key={signer.email}
                        className="flex items-center justify-between py-2"
                      >
                        <div className="flex items-center gap-2">
                          <Clock className="h-4 w-4 text-amber-500" />
                          <span className="text-sm">{signer.name}</span>
                        </div>
                        {signer.email === userEmail && (
                          <Button size="sm" variant="outline">
                            Sign Now
                          </Button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Related Documents */}
            {document.relatedDocuments.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Related Documents</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {document.relatedDocuments.map((doc) => (
                    <Link
                      key={doc.id}
                      href={`/documents/${doc.id}`}
                      className="flex items-center gap-2 py-2 text-sm hover:text-primary transition-colors"
                    >
                      <FileText className="h-4 w-4 text-muted-foreground" />
                      {doc.title}
                    </Link>
                  ))}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
