"use client";

import { Suspense } from "react";
import { signIn } from "next-auth/react";
import { useSearchParams } from "next/navigation";
import { useBranding } from "@/contexts/branding-context";
import { Button } from "@/components/ui/button";

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginSkeleton />}>
      <LoginContent />
    </Suspense>
  );
}

function LoginContent() {
  const searchParams = useSearchParams();
  const error = searchParams.get("error");
  const { branding } = useBranding();

  const handleGoogleSignIn = () => {
    signIn("google", { callbackUrl: "/" });
  };

  return (
    <div className="min-h-screen flex flex-col bg-[var(--ink)]">
      {/* Top decorative rule */}
      <div className="h-[2px] bg-gradient-to-r from-transparent via-[var(--gold)] to-transparent opacity-40" />

      <div className="flex-1 flex items-center justify-center px-4">
        <div className="w-full max-w-sm">
          {/* Logo mark */}
          <div className="flex justify-center mb-10">
            <div className="w-14 h-14 rounded border border-[var(--gold)]/30 bg-[var(--gold)]/5 flex items-center justify-center">
              <span className="font-mono text-xl font-medium text-[var(--gold)]">{branding.app_name?.[0]?.toUpperCase() || "B"}</span>
            </div>
          </div>

          {/* Title block */}
          <div className="text-center mb-10">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-[var(--gold)] mb-4">
              {branding.app_name}
            </div>
            <h1 className="font-serif text-4xl font-light text-[var(--paper)] tracking-tight">
              {branding.organization_name || branding.app_name}
            </h1>
            <div className="mx-auto mt-4 w-16 h-px bg-[var(--gold)] opacity-40" />
          </div>

          {/* Sign in card */}
          <div className="bg-[var(--ink-light)] border border-[var(--rule)] rounded-md p-8">
            {error && (
              <div className="mb-6 bg-[var(--accent-red)]/10 border border-[var(--accent-red)]/20 rounded p-3 text-sm text-[var(--accent-red)]">
                {error === "AccessDenied"
                  ? "Access denied. Your email is not authorized for board access."
                  : "An error occurred during sign in. Please try again."}
              </div>
            )}

            <p className="text-sm text-[var(--mist)] text-center mb-6 font-light">
              Sign in with your authorized Google account to access the board portal.
            </p>

            <Button
              onClick={handleGoogleSignIn}
              className="w-full h-12 bg-[var(--paper)] hover:bg-[var(--paper-warm)] text-[var(--ink)] font-medium text-sm rounded transition-colors"
              size="lg"
            >
              <GoogleIcon className="mr-3 h-5 w-5" />
              Continue with Google
            </Button>
          </div>

          {/* Footer */}
          <div className="mt-8 text-center">
            <p className="font-mono text-[9px] tracking-[0.25em] uppercase text-[var(--steel-light)]">
              Authorized board members only
            </p>
          </div>
        </div>
      </div>

      {/* Bottom decorative rule */}
      <div className="h-[2px] bg-gradient-to-r from-transparent via-[var(--gold)] to-transparent opacity-20" />
    </div>
  );
}

function LoginSkeleton() {
  return (
    <div className="min-h-screen flex flex-col bg-[var(--ink)]">
      <div className="h-[2px] bg-gradient-to-r from-transparent via-[var(--gold)] to-transparent opacity-40" />
      <div className="flex-1 flex items-center justify-center px-4">
        <div className="w-full max-w-sm">
          <div className="flex justify-center mb-10">
            <div className="w-14 h-14 rounded border border-[var(--gold)]/30 bg-[var(--gold)]/5 flex items-center justify-center">
              <span className="font-mono text-xl font-medium text-[var(--gold)]">B</span>
            </div>
          </div>
          <div className="text-center mb-10">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-[var(--gold)] mb-4">
              Board Portal
            </div>
            <div className="h-10 w-48 mx-auto bg-[var(--steel)] rounded animate-pulse" />
            <div className="mx-auto mt-4 w-16 h-px bg-[var(--gold)] opacity-40" />
          </div>
          <div className="bg-[var(--ink-light)] border border-[var(--rule)] rounded-md p-8">
            <div className="h-4 w-3/4 mx-auto bg-[var(--steel)] rounded animate-pulse mb-6" />
            <div className="h-12 bg-[var(--steel)] rounded animate-pulse" />
          </div>
          <div className="mt-8 text-center">
            <p className="font-mono text-[9px] tracking-[0.25em] uppercase text-[var(--steel-light)]">
              Authorized board members only
            </p>
          </div>
        </div>
      </div>
      <div className="h-[2px] bg-gradient-to-r from-transparent via-[var(--gold)] to-transparent opacity-20" />
    </div>
  );
}

function GoogleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      />
    </svg>
  );
}
