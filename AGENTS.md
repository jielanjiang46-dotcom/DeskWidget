# DeskWidget Repository Rules

## Scope safety

- These instructions apply only to this repository (`D:\DeskWidget`).
- Never modify, stage, commit, or push any other project or repository, especially the separate Django/website project.
- Never commit secrets, `.env` files, credentials, virtual environments, caches, build outputs, runtime state (`settings.json`, `widgets.json`, `plans.json`), or user-provided files under `assets/`.

## Git workflow after each user-requested logical task

1. Finish the complete logical task; do not commit after every individual file edit.
2. Run the relevant tests or checks available for the changed code. For Python changes, at minimum run an appropriate syntax/import check when no focused test suite exists.
3. Run `git status --short --branch` and inspect the diff.
4. Stage only files that belong to the current user-requested task, using explicit paths. Never use `git add .`, `git add -A`, or `git add --all`.
5. If tests or checks fail, do not commit or push; report the failure.
6. Create one short, descriptive commit message for the logical task.
7. Push the current branch with `git push origin HEAD`.
8. Report the checks run, committed files, commit message, branch, and push result.

## Guardrails

- Do not include unrelated pre-existing changes in a commit.
- Do not amend, force-push, rewrite history, delete branches, or change remotes unless the user explicitly asks.
- Before every push, confirm that the repository root is `D:\DeskWidget` and the remote belongs to this DeskWidget repository.
- If authentication, tests, repository identity, or file scope is uncertain, stop before committing or pushing and explain what needs attention.
