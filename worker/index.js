const BACKEND = 'https://hackathonrdarfinder.onrender.com';

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
    headers.delete('x-forwarded-for');
    headers.delete('x-real-ip');
    const forwarded = new Request(upstream, {
      method: request.method,
      headers,
      body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
      redirect: 'manual',
    });
    try {
      const response = await fetch(forwarded);
      const responseHeaders = new Headers(response.headers);
      responseHeaders.delete('set-cookie');
      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: responseHeaders,
      });
    } catch {
      return Response.json({ detail: 'Backend temporarily unavailable.' }, { status: 502 });
    }
  },
};
