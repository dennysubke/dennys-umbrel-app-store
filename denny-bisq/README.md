# Bisq for Umbrel

Bisq is a decentralized peer-to-peer exchange for buying and selling Bitcoin directly with other people. This Umbrel package runs the complete Bisq 1 desktop application continuously on your server and makes the original graphical interface available through your browser.

##

> [!WARNING]
> **This app supports only `amd64` / `x86_64` systems.** It is not compatible with Raspberry Pi devices or other `arm64` hardware. It is intended for Umbrel Home and other x86-64 Umbrel installations.

> [!IMPORTANT]
> Bisq is a resource-intensive desktop application. The graphical interface, Java runtime, Bitcoin network synchronization, and Tor services run continuously inside the container. Systems with limited available memory may become slow or unresponsive while Bisq is running.


## Features

- Complete Bisq 1 desktop interface in the browser
- Direct peer-to-peer Bitcoin trading
- Integrated Tor connectivity
- Local wallet and trade data storage
- Persistent operation while your computer is turned off
- Access through the Umbrel dashboard
- No directly exposed VNC port
- Optional connection to your own Bitcoin node
- Cryptographic verification of the official Bisq installation package
- Persistent Bisq configuration across app updates

## Architecture support

| Platform | Supported |
|---|---:|
| Umbrel Home | Yes |
| x86-64 mini PC or server | Yes |
| `amd64` / `x86_64` | Yes |
| Raspberry Pi 4 or 5 | No |
| `arm64` / `aarch64` | No |

The Docker image is intentionally built only for `linux/amd64` because the official Bisq 1 Linux release is provided for x86-64 systems.

Installation on ARM64 hardware is not supported. This includes Raspberry Pi devices, even when running a 64-bit operating system.

## Resource requirements

Bisq requires considerably more system resources than a typical Umbrel web application.

The container continuously runs:

- The complete Java-based Bisq desktop application
- A virtual graphical desktop session
- The browser-based remote display
- Tor network services
- Bitcoin network connections
- Local wallet and trading databases

Memory usage can increase while Bisq initializes, connects to Tor, loads market data, processes Bitcoin network information, or handles active trades.

For the best experience:

- Avoid running Bisq on systems with very limited available memory.
- Close or stop other resource-intensive Umbrel apps when necessary.
- Allow several minutes for the interface to become responsive after startup.
- Do not interrupt the container while Bisq is updating its local data.
- Make sure the Umbrel device has sufficient free storage for application data and backups.

The app is therefore better suited to Umbrel Home or a reasonably powerful x86-64 server than to low-memory hardware.

## First start

The first launch can take several minutes while the graphical environment, Bisq database, Bitcoin network connection, and Tor services are initialized.

During this period, the interface may respond slowly or appear temporarily frozen. This does not necessarily mean the app has failed to start.

Bisq opens directly in the browser through the Umbrel dashboard.

Before depositing Bitcoin:

1. Set a strong Bisq wallet password.
2. Write down the wallet seed and store it offline.
3. Create a Bisq application backup.
4. Verify that the backup can be accessed.
5. Keep only the amount required for active trades in the Bisq wallet.

## Updating Bisq

Before installing an update:

1. Finish or carefully review active trades.
2. Create a backup from inside Bisq.
3. Stop the Bisq app cleanly through Umbrel.
4. Back up the persistent Umbrel app data directory.
5. Install the update through the Umbrel dashboard.

Do not uninstall the app before updating, because uninstalling may remove its persistent data.

After Bisq has opened its data with a newer version, do not downgrade to an older version using the same data directory.

## Persistent data

All Bisq data is stored inside the Umbrel app data directory:

```text
${APP_DATA_DIR}/data/Bisq
```

This includes:

- Wallet data
- Wallet seed information
- Payment accounts
- Open and completed trades
- Dispute information
- Bisq settings
- Tor and network data
- Local databases
- Application backups

These files contain sensitive financial information and must never be added to the Git repository, shared publicly, or included in support logs without careful review.

Updating the Docker image does not normally remove this directory.

## Connect your Umbrel Bitcoin node

Bisq can optionally connect to the Bitcoin node running on the same Umbrel device.

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

The connection may take several minutes to become available after restarting.

## Security notice

Bisq includes a hot wallet and manages sensitive trading information locally.

Always:

- Back up the wallet seed and application data before funding the wallet.
- Store the seed independently from the Umbrel device.
- Protect access to the Umbrel dashboard.
- Verify payment details before sending money.
- Review trade information before confirming transactions.
- Install security updates promptly.
- Avoid keeping unnecessary Bitcoin balances in the Bisq wallet.
- Never share wallet files, seeds, passwords, or complete diagnostic archives.

Bisq is non-custodial, but the security of the local wallet and Umbrel server remains the responsibility of the user.

---
