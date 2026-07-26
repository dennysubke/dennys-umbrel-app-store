# Pages for Umbrel

Pages turns your Umbrel into a polished, private home for static websites. It combines an Umbrel-style dashboard with starter templates, a browser-based file manager and editor, ZIP imports and exports, live previews, local statistics, restorable backups, custom domains, and first-class Onion sharing.

## What Pages can host

Pages serves completed static website files such as:

- HTML
- CSS
- JavaScript
- JSON and XML
- Images and SVG files
- Fonts
- Audio and video files
- WebAssembly files
- Nostr NIP-05 verification files

Pages does not execute uploaded PHP, Node.js, Python, shell scripts, databases, or other server-side applications.

## Sign in

The Pages dashboard uses the automatically generated Umbrel app password. Public websites are not placed behind the Umbrel dashboard login.

## Local and Onion URLs

Every website receives a unique path such as:

```text
http://umbrel.local:8377/p/my-website/
```

Pages also reads the Onion address supplied by Umbrel and combines it with the same website path:

```text
http://<pages-hidden-service>.onion/p/my-website/
```

All websites share the Pages Hidden Service and remain separated by their unique paths. Pages does not generate a separate Onion key for every website.

The **Sharing** tab shows the available local, Onion, and custom-domain addresses. Each address can be opened, copied, or displayed as a QR code. QR codes are generated locally inside the Pages container; the URL is not sent to an external QR service.

## Onion availability

A valid Umbrel Hidden Service is detected automatically. If Umbrel has not supplied a usable address, Pages shows the Tor entry as unavailable instead of presenting a broken placeholder link. Restart Pages after changing the Tor availability so it receives the current environment value.

## Custom domains

A custom domain requires a reverse proxy such as NPMplus, Nginx Proxy Manager, Pangolin, or another proxy that can forward traffic to the Pages app port.

1. Forward the domain to the Umbrel address on port `8377`.
2. Preserve the original `Host` header.
3. Add the hostname in the website's **Sharing** tab inside Pages.

Pages reads the incoming host header and serves the matching website automatically.

## Persistent data

All files and settings are stored below:

```text
${APP_DATA_DIR}/data
```

Umbrel backups of the app data directory therefore include the Pages database, all hosted websites, and local Pages backups.

## Upload limits

The default maximum size for a single file or ZIP upload is 100 MB. Extracted ZIP contents are limited to 500 MB. Unsafe archive paths and symbolic links are rejected. These limits can be changed through `MAX_UPLOAD_BYTES` and `MAX_EXTRACTED_BYTES` in `docker-compose.yml`.
