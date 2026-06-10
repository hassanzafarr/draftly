---
name: lint
description: Run all lint/format checks (ruff, eslint, prettier) and auto-fix what's fixable before pushing. Use when the user says "/lint", "run lint", "fix lint errors", "check before push", or before pushing to main.
---

# Lint & Fix

Run the same checks as the git pre-push hook (`.pre-commit-config.yaml`), but with auto-fix enabled so the push will pass.

## Steps

1. **Auto-fix backend** (from repo root):
   ```powershell
   x:\draftly\backend\.venv\Scripts\python.exe -m ruff check backend --fix
   x:\draftly\backend\.venv\Scripts\python.exe -m ruff format backend
   ```

2. **Auto-fix frontend**:
   ```powershell
   npm --prefix x:\draftly\frontend run lint -- --fix
   npm --prefix x:\draftly\frontend run format
   ```

3. **Verify everything passes** (same command the pre-push hook runs):
   ```powershell
   x:\draftly\backend\.venv\Scripts\pre-commit.exe run --all-files --hook-stage pre-push
   ```

4. **Manual fixes**: anything still failing after step 3 is not auto-fixable (e.g. `react/no-unescaped-entities` — replace straight quotes in JSX text with `&ldquo;`/`&rdquo;`/`&apos;` or Unicode curly quotes). Read the file, fix each reported line, re-run step 3 until green.

5. Report: list files changed by auto-fix, and any manual fixes applied. If everything was already clean, say so.

## Notes

- The pre-push hook blocks `git push` if any of these fail — running this skill first guarantees the push goes through.
- Do NOT use `--no-verify` to bypass the hook.
- Ruff version is pinned in `backend/requirements-dev.txt` and must match `rev:` in `.pre-commit-config.yaml`.
