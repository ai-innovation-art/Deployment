# QuickBite

The demo product for the Kubernetes deep-dive labs (`labs/k8s-deep/`).

| Service | Image | Role |
|---|---|---|
| web | `kumawatsunil/quickbite-web:1.0` | nginx UI, proxies `/api/*` |
| menu-api | `kumawatsunil/quickbite-menu-api:1.0 / 1.1 / 1.2-broken` | menu, Redis cache, shows pod + node |
| orders-api | `kumawatsunil/quickbite-orders-api:1.0` | orders in Postgres, events to Redis; `python -m app.migrate` = db-migrate |
| notifier | `kumawatsunil/quickbite-notifier:1.0` | worker, consumes `orders:events` |
| daily-report | `kumawatsunil/quickbite-daily-report:1.0` | batch sales report (CronJob) |
| postgres / redis | `postgres:16-alpine` / `redis:7-alpine` | data stores |

## Commands (run inside `labs/quickbite`)

```bash
make push       # once: build all images + push to Docker Hub (docker login first)
make resume     # every session: cluster + full app (works on new or restarted Codespaces)
make cluster    # empty 3-node cluster (Chapter 1 start)
make status     # nodes + pods with their node
make reset      # wipe the app and redeploy
make compose-up # same app on plain Docker
```
