# Coolify for Umbrel

This package runs Coolify with its own isolated Docker daemon. Coolify does not receive access to Umbrel's Docker socket and cannot manage Umbrel's application containers.

## Ports

| Port | Purpose |
|---:|---|
| `8527` | Coolify dashboard through Umbrel App Proxy |
| `6001` | Realtime events and deployment updates |
| `6002` | Browser terminal WebSocket |
| `8531` | HTTP entry point for applications deployed by Coolify |
| `8532` | HTTPS and HTTP/3 entry point for applications deployed by Coolify |

For public applications, forward the required external ports to `8531` and `8532`, or use an external reverse proxy that targets these ports.

## Architecture

Coolify connects by SSH to the bundled `coolify-testing-host`. Its Docker CLI uses a Unix socket belonging only to the bundled `coolify-docker` daemon. Database, cache, and realtime services use app-specific DNS names to prevent collisions with other Umbrel apps. Persistent state is stored below `${APP_DATA_DIR}/data/`.

The Docker-in-Docker service needs privileged mode because it runs a complete Docker daemon. This is intentionally isolated from Umbrel's own Docker daemon.

## Permissions

No manual `chmod` or `chown` command is required. A one-shot initialization service creates Coolify's required directories and assigns them to Coolify's runtime UID `9999` before the dashboard and realtime containers start.

## First start

Open Coolify from the Umbrel dashboard and create the initial administrator account. The local server created during onboarding points to the isolated deployment environment supplied by this package.
