# Bisq for Umbrel

> [!WARNING]
> **This app currently supports only `amd64` / `x86_64` systems.** It is not compatible with Raspberry Pi devices or other `arm64` systems. It is intended for Umbrel Home and other x86-64 Umbrel installations.

Bisq is a decentralized peer-to-peer exchange for buying and selling Bitcoin directly with other people. This Umbrel package runs the complete Bisq desktop application continuously on your server and makes the original interface available in your browser.

## Features

- Full Bisq 1 desktop interface in the browser
- Direct peer-to-peer Bitcoin trading
- Integrated Tor connectivity
- Local wallet and trade data storage
- Persistent operation while your computer is turned off
- Access through the Umbrel dashboard
- No directly exposed VNC port
- Optional connection to your own Bitcoin node

## System requirements

| Requirement | Supported |
|---|---:|
| Umbrel Home | Yes |
| x86-64 mini PC or server | Yes |
| `amd64` / `x86_64` | Yes |
| Raspberry Pi 4 or 5 | No |
| `arm64` / `aarch64` | No |

The Docker image is intentionally built only for `linux/amd64`. Installation on ARM64 hardware is not supported at this time.

## First start

The first launch can take several minutes while the graphical session and Tor connection are initialized. Bisq then opens directly in the browser through the Umbrel dashboard.

Before depositing Bitcoin:

1. Set a Bisq wallet password.
2. Write down the wallet seed offline.
3. Create a Bisq backup.
4. Keep only the amount required for active trades in the Bisq wallet.

## Persistent data

All Bisq data is stored inside the Umbrel app data directory:

```text
${APP_DATA_DIR}/data/Bisq
```

This includes the wallet, payment accounts, trade history, settings, and backups. These files must never be added to the Git repository.

## Connect your Umbrel Bitcoin node

1. Open the **Bitcoin Node** app on Umbrel.
2. Open its connection details.
3. Copy the Bitcoin P2P Tor address including port `8333`.
4. Open Bisq.
5. Go to **Settings → Network Info**.
6. Enable **Use custom Bitcoin Core nodes**.
7. Enter the address in this format:

```text
exampleaddress.onion:8333
```

8. Keep Tor enabled for the Bitcoin network.
9. Restart Bisq when prompted.

## Security notice

Bisq includes a hot wallet. Back up the seed and application data before funding it. Carefully verify payment details and trade information before confirming transactions.

---
