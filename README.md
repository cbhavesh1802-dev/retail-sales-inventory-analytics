# ADG MVP — Setup Guide

## What this does
Every time a pull request is opened on your GitHub repo, ADG automatically:
1. Scans dependencies with Snyk
2. Calculates a trust score (0–100)
3. Posts a comment on the PR with findings and decision

---

## Step 1 — Install Python dependencies

```bash
cd adg-mvp
pip install -r requirements.txt
```

---

## Step 2 — Get your API tokens

### GitHub Token
1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Give it a name: `adg-mvp`
4. Select scopes: `repo` (full) + `pull_requests`
5. Copy the token

### Snyk Token
1. Sign up free at https://app.snyk.io
2. Go to Account Settings → API Token
3. Copy the token

---

## Step 3 — Create your .env file

```bash
cp .env.example .env
```

Open `.env` and fill in your tokens:
```
GITHUB_TOKEN=ghp_your_token_here
GITHUB_WEBHOOK_SECRET=pick_any_random_string_123
SNYK_TOKEN=your_snyk_token_here
```

---

## Step 4 — Run the server

```bash
uvicorn app.main:app --reload --port 8000
```

You should see:
```
INFO | ADG MVP started — waiting for GitHub webhooks
INFO | Uvicorn running on http://0.0.0.0:8000
```

---

## Step 5 — Expose your local server with ngrok

In a new terminal:
```bash
# Install ngrok from https://ngrok.com (free)
ngrok http 8000
```

Copy the HTTPS URL — looks like: `https://abc123.ngrok.io`

---

## Step 6 — Add the webhook to GitHub

1. Go to your GitHub repo → Settings → Webhooks → Add webhook
2. **Payload URL:** `https://abc123.ngrok.io/webhook/github`
3. **Content type:** `application/json`
4. **Secret:** same string you put in `GITHUB_WEBHOOK_SECRET`
5. **Events:** Select "Pull requests" only
6. Click "Add webhook"

---

## Step 7 — Test it

Open a pull request on your repo. Within seconds, ADG will post a comment like:

```
✅ ADG — Deployment Trust Score

| Trust score | 87/100 |
| Decision    | ✅ APPROVE |
| Dep risk    | 0/100 |

Score  [█████████████████░░░] 87/100

Findings
✅ No dependency vulnerabilities found.
📝 42 lines changed across 3 file(s).
```

---

## Manual test (no webhook needed)

You can test against any existing PR immediately:

```bash
curl -X POST http://localhost:8000/evaluate/OWNER/REPO/PR_NUMBER
```

Example:
```bash
curl -X POST http://localhost:8000/evaluate/torvalds/linux/1234
```

---

## Health check

```bash
curl http://localhost:8000/health
```

---

## Run with Docker

```bash
docker build -t adg-mvp .
docker run -p 8000:8000 --env-file .env adg-mvp
```

---

## Project structure

```
adg-mvp/
├── app/
│   ├── main.py              ← FastAPI app + webhook endpoint
│   ├── config.py            ← Environment variables
│   └── services/
│       ├── snyk.py          ← Snyk vulnerability scanner
│       ├── scorer.py        ← Trust score calculator
│       └── github.py        ← GitHub API (fetch PR, post comment)
├── requirements.txt
├── Dockerfile
└── .env.example
```

---

## What's next (Phase 2)

Once this is working:
- Add SonarQube code quality scanning
- Add ML-based anomaly detection
- Add auto-remediation (fix PRs)
- Add a dashboard frontend

Built with FastAPI + Snyk + GitHub API.
