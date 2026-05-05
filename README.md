# cloud-url-shortener

A self-hosted URL shortener deployed on AWS EC2 using Docker Compose, with infrastructure provisioned by Terraform and CI/CD via GitHub Actions.

---

## Architecture

```
                        ┌─────────────────────────────────────────┐
                        │              EC2 Instance                │
                        │                                          │
Internet ──── :80 ────► │  ┌──────────┐     ┌──────────────────┐  │
                        │  │  nginx   │────►│   shortener :5000│  │
                        │  │ (frontend│     │   (Flask)        │  │
                        │  │  + proxy)│     └────────┬─────────┘  │
                        │  └──────────┘              │            │
                        │                    ┌───────▼──────────┐ │
                        │                    │   logger :5001   │ │
                        │                    │   (Flask)        │ │
                        │                    └───────┬──────────┘ │
                        │                    ┌───────▼──────────┐ │
                        │                    │  postgres :5432  │ │
                        │                    │  (Alpine)        │ │
                        │                    └──────────────────┘ │
                        └─────────────────────────────────────────┘
```

**Services:**

- **nginx** — Serves the static frontend and reverse-proxies API calls to the shortener. Handles short-code redirects via regex location block.
- **shortener** — Flask app on port 5000. Handles URL creation, lookup, and redirects. Calls the logger service on each visit.
- **logger** — Flask app on port 5001. Records visit metadata (IP, user agent) to Postgres.
- **postgres** — Persistent database. Initialized via `init-db.sql` on first run.

**Nginx routing:**

| Path | Destination |
|---|---|
| `POST /shorten` | `shortener:5000/shorten` |
| `GET /stats/:code` | `shortener:5000/stats/:code` |
| `GET /:code` (6 alphanum chars) | `shortener:5000/:code` → redirects |
| Everything else | Static frontend (`index.html`) |

---

## 15-Factor App Compliance

| # | Factor | How it's addressed |
|---|---|---|
| 1 | **Codebase** | Single Git repo (`cloud-url-shortener`); one codebase deployed to one environment via `git pull` on the EC2 instance. |
| 2 | **Dependencies** | Each service declares dependencies explicitly (`requirements.txt` + `Dockerfile`); nothing is assumed from the host. |
| 3 | **Config** | All environment-specific values (`DB_USER`, `DB_PASS`, `PUB_DNS`) are injected via `.env` written by CI — never hardcoded in source. |
| 4 | **Backing services** | Postgres and the logger are consumed over the Docker network by URL (`DATABASE_URL`, `LOGGER_URL`), swappable without code changes. |
| 5 | **Build, release, run** | GitHub Actions builds images (`--build`), composes them with the `.env` release config, then runs containers — three distinct stages. |
| 6 | **Processes** | Each service is a stateless process; persistent state lives exclusively in Postgres, not in container memory or local disk. |
| 7 | **Port binding** | Each service exports itself via a port (`5000`, `5001`), (`80`) declared in `docker-compose.yml` — no app server required externally. |
| 8 | **Concurrency** | Services are independently scalable via Docker Compose `scale` or by running multiple containers behind nginx. |
| 9 | **Disposability** | Containers start fast and shut down cleanly; Postgres data survives restarts via a named volume (`postgres_data`). |
| 10 | **Dev/prod parity** | Single-environment setup; dev and prod run the same Docker images locally and on EC2, with only `.env` values differing between a developer's machine and the server. |
| 11 | **Logs** | Services write to stdout/stderr; logs are accessible via `docker compose logs` and can be forwarded to any aggregator. |
| 12 | **Admin processes** | One-off tasks (e.g. DB inspection) run as ephemeral commands via `docker exec` against the running container. |
| 13 | **API first** | Shortener and logger communicate exclusively over HTTP REST APIs; the frontend is fully decoupled from backend logic. |
| 14 | **Telemetry** | The logger records IP, user agent, and timestamp per visit to Postgres; /stats/:code exposes total visit count per URL; /health checks live DB connectivity and returns 503 if disconnected. |
| 15 | **Auth & security** | DB credentials and SSH keys are stored as GitHub Secrets, never in source; `DEBUG_MODE` gates exposure of error details in responses. |

---

## Infrastructure

