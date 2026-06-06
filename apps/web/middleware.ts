import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Add paths that do NOT require authentication here
const publicPaths = ['/login', '/signup', '/api/v1/auth/login', '/api/v1/auth/signup'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // Exclude static files, images, and next.js internals
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/favicon.ico') ||
    pathname.includes('.')
  ) {
    return NextResponse.next();
  }

  const token = request.cookies.get('token')?.value;

  // If user is trying to access a public path
  if (publicPaths.includes(pathname)) {
    // Redirect authenticated users away from login/signup to dashboard
    if (token) {
      return NextResponse.redirect(new URL('/dashboard', request.url));
    }
    return NextResponse.next();
  }

  // If user is not authenticated and trying to access a protected path (including '/')
  if (!token) {
    // Redirect all unauthenticated traffic to login
    return NextResponse.redirect(new URL('/login', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
