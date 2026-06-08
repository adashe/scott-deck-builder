# Deployment Guide — SCOTT Automation Deck Builder

This guide walks SCOTT IT (or whoever is deploying) from a fresh GitHub repo
to a live URL that the sales team can use. Total time: about 20 minutes.

## What you need before starting

- The SCOTT GitHub account login
- The SCOTT Vercel account login (it can sign in via GitHub)
- This codebase (the `scott-deck-builder/` folder)

## Step 1 — Create a GitHub repository

1. Log in to GitHub as the SCOTT account
2. Click **New repository** (top right, "+" icon)
3. Name it `scott-deck-builder` (or your preferred name — affects the deployed URL)
4. Choose **Private** (this is internal-only)
5. **Don't** initialize with a README — we already have one
6. Click **Create repository**

GitHub will show you commands to push existing code. Note the repo URL — it will look like `git@github.com:scott-industrial-systems/scott-deck-builder.git`.

## Step 2 — Push this code to the repo

Open a terminal in the `scott-deck-builder` folder and run:

```bash
git init
git add .
git commit -m "Initial commit — SCOTT Automation Deck Builder"
git branch -M main
git remote add origin <your-repo-url-from-step-1>
git push -u origin main
```

Confirm in GitHub that the files are there.

## Step 3 — Connect Vercel to the repo

1. Log in to Vercel (use **Continue with GitHub** if you don't already have a Vercel account)
2. From the dashboard, click **Add New** → **Project**
3. Click **Import** next to `scott-deck-builder` in the repository list
   - If you don't see it, click **Adjust GitHub App Permissions** and grant Vercel access to the SCOTT org
4. On the configuration screen:
   - **Framework Preset**: leave as **Other** (Vercel will autodetect)
   - **Root Directory**: leave blank (the repo root)
   - **Build Command**: leave blank
   - **Output Directory**: leave blank
   - **Install Command**: leave blank
   - Environment variables: none needed
5. Click **Deploy**

Vercel will spend 1–3 minutes building. It needs to:
- Install Python and the libraries in `requirements.txt`
- Bundle the `templates/source_deck.pptx` (24 MB) with the serverless function
- Deploy the static frontend

When it's done, you'll get a URL like `scott-deck-builder.vercel.app`. That's the URL to share with sales.

## Step 4 — Test it

1. Visit the deployed URL
2. Fill in the form with a test customer (e.g. "Test Customer Inc")
3. Pick a couple of value drivers, add some text in each Why field
4. Click **Generate deck + script**
5. You should get a download of `SCOTT_Test_Customer_Inc_Deck_Bundle.zip` within 10–20 seconds
6. Unzip and open both files to confirm they look right

## Step 5 — Share with the sales team

That's it. Send the URL to your sales team. No installs, no logins.

## Custom domain (optional)

If you want `decks.scottautomation.com` instead of `scott-deck-builder.vercel.app`:

1. In the Vercel project, go to **Settings** → **Domains**
2. Add your domain
3. Vercel will give you DNS records to point your domain at it
4. Add those records in your DNS provider (GoDaddy, Cloudflare, etc.)
5. SSL is automatic

## Updating the app

Any time you (or anyone with push access to the repo) commits to `main`:
- GitHub notifies Vercel
- Vercel rebuilds and deploys automatically (1–3 minutes)
- The new version is live at the same URL — no downtime

To roll back: in Vercel, find the previous deployment in the **Deployments** list, click **Promote to Production**.

## Troubleshooting

### Deploy fails with "function exceeded size limit"

Vercel's Python functions cap at 500 MB unpacked. Our function uses about 50 MB
(24 MB template + ~25 MB of Python deps), so we're well under. If this ever
trips, the most likely cause is someone added a large dependency. Check the
**Functions** tab in the Vercel deployment logs for the actual size.

### Form submits but no download

Open the browser developer tools (F12), go to the **Network** tab, click
**Generate** again, and look at the response from `/api/generate`. The JSON
error will tell you what happened. Common causes:
- The Vercel function timed out (default 60s in our `vercel.json`). If reps are
  generating decks with many proposal images, you may need to bump `maxDuration`
  in `vercel.json` and redeploy.
- Vercel hit its monthly invocation limit (very unlikely — Hobby tier is 1M/mo).

### Sales rep reports the deck is corrupted

If a generated `.pptx` won't open in PowerPoint:
1. Have them resubmit; transient issues happen
2. If it repeats, check Vercel's function logs for the timestamp of their submit
3. Errors in the logs will point at the failing slide or step

### Want to change the template

The source `.pptx` lives at `templates/source_deck.pptx` in the repo. Replace
it with a new version and push to main. Vercel auto-deploys. Caveat: if you
add or remove slides, you may need to update the section/slide number mappings
in `lib/deck_builder.py` (the `SECTION_SLIDES` and `INDEX_LINE_TRIGGERS` dicts).
