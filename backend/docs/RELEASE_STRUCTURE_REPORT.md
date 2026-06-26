# Phase VI — Release Structure Report

## Release Directory

```
release/
├── RELEASE_NOTES.md      — v0.1.0 release notes (overview, features, arch, limitations, non-goals)
├── CHANGELOG.md          — Full chronological changelog (Phases A–VI)
├── QUICK_START.md         — 5-step quick start (prerequisites → setup → start → verify → seed → stop)
├── DEPLOYMENT_GUIDE.md    — Production deployment (env vars, DB, Redis, Celery, Feishu, HTTPS, monitoring)
├── DEMO_SCRIPT.md         — Demo walkthrough for presenters (5 steps with expected results)
├── LICENSE.md             — MIT license placeholder
└── cpis-v1-local-demo.tar.gz — 776K release package
```

## Startup Scripts

```
scripts/
├── start_backend.sh   — postgres + redis + backend API
├── start_frontend.sh  — frontend service
├── start_worker.sh    — celery worker
├── start_demo.sh      — one-click start all + seed
└── stop_demo.sh       — stop all, preserve volumes
```

## Docker Compose

| File | Services | Ports |
|------|----------|-------|
| `docker-compose.yml` | postgres, redis, backend, celery-worker, frontend, migrate | 8000 (API), 80 (frontend) |
| `docker-compose.demo.yml` | postgres, redis, backend, celery-worker, frontend | 8000 (API), 8080 (frontend) |

## .env.example
Enhanced with Phase V collector feature flags, LLM_PROVIDER=stub default.
41 lines → now includes 6 collector toggles (all false).

## README.md
Rewritten: comprehensive project README with architecture, features, quick start, demo, tech stack, project structure.
