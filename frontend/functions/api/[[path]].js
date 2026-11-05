import { forwardApi } from '../../src/server/pagesProxy.js';

// Fixed upstream: client headers, query parameters and bindings cannot select it.
export function onRequest({ request }) {
  return forwardApi(request);
}
