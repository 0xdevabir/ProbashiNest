# Probashi Shield — frontend

Mobile-first web app (React, Vite, TypeScript, Tailwind) for checking a job offer before paying a recruiting agent. Bangla by default, with an English toggle. Installable as a PWA.

| Home | Checking | High risk | Check further | Looks safe | Privacy |
| --- | --- | --- | --- | --- | --- |
| ![Home](docs/screenshots/home.png) | ![Loading](docs/screenshots/loading.png) | ![Red verdict](docs/screenshots/result-red.png) | ![Amber verdict](docs/screenshots/result-amber.png) | ![Green verdict](docs/screenshots/result-green.png) | ![Privacy](docs/screenshots/privacy.png) |

Screenshots are from a demo-mode build at 360 px wide.

## Run locally

Needs Node 20 or newer.

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

Other commands:

```bash
npm test           # Vitest + Testing Library
npm run build      # type-check, then production build into dist/
npm run preview    # serve dist/ locally, service worker included
```

## Environment variables

Vite reads them from the `.env` file at the **repo root** (see `.env.example` there), or from the shell. They are baked in at build time.

| Variable | Default | Meaning |
| --- | --- | --- |
| `VITE_API_URL` | empty (same origin) | Base URL of the backend. The app calls `POST {VITE_API_URL}/api/check`. |
| `VITE_DEMO_MODE` | `false` | `true` answers from bundled fixtures and enables the hidden demo menu. |

## Demo mode

```bash
VITE_DEMO_MODE=true npm run dev
```

In demo mode no request leaves the phone. Every check returns one of three fixtures in `src/fixtures/` (red, amber, green), shaped like `CheckResponse` in `probashi/schemas.py`.

- **Choosing the verdict:** tap the logo five times within three seconds. The menu offers red (the default), amber, green, and "live server", which switches back to the real API without a rebuild.
- **Offline pitch:** run `npm run build && npm run preview` (or the Docker image) and open the app once while online. The service worker then caches the whole app, fonts and fixtures included, so it keeps working with the network off.
- **Spoken answer:** the fixtures carry no `audio_base64`. The result screen then reads the answer with the device's own Bangla voice if it has one; if not, the listen button is hidden. Check this on the pitch device beforehand.
- Fixture results always show a "নমুনা তথ্য, আসল নয়" (sample data, not real) badge.

The fixtures are **synthetic**. Employer and agency names and licence numbers are marked as made up. The two helpline numbers (Probash Bondhu call centre, 16135 and +8809610102030) are real and were checked against [The Business Standard](https://www.tbsnews.net/node/490534) and [Dhaka Tribune](https://www.dhakatribune.com/bangladesh/293573/govt-launches-probash-bondhu-hotline-service-for). One reason in the red fixture has no source yet and says so.

## Docker

```bash
docker build -t probashi-frontend \
  --build-arg VITE_API_URL=https://api.example.org \
  --build-arg VITE_DEMO_MODE=false \
  frontend/
docker run -p 8080:80 probashi-frontend
```

The image serves `dist/` with nginx: hashed assets are cached for a year, the service worker and `index.html` are always revalidated.

## How it is put together

| Path | What it holds |
| --- | --- |
| `src/i18n/translations.ts` | Every piece of UI text, Bangla and English |
| `src/types.ts` | TypeScript mirror of `probashi/schemas.py` |
| `src/api.ts` | `checkOffer()`: multipart POST, timeout, error kinds |
| `src/compress.ts` | Client-side photo downscaling to under 2 MB |
| `src/demo.ts`, `src/fixtures/` | Demo mode |
| `src/components/SpeakButton.tsx` | Hold-to-speak recorder (MediaRecorder, 2 minute limit) |
| `src/components/VerdictCard.tsx`, `Signal.tsx` | The traffic-light verdict |
| `src/screens/` | Home, type, loading and error, result, privacy |

Behaviour worth knowing:

- **Verdict** is shown three ways at once: lamp position and colour, a mark inside the lit lamp (cross, exclamation, tick), and words. A response whose level is not `red`, `amber` or `green` is treated as an error; the app never guesses a level.
- **Speaking:** hold the button and let go to send. A short tap also works: it starts recording, and a second tap sends. Recordings under one second are discarded.
- **Photo:** the file input has no `capture` attribute, so phones offer both the camera and the gallery (offers often arrive as WhatsApp images). Desktop gets a file picker.
- **Errors** are split into offline, timeout (90 s), server, bad request and unreadable answer, each with its own Bangla message and a retry button that resends the same input.
- **Nothing is stored:** recordings and photos live in memory only until the request finishes. Only the language choice is kept in `localStorage`.
- **Size:** the first load is about 75 KB of JS and CSS gzipped plus two font weights; result, typing, privacy and demo screens load on demand.
