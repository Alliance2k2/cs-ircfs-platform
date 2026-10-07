# CS-IRCFS frontend (experimental, not in use)

> **Status: experimental draft.** The platform people actually use is the `dashboard/` folder, which FastAPI serves at `/`. This React/Vite draft only repeats the sign-in pages. It is kept as a possible future rewrite and is **not** part of the presentation, the Docker image, or the handover.

If you want to try it:

```powershell
cd frontend
npm install
npm run dev
```

Before any real use, pin the dependency versions in `package.json` (they currently say `latest`).
