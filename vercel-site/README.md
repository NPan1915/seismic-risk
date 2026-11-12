# Globe site (Vercel)
Static site. `public/index.html` is the globe; it loads `public/zones.json` (same folder). The weekly GitHub Action
overwrites `zones.json`/`metrics.json` and Vercel redeploys on each push. Until the first real `zones.json` exists
the page shows illustrative sample zones. Settings: Root Directory `vercel-site`, no build command, output dir `public`.