Infrastructure is provisioned with **Terraform**. On `terraform apply`, it:

1. Creates an EC2 instance (Amazon Linux 2)
2. Attaches an **Elastic IP (EIP)** so the public address survives instance stop/start
3. Runs a **user data script** on first boot that:
   - Installs Docker and Docker Compose
   - Clones this repository to `/home/ec2-user/cloud-url-shortener`

After provisioning, the instance is ready for the GitHub Actions deploy workflow — no manual SSH setup required.

---

## Local Development

**Prerequisites:** Docker, Docker Compose

```bash
git clone https://github.com/<your-org>/cloud-url-shortener
cd cloud-url-shortener
```

Create a `.env` file:

```env
DB_USER=admin
DB_PASS=admin123
PUB_DNS=http://localhost:5000
```

Start all services:

```bash
docker compose up --build
```

The app will be available at `http://localhost`.

**Verify everything is healthy:**

```bash
docker compose ps
# All three services should show "healthy"
```

**Test the database:**

```bash
docker exec -it url_shortener_db psql -U $DB_USER -d url_shortener
# Then: \dt  to see tables
```

**Tear down and reset volumes:**

```bash
docker compose down -v
```

---

## Deployment (GitHub Actions)

Deployments trigger automatically on every push to `main`, or manually via the **Actions** tab (`workflow_dispatch`).

**What the workflow does:**

1. SSHs into the EC2 instance using the stored private key
2. Derives the AWS public DNS hostname from the EIP (e.g. `1.2.3.4` → `http://ec2-1-2-3-4.compute-1.amazonaws.com`)
3. Writes a `.env` file on the instance with credentials and the public DNS
4. Runs `git pull` then `docker compose up -d --build`

**Required GitHub Secrets:**

| Secret | Description |
|---|---|
| `EC2_EIP` | The Elastic IP address of your EC2 instance (e.g. `54.80.229.26`) |
| `EC2_SSH_KEY` | The private SSH key for the `ec2-user` account (PEM format) |
| `DB_USER` | Postgres username |
| `DB_PASS` | Postgres password |

To add secrets: **Settings → Secrets and variables → Actions → New repository secret**

---

## Environment Variables

| Variable | Service | Description | Example |
|---|---|---|---|
| `DATABASE_URL` | shortener, logger | Full Postgres connection string | `postgresql://admin:pass@database:5432/url_shortener` |
| `LOGGER_URL` | shortener | Internal URL of the logger service | `http://logger:5001` |
| `BASE_URL` | shortener | Public-facing base URL used in short link responses | `http://ec2-1-2-3-4.compute-1.amazonaws.com` |
| `DEBUG_MODE` | shortener, logger | If `"true"`, error details are included in API responses | `"true"` |
| `DB_USER` | compose / Terraform | Postgres username (used to build `DATABASE_URL`) | `admin` |
| `DB_PASS` | compose / Terraform | Postgres password | `admin123` |
| `PUB_DNS` | compose | Injected by CI to set `BASE_URL` | `http://ec2-...compute-1.amazonaws.com` |

> **Note:** `.env` is written by the deploy workflow on the EC2 instance. Never commit it to the repository.

---

## API Reference

### `POST /shorten`

Creates a short URL.

**Request:**
```json
{ "long_url": "https://example.com/very/long/path" }
```

**Response `201`:**
```json
{
  "short_url": "http://your-domain/aB3xYz",
  "code": "aB3xYz",
  "long_url": "https://example.com/very/long/path"
}
```

**Errors:** `400` if `long_url` is missing or doesn't start with `http://` / `https://`

---

### `GET /:code`

Redirects to the original URL. Returns `302` on success, `404` if the code doesn't exist.

---

### `GET /stats/:code`

Returns visit statistics for a short code, proxied from the logger service.

**Response `200`:**
```json
{
  "code": "aB3xYz",
  "total_visits": 42
}
```

**Errors:** `404` if code not found, `503` if the logger is unavailable.

---

### `GET /health`

Available on both services. Returns service status.

**Response `200`:**
```json
{
  "status": "healthy",
  "service": "shortener",
  "debug_mode": false,
  "timestamp": "2025-01-01T00:00:00+00:00"
}
```
