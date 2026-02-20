"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

export default function CredentialsLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const result = await signIn("credentials", {
        email,
        password,
        redirect: false,
      });

      if (result?.error) {
        setError("Invalid email or password");
      } else {
        router.push("/");
      }
    } catch {
      setError("Sign in failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[var(--ink)]">
      <div className="flex-1 flex items-center justify-center px-4">
        <div className="w-full max-w-sm">
          <div className="text-center mb-8">
            <div className="font-mono text-[10px] tracking-[0.3em] uppercase text-[var(--gold)] mb-4">
              Dev Access
            </div>
            <h1 className="font-serif text-3xl font-light text-[var(--paper)]">
              Credentials Login
            </h1>
          </div>

          <form onSubmit={handleSubmit} className="bg-[var(--ink-light)] border border-[var(--rule)] rounded-md p-8 space-y-4">
            {error && (
              <div className="bg-[var(--accent-red)]/10 border border-[var(--accent-red)]/20 rounded p-3 text-sm text-[var(--accent-red)]">
                {error}
              </div>
            )}

            <div>
              <label className="text-sm font-medium text-[var(--mist)]">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="amir.haque@themany.com"
                required
                className="w-full mt-1 h-10 px-3 rounded-md border border-[var(--rule)] bg-[var(--ink)] text-[var(--paper)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--gold)]"
              />
            </div>

            <div>
              <label className="text-sm font-medium text-[var(--mist)]">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full mt-1 h-10 px-3 rounded-md border border-[var(--rule)] bg-[var(--ink)] text-[var(--paper)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--gold)]"
              />
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full h-10 bg-[var(--gold)] hover:bg-[var(--gold-light)] text-[var(--ink)] font-medium text-sm"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Sign In"
              )}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
