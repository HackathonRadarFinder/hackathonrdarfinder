const BACKEND = 'https://hackathonrdarfinder.onrender.com';
const REDIRECTS = new Set([301, 302, 303, 307, 308]);

function unavailable(status) {
  return Response.json({ detail: 'Backend temporarily unavailable. Please try again.' }, {
    status,
    headers: { 'Cache-Control': 'no-store' },
  });
}

export default {
  async fetch(request, env) {
    const incoming = new URL(request.url);
    if (!incoming.pathname.startsWith('/api/')) {
      return env.ASSETS.fetch(request);
    }
    const upstream = new URL(BACKEND);
    upstream.pathname = incoming.pathname.slice('/api'.length);
    upstream.search = incoming.search;
    const headers = new Headers(request.headers);
    headers.delete('host');
    headers.delete('cookie');
    headers.delete('cf-connecting-ip');
    headers.delete('forwarded');
    headers.delete('x-forwarded-for');
    headers.delete('x-forwarded-host');
    headers.delete('x-forwarded-proto');
    headers.delete('x-real-ip');
    // Render's free service may need about a minute to start from idle.
    const timeout = AbortSignal.timeout(90_000);
    try {
      const forwarded = new Request(upstream, {
        method: request.method,
        headers,
        body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
        redirect: 'manual',
        signal: timeout,
      });
      const response = await fetch(forwarded);
      const responseHeaders = new Headers(response.headers);
      responseHeaders.delete('set-cookie');
      responseHeaders.set('Cache-Control', 'no-store');
      if (REDIRECTS.has(response.status)) {
        const location = responseHeaders.get('location');
        await response.body?.cancel();
        const target = location && new URL(location, upstream);
        if (!target || target.origin !== BACKEND || target.username || target.password) {
          return unavailable(502);
        }
        responseHeaders.set('Location', `/api${target.pathname}${target.search}${target.hash}`);
        responseHeaders.delete('content-length');
        responseHeaders.delete('content-encoding');
        return new Response(null, { status: response.status, headers: responseHeaders });
      }
      if (response.status >= 500 && responseHeaders.get('content-type')?.includes('text/html')) {
        await response.body?.cancel();
        return unavailable(response.status);
      }
      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: responseHeaders,
      });
    } catch {
      return unavailable(timeout.aborted ? 504 : 502);
    }
  },
};
