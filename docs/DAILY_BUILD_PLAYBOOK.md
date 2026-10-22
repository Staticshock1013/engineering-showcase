# Daily Build Playbook

Rules for the scheduled daily build. Each run ships **one** roadmap milestone (or a clearly scoped part of
one) to `main`. Small, honest, working increments beat large, flashy, broken ones.

## Daily loop

1. **Orient.** Read `ROADMAP.md`, the latest entries in `PROGRESS.md`, and the current project's README.
   Pick the first unchecked milestone of the first incomplete project.
2. **Research (short).** Spend a few minutes looking at how real teams solve this problem (e.g. how
   ITIL help desks model ticket states and SLAs, how uptime monitors define incidents, how SOC teams
   triage failed-login alerts). Apply what you learn; note one concrete takeaway in the progress log.
3. **Build.** Implement the milestone in the project's folder. Follow existing conventions in that folder.
4. **Verify.** Run lint, typecheck, tests, and build for the project. Everything must pass before pushing.
   If a milestone is too big to finish green, ship a smaller green slice and leave the rest unchecked.
5. **Document.** Update the project README (architecture, how to run, how to test) as features land.
6. **Record.** Check off the milestone in `ROADMAP.md`, update the status column in the root `README.md`
   (and link the project name to its folder once the folder exists),
   and add a dated entry at the top of `PROGRESS.md` (what shipped, how verified, research takeaway, next step).
7. **Commit and push to `main`.** Use small, descriptive conventional commits (`feat(service-desk): ...`,
   `test(...)`, `docs(...)`). Several focused commits per day is better than one large commit.

## Quality bar (every flagship project)

- **Runs for real.** A working live demo or a reproducible setup, ideally one command (`make dev`,
  `docker compose up`, or `npm run dev`). No buttons or links that do nothing.
- **README** explaining the problem, who has it, the architecture (with a Mermaid diagram), the
  technologies and why they were chosen, and how to run and test it.
- **Automated tests** that cover real behavior (validation, state transitions, error paths), wired
  into GitHub Actions CI under `.github/workflows/`.
- **Technical challenges solved** section in the README, written from what actually happened.
- **Demo video:** the author records this personally. Add a `DEMO_SCRIPT.md` with a 60–90 second shot list
  and a clearly marked `<!-- DEMO VIDEO: to be recorded by the author -->` placeholder in the README.
  Never embed or link a video that does not exist.
- **Honesty:** no API keys or secrets in code (use `.env.example` with dummy values); no fabricated
  users, testimonials, stars, or production metrics. Demo data is fictional and labeled
  `Fictional demo data` in the seed files and UI.
- **Accessible and responsive** frontends: semantic HTML, keyboard navigation, visible focus, sufficient
  contrast, automated axe checks.

## Language guidance

- Python is the core backend and tooling language (FastAPI, pytest, ruff, mypy).
- TypeScript + React for frontends (Vite, Vitest, Testing Library, ESLint).
- C++ (C++17/20, CMake, GoogleTest) only where it genuinely fits: performance-sensitive components such
  as the system-metrics probe in the Cloud Infrastructure Monitor and the streaming log parser in the
  Security Operations Lab. Do not add C++ for its own sake.

## Repo layout

```
projects/
  01-portfolio-site/
  02-it-service-desk/
    backend/    # FastAPI + SQLAlchemy + Alembic
    frontend/   # React + TypeScript
  03-cloud-infra-monitor/
  04-security-ops-lab/
  05-qa-automation-suite/
docs/
.github/workflows/   # one CI workflow per project, path-filtered
```

## Things the agent must not do

- Push failing builds or skip tests to make CI pass.
- Rewrite history on `main` or force-push.
- Start a new project before the current one is complete.
- Commit secrets, real personal data, or large binaries.
- Claim features, results, or metrics in docs that the code does not support.
