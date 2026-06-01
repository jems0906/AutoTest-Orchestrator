# Branch Protection Recommendations

Use this checklist when configuring branch protection for your default branch (for example, `main`).

## Required status checks

Configure these GitHub Actions jobs as required checks:

- `Backend Tests`
- `Security RBAC Tests`
- `DB Migration Check`
- `Schema Drift Check`
- `Migration File Guard`
- `API Contract Smoke Test`
- `Frontend Static Smoke Test`
- `Container Compose Smoke Test`

These check names match the `name:` fields in `.github/workflows/ci.yml`.

## Recommended protection settings

- Require a pull request before merging
- Require approvals: at least 1
- Dismiss stale approvals when new commits are pushed
- Require conversation resolution before merging
- Require status checks to pass before merging
- Require branches to be up to date before merging
- Restrict who can push to matching branches (optional, team policy)
- Include administrators (recommended)
- Do not allow force pushes
- Do not allow deletions

## Notes

- If you rename workflow jobs, update required check names in branch protection settings.
- If you split workflows, keep required checks focused on backend tests, API contracts, and frontend smoke checks.
