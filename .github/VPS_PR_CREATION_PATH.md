# VPS Authenticated PR-Creation Path

## Overview

The VPS openclaw service can create PRs on GitHub repositories using the `gh` CLI
with credentials stored in the git credential store. No tokens are embedded in
repo URLs or config files.

## Components

### gh CLI
- **Binary:** `/home/openclaw/.local/bin/gh` (v2.74.0)
- **Auth:** Stored at `/home/openclaw/.config/gh/hosts.yml`
- **Account:** `iamade` (GitHub PAT-based, scope: repo)

### Git Credential Helper
- **Helper:** `!/home/openclaw/.local/bin/gh auth git-credential`
- **Store:** `credential.helper=store` + `.git-credentials` fallback
- **Config:** `~/.gitconfig` global scope

### Repo Origin (normalized)
- **URL:** `https://github.com/iamade/litinkapp.git` (no embedded tokens)
- **Fetch/Push:** Use credential helper for auth

## Creating a PR from VPS

```bash
cd /opt/openclaw/repos/litinkapp
git checkout -b fix/KAN-xxx-description
# ... make changes, commit ...
git push origin fix/KAN-xxx-description
gh pr create --title "fix(KAN-xxx): description" --body "PR body" --base main
```

## Security Notes

- **Never** embed PAT tokens in git remote URLs
- **Never** print token values in logs, Discord, or agent output
- The `.git-credentials` file at `~/.git-credentials` contains hashed auth — treat as secret
- If gh auth expires, re-authenticate with `gh auth login` (interactive) or provision via env var `GH_TOKEN`
- Refer to credentials by env var name only (e.g. `${GH_ALL_REPO_PAT}`, `${LITINKAPP_GH_PAT}`)

## KAN Code/Review Ownership

PR creation from VPS is an **infra convenience path only**. Code review, approval,
and merge authority for litinkapp KAN tickets remains with LC/COS/PSQ. The VPS
path exists to unblock CI/CD when the Mac path is unavailable.

## Maintenance

- gh binary lives at `/home/openclaw/.local/bin/gh` — durable across reboots
- `/tmp/gh_2.74.0_linux_amd64/` is the original temp extraction; can be cleaned
- If gh is upgraded, update the credential helper path in `~/.gitconfig`

---

Documented: 2026-07-12 by Amara (VPS Ops)
Per: KAN-416 Codex Dispatch correction
