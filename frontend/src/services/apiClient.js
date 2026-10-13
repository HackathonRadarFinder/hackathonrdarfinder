/** Backend contracts only. Tokens stay in memory; no browser credentials are seeded. */
export function validateApiBase(value = '/api') {
  if (typeof value !== 'string' || value.includes('\\') || [...value].some(char => char.charCodeAt(0) <= 32 || char.charCodeAt(0) === 127)) throw new Error('Invalid API base.');
  const base = value.replace(/\/$/, '');
  if (/^\/(?!\/)[^?#]*$/.test(base)) return base;
  const url = new URL(base);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new Error('API base must be a relative path or HTTP(S) URL without credentials.');
  }
  return base;
}

export function safeEventUrl(value) {
  try {
    if (typeof value !== 'string' || [...value].some(char => char.charCodeAt(0) <= 32 || char.charCodeAt(0) === 127)) return null;
    const url = new URL(value);
    return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password ? url.href : null;
  } catch { return null; }
}

export function createApiClient(base, fetchImpl = (...args) => fetch(...args)) {
  base = validateApiBase(base);
  let token = null;
  let user = null;
  let version = 0;
  let expiryTimer;
  const listeners = new Set();
  const notify = () => listeners.forEach(listener => listener(user));
  function clearSession() {
    version++;
    token = null;
    user = null;
    clearTimeout(expiryTimer);
    notify();
  }
  async function request(path, { method = 'GET', body, signal, authenticated = true } = {}) {
    const requestToken = authenticated ? token : null;
    const headers = { Accept: 'application/json' };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (requestToken) headers.Authorization = `Bearer ${requestToken}`;
    let response;
    try {
      response = await fetchImpl(`${base}${path}`, {
        method, headers, signal, ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
      });
    } catch (error) {
      if (error.name === 'AbortError') throw error;
      throw new Error('Cannot reach the API. Please try again.');
    }
    let data;
    try { data = await response.json(); } catch { throw new Error('The API returned an unreadable response.'); }
    if (!response.ok) {
      if (response.status === 401 && requestToken && requestToken === token) clearSession();
      const message = data.message || (typeof data.detail === 'string' ? data.detail : 'Request failed.');
      const error = new Error(message);
      error.status = response.status;
      error.code = data.code;
      error.requestId = data.request_id;
      throw error;
    }
    return data;
  }
  async function login(email, password) {
    clearSession();
    const loginVersion = version;
    const result = await request('/auth/login', { method: 'POST', body: { email: email.trim(), password }, authenticated: false });
    if (loginVersion !== version) throw new Error('Sign-in was cancelled.');
    if (typeof result.access_token !== 'string' || result.token_type !== 'bearer') throw new Error('Invalid sign-in response.');
    token = result.access_token;
    try {
      const profile = await request('/auth/me');
      if (loginVersion !== version) throw new Error('Sign-in was cancelled.');
      user = profile;
      // JWT expiry only schedules local cleanup; roles and access always come from the backend.
      const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
      const remaining = payload.exp * 1000 - Date.now();
      if (!Number.isFinite(remaining) || remaining <= 0) throw new Error('Session expired. Please sign in again.');
      expiryTimer = setTimeout(clearSession, Math.min(remaining, 2_147_483_647));
      expiryTimer.unref?.();
      notify();
      return { user };
    } catch (error) {
      if (loginVersion === version) clearSession();
      throw error;
    }
  }
  async function logout() {
    try {
      if (token) await request('/auth/logout', { method: 'POST' });
    } finally { clearSession(); }
  }
  return {
    request, login, logout, clearSession,
    subscribe(listener) { listeners.add(listener); listener(user); return () => listeners.delete(listener); },
    async register({ name, email, password }) {
      await request('/auth/register', { method: 'POST', authenticated: false, body: { name: name.trim(), email: email.trim(), password } });
      return login(email, password);
    },
    async forgotPassword() { throw new Error('Password reset is not supported by this backend yet. No email was sent.'); },
    async events({ page = 1, pageSize = 12, q, location, mode, organizationId, startFrom, startTo } = {}, signal) {
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
      if (q?.trim()) params.set('q', q.trim());
      if (location?.trim()) params.set('location', location.trim());
      if (mode?.trim()) params.set('mode', mode.trim());
      if (organizationId) params.set('organization_id', String(organizationId));
      if (startFrom) params.set('start_from', startFrom);
      if (startTo) params.set('start_to', startTo);
      const result = await request(`/events/?${params}`, { signal, authenticated: false });
      if (!Array.isArray(result.data) || !Number.isInteger(result.total) || !Number.isInteger(result.page)) {
        throw new Error('Invalid event page response.');
      }
      return result;
    },
    async event(id, signal) {
      if (!/^\d+$/.test(String(id)) || Number(id) < 1 || Number(id) > 2_147_483_647) throw new Error('Invalid event ID.');
      const result = await request(`/events/${id}`, { signal, authenticated: false });
      return result.data;
    },
    async organizations(signal) { return (await request('/organizations/', { signal, authenticated: false })).data; },
    async eventDiscovery(id, signal) {
      if (!/^\d+$/.test(String(id)) || Number(id) < 1 || Number(id) > 2_147_483_647) throw new Error('Invalid event ID.');
      return (await request(`/events/${id}/discovery`, { signal, authenticated: false })).data;
    },
    async saved(signal) { return (await request('/account/saved', { signal })).data; },
    async save(id, saved) { return request(`/account/saved/${id}`, { method: saved ? 'DELETE' : 'PUT' }); },
    preferences(signal) { return request('/account/preferences', { signal }); },
    async notifications(signal) { return (await request('/notifications/', { signal })).data; },
    readNotification(id) { return request(`/notifications/${encodeURIComponent(id)}/read`, { method: 'PUT' }); },
    updatePreferences(body) { return request('/account/preferences', { method: 'PUT', body }); },
    async predictions(signal) { return (await request('/predictions/catalog', { signal, authenticated: false })).data; },
    async predictionReadiness(signal) { return (await request('/predictions/readiness', { signal, authenticated: false })).data; },
    async admin(signal) {
      const [stats, users, organizations] = await Promise.all([
        request('/admin/stats', { signal }), request('/admin/users', { signal }), request('/admin/organizations', { signal }),
      ]);
      return { stats, users: users.data, organizations: organizations.data };
    },
  };
}

export const api = createApiClient(import.meta.env?.VITE_API_BASE_URL || '/api');
