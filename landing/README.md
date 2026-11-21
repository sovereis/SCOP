# SCOP landing page v0.1

An original SCOP composition built around the supplied astronaut contemplating Earth reference, a graphite background, silver highlights, deep navy supporting surfaces and an open geometric wordmark. The page distinguishes the current public-PR review MVP from the planned ecosystem. Source copy and the hero follow the user brief. The supplied README is visual guidance, with the user's request controlling scope.

## Preview and real signup storage

From the repository root on Linux or Windows with WSL and Python 3.12:

```sh
python3.12 -B -m server.scop_landing
# Open http://127.0.0.1:8780
```

Without a signup directory the page loads with collection disabled. To test persistence, create a dedicated directory outside all Git worktrees. Use synthetic information during development.

```sh
mkdir -m 700 "$HOME/scop-signups"
python3.12 -B -m server.scop_landing --signup-dir "$HOME/scop-signups"
```

A successful POST writes a UUID-named `.signup.json` file, mode 0600, containing email, coding tool, challenge, explicit consent, consent version and server UTC timestamp. HTTP 201 and the success message follow the completed write. There is no confirmation email. Repeated submissions create separate records, so a retry after a lost response can duplicate a signup. Storage failures and unavailable collection show errors. Capacity is 10,000 files. The operator can inspect or remove records directly in the private directory. Keep it separate from measurement records and never add it to Git, screenshots, issue bodies or PR descriptions.

The runtime uses Python's standard library. It reuses the existing private-directory and atomic-write helpers while leaving the v0.9 modules and contracts unchanged. Store ownership, mode, symlink and Git-worktree checks still apply. The HTTP adapter has its own loopback port, fixed assets, strict Host/Origin/session checks, CSP, no CORS, bounded 8 KiB JSON, socket inactivity timeout and redacted errors. Single-process handling serializes writes. No subprocesses, remote integrations or user-controlled file paths are exposed. Input text is never injected into HTML. Email syntax validation does not establish ownership or deliverability.

## Image and visual implementation

`assets/hero.webp` is a faithful image-tool adaptation of the astronaut inline reference (1672 × 941), encoded as WebP. The inline attachment was visible but had no downloadable original path, so the adapted asset should be visually reviewed against the supplied image. Its aspect ratio is preserved with CSS, and positioning adapts to the viewport. The desktop gradient creates text space to the left while keeping Earth and the astronaut visible. On mobile a 360px image region sits above the text to avoid overlap. No external fonts, analytics, stock claims, partner logos or ClearPath branding are included. Confirm rights to the supplied image before public publication.

The hero image is preloaded and served locally. On desktop, requestAnimationFrame applies bounded scroll transforms to the artwork, ambient light and content. The artwork keeps the astronaut, Earth and stars together, with a separate ambient lighting plane providing the additional depth. There is no extracted character mesh. Desktop mouse movement adds at most three horizontal and two vertical pixels of microparallax. A metallic sheen moves across focused or hovered primary buttons. Scroll transforms and the sheen are disabled for reduced motion and widths below 1001 px. The UI includes a skip link, visible keyboard focus, field labels, inline errors, consent and live submission feedback.

## Deploy to Vercel after approval

The production target is **only `landing/`**. Vercel serves four allowlisted static files built into `public/`, with Python functions at `/api/config` and `/api/signup`. They import only `landing/backend`, independently of Workspace and the local preview server. Production uses Supabase Postgres over HTTPS through the small `SupabaseStore.save` adapter. It never writes signup data to the function filesystem.

`/api/config` returns a short-lived signed submission token when server configuration is present. The static page starts disabled and enables submission only after this response. Missing configuration returns 503. Database connectivity, schema and permissions are checked by the insert operation, whose failure also returns 503. A successful insert must acknowledge the submitted UUID before the API returns 201. No response exposes credentials or database details.

### Variables in Vercel Settings → Environment Variables

| Variable | Value | Scope |
| --- | --- | --- |
| `SCOP_PUBLIC_ORIGIN` | Exact HTTPS origin, such as `https://scop.example.com`, without trailing slash or path | Configure separately per Preview/Production |
| `SCOP_SUPABASE_URL` | Project endpoint `https://<project-ref>.supabase.co` | Server only |
| `SCOP_SUPABASE_SERVICE_ROLE_KEY` | Supabase legacy `service_role` JWT from that project | Sensitive server-only variable |
| `SCOP_SIGNUP_SECRET` | Independent random secret of at least 32 characters, e.g. generated with `openssl rand -hex 32` | Sensitive server-only variable |

