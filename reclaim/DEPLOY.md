# Putting the prototype online

The prototype is a single Node server that keeps its demo database and uploaded form-check
videos as files, so it needs **one long-running server**. Serverless hosting (e.g. Vercel)
won't work as-is: each request may land on a fresh instance and logins would be lost.

Every hosted copy must set `SITE_PASSWORD`; the whole site then asks for that password
before anything loads, because the demo logins are printed on the login page.

## Option A — Render (fewest steps, free tier)

1. Sign in at render.com with GitHub and allow access to this repository.
2. **New → Blueprint**, choose this repository and the branch `claude/clever-ritchie-uarnay`.
3. Render reads `render.yaml`, asks for `SITE_PASSWORD`, and builds (about 3–5 minutes).
4. Open the `…onrender.com` address, enter any username and the password, then log in with a demo account.

Free tier: the server sleeps after 15 minutes idle (first visit then takes about a minute) and
its disk is not persistent, so demo data resets to the seed on each restart. Fine for a demo; use a
paid instance with a disk, or Option B, for a pilot.

## Option B — Fly.io, Toronto region (persistent disk)

```bash
cd reclaim
fly launch --no-deploy --region yyz --name reclaim-prototype
fly volumes create data --region yyz --size 1
fly secrets set SITE_PASSWORD='choose-a-long-password'
fly deploy
```
Add to the generated `fly.toml`:
```toml
[mounts]
  source = "data"
  destination = "/data"
```

## Before real members or patients

This is a prototype: payments, email, EMR and pharmacy integrations are mocks and the legal
pages are drafts. See `docs/WEBSITE_SPEC.md` §8 (rollout gates) before taking real data.
