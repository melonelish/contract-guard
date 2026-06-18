# Changelog

## Phase 0 - 2026-06-18

### Added

- Set up the `backend/` FastAPI service skeleton with authentication, contract list/detail endpoints, health checks, and a baseline error model.
- Added the initial Alembic migration, SQLAlchemy models, and test cases to complete the minimum backend loop for Phase 0.
- Built the `frontend/` React + TypeScript + Ant Design workspace with login, contract list, and contract detail pages.
- Added frontend state stores and an API client layer to prepare for later integration with the real review pipeline.
- Added development Dockerfiles, frontend/backend local integration config, `Makefile`, and sample environment variables to reduce local startup cost.
- Added multiple technical and implementation-spec documents, including API contracts, error handling, testing fixtures, page state flows, and preview drafts.

### Updated

- Revised `00-README.md`, `04-technical/`, and `08-impl-spec/` documents so the Phase 0 implementation stays aligned with the design docs.
- Added repository-level governance entry points in `AGENTS.md` and `CLAUDE.md` to standardize agent reading order and execution boundaries.
- Updated `.gitignore` to exclude logs, frontend build artifacts, dependency directories, test cache files, and temporary PDFs from commits.

### Notes

- This Phase 0 release focuses on landing the development skeleton, initial API surface, and document contracts.
- Phase 1 can build on this baseline to connect real uploads, orchestration, and review-report generation.
