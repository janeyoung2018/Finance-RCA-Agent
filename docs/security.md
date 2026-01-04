# Security & Hardening Guide

Basic safeguards are available to protect the RCA API from unauthenticated access and overload. Configure these environment variables before starting the API.

## API authentication
- Set `API_KEY` to enable a shared secret on all endpoints except `/health`.
- Clients must send `X-API-Key: $API_KEY` on every request (health checks remain open for liveness probes).

## Request throttling
- `RATE_LIMIT_REQUESTS` (default `60`) and `RATE_LIMIT_WINDOW_SECONDS` (default `60`) apply a per-client in-memory rate limit.
- Exceeding the limit returns `429` with a short error message.
- Lower the values for tighter control or raise them for trusted environments.

## Backpressure and concurrency
- `MAX_CONCURRENT_RUNS` caps simultaneous RCA executions (default `2`).
- `MAX_QUEUED_RUNS` caps queued + running jobs (default `10`); additional requests receive `429` until capacity frees up.
- Health endpoint stays available even when the queue is full.

## Operational tips
- Rotate `API_KEY` via environment updates and process restarts; no key storage is persisted.
- When rate limits or queue limits trigger, clients should back off and retry with jitter.
- For production needs (RBAC, tenant isolation, persistent quotas), plan to front the API with an API gateway or identity provider and move limits into a shared store (Redis/Redis-Stack) for multi-instance deployments.
