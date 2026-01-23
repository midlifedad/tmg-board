/**
 * API Proxy Route
 *
 * Proxies requests to the backend to avoid CORS issues.
 * Forwards all headers including X-User-Email for authentication.
 */

import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:3010";

async function proxyRequest(req: NextRequest, path: string[]) {
  // Backend requires trailing slashes
  const targetPath = `/api/${path.join("/")}/`;
  const url = new URL(targetPath, BACKEND_URL);
  console.log("Proxy request to:", url.toString());

  // Copy query params
  req.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.set(key, value);
  });

  // Forward headers
  const headers: HeadersInit = {};
  req.headers.forEach((value, key) => {
    // Skip host header to avoid issues
    if (key.toLowerCase() !== "host") {
      headers[key] = value;
    }
  });

  // Handle body - for multipart/form-data, pass as buffer; otherwise as text
  let body: BodyInit | undefined;
  if (req.body && req.method !== "GET" && req.method !== "HEAD") {
    const contentType = req.headers.get("content-type") || "";
    if (contentType.includes("multipart/form-data")) {
      // For file uploads, pass the body as ArrayBuffer
      body = await req.arrayBuffer();
    } else {
      body = await req.text();
    }
  }

  try {
    const response = await fetch(url.toString(), {
      method: req.method,
      headers,
      body,
    });

    // Create response with same status and headers
    const responseHeaders = new Headers();
    response.headers.forEach((value, key) => {
      responseHeaders.set(key, value);
    });

    const responseBody = await response.text();

    return new NextResponse(responseBody, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error("Proxy error:", error);
    return NextResponse.json(
      { error: "Failed to proxy request" },
      { status: 502 }
    );
  }
}

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(req, path);
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(req, path);
}

export async function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(req, path);
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(req, path);
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(req, path);
}
