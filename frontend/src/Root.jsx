import { lazy } from 'react';
// Production entrypoint is always the real backend-backed portal.
// The fictional design demo is not part of the public application bundle.
const Root = lazy(() => import('./App.jsx'));
export default Root;
