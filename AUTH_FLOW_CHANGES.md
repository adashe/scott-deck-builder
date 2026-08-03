# Deck Builder auth flow — diagnosis and rewrite

## What was actually breaking

Andrea's trace was right, and it pointed straight at the real cause.

- `auth-callback` is reached at `https://www.siscc-portal.com/scott-deck-builder/auth-callback` — i.e. on the **portal** domain.
- When it did `Set-Cookie`, that cookie was scoped to **`siscc-portal.com`**.
- It then 302-redirected to `https://scott-deck-builder.vercel.app/` — a **different** domain, where a `siscc-portal.com` cookie is never sent.
- So `index.py` (on vercel.app) always saw **no cookie** and bounced to login. That's exactly the `if not request_has_valid_session(...)` branch her Reddit test URL fired from.

The old comment in `auth_callback.py` ("use the absolute Vercel URL so the browser stays on the same domain as the cookie") had it backwards. The redirect *target* wasn't the problem — the cookie was minted on the wrong **domain** to begin with. No redirect destination can rescue a cookie the browser filed under a different site.

And Andrea's proposed fix was the correct architecture: the credential has to travel to vercel.app **in the URL**, and code running **on vercel.app** (`index.py`) has to turn it into the cookie there. That's what this rewrite does.

## The corrected flow

```
Portal (siscc-portal.com)
   │  login ok → redirect
   ▼
/auth-callback?token=<supabase_access_token>      [runs on portal domain]
   │  verify Supabase JWT signature + expiry
   │  mint a SHORT-LIVED handoff token (this app's own, ~2 min)
   ▼  302
https://scott-deck-builder.vercel.app/?st=<handoff_token>   [now on vercel.app]
   │  index.py: no cookie yet, but ?st= is valid
   │  Set-Cookie: scott_deck_session=...   ← minted on the RIGHT domain
   ▼  302 to "/"  (token stripped from the URL)
https://scott-deck-builder.vercel.app/            [cookie now sent]
   │  index.py: valid cookie → serve the form
   ▼
Deck builder
```

### One refinement on the plan

Rather than putting the 8-hour session token in the URL, the URL carries a
**separate, ~2-minute handoff token**. If a URL ever leaks (browser history,
`Referer`, a proxy log), the exposure is a credential that's already dead. The
two tokens are signed with the same `SESSION_SECRET` but carry a `typ` claim and
are **not interchangeable** — a handoff token can't be replayed as a session
cookie, and vice versa. Responses in the token path also send
`Referrer-Policy: no-referrer`.

`request_has_valid_session()` stays a pure cookie check (as it was). The
token-exchange step lives in `index.py`, because trading a token for a cookie
means *setting a cookie and redirecting* — side effects that don't belong inside
a boolean helper.

## The login-loop fix

On any auth failure, both `index.py` and `auth_callback.py` now serve a
**self-contained HTML page** (`auth_error_page_preview.html` shows it) with
**Log in** and **Return to main app** buttons and **no automatic redirect**.
That's what breaks the oblique loop — there's a visible stop with a clear
message instead of a silent bounce back to portal login.

(HTTP status is 401 for auth failures, 500 for unexpected errors. Semantically
truer than a 404, and the body renders the same friendly page either way.)

## Two knobs to confirm before deploy

In `lib/auth.py` (both were pointed at monday.com during the trace; restored here):

- `PORTAL_LOGIN_URL = "https://www.siscc-portal.com/login"` — restored from the
  commented-out original. Confirm it's still correct.
- `PORTAL_HOME_URL = "https://www.siscc-portal.com/"` — **new**, used by the
  "Return to main app" button. I guessed the portal root; set it to the real
  landing page if that's different.

`FORM_URL` in `auth_callback.py` stays `https://scott-deck-builder.vercel.app/`.

## What did NOT change

- **No portal-side change.** The portal still redirects to
  `/scott-deck-builder/auth-callback?token=<supabase_token>` exactly as before.
- **No new environment variables.** Still just `SUPABASE_JWT_SECRET` and
  `SESSION_SECRET` (the same secret the old session cookie already used).
- **`generate.py` is unchanged.** Its cookie check and 401-on-failure are
  correct as-is.
- **`form.js` is unchanged.** The page is served from vercel.app and POSTs to
  vercel.app/api/generate — same origin — so the httpOnly cookie is sent.

## One thing to watch

The fix relies on the user landing on **vercel.app** for the app itself (the
`?st=` handoff redirects there). If the deck-builder *page* is ever served
through the portal proxy (`siscc-portal.com/scott-deck-builder/`) instead, then
`form.js`'s same-origin POST to vercel.app becomes cross-origin and the httpOnly
cookie won't ride along — `/api/generate` would 401. Keep the app landing on
vercel.app and this stays clean.

## Verifying

`flow_test.py` drives the real handler classes through all nine branches
(success handoff, cookie serve, expired/tampered/typ-mismatch tokens, bad
Supabase signature, missing token, the friendly page). Run from the repo root:

```
SUPABASE_JWT_SECRET=x SESSION_SECRET=y python3 flow_test.py
```

## Files

- `lib/auth.py` — handoff + session tokens (typ-separated), portal URLs,
  friendly-page renderer, `get_handoff_token_from_path`.
- `api/index.py` — cookie → handoff-exchange → friendly page.
- `api/auth_callback.py` — verify Supabase token → mint & forward handoff token;
  friendly page on failure. Andrea's token-rejection diagnostics retained.
