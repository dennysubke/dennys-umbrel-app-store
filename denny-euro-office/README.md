# Euro-Office for Umbrel

This package runs Euro-Office DocumentServer on port `8400`. Euro-Office is an editing engine, not a file manager. It is intended to be connected to Nextcloud or another supported storage platform.

## Requirements

- Umbrel on `amd64` or `arm64`
- At least 4 GB of RAM available to Umbrel is recommended
- Nextcloud 33, 34 or 35 for the included integration instructions
- Several gigabytes of free disk space; the compressed DocumentServer image alone is approximately 2.5 GB

The first start can take several minutes while the image is downloaded and fonts are generated.

## Check the DocumentServer

After installation, open one of these addresses in a browser:

```text
http://umbrel.local:8400/healthcheck
http://<UMBREL-IP>:8400/healthcheck
```

A healthy server returns `true`.

## Connect Nextcloud

1. In Nextcloud, open **Apps** and install or enable **Nextcloud Office** with the app ID `eurooffice`.
2. Open **Administration settings > Nextcloud Office**.
3. Enter the following Document Editing Service address, preferably using the fixed LAN address of the Umbrel machine:

   ```text
   http://<UMBREL-IP>:8400/
   ```

4. Retrieve the JWT secret on the Umbrel host:

   ```bash
   docker inspect denny-euro-office_server_1 --format '{{range .Config.Env}}{{println .}}{{end}}' | sed -n 's/^JWT_SECRET=//p'
   ```

5. Enter that value as the **Secret key** in Nextcloud. Use `AuthorizationJwt` as the JWT header if Nextcloud asks for it.
6. Save the settings. The connection test should turn green.

The DocumentServer URL must be reachable from the browser and Nextcloud. Euro-Office must also be able to reach the Nextcloud URL. If `umbrel.local` does not resolve inside a container, use the Umbrel machine's fixed LAN IP address in the Nextcloud settings.

If Nextcloud displays advanced address fields, use the same reachable LAN URL for internal DocumentServer requests and enter the complete reachable Nextcloud URL as the storage address. If Collabora or ONLYOFFICE currently handles the same file types, disable its Nextcloud connector while testing Euro-Office to avoid competing file actions.

## HTTPS and remote access

For access outside the local network, place both Nextcloud and Euro-Office behind HTTPS and use URLs that are reachable by the browser and both services. Do not expose the DocumentServer directly to the public internet without TLS and an appropriately configured reverse proxy.

When Nextcloud itself is loaded over HTTPS, the browser will normally block an `http://` DocumentServer as mixed content. In that situation Euro-Office must also be served over HTTPS.

Self-signed HTTPS certificates are rejected by default. If a self-signed certificate is unavoidable, change `USE_UNAUTHORIZED_STORAGE` to `"true"` in `docker-compose.yml`, then restart the app. A trusted certificate is preferable.

## Persistent data

The package stores generated secrets and server data in `${APP_DATA_DIR}/data`. Office documents themselves remain in Nextcloud. Runtime logs stay inside the replaceable DocumentServer container.

## Notes

- JWT authentication is enabled and uses Umbrel's unique `APP_SEED`.
- The public example editor and admin panel are disabled.
- Private IP access is enabled because local Nextcloud instances normally use a private LAN address.
- The image is pinned to the tested multi-architecture digest for Euro-Office 9.3.4.
- Euro-Office currently describes its container image as intended for testing and integration. Treat this package as experimental and keep backups of important files.

For troubleshooting, inspect the latest server messages with:

```bash
docker logs --tail 200 denny-euro-office_server_1
```

## Sources

- [Euro-Office](https://github.com/Euro-Office)
- [DocumentServer](https://github.com/Euro-Office/DocumentServer)
- [Nextcloud connector](https://github.com/Euro-Office/eurooffice-nextcloud)
- [Nextcloud App Store](https://apps.nextcloud.com/apps/eurooffice)
