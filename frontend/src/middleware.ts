import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const response = NextResponse.next();

  if (request.nextUrl.pathname.startsWith("/api/")) {
    const apiKey = process.env.API_KEY || "";
    if (apiKey) {
      response.headers.set("X-API-Key", apiKey);
    }
  }

  return response;
}

export const config = {
  matcher: ["/api/:path*"],
};
