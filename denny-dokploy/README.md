# Dokploy on Umbrel

Dokploy is a self-hosted deployment platform for managing applications, databases, Docker Compose projects, domains, certificates, logs, backups, and automated deployments from a central interface.

## ⚠️ Important security warning

This package mounts the Umbrel host Docker socket into Dokploy:

```text
/var/run/docker.sock
```

This gives Dokploy effective root-level control over the entire Umbrel Docker host. Dokploy can create, modify, stop, or remove other containers and can mount host paths into containers. A compromised Dokploy installation could therefore compromise the complete Umbrel system and the data of other apps.

This package intentionally does not follow the normal Umbrel security model and should only be installed by users who fully understand and accept this risk. It is an experimental Community App Store package and is not supported by the Umbrel or Dokploy teams.

## Ports

| Purpose | Port |
|---|---:|
| Dokploy dashboard through Umbrel App Proxy | `8528` |
| Applications routed through Dokploy Traefik via HTTP | `8529` |
| Applications routed through Dokploy Traefik via HTTPS | `8530` |
| HTTP/3 through Dokploy Traefik | `8530/UDP` |

## Docker Swarm

The `hooks/pre-start` script initializes Docker Swarm only when the Umbrel host is not already part of a Swarm. It then verifies that the local node is a manager and creates the attachable overlay network `dokploy-network` when it does not already exist.

Docker Swarm remains enabled on the Umbrel host after Dokploy is stopped or uninstalled.

## Domains and certificates

Dokploy normally expects its Traefik instance to receive public traffic on ports `80` and `443`. Umbrel already uses those ports, so this package publishes Dokploy Traefik on ports `8529` and `8530`.

For public domains and automatic HTTP-challenge certificates, the router or an upstream reverse proxy must forward:

```text
External TCP 80  -> Umbrel TCP 8529
External TCP 443 -> Umbrel TCP 8530
External UDP 443 -> Umbrel UDP 8530
```

Without this forwarding, the Dokploy dashboard can still be used locally, but public routing and automatic certificate issuance may not work as expected.

## Updates

Do not use Dokploy's built-in self-update function. This package runs the Dokploy dashboard as an Umbrel Compose container rather than as the upstream `dokploy` Swarm service, so the upstream update mechanism cannot safely replace it.

Update Dokploy by changing the image, version, release notes, and image digest in the Umbrel app package.

## Existing installations

Older versions of this package used the fixed PostgreSQL password
`supersecurepass`. The one-shot `postgres-password-migration` service first
tests the current `${APP_SEED}` password and, when necessary, changes the
existing `dokploy` database role from the legacy password to `${APP_SEED}`.

The migration service does not delete or recreate the database.

## Data

Persistent data is stored below the Umbrel app data directory:

```text
data/docker
data/etc
data/postgres
data/redis
```

## Removal

Uninstalling the Umbrel app does not automatically disable Docker Swarm or remove `dokploy-network`. Only remove them manually when no other Swarm services or applications depend on them:

```bash
docker network rm dokploy-network
docker swarm leave --force
```

Do not run these cleanup commands while Dokploy-managed services are still required.
