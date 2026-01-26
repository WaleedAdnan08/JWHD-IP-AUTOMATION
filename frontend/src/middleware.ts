import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  // Check for the presence of the auth token cookie
  // Note: In a real-world scenario, you might want to validate the token content
  // or use a more robust session management library.
  // We assume the token is stored in a cookie named 'token' or 'auth_token'.
  // However, since our client-side code stores it in localStorage/sessionStorage (typical for JWT),
  // middleware access to localStorage is not possible.
  //
  // FOR THIS ARCHITECTURE:
  // Since we are using client-side JWT storage, the "middleware" protection here 
  // is primarily for redirection based on route structure, but the actual 
  // authentication check happens in the API calls or client-side Context.
  //
  // BUT, to implement "Protected Routes" at the edge, we ideally need the token in a cookie.
  //
  // IF the app is configured to use Cookies for auth:
  const token = request.cookies.get('token')?.value;

  // Define protected routes
  const protectedRoutes = ['/dashboard'];
  const isProtectedRoute = protectedRoutes.some(path => request.nextUrl.pathname.startsWith(path));
  
  // Define public routes (login, register, etc.)
  const publicRoutes = ['/login', '/register', '/'];
  const isPublicRoute = publicRoutes.some(path => request.nextUrl.pathname === path);

  // If trying to access a protected route without a token
  if (isProtectedRoute && !token) {
    // Redirect to login page
    return NextResponse.redirect(new URL('/login', request.url));
  }

  // If trying to access login page while already authenticated
  // REMOVED: This causes infinite loops if the token is invalid/stuck.
  // We handle "already logged in" redirection on the client side instead.
  // if (isPublicRoute && token && request.nextUrl.pathname === '/login') {
  //   return NextResponse.redirect(new URL('/dashboard', request.url));
  // }

  return NextResponse.next();
}

// Config to match all paths except static files
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
};