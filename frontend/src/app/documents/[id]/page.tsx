"use client";

import { use, useState, useEffect, useRef, useCallback } from "react";
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
  History,
  Archive,
  ArchiveRestore,
  Edit,
  Upload,
  MoreVertical,
  ChevronRight,
  Maximize2,
  Minimize2,
  Globe,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { documentsApi, api, type Document as ApiDocument, type DocumentVersion } from "@/lib/api";
import { usePermissions } from "@/hooks/use-permissions";
import { EditDocumentModal } from "@/components/edit-document-modal";
import { UploadVersionModal } from "@/components/upload-version-modal";
import { PdfViewer } from "@/components/pdf-viewer";

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
  archivedAt: string | null;
  category: string | null;
  tags: string[];
}

const typeColors: Record<string, string> = {
  resolution: "bg-blue-500/20 text-blue-400",
  minutes: "bg-green-500/20 text-green-400",
  financial: "bg-amber-500/20 text-amber-400",
  consent: "bg-purple-500/20 text-purple-400",
  legal: "bg-red-500/20 text-red-400",
  whitepaper: "bg-indigo-500/20 text-indigo-400",
  strategy: "bg-cyan-500/20 text-cyan-400",
  audit: "bg-orange-500/20 text-orange-400",
};

export default function DocumentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: session } = useSession();
  const { can } = usePermissions();
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [versions, setVersions] = useState<DocumentVersion[]>([]);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [showVersionHistory, setShowVersionHistory] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [isHtmlDocument, setIsHtmlDocument] = useState(false);
  const [htmlBlobUrl, setHtmlBlobUrl] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const fullscreenRef = useRef<HTMLDivElement>(null);

  const enterFullscreen = useCallback(async () => {
    if (fullscreenRef.current) {
      try {
        await fullscreenRef.current.requestFullscreen();
        setIsFullscreen(true);
      } catch {
        // Fallback to CSS fullscreen if API not available
        setIsFullscreen(true);
      }
    }
  }, []);

  const exitFullscreen = useCallback(async () => {
    if (window.document.fullscreenElement) {
      await window.document.exitFullscreen();
    }
    setIsFullscreen(false);
  }, []);

  // Listen for fullscreen changes (e.g. user presses Escape)
  useEffect(() => {
    const handleFullscreenChange = () => {
      if (!window.document.fullscreenElement) {
        setIsFullscreen(false);
      }
    };
    window.document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => window.document.removeEventListener("fullscreenchange", handleFullscreenChange);
  }, []);

  useEffect(() => {
    const fetchDocument = async () => {
      try {
        setLoading(true);
        const email = session?.user?.email;
        if (email) {
          api.setUserEmail(email);
        }
        const docData = await documentsApi.get(id);

        // Check if this is an HTML document
        setIsHtmlDocument(documentsApi.isHtmlDocument(docData));

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
          description: (docData as any).description || "",
          fileUrl: docData.file_path,
          uploadedBy: `User ${docData.uploaded_by_id}`, // TODO: Fetch user name
          uploadedAt: docData.created_at,
          signers: signers,
          relatedDocuments: [], // TODO: Fetch related documents
          archivedAt: (docData as any).archived_at || null,
          category: (docData as any).category || null,
          tags: (docData as any).tags || [],
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

  // Fetch HTML content for inline rendering
  useEffect(() => {
    if (!isHtmlDocument) return;

    let blobUrl: string | null = null;
    const fetchHtml = async () => {
      try {
        blobUrl = await documentsApi.fetchHtmlContent(id);
        setHtmlBlobUrl(blobUrl);
      } catch (err) {
        console.error("Failed to load HTML document:", err);
      }
    };
    fetchHtml();

    return () => {
      if (blobUrl) URL.revokeObjectURL(blobUrl);
    };
  }, [id, isHtmlDocument]);

  // Fetch version history when expanded
  useEffect(() => {
    const fetchVersions = async () => {
      if (!showVersionHistory || versions.length > 0) return;
      try {
        setVersionsLoading(true);
        const versionData = await documentsApi.getVersions(id);
        setVersions(versionData);
      } catch (err) {
        console.error("Failed to fetch versions:", err);
      } finally {
        setVersionsLoading(false);
      }
    };
    fetchVersions();
  }, [id, showVersionHistory, versions.length]);

  const handleArchive = async () => {
    if (!document) return;
    try {
      setArchiving(true);
      await documentsApi.archive(id);
      // Update local state
      setDocument((prev) => prev ? { ...prev, archivedAt: new Date().toISOString() } : null);
    } catch (err) {
      console.error("Failed to archive document:", err);
    } finally {
      setArchiving(false);
    }
  };

  const handleUnarchive = async () => {
    if (!document) return;
    try {
      setArchiving(true);
      await documentsApi.unarchive(id);
      // Update local state
      setDocument((prev) => prev ? { ...prev, archivedAt: null } : null);
    } catch (err) {
      console.error("Failed to unarchive document:", err);
    } finally {
      setArchiving(false);
    }
  };

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
              <h1 className="text-2xl font-light">{document.title}</h1>
              <span
                className={cn(
                  "inline-flex px-2 py-1 rounded text-xs font-medium capitalize",
                  typeColors[document.type] || "bg-muted text-muted-foreground"
                )}
              >
                {document.type}
              </span>
              {document.archivedAt && (
                <span className="inline-flex px-2 py-1 rounded text-xs font-medium bg-red-500/20 text-red-400">
                  Archived
                </span>
              )}
              {document.category && (
                <span className="inline-flex px-2 py-1 rounded text-xs font-medium bg-muted text-muted-foreground">
                  {document.category}
                </span>
              )}
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
            {can("documents.edit") && !document.archivedAt && (
              <Button variant="outline" onClick={() => setShowEditModal(true)}>
                <Edit className="h-4 w-4 mr-2" />
                Edit
              </Button>
            )}
            {can("documents.upload") && !document.archivedAt && (
              <Button variant="outline" onClick={() => setShowUploadModal(true)}>
                <Upload className="h-4 w-4 mr-2" />
                New Version
              </Button>
            )}
            <Button
              variant="outline"
              onClick={() => {
                // Download via proxy - open in new tab for browser to handle
                const downloadUrl = `/api/proxy/documents/${id}/download`;
                window.open(downloadUrl, "_blank");
              }}
            >
              <Download className="h-4 w-4 mr-2" />
              Download {isHtmlDocument ? "HTML" : "PDF"}
            </Button>
            {can("documents.archive") && (
              document.archivedAt ? (
                <Button
                  variant="outline"
                  onClick={handleUnarchive}
                  disabled={archiving}
                >
                  <ArchiveRestore className="h-4 w-4 mr-2" />
                  {archiving ? "Restoring..." : "Restore"}
                </Button>
              ) : (
                <Button
                  variant="outline"
                  onClick={handleArchive}
                  disabled={archiving}
                >
                  <Archive className="h-4 w-4 mr-2" />
                  {archiving ? "Archiving..." : "Archive"}
                </Button>
              )
            )}
            {currentUserSigner && !hasUserSigned && (
              <Button>
                <PenLine className="h-4 w-4 mr-2" />
                Sign Document
              </Button>
            )}
          </div>
        </div>

        {/* Fullscreen HTML Viewer Container */}
        {isHtmlDocument && (
          <div
            ref={fullscreenRef}
            className={cn(
              isFullscreen ? "fixed inset-0 z-50 bg-background flex flex-col" : "hidden"
            )}
          >
            <div className="flex items-center justify-between px-4 py-2 border-b bg-card shrink-0">
              <div className="flex items-center gap-2">
                <Globe className="h-4 w-4 text-indigo-400" />
                <span className="text-sm font-medium">{document.title}</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={exitFullscreen}
              >
                <Minimize2 className="h-4 w-4 mr-1" />
                Exit Fullscreen
              </Button>
            </div>
            <iframe
              src={htmlBlobUrl || "about:blank"}
              className="w-full flex-1 border-0"
              sandbox="allow-same-origin"
              title={document.title}
            />
          </div>
        )}

        <div className={cn(
          "grid gap-6",
          isHtmlDocument ? "grid-cols-1" : "grid-cols-1 lg:grid-cols-3"
        )}>
          {/* Document Viewer */}
          <div className={isHtmlDocument ? "" : "lg:col-span-2"}>
            {isHtmlDocument ? (
              /* HTML Viewer - sandboxed iframe */
              <Card>
                <div className="flex items-center justify-between px-4 py-2 border-b">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Globe className="h-4 w-4 text-indigo-400" />
                    HTML Document
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={enterFullscreen}
                  >
                    <Maximize2 className="h-4 w-4 mr-1" />
                    Fullscreen
                  </Button>
                </div>
                <CardContent className="p-0">
                  <iframe
                    src={htmlBlobUrl || "about:blank"}
                    className="w-full border-0 rounded-b-lg"
                    style={{ height: "80vh" }}
                    sandbox="allow-same-origin"
                    title={document.title}
                  />
                </CardContent>
              </Card>
            ) : (
              /* PDF Viewer */
              <PdfViewer
                url={`/api/proxy/documents/${id}/download`}
                title={document.title}
              />
            )}
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

            {/* Version History */}
            <Card>
              <CardHeader className="pb-2">
                <button
                  onClick={() => setShowVersionHistory(!showVersionHistory)}
                  className="flex items-center justify-between w-full text-left"
                >
                  <CardTitle className="text-base flex items-center gap-2">
                    <History className="h-4 w-4" />
                    Version History
                  </CardTitle>
                  <ChevronRight
                    className={cn(
                      "h-4 w-4 transition-transform",
                      showVersionHistory && "rotate-90"
                    )}
                  />
                </button>
              </CardHeader>
              {showVersionHistory && (
                <CardContent className="space-y-2">
                  {versionsLoading ? (
                    <div className="flex items-center justify-center py-4">
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                    </div>
                  ) : versions.length === 0 ? (
                    <p className="text-sm text-muted-foreground py-2">
                      No version history available
                    </p>
                  ) : (
                    versions.map((version) => (
                      <div
                        key={version.id}
                        className="flex items-start justify-between py-2 border-b border-border/50 last:border-0"
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium">
                              v{version.version_number}
                            </span>
                            {version.version_number === versions[0]?.version_number && (
                              <span className="text-xs bg-green-500/20 text-green-400 px-1.5 py-0.5 rounded">
                                Current
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-muted-foreground">
                            {version.uploaded_by_name || `User ${version.uploaded_by_id}`}
                          </p>
                          {version.upload_reason && (
                            <p className="text-xs text-muted-foreground italic">
                              "{version.upload_reason}"
                            </p>
                          )}
                        </div>
                        <div className="text-right">
                          <p className="text-xs text-muted-foreground">
                            {new Date(version.created_at).toLocaleDateString("en-US", {
                              month: "short",
                              day: "numeric",
                              year: "numeric",
                            })}
                          </p>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 px-2 text-xs mt-1"
                            onClick={() => {
                              window.open(`/api/proxy/documents/${id}/versions/${version.id}/download`, "_blank");
                            }}
                          >
                            <Download className="h-3 w-3 mr-1" />
                            Download
                          </Button>
                        </div>
                      </div>
                    ))
                  )}
                </CardContent>
              )}
            </Card>

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

      {/* Edit Document Modal */}
      <EditDocumentModal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        onSuccess={async () => {
          // Refresh document data
          const docData = await documentsApi.get(id);
          setDocument((prev) =>
            prev
              ? {
                  ...prev,
                  title: docData.title,
                  type: docData.type,
                  description: (docData as any).description || "",
                  category: (docData as any).category || null,
                  tags: (docData as any).tags || [],
                }
              : null
          );
        }}
        document={
          document
            ? {
                id: document.id,
                title: document.title,
                type: document.type,
                description: document.description,
                category: document.category,
                tags: document.tags,
              }
            : null
        }
      />

      {/* Upload Version Modal */}
      <UploadVersionModal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onSuccess={async () => {
          // Refresh versions
          const versionData = await documentsApi.getVersions(id);
          setVersions(versionData);
          setShowVersionHistory(true);
        }}
        documentId={id}
        documentTitle={document?.title || ""}
      />
    </AppShell>
  );
}
