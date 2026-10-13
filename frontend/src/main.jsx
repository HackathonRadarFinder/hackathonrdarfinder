import { StrictMode, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import Root from './Root.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Suspense fallback={<p role="status">Loading portal…</p>}><Root /></Suspense>
  </StrictMode>,
)
