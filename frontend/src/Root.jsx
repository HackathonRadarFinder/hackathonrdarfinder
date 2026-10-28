import { lazy } from 'react';
const Root = lazy(() => window.location.pathname === '/demo' || window.location.pathname.startsWith('/demo/')
  ? import('./DemoPlatform.jsx') : import('./App.jsx'));
export default Root;
