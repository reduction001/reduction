// Reduction Facts Pages router template. Build substitutes the asset list below.
const FACT_PATHS = new Set(__FACT_PATHS__);
const FACT_HOST = "facts.reduction.nyc";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.hostname !== FACT_HOST) {
      // Preserve the project's existing /rtx/ canonical redirect.
      if (url.pathname === "/rtx/") {
        url.pathname = "/rtx";
        return Response.redirect(url.toString(), 301);
      }
      return env.ASSETS.fetch(request);
    }
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method not allowed", { status: 405, headers: { Allow: "GET, HEAD" } });
    }
    // Canonicalize explicit index / accidental deployment-directory URLs.
    if (url.pathname === "/index.html" || url.pathname === "/facts" || url.pathname === "/facts/" || url.pathname === "/facts/index.html") {
      url.pathname = "/";
      return Response.redirect(url.toString(), 302);
    }
    if (url.pathname.startsWith("/facts/")) {
      url.pathname = url.pathname.slice(6);
      return Response.redirect(url.toString(), 302);
    }
    // Prevent Pages' SPA fallback from returning the main homepage for a missing Facts file.
    if (!FACT_PATHS.has(url.pathname)) {
      return new Response("Facts page not found", { status: 404, headers: { "Content-Type": "text/plain; charset=utf-8", "X-Content-Type-Options": "nosniff" } });
    }
    const assetURL = new URL(url);
    assetURL.pathname = "/facts" + url.pathname;
    const response = await env.ASSETS.fetch(new Request(assetURL, request));
    const headers = new Headers(response.headers);
    // Keep the internal /facts directory out of any asset canonicalization redirect.
    const location = headers.get("Location");
    if (location && response.status >= 300 && response.status < 400) {
      const target = new URL(location, assetURL);
      if (target.origin === assetURL.origin && (target.pathname === "/facts" || target.pathname.startsWith("/facts/"))) {
        target.pathname = target.pathname.slice(6) || "/";
        headers.set("Location", target.toString());
      }
    }
    headers.set("X-Content-Type-Options", "nosniff");
    headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
    headers.set("X-Frame-Options", "DENY");
    headers.set("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
    if (url.pathname.endsWith(".json")) headers.set("Cache-Control", "public, max-age=0, must-revalidate");
    return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
  }
};
