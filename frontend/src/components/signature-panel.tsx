"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PenLine, CheckCircle, Loader2 } from "lucide-react";
import type { ResolutionSignature } from "@/lib/api";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface SignaturePanelProps {
  resolutionId: string;
  signatures: ResolutionSignature[];
  signedCount: number;
  totalMembers: number;
  currentUserId: number;
  isClosed: boolean;
  onSign: () => void;
  signing: boolean;
}

// ---------------------------------------------------------------------------
// SignaturePanel
// ---------------------------------------------------------------------------

export function SignaturePanel({
  signatures,
  signedCount,
  totalMembers,
  currentUserId,
  isClosed,
  onSign,
  signing,
}: SignaturePanelProps) {
  const hasSigned = signatures.some(
    (s) => s.member_id === currentUserId && s.signed_at
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <PenLine className="h-4 w-4" />
          Signatures ({signedCount}/{totalMembers})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {signatures.map((sig) => (
          <div
            key={sig.member_id}
            className="flex items-center justify-between py-1.5"
          >
            <span className="text-sm">{sig.member_name}</span>
            {sig.signed_at ? (
              <span className="text-xs text-green-500 flex items-center gap-1">
                <CheckCircle className="h-3 w-3" />
                {new Date(sig.signed_at).toLocaleDateString()}
              </span>
            ) : (
              <span className="text-xs text-muted-foreground">Pending</span>
            )}
          </div>
        ))}

        {isClosed && !hasSigned && (
          <Button
            onClick={onSign}
            disabled={signing}
            className="w-full mt-2 bg-[var(--gold)]/20 text-[var(--gold)] hover:bg-[var(--gold)]/30 border border-[var(--gold)]/30"
          >
            {signing ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <PenLine className="h-4 w-4 mr-2" />
            )}
            Sign Resolution
          </Button>
        )}

        {hasSigned && (
          <div className="text-center text-sm text-green-500 flex items-center justify-center gap-1 mt-2">
            <CheckCircle className="h-4 w-4" />
            You have signed this resolution
          </div>
        )}
      </CardContent>
    </Card>
  );
}
