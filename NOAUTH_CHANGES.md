# Deck Builder — auth layer removed

The app now runs open: the form loads for anyone, and `/api/generate` builds a
deck for any well-formed POST. No portal login, no Supabase token, no session
cookie.

## Files in this bundle (replace yours with these)

- `api/index.py` — now just serves `templates/index.html`. All session/handoff
  logic gone.
- `api/generate.py` — the `request_has_valid_session` gate and its import are
  removed. Everything else (form parsing, deck/script generation, Vercel Blob
  upload, CORS) is unchanged.
- `vercel.json` — the two `/auth-callback` rewrites are removed. All other
  routes are unchanged.

## Files to DELETE from the repo

These are now unused. **Delete them** — don't just leave them:

- `api/auth_callback.py`
- `lib/auth.py`

Note: Vercel auto-deploys every `api/*.py` file as a function regardless of
`vercel.json`. So if you leave `api/auth_callback.py` in the repo, an inert
`/api/auth_callback` endpoint still ships. Deleting the file is what actually
removes it.

(`lib/__init__.py` stays; `lib/deck_builder.py` and `lib/script_builder.py` are
still used by `generate.py`.)

## Environment variables you can remove (optional)

No longer read by any code:

- `SUPABASE_JWT_SECRET`
- `SESSION_SECRET`

Still needed:

- `BLOB_READ_WRITE_TOKEN` — set automatically by Vercel when a Blob store is
  linked. Leave it.

## The one thing to be aware of

`scott-deck-builder.vercel.app` is a public URL. With auth gone, anyone who has
or guesses it can load the form and POST to `/api/generate`, which spends
compute and writes to your Blob store. `generate.py` also sends
`Access-Control-Allow-Origin: *`, so any website can call it too.

If you want to stay out of the portal/Supabase flow but not be fully open, gate
the whole deployment at the platform level with **zero code**:

Vercel → your project → Settings → Deployment Protection → either
- **Vercel Authentication** (only your Vercel team can view), or
- **Password Protection** (one shared password for the whole app).

That covers the page and the API together and needs no changes to this code.

## Verifying

A smoke test drove the two remaining handlers:
- `GET /` → 200, serves the form, no redirect (previously bounced to login).
- `POST /api/generate` with no cookie → reaches normal validation (400 on a
  non-multipart body) instead of a 401 auth gate.
- `GET`/`OPTIONS /api/generate` → unchanged (info text / CORS preflight).
