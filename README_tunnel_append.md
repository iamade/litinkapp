---

## Mac Tunnel Mode (VPS Services)

This lets you run local code that connects to VPS staging or dev services via SSH tunnel — so you see PSQ's live test data without needing Render access.

### First-Time Setup

```bash
cd ~/My_app_projects/People-Protocol-apps/litinkapp
chmod +x scripts/*.sh
```

### Using Staging (PSQ's test data)

**Terminal 1** — keep this running:
```bash
bash scripts/tunnel-staging.sh
```

**Terminal 2**:
```bash
bash scripts/start-staging.sh
```

Open: http://localhost:5173

### Using Dev

**Terminal 1**:
```bash
bash scripts/tunnel-dev.sh
```

**Terminal 2**:
```bash
bash scripts/start-dev.sh
```

### Stopping

```bash
# Kill tunnels
pkill -f 'ssh -N.*72.62.97.111'

# Stop containers
docker compose -f backend/local.yml down
```

### Scripts

| File | Purpose |
|------|---------|
| `scripts/tunnel-staging.sh` | SSH tunnel to VPS staging services |
| `scripts/tunnel-dev.sh` | SSH tunnel to VPS dev services |
| `scripts/start-staging.sh` | Start staging environment |
| `scripts/start-dev.sh` | Start dev environment |
| `scripts/env.staging` | Staging env vars |
| `scripts/env.dev` | Dev env vars |
| `backend/local-tunnel.yml` | Docker override (uses tunneled services) |