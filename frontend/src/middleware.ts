import { auth } from "@/lib/auth";
import { NextResponse } from "next/server";

// Development mode bypass - set via query param or env
const DEV_BYPASS = process.env.NODE_ENV === "development";

export default auth((req) => {
  const { pathname } = req.nextUrl;

  // Public routes that don't require authentication
  const publicRoutes = ["/login", "/api/auth"];
  const isPublicRoute = publicRoutes.some((route) =>
    pathname.startsWith(route)
  );

  // Static files and API routes
  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/favicon") ||
    pathname.includes(".")
  ) {
    return NextResponse.next();
  }

  // Backend API routes - let rewrites handle these
  // (exclude /api/auth which is a Next.js route)
  if (pathname.startsWith("/api/") && !pathname.startsWith("/api/auth")) {
    return NextResponse.next();
  }

  // Development mode: allow unauthenticated access for testing
  if (DEV_BYPASS && !req.auth && !isPublicRoute) {
    // Set a dev user email header for API requests
    const response = NextResponse.next();
    response.headers.set("X-Dev-User", "test@example.com");
    return response;
  }

  // If not authenticated and trying to access protected route
  if (!req.auth && !isPublicRoute) {
    const loginUrl = new URL("/login", req.url);
    return NextResponse.redirect(loginUrl);
  }

  // If authenticated and trying to access login page, redirect to home
  if (req.auth && pathname === "/login") {
    return NextResponse.redirect(new URL("/", req.url));
  }

  return NextResponse.next();
});

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
