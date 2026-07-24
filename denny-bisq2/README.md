# Bisq 2 Node for Umbrel

<p align="center">
  <img src="https://raw.githubusercontent.com/dennysubke/dennys-umbrel-app-gallery/master/denny-bisq2/logo.png" alt="Bisq logo" width="100">
</p>

Bisq 2 Node is a self-hosted backend for the **Bisq Connect** mobile app. It runs continuously on Umbrel, communicates with the Bisq peer-to-peer network through its bundled Tor service, and exposes a small local dashboard for status information and mobile pairing.

## Important distinction

This package is **not** the complete Bisq 2 desktop application in a browser. The Umbrel dashboard displays the node status, Tor information, software version, pairing QR code, and pairing secret. Trading and communication are handled in the Bisq Connect mobile app.

## Supported architectures

The package uses the official digest-pinned Bisq container images and supports:

- `linux/amd64`
- `linux/arm64`

No architecture-specific setting is required in the Compose file.

## Pairing Bisq Connect

1. Install and start **Bisq 2 Node** on Umbrel.
2. Wait until Tor has finished bootstrapping and the node reports that it is running.
3. Open the Bisq 2 Node dashboard from the Umbrel home screen.
4. In Bisq Connect, open the trusted-node setup and scan the displayed QR code.
5. Confirm that the mobile app connects to the onion address of your Umbrel-hosted node.

The first startup may take a few minutes while Tor creates and publishes the onion service.

## Security warning

The pairing QR code and the text pairing code grant control of the Bisq 2 node. Treat them like a password.

- Keep Umbrel authentication enabled for this app.
- Do not set `PROXY_AUTH_ADD: "false"` in `docker-compose.yml`.
- Do not publish port `8091` directly on the host.
- Do not expose the dashboard through an unauthenticated reverse proxy.
- Pair only devices you control.

The mobile connection uses the node's Tor onion service. The local browser dashboard is reached exclusively through Umbrel's authenticated app proxy.

## Persistent data

All persistent node data is stored under:

```text
${APP_DATA_DIR}/data
```

Umbrel backups of the app data directory therefore include the node identity and configuration. Back up the app before deleting or reinstalling it when the existing node identity should be retained.

## Container images

```text
ghcr.io/bisq-network/bisq2-api@sha256:af77443abc90114b0282d44a1fa5b5f3beeb608b6df76d8674f4366236856154
ghcr.io/bisq-network/bisq2-api-web-ui@sha256:0295d45b6dafb3d9bf0d2e6ba74caeb42222e00eb30d9fa847a136a0f358aa23
```

The `web` service shares the network namespace of the `server` service. This allows the dashboard to access the Bisq API bound to loopback without exposing the API directly.

## Resources

- Bisq website: https://bisq.network/
- Umbrel packaging: https://github.com/bisq-network/bisq2-umbrel
- Bisq 2 source: https://github.com/bisq-network/bisq2
- Bisq Connect source: https://github.com/bisq-network/bisq-mobile
