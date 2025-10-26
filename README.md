# LetterboxdSync
(AI-generated README, lazy)

Sync Letterboxd lists between users. 

This app lets you share a list and automatically mirror changes to other members’ lists, even though Letterboxd doesn’t provide this capability by default (Shame on them).
Where the official API falls short, this project carefully uses scraping of the authenticated web experience to provide a reliable sync.

**Try it out: https://lbsync.fosanz.dev/**

### NOTE: This project is still under development and may not work as expected.

Important:
- No extra registrations or sign-ups: your session is created when you log in with your Letterboxd credentials inside the app.
- Credentials are encrypted at rest. Databases and keys live under a single configurable data directory.
- Docker-first deployment: `docker compose up -d` brings everything online, no extra setup required.


## Features
- Share any of your Letterboxd lists with a group via a simple code.
- Two sync modes:
  - Master/Slave: one source list is the single source of truth; others follow it.
  - Collaborative: every member’s changes propagate to all other members.
- Background polling to keep lists in sync.
- List browser: view and refresh your own lists after login.
- Group management UI: share, unshare, trigger manual syncs, inspect last sync.
- Minimal infrastructure: SQLite for persistence and Redis for coordination/queuing.


## How it works (High‑level)
- Frontend is built with Reflex and exported to static files served by Nginx.
- Backend is a Reflex API server (Starlette) running in a separate container.
- The frontend proxies WebSocket/events and API calls to the backend via Nginx.
- Your Letterboxd session is created by logging in from the app. The app then scrapes the same web endpoints you use in your browser to read lists and add/remove films when syncing.
- A `SyncManager` orchestrates groups, members, operations, and auto‑polling.
- Credentials are symmetrically encrypted using per‑deployment keys stored in the data directory.

Key paths and services (compose):
- Frontend (Nginx) exposed on host: `http://127.0.0.1:9300`
- Backend (Reflex API) on the Docker network at `backend:8000` (not exposed to host)
- Redis for background tasks/coordination at `redis://redis`
- Persistent data volume mounted at `./data` (configurable)


## Quickstart (Docker)
Prerequisites: Docker and Docker Compose.

1) Clone the repo
```
git clone https://github.com/your-user/LetterboxdSync.git
cd LetterboxdSync
```

2) Start the stack
```
docker compose up -d --build
```

3) Open the app
- Visit: `http://127.0.0.1:9300`
- Log in with your Letterboxd username/password. The app will create an encrypted session and list your lists.

4) Share and sync
- Go to “Lists” and share one of your lists (this creates a Sync Group and a code).
- Share the code with others so they can join with their own list.
- Switch to the “Sync” page to manage groups, trigger syncs, and see status.

To stop the stack:
```
docker compose down
```

Data location:
- By default, databases and keys are stored in `./data` (bind mounted into the backend container).
- You can change this by setting `DATABASE_PATH` in `compose.yml` or environment.


## Configuration
Environment variables (sensible defaults provided):
- `DATABASE_PATH` (backend): defaults to `./data` in the project root. This directory will contain:
  - `letterboxd_sync.db` (sync data)
  - `letterboxd_users.db` (auth/session data)
  - `sync_key.key`, `auth_key.key` (encryption keys)
- `REDIS_URL`: defaults to `redis://redis` (the `redis` service from compose)

Ports:
- Frontend (Nginx) exposed on `127.0.0.1:9300` → safe local access only.
- Backend is only reachable inside the Docker network. Nginx proxies `/ping`, `/_event` (WebSockets), and `/_upload` to the backend.

Build args / Frontend export:
- The static frontend sets `API_URL` during build (see `web.Dockerfile`). It uses Nginx locations to talk to the backend container, so no extra changes are needed in a local compose setup.


## Development (without Docker)
You can run everything locally for iteration.

1) Python env
- Python 3.12 recommended
- Install tools: `pip install -r requirements.txt`

2) Data path
- Optionally set where to store databases/keys:
```
export DATABASE_PATH="$(pwd)/data"
```

3) Run Reflex backend+frontend (dev)
- In one terminal:
```
reflex run --loglevel debug
```
This runs the development server. Alternatively, to mimic production separation:

4) Run backend only
```
reflex run --backend-only --backend-host 0.0.0.0 --backend-port 8000 --loglevel debug
```

5) Serve the frontend
- For production‑like static hosting, build with:
```
reflex export --frontend-only
```
- Then serve `.web/build/client` with any static server, and proxy `/_event`, `/ping`, `/_upload` to the backend.

Note: The repository includes `web.Dockerfile` which demonstrates a full static export pipeline and an Nginx config (`nginx.conf`) that correctly proxies backend endpoints.


## Usage walkthrough
- Login: Use your Letterboxd credentials inside the app. These are stored encrypted at rest.
- Lists page:
  - Refresh and browse your own lists.
  - Open a list to see details.
  - Share a list to create a Sync Group and invite others with a code.
- Sync page:
  - View all your groups, see member count, mode, last sync.
  - Trigger immediate syncs.
  - Open Manage to adjust members, switch mode, unshare, or leave a group.
- Modes:
  - Master/Slave: Choose a master list; all others mirror its content.
  - Collaborative: Adds/removes from any member propagate to all others.


## Data, Security, and Privacy
- Credentials encryption: A Fernet key stored at `data/sync_key.key` and `data/auth_key.key` is used to encrypt Letterboxd credentials and session data in SQLite.
- Data at rest: All application state lives under `DATABASE_PATH` so you can back it up or wipe it easily.
- Access: By default, the app is only exposed on `127.0.0.1:9300`. If you wish to expose it externally, put it behind your reverse proxy and add TLS.
- Secrets: Treat the data directory as sensitive. Do not commit it to version control.


## Scraping notes and limits
- This project relies on scraping the authenticated web experience to work around missing API features.
- Be mindful of Letterboxd’s terms of service and reasonable request rates.
- The app implements paging and polling, but extremely large lists or very frequent syncs may be slower.


## Project layout
- `LetterboxdSync/` — Reflex app: pages, components, and state management.
- `services/` — domain services, including Letterboxd integration and sync logic.
- `models/` — dataclasses / enums for sync entities.
- `db/` — database manager and centralized `db_config`.
- `LetterboxdScraper/` — lower‑level scraper utilities.
- `sync_manager.py` — high‑level orchestration for groups and syncing.
- `compose.yml`, `Dockerfile`, `web.Dockerfile`, `nginx.conf` — deployment and packaging.


## Troubleshooting
- “Can’t connect to backend”: Ensure `docker compose ps` shows `backend` healthy, and that `frontend` can reach `backend:8000` on the Docker network.
- “Database is locked”: SQLite WAL mode and busy timeouts are enabled, but if you share the same data dir between multiple instances, avoid concurrent writes.
- “Login fails”: Check your credentials; try again later in case of Letterboxd rate limiting or website changes.
- “Sync stuck”: Use the “Sync Now” button in a group to force a cycle; check logs with `docker compose logs -f backend`.


## Roadmap
- More robust anti‑rate‑limit strategies.


## License
This repository currently does not declare a license. If you plan to deploy or modify it publicly, consider adding a LICENSE file (e.g., MIT) or clarify usage terms.