# IoT Platform Web

Operator UI for the CropDataSpace IoT platform. Stack: Next.js 14 (App
Router), TypeScript, Tailwind, shadcn-style primitives over Radix UI,
TanStack Query, react-hook-form + Zod.

## Run

```bash
cp .env.local.example .env.local
npm install
npm run dev
```

UI on http://localhost:3000. The API must be reachable at
`NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`). Bring it
up from the repo root with `make up`.

Authentication is **not** wired up yet. The user dropdown shows a
placeholder "Sign out" entry; real auth lands in ticket 0009 (Keycloak).
