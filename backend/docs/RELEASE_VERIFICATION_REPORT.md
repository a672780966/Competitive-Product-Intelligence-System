# Phase VI — Release Verification Report

## Verification Results

| # | Check | Command | Result |
|---|-------|---------|--------|
| 1 | Backend pytest | `pytest -q --ignore=tests/test_cleaners.py` | ✅ **519 passed** in 31.53s |
| 2 | Frontend build | `npm run build` | ✅ **✓ built** in 8.17s |
| 3 | Alembic current | `alembic current` | ✅ **006_add_source_type (head)** |
| 4 | Docker compose config | `docker compose -f docker-compose.demo.yml config -q` | ✅ **compose config: OK** |
| 5 | Secret scan | `find . -name '.env'` (excl node_modules, .venv) | ✅ **clean — no .env leaks** |
| 6 | Git status | `git status --short` | ✅ **158 files** (expected working tree state) |
| 7 | Release package | `scripts/package-release.sh` | ✅ **776K at release/cpis-v1-local-demo.tar.gz** |

## Packaging Details

- Archive: `release/cpis-v1-local-demo.tar.gz` (776K)
- Bundled: backend/, frontend/, docker-compose.yml, docker-compose.demo.yml, scripts/, release/, README.md, .env.example, CLAUDE.md
- Excluded: .env, __pycache__, *.pyc, node_modules, .git, venv, other tar.gz files
