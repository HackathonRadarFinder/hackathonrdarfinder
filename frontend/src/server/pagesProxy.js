export const BACKEND_ORIGIN = 'https://hackathonrdarfinder.onrender.com';
const MAX_BYTES = 4 * 1024 * 1024;

function failure(status, code, message, requestId) {
  return Response.json({ code, message, request_id: requestId }, {
    status, headers: { 'Cache-Control': 'no-store', 'X-Request-ID': requestId, 'Retry-After': '30' },
  });
}

async function boundedBytes(body, signal) {
  if (!body) return new Uint8Array();
  const reader = body.getReader();
  const abort = () => { reader.cancel().catch(() => {}); };
  signal.addEventListener('abort', abort, { once: true });
  if (signal.aborted) abort();
  const chunks = [];
  let length = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (signal.aborted) throw new Error('Request aborted');
      if (done) break;
      length += value.byteLength;
      if (length > MAX_BYTES) {
        await reader.cancel();
        throw new RangeError('Payload limit exceeded');
      }
      chunks.push(value);
    }
  } finally {
    signal.removeEventListener('abort', abort);
    reader.releaseLock();
  }
  const bytes = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  return bytes;
}

export async function forwardApi(request, fetchImpl = fetch, timeoutMs = 25_000) {
  const requestId = crypto.randomUUID();
  const incoming = new URL(request.url);
  if (!/^\/api(?:\/|$)/.test(incoming.pathname)) {
    return failure(404, 'API_ROUTE_NOT_FOUND', 'API route not found.', requestId);
  }
  const target = new URL(BACKEND_ORIGIN);
  // Assign pathname, never resolve a user-supplied URL against the origin.
  target.pathname = incoming.pathname.slice(4) || '/';
  target.search = incoming.search;
  const headers = new Headers({ 'X-Request-ID': requestId });
  for (const name of ['accept', 'content-type', 'authorization']) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  const controller = new AbortController();
  const abort = () => controller.abort();
  request.signal.addEventListener('abort', abort, { once: true });
  if (request.signal.aborted) abort();
  const timer = setTimeout(abort, timeoutMs);
  try {
    let body;
    if (!['GET', 'HEAD'].includes(request.method)) {
      try { body = await boundedBytes(request.body, controller.signal); } catch (error) {
        if (error instanceof RangeError) return failure(413, 'API_PAYLOAD_TOO_LARGE', 'Request exceeds the API payload limit.', requestId);
        throw error;
      }
    }
    const upstream = await fetchImpl(target.href, {
      method: request.method, headers, ...(body?.length ? { body } : {}),
      redirect: 'manual', signal: controller.signal,
    });
    const responseHeaders = new Headers({ 'Cache-Control': 'no-store', 'X-Request-ID': requestId });
    for (const name of ['content-type', 'www-authenticate', 'retry-after', 'x-request-id']) {
      const value = upstream.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }
    if (upstream.status >= 300 && upstream.status < 400) {
      const location = upstream.headers.get('location');
      const redirect = location && new URL(location, target);
      if (!redirect || redirect.origin !== BACKEND_ORIGIN || redirect.username || redirect.password) {
        await upstream.body?.cancel();
        return failure(502, 'UPSTREAM_REDIRECT_REJECTED', 'The API returned an unsupported redirect.', requestId);
      }
      responseHeaders.set('Location', `/api${redirect.pathname}${redirect.search}${redirect.hash}`);
      await upstream.body?.cancel();
      return new Response(null, { status: upstream.status, headers: responseHeaders });
    }
    if (request.method === 'HEAD' || [204, 205].includes(upstream.status)) {
      await upstream.body?.cancel();
      return new Response(null, { status: upstream.status, headers: responseHeaders });
    }
    const type = upstream.headers.get('content-type')?.split(';')[0].trim().toLowerCase();
    if (type !== 'application/json' && !type?.endsWith('+json')) {
      await upstream.body?.cancel();
      return failure(upstream.status === 503 ? 503 : 502, 'UPSTREAM_UNAVAILABLE',
        'The API is starting or temporarily unavailable. Please retry shortly.', requestId);
    }
    const bytes = await boundedBytes(upstream.body, controller.signal);
    try { JSON.parse(new TextDecoder().decode(bytes)); } catch {
      return failure(502, 'UPSTREAM_INVALID_JSON', 'The API returned an invalid response. Please retry shortly.', requestId);
    }
    return new Response(bytes, { status: upstream.status, headers: responseHeaders });
  } catch {
    return failure(controller.signal.aborted ? 504 : 502, 'UPSTREAM_UNAVAILABLE',
      'The API is starting or temporarily unavailable. Please retry shortly.', requestId);
  } finally {
    clearTimeout(timer);
    request.signal.removeEventListener('abort', abort);
  }
}
