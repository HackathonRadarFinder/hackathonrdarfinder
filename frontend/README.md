# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and Oxlint's TypeScript related rules in your project.

## Disposable browser acceptance

`npm run test:browser` uses an installed Chromium browser through Playwright Core. It checks responsive layouts at 320, 390, 768 and 1440 pixels, automated WCAG 2.2 AA rules, keyboard navigation, registration/login/logout, pagination/filtering, saved-event and consent persistence, notification read state, admin denial and prediction presentation. A synthetic intercepted prediction response tests rendering only and is never saved to a database.

The runner accepts only `http://127.0.0.1:5174` and verifies the fixture-only marker before any registration or other writes. The fixture creates and migrates a temporary SQLite database, disables email and binds only to loopback. Use unused ports 8020 and 5174; preserve any existing processes and the normal Compose stack.

Prepare from the repository worktree:

```powershell
python -m venv .test-support/browser-venv
& .test-support/browser-venv/Scripts/python.exe -m pip install -r backend/requirements.txt
Set-Location frontend
npm.cmd ci
```

Terminal 1, from the repository worktree:

```powershell
& .test-support/browser-venv/Scripts/python.exe scripts/disposable_backend.py
```

Terminal 2, from `frontend`:

```powershell
$env:API_PROXY_TARGET = 'http://127.0.0.1:8020'
npm.cmd run dev -- --port 5174 --strictPort
```

Terminal 3, from `frontend`:

```powershell
$env:FRONTEND_DISPOSABLE_BROWSER_BASE = 'http://127.0.0.1:5174'
npm.cmd run test:browser
$env:FRONTEND_DISPOSABLE_API = 'http://127.0.0.1:5174/api'
npm.cmd test
```

Set `BROWSER_EXECUTABLE_PATH` if Chrome or Edge is not installed in a detected Windows path. JSON evidence and screenshots are written to ignored `.test-support/browser-evidence` in the worktree. Stop only these test processes when finished. Automated axe checks and Chromium keyboard checks are acceptance evidence for the covered screens, not a complete WCAG conformance claim; manual screen-reader and additional-browser review remain required.
