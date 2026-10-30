# Accent-Aware Multilingual Translator

A React, TypeScript, and Vite multilingual translation app with a Node.js backend proxy for OpenRouter. The server keeps the OpenRouter API key out of the browser bundle.

## Languages
Includes Kannada, Telugu, Tamil, Malayalam, Marathi, Urdu, Bhojpuri, Hindi, and other languages.

## Deploy on Render
This repository uses a Render Blueprint. Upload the cleaned application source archive as `source.zip` at the repository root (download the prepared source ZIP from the ChatGPT conversation). The archive should contain `package.json`, `package-lock.json`, `server.js`, `App.tsx`, and the source folders at its root.

1. Open Render and choose **New → Blueprint**.
2. Select this repository: `Avinash-273/Accent-aware-multilingual-translator`.
3. Render reads `render.yaml` and creates the web service.
4. When prompted, set `OPENROUTER_API_KEY` to a newly generated OpenRouter key.
5. Deploy. The health endpoint is `/api/health`.

Do not add the key as a `VITE_*` variable or commit it to GitHub. The frontend calls the same-origin `/api/translate` backend route.

## Local development
Extract `source.zip`, open the extracted project folder, and run:

```bash
npm ci
# Terminal 1
npm run api:dev
# Terminal 2
npm run dev
```

The Vite dev server proxies `/api` requests to the local Node server on port 3001.

## Speech
Speech output uses the browser Web Speech API and relies on voices installed on each user's device. A language may translate successfully while lacking a local speech voice.
