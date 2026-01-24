"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  FileText,
  Plus,
  Search,
  Filter,
  ChevronDown,
  Download,
  PenLine,
  CheckCircle,
  Clock,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { documentsApi, api, type Document as ApiDocument } from "@/lib/api";
import { UploadDocumentModal } from "@/components/upload-document-modal";

type SigningStatusType = "signed" | "pending" | "draft" | "declined";

interface Document {
  id: string;
  title: string;
  type: string;
  date: string;
  status: SigningStatusType;
  uploadedBy: string;
}

// Document types with colors - includes all known types from backend
const documentTypes: Record<string, { label: string; color: string }> = {
  resolution: { label: "Resolution", color: "bg-blue-500/20 text-blue-400" },
  minutes: { label: "Minutes", color: "bg-green-500/20 text-green-400" },
  financial: { label: "Financial", color: "bg-amber-500/20 text-amber-400" },
  consent: { label: "Consent", color: "bg-purple-500/20 text-purple-400" },
  legal: { label: "Legal", color: "bg-red-500/20 text-red-400" },
  audit: { label: "Audit", color: "bg-orange-500/20 text-orange-400" },
  strategy: { label: "Strategy", color: "bg-cyan-500/20 text-cyan-400" },
};

// Default style for unknown types
const defaultDocType = { label: "Document", color: "bg-gray-500/20 text-gray-400" };

// Signing status badges
const signingStatus: Record<SigningStatusType, { label: string; icon: typeof CheckCircle; color: string }> = {
  signed: { label: "Signed", icon: CheckCircle, color: "text-green-500" },
  pending: { label: "Pending", icon: Clock, color: "text-amber-500" },
  draft: { label: "Draft", icon: FileText, color: "text-muted-foreground" },
  declined: { label: "Declined", icon: AlertCircle, color: "text-red-500" },
};

export default function DocumentsPage() {
  const { data: session } = useSession();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);

  useEffect(() => {
    const fetchDocuments = async () => {
      try {
        setLoading(true);
        const email = session?.user?.email;
        if (email) {
          api.setUserEmail(email);
        }
        const data = await documentsApi.list();
        // Transform API response to match component interface
        const transformed: Document[] = data.map((doc) => {
          // Map signing_status to our status type
          let status: SigningStatusType = "draft";
          if (doc.signing_status === "completed") status = "signed";
          else if (doc.signing_status === "pending" || doc.signing_status === "sent") status = "pending";
          else if (doc.signing_status === "declined") status = "declined";

          return {
            id: String(doc.id),
            title: doc.title,
            type: doc.type,
            date: doc.created_at.split("T")[0],
            status: status,
            uploadedBy: `User ${doc.uploaded_by_id}`, // TODO: Fetch user name
          };
        });
        setDocuments(transformed);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load documents");
      } finally {
        setLoading(false);
      }
    };

    fetchDocuments();
  }, [session?.user?.email]);

  const userRole = (session?.user as { role?: string })?.role;
  // Show upload button for admin/chair roles, or when no session (dev/staging with hardcoded email)
  const isAdmin = userRole === "admin" || userRole === "chair" || !session;

  const refetchDocuments = async () => {
    try {
      const data = await documentsApi.list();
      const transformed: Document[] = data.map((doc) => {
        let status: SigningStatusType = "draft";
        if (doc.signing_status === "completed") status = "signed";
        else if (doc.signing_status === "pending" || doc.signing_status === "sent") status = "pending";
        else if (doc.signing_status === "declined") status = "declined";
        return {
          id: String(doc.id),
          title: doc.title,
          type: doc.type,
          date: doc.created_at.split("T")[0],
          status: status,
          uploadedBy: `User ${doc.uploaded_by_id}`,
        };
      });
      setDocuments(transformed);
    } catch (err) {
      console.error("Failed to refetch documents:", err);
    }
  };

  // Filter documents
  const filteredDocuments = documents.filter((doc) => {
    if (searchQuery && !doc.title.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    if (selectedType && doc.type !== selectedType) {
      return false;
    }
    if (selectedYear && !doc.date.startsWith(selectedYear.toString())) {
      return false;
    }
    return true;
  });

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
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Documents</h1>
            <p className="text-muted-foreground mt-1">
              Board resolutions, minutes, and official documents
            </p>
          </div>
          {isAdmin && (
            <Button onClick={() => setShowUploadModal(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Upload Document
            </Button>
          )}
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px] max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search documents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-10 pl-9 pr-4 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          {/* Type Filter */}
          <select
            value={selectedType || ""}
            onChange={(e) => setSelectedType(e.target.value || null)}
            className="h-10 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="">All Types</option>
            {Object.entries(documentTypes).map(([key, { label }]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>

          {/* Year Filter */}
          <select
            value={selectedYear || ""}
            onChange={(e) => setSelectedYear(e.target.value ? parseInt(e.target.value) : null)}
            className="h-10 px-3 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="">All Years</option>
            <option value="2026">2026</option>
            <option value="2025">2025</option>
            <option value="2024">2024</option>
          </select>
        </div>

        {/* Documents Table */}
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="text-left p-4 font-medium text-sm">Document</th>
                    <th className="text-left p-4 font-medium text-sm">Type</th>
                    <th className="text-left p-4 font-medium text-sm">Date</th>
                    <th className="text-left p-4 font-medium text-sm">Status</th>
                    <th className="text-right p-4 font-medium text-sm">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredDocuments.map((doc) => {
                    const typeInfo = documentTypes[doc.type] || defaultDocType;
                    const statusInfo = signingStatus[doc.status];
                    const StatusIcon = statusInfo.icon;

                    return (
                      <tr
                        key={doc.id}
                        className="border-b last:border-0 hover:bg-muted/20 transition-colors"
                      >
                        <td className="p-4">
                          <Link
                            href={`/documents/${doc.id}`}
                            className="flex items-center gap-3 hover:text-primary transition-colors"
                          >
                            <FileText className="h-5 w-5 text-muted-foreground" />
                            <div>
                              <p className="font-medium">{doc.title}</p>
                              <p className="text-xs text-muted-foreground">
                                Uploaded by {doc.uploadedBy}
                              </p>
                            </div>
                          </Link>
                        </td>
                        <td className="p-4">
                          <span
                            className={cn(
                              "inline-flex px-2 py-1 rounded text-xs font-medium",
                              typeInfo.color
                            )}
                          >
                            {typeInfo.label}
                          </span>
                        </td>
                        <td className="p-4 text-sm text-muted-foreground">
                          {new Date(doc.date).toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                            year: "numeric",
                          })}
                        </td>
                        <td className="p-4">
                          <div className={cn("flex items-center gap-1.5 text-sm", statusInfo.color)}>
                            <StatusIcon className="h-4 w-4" />
                            {statusInfo.label}
                          </div>
                        </td>
                        <td className="p-4">
                          <div className="flex items-center justify-end gap-2">
                            <Button variant="ghost" size="sm" asChild>
                              <Link href={`/documents/${doc.id}`}>View</Link>
                            </Button>
                            {doc.status === "pending" && (
                              <Button size="sm">
                                <PenLine className="h-3 w-3 mr-1" />
                                Sign
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              {filteredDocuments.length === 0 && (
                <div className="p-8 text-center text-muted-foreground">
                  No documents found matching your criteria.
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Pagination placeholder */}
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <p>Showing {filteredDocuments.length} of {documents.length} documents</p>
        </div>
      </div>

      {/* Upload Modal */}
      <UploadDocumentModal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onSuccess={refetchDocuments}
      />
    </AppShell>
  );
}
