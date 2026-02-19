import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3010";

interface BackendUser {
  id: string;
  email: string;
  name: string;
  role: "admin" | "chair" | "board" | "shareholder";
}

/**
 * Verify user exists in backend and get their role
 */
async function verifyAndGetUser(email: string): Promise<BackendUser | null> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/auth/verify`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      }
    );

    if (!response.ok) {
      throw new Error(`Backend error: ${response.status}`);
    }

    const data = await response.json();
    if (!data.exists) {
      console.log(`User not found in backend: ${email}`);
      return null;
    }

    return {
      id: String(data.id),
      email: data.email,
      name: data.name,
      role: data.role,
    };
  } catch (error) {
    console.error("Error verifying user with backend:", error);
    // In development, allow sign-in even if backend is down
    if (process.env.NODE_ENV === "development") {
      console.warn("Development mode: allowing sign-in without backend verification");
      return {
        id: "dev-user",
        email,
        name: email.split("@")[0],
        role: "admin",
      };
    }
    return null;
  }
}

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: {
        params: {
          prompt: "select_account",
        },
      },
    }),
  ],
  pages: {
    signIn: "/login",
    error: "/login",
  },
  callbacks: {
    async signIn({ user }) {
      if (!user.email) {
        console.log("Sign-in rejected: no email provided");
        return false;
      }

      // Verify user exists in backend whitelist
      const backendUser = await verifyAndGetUser(user.email);

      if (!backendUser) {
        console.log(`Sign-in rejected: ${user.email} not authorized`);
        return false;
      }

      console.log(`User signed in: ${user.email} (${backendUser.role})`);
      return true;
    },

    async jwt({ token, user, trigger }) {
      // On initial sign-in, fetch user data from backend
      if (user?.email) {
        const backendUser = await verifyAndGetUser(user.email);
        if (backendUser) {
          token.userId = backendUser.id;
          token.role = backendUser.role;
          token.email = backendUser.email;
        }
      }

      // On session update, refresh user data
      if (trigger === "update" && token.email) {
        const backendUser = await verifyAndGetUser(token.email as string);
        if (backendUser) {
          token.role = backendUser.role;
        }
      }

      return token;
    },

    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.userId as string;
        (session.user as { role?: string }).role = token.role as string;
      }
      return session;
    },
  },
});

// Extend the session type
declare module "next-auth" {
  interface Session {
    user: {
      id: string;
      name?: string | null;
      email?: string | null;
      image?: string | null;
      role?: string;
    };
  }
}