Use a dedicated Supabase project for these signups. The service-role key bypasses RLS and must never appear in frontend code, a public variable, source control, screenshots or logs. Use separate databases and secrets for Preview and Production. This adapter expects the legacy service-role JWT, not an anonymous/publishable key. Custom Supabase domains are not supported by the fixed endpoint allowlist.

### Exact setup sequence

1. In Supabase, create the dedicated project and run `landing/schema.sql` once in **SQL Editor**. It creates `public.scop_signups`, enables RLS and denies table access to anonymous/authenticated clients. Copy the project URL and service-role key into the sensitive Vercel variables. Never insert real personal data during validation.
2. In Vercel, choose **Add New → Project**, import `sovereis/SCOP`, and choose **Other** for the framework. Set **Root Directory** to `landing`. Disable inclusion of files outside the root directory. The config sets **Build Command** to `python3 build.py` and **Output Directory** to `public`. Leave the install command empty. Python 3.12 is selected by `.python-version`.
3. Use branch `feat/landing-page-v01` for the initial review deployment. In **Settings → Git**, set the production branch deliberately when preparing Production. `git.deploymentEnabled: false` prevents later Git pushes from triggering deployments. This task has not created a Vercel project or clicked **Deploy**.
4. Only when publication is authorized, click **Deploy**. If a deployment/domain is needed to determine the origin, the first deployment can omit variables and safely leave signup disabled. In **Settings → Domains**, choose the final domain, set `SCOP_PUBLIC_ORIGIN` to that exact HTTPS origin, configure the other variables, and manually **Redeploy**. Environment changes require a new deployment. Each accepted hostname must match the configured origin; use the configured domain for testing rather than an alternate deployment alias.
5. Before allowing public traffic, enable appropriate Vercel Firewall rate limits for `/api/signup`, configure operator contact, retention and deletion details in the privacy copy, and protect Preview deployments with Vercel's deployment protection. Configure backups and restrict Supabase administrative access.
6. On the chosen domain, verify `/`, `/style.css`, `/app.js`, and `/assets/hero.webp`; verify `/server/scop_workspace.py` and `/api/run` return 404. Submit synthetic answers and confirm the new row in Supabase Table Editor. Test consent denial and temporary invalid database credentials in Preview and confirm no success message. Restore the correct credentials and redeploy before final review.

### Before publication

Run the Python and Chromium commands below and `python landing/build.py`. The public output must contain only `index.html`, `style.css`, `app.js`, and `assets/hero.webp`. The local production HTTP test harness executes the production request boundary and static output with a database test double. Unit tests check the PostgREST acknowledgement contract and failure paths. These tests cannot establish real Supabase persistence or Vercel platform routing without a configured project.

For a Vercel preview, use synthetic records and compare UI success against the database row. Opening a hosted preview is itself a deployment and requires authorization. This repository contains no configured database or credentials, and no live insert or hosted deployment was performed during implementation.

### Production limitations

Tokens expire after one hour; reload the page if an old form is rejected. They protect browser origin boundaries, not against bots that obtain tokens. Production abuse controls and retention are operator responsibilities. Email ownership and delivery are not verified. Lost responses or repeated submissions can create duplicate rows. The database request has an eight-second timeout, a bounded acknowledgement and refuses redirects; the function has a 15-second platform limit. Same-origin HTTPS JSON requests, Host/Origin validation, signed tokens, CSP, no CORS, 8 KiB bodies, field limits and explicit consent remain enforced. A provider outage produces a clear failure, never a local-storage fallback.

## Automated validation

```sh
python -m pytest -q
npm ci --ignore-scripts --prefix tests/ui
tests/ui/node_modules/.bin/playwright install --with-deps chromium
node --test tests/ui/*.test.cjs
```

For an existing browser use `SCOP_CHROMIUM=/usr/bin/chromium`; set `PYTHON` to your pytest-equipped interpreter for browser fixtures. Browser tests use disposable private stores and synthetic contact data. They exercise real writes, consent, validation, errors, disabled collection, keyboard focus and horizontal layout at 1440, 1024, 768 and 390 px. Screenshots are written to `/tmp/scop-landing-{desktop,tablet,mobile}.png`. Existing Workspace browser tests remain included. Required CI runs both suites.
