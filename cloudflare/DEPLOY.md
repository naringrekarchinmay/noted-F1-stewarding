# Deploying Noted with friends' votes

Nothing here is deployed yet. **Until it is, steward-mode picks stay in each browser's
localStorage only** (key `noted:rulings`); nobody else sees them.

**None of these steps has been run against Cloudflare.** The Function is tested locally
(`node --test cloudflare/test/votes.test.mjs`, a fake D1, and once against `node:sqlite`), and the
page's vote sync against a local stand-in. Unverified: the wrangler version pin, the exact flags,
`pages_build_output_dir` pointing outside this folder (`../data/site`), and the free-tier figures.
Expect to adjust a step or two on the first run.

What gets deployed: the static site (`data/site`), one Pages Function (`functions/api/votes.js`,
served at `/api/votes`) and one D1 database (`noted-votes`, table `votes`, see `schema.sql`).
Cost: **$0/month** on the free plans below.

## Before you start

- Create a free Cloudflare account yourself at dash.cloudflare.com. (Nobody else should make it for you.)
- Decide on privacy first (see "Who can see it" below): every ruling page carries the stewards'
  full decision text.
- All commands below use `npx wrangler@4.20.0`. That downloads wrangler and its dependencies
  from npm into the npx cache (download size unknown). Ask before running it on a machine
  where that matters. The pin is a version believed to exist; if npx
  cannot find it, use the current version shown on npmjs.com/package/wrangler and pin that.

## Steps

Run everything from `cloudflare/` unless the step says otherwise.

1. Log in (opens a browser):
   `npx wrangler@4.20.0 login`
2. Create the database:
   `npx wrangler@4.20.0 d1 create noted-votes`
3. Copy the `database_id` it prints into `wrangler.toml`, replacing
   `REPLACE_AFTER_wrangler_d1_create`.
4. Create the table:
   `npx wrangler@4.20.0 d1 execute noted-votes --remote --file=schema.sql`
5. Build the site with vote sync on, from `pipeline/`:
   `uv run noted site --votes`
   (writes `data/site`, about 1,300 files)
6. Deploy, from `cloudflare/`:
   `npx wrangler@4.20.0 pages deploy --branch main`
   (`--branch main` makes it a production deployment whatever branch git is on; unverified
   against this exact wrangler version.)
   The first run asks to create the Pages project `noted`; accept, production branch `main`.
   It prints the URL (`https://noted.pages.dev`, or a variant if the name is taken).
7. Check it: open a ruling page, pick a penalty, then
   `npx wrangler@4.20.0 d1 execute noted-votes --remote --command="SELECT COUNT(*) FROM votes"`

To update later: repeat steps 5 and 6. The database and its votes are kept.

## Free-tier limits that matter

As of this plan; check the Cloudflare pricing pages before relying on them.

- Pages: 500 builds/month (not used: we upload directly, no Cloudflare build);
  20,000 files per deployment (the site is ~1,300 HTML pages, ~1,310 files in all).
  Static page views are not metered.
- Functions: count against the Workers free plan, 100,000 requests/day. Only `/api/votes`
  calls count. Over the limit, the API errors for the rest of the day; the pages still load.
- D1: 5 GB storage, 5 million rows read/day, 100,000 rows written/day. One vote is one
  row (about 100 bytes); one tally reads that ruling's votes.

## Who can see it

By default the site is public at its `pages.dev` URL. The published pages include the stewards'
full ruling text, as well as anything else the pipeline renders. Decide whether that is fine on
the open web. If not, put it behind Cloudflare Access:

- Dashboard > Zero Trust (free for up to 50 users; setup may ask for a payment card even on the
  free plan) > Access > Applications > Add > Self-hosted.
- Domain: the hostname printed in step 6 (e.g. `noted.pages.dev`), plus a second entry
  `*.<that hostname>` to cover preview URLs.
- Policy: Allow, Include > Emails > your friends' addresses. Login method: one-time PIN by email.
- `/api/votes` is on the same domain, so Access covers it too. With Access on, only those people
  can read the pages or vote.

Without Access, anyone who finds the URL can vote, and a voter id is just a random string the
browser makes, so one person could stuff votes. Fine for friends; not a secure poll.

## Rolling back

- List deployments: `npx wrangler@4.20.0 pages deployment list --project-name noted`
- Roll back: Dashboard > Workers & Pages > noted > Deployments > pick an earlier one > Rollback.
- Rollback changes the site and Function, not the database. To keep a copy of the votes first:
  `npx wrangler@4.20.0 d1 export noted-votes --remote --output=votes-backup.sql`
- To take it all down: `npx wrangler@4.20.0 pages project delete noted` and
  `npx wrangler@4.20.0 d1 delete noted-votes` (this deletes the votes for good).

## If something goes wrong

- Wrangler warns that `compatibility_date` is newer than it supports: use a newer wrangler,
  or set the date to the one it suggests.
- Wrangler will not use `../data/site` as the output directory: run `npx wrangler@4.20.0 pages
  deploy ../data/site --project-name noted --branch main` instead.
