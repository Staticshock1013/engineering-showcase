# Roadmap

Projects are built in order. Each milestone is sized for one day of focused work and must leave the
project in a working, tested state. Check items off (`[x]`) as they land on `main`.

A project is **Complete** when every milestone is checked and it meets the standards in the
[README](README.md#standards-every-project-meets). Only then does work move to the next project.

---

## 1. Developer Portfolio Website — `projects/01-portfolio-site`

React + TypeScript + Vite + Tailwind CSS, deployable to Vercel as a static site.

- [ ] Scaffold Vite + React + TypeScript + Tailwind, ESLint, Prettier, Vitest; CI job for lint, typecheck, test, build
- [ ] Layout shell: header, nav, footer, dark/light theme, responsive breakpoints, skip-to-content link
- [ ] Hero + About sections driven by a typed content file (no hardcoded copy in components)
- [ ] Projects section: cards generated from a typed project list; links to this repo's project folders and to Career Intelligence OS
- [ ] Project case-study pages (problem, architecture diagram, stack, challenges) with client-side routing
- [ ] Skills + experience timeline; resume download link (placeholder file clearly marked until the author adds a real resume)
- [ ] Contact section using a `mailto:` link or a documented form service (no fake submit button)
- [ ] Accessibility pass (axe checks in tests, keyboard nav, color contrast) and Lighthouse budget documented
- [ ] SEO metadata, Open Graph image, sitemap; Vercel config + deploy instructions
- [ ] README polish, technical challenges section, demo video script

## 2. IT Service Desk Simulator — `projects/02-it-service-desk`

React + TypeScript frontend, FastAPI backend, SQLite (SQLAlchemy + Alembic) for local dev.

- [ ] Backend scaffold: FastAPI app, settings via env vars, SQLAlchemy models, Alembic migration, pytest setup, CI job
- [ ] Ticket model + CRUD API: title, description, requester, category, priority (P1–P4), status workflow (New → Triaged → In Progress → Waiting on User → Resolved → Closed) with validated transitions
- [ ] Technicians: model, assignment endpoint, workload counts, validation for invalid assignments
- [ ] Troubleshooting notes: append-only activity log per ticket (note, status change, assignment) with timestamps
- [ ] SLA timers: response/resolution targets per priority, breach detection computed server-side, tested with frozen time
- [ ] Search + filtering: full-text on title/description, filter by status/priority/technician/category, pagination
- [ ] Knowledge base: articles CRUD, tagging, search, link articles to tickets
- [ ] Seed script with clearly labeled fictional demo data (`demo_data.py`, every record marked fictional)
- [ ] Frontend scaffold: Vite + React + TypeScript, typed API client, React Query, routing, Vitest + Testing Library
- [ ] Ticket queue dashboard: sortable/filterable table, priority + SLA badges, responsive layout
- [ ] Ticket detail page: edit fields, status transitions, assign technician, add notes, activity timeline
- [ ] New ticket form with client + server validation and accessible error messages
- [ ] Knowledge base UI: browse, search, view, attach article to ticket
- [ ] Error handling end to end: API error schema, toast/alert UI, empty and loading states
- [ ] Accessibility + responsive pass (axe tests, keyboard-only flow, mobile layout)
- [ ] One-command local run (Docker Compose or Makefile), README with architecture diagram, API docs link, challenges section, demo video script

## 3. Cloud Infrastructure Monitor — `projects/03-cloud-infra-monitor`

Python + FastAPI service with a small C++ health-check probe where raw speed and low overhead matter.

- [ ] FastAPI backend + SQLite storage for targets, checks, and incidents; CI job
- [ ] HTTP/TCP health checks with timeouts and retries (Python, asyncio)
- [ ] C++ probe: lightweight CLI that samples CPU/memory/disk on Linux (`/proc`) and emits JSON; CMake build + GoogleTest; Python ingests its output
- [ ] Alert rules (thresholds, consecutive failures) and incident open/close lifecycle
- [ ] Status dashboard with uptime and latency charts
- [ ] Dockerfile + Compose; documented deploy to a small cloud VM (AWS free tier); README + challenges + demo script

## 4. Security Operations Lab — `projects/04-security-ops-lab`

Python analysis tooling plus a C++ log parser for high-volume input.

- [ ] Synthetic log generator (auth, SSH, web access) — output clearly labeled synthetic
- [ ] C++ streaming log parser (CMake, tests) that normalizes raw lines to JSON; Python fallback parser with matching tests
- [ ] Detections: brute-force failed logins, impossible travel, off-hours admin activity, port-scan patterns
- [ ] Alert triage CLI/report and event timeline builder
- [ ] Written incident report template + one worked investigation using the synthetic data
- [ ] README, MITRE ATT&CK mapping table, challenges, demo script

## 5. QA Automation Testing Suite — `projects/05-qa-automation-suite`

Playwright + TypeScript tests against the IT Service Desk Simulator (and Career Intelligence OS if it is publicly reachable).

- [ ] Playwright setup, page objects, CI job that boots the service desk app and runs tests
- [ ] End-to-end flows: create ticket, triage, assign, resolve, search KB
- [ ] API contract tests against the FastAPI OpenAPI schema
- [ ] Broken-link and accessibility scans
- [ ] Visual regression baselines and HTML test report published as a CI artifact
- [ ] README, test strategy doc, challenges, demo script
