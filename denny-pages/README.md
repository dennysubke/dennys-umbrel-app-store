# Pages

Pages is a lightweight static website host designed for Umbrel. It combines a polished control panel, an integrated template library, browser-based editing, local backups, and flexible publishing over the local network, custom domains, Tor, or a completely independent Onion v3 address for each website.

<p align="center">
  <img src="https://raw.githubusercontent.com/dennysubke/pages/master/public/banner.png" alt="Pages Banner">
</p>

## Features

- Multiple independently managed static websites
- Overview dashboard with published sites, drafts, visits, storage, backups, and Tor status
- Dedicated **Sites**, **Templates**, and **Settings** sections
- Nine professionally designed, responsive templates
- Searchable template library with categories and full live previews
- One-click site creation from any template
- Draft and published workflows
- Browser-based file manager and code editor
- File, folder, and hardened ZIP uploads
- ZIP export and restorable local website backups
- Live website previews
- Automatic local-network and Umbrel Onion addresses
- Optional independent Onion v3 identity for every website
- Persistent per-site Onion keys with generate, disable, enable, and regenerate controls
- Dedicated sharing view with open, copy, and locally generated QR-code actions
- Custom domain routing through the HTTP `Host` header
- Optional SPA fallback, CORS, directory listings, and cache policies
- Local page-view counters
- Built-in password authentication
- SQLite configuration database
- No external database container, remote template assets, or Docker socket access
- Multiarch support for `amd64` and `arm64`

## Template library

Every starter is plain, editable HTML and CSS stored inside the Pages image. The templates do not load remote fonts, analytics, stock images, scripts, or other third-party resources.

| Template | Category | Purpose |
|---|---|---|
| **Noir Portfolio** | Personal | Bold portfolio for designers, developers, and makers |
| **Orbit Launch** | Business | Product landing page with features, proof, and calls to action |
| **Aura Links** | Personal | Refined link-in-bio profile and project hub |
| **Northstar Docs** | Developer | Responsive documentation with navigation and code examples |
| **Paper Journal** | Content | Editorial personal blog with featured stories |
| **Atelier Studio** | Business | Sophisticated agency or small-business website |
| **Afterglow** | Business | Focused coming-soon and launch page |
| **Purple Nostr** | Nostr | Nostr profile with a prepared NIP-05 file and CORS support |
| **Blank Canvas** | Developer | Clean semantic HTML foundation and lightweight design system |

A template can be previewed in the library before it is used. Creating a site copies the complete starter into that site's private data directory, where every file can be edited, replaced, exported, or backed up.

## Drafts and publishing

A site can be created as a private draft or published immediately. Drafts remain available in the dashboard and authenticated preview, but their local, Onion, and custom-domain public routes return `404` until the site is published. Publishing or unpublishing does not remove any files or Onion identity.

## Publishing addresses

Each published site can be reached in several independent ways.

### Local network

```text
http://umbrel.local:8377/p/portfolio/
```

### Shared Umbrel Onion address

When Umbrel supplies `APP_HIDDEN_SERVICE`, Pages appends the site's path:

```text
http://<pages-umbrel-address>.onion/p/portfolio/
```

### Independent Onion address

From the site's **Sharing** tab, select **Generate Onion address**. Pages creates a separate Onion v3 identity for that website and serves it directly at the root path:

```text
http://<website-specific-address>.onion/
```

This address is independent of Umbrel's remote-Tor address. It is managed by the bundled Tor sidecar and therefore works even when Umbrel has not supplied `APP_HIDDEN_SERVICE`, provided the Pages Tor container can reach the Tor network.

The available controls are:

- **Generate**: Create the first independent Onion identity
- **Disable**: Stop publishing while preserving the address and key
- **Enable**: Restore the same preserved address
- **Regenerate**: Permanently retire the current identity and create a new address

Disabled and retired Onion hostnames are blocked rather than falling through to the Pages dashboard. Regeneration intentionally makes the old address unusable.

## Managed Tor architecture

Pages uses a separate Tor sidecar container. The web container controls detached Onion services through Tor's authenticated Unix control socket. Website traffic is forwarded from Tor to Pages over a second Unix socket instead of a Docker TCP port.

```text
Tor network
    │
    ▼
pages-tor sidecar
    │  Unix website socket
    ▼
Pages web server
    │
    └── Host header → matching website
```

The web dashboard is not exposed through an independent site Onion. Only the matching published website is served for that Onion hostname.

## Persistent data

Pages stores application data beneath `/data` in the web container:

```text
/data/
├── pages.sqlite
├── sites/
├── backups/
├── tmp/
└── tor/
    └── keys/
        └── <site-id>.key
```

The Umbrel package also stores Tor runtime state under `${APP_DATA_DIR}/tor/state`. The control socket and website socket directories are runtime communication paths.

An independent Onion address is derived from its private identity key. The key file is stored with mode `0600`; keeping it preserves the same address across container and Umbrel restarts. Website ZIP exports and individual website backups do not include Onion keys. A backup of the complete Umbrel app-data directory does.

## Environment variables

| Variable | Default | Purpose |
|---|---:|---|
| `PORT` | `3000` | Internal dashboard and local HTTP port |
| `DATA_DIR` | `/data` | Persistent Pages data directory |
| `PUID` | `1000` | UID used by the unprivileged Pages process |
| `PGID` | `1000` | GID used by the unprivileged Pages process |
| `PAGES_ADMIN_PASSWORD` | `APP_PASSWORD` | Dashboard password |
| `APP_HIDDEN_SERVICE` | empty | Optional Umbrel-provided shared Onion hostname |
| `DEVICE_DOMAIN_NAME` | empty | Umbrel device hostname |
| `PAGES_PUBLIC_PORT` | `8377` | External Pages port used for local links |
| `TOR_CONTROL_SOCKET` | `/tor-control/control` | Tor control Unix socket |
| `TOR_CONTROL_COOKIE` | `/tor-control/control.authcookie` | SAFECOOKIE authentication file |
| `TOR_ONION_TARGET` | `unix:/site-socket/pages.sock` | Target used by generated Onion services |
| `TOR_SITE_SOCKET_DIR` | `/site-socket` | Directory for the website Unix socket |
| `TOR_RECONCILE_INTERVAL_MS` | `30000` | Managed Onion reconciliation interval |
| `MAX_UPLOAD_BYTES` | `104857600` | Maximum uploaded file or ZIP size in bytes |
| `MAX_EXTRACTED_BYTES` | `524288000` | Maximum extracted ZIP size in bytes |
| `PAGES_DISABLE_AUTH` | `false` | Development-only authentication bypass |
| `PAGES_DEVICE_DOMAIN` | empty | Local-development fallback for `DEVICE_DOMAIN_NAME` |
| `PAGES_HIDDEN_SERVICE` | empty | Local-development fallback for `APP_HIDDEN_SERVICE` |

## Local development

Pages has no npm dependencies and requires Node.js 22.5 or newer. The normal web UI can be run without managed Tor:

```bash
mkdir -p ./data
PAGES_ADMIN_PASSWORD="pages" \
PAGES_DEVICE_DOMAIN="localhost" \
PAGES_PUBLIC_PORT="3000" \
DATA_DIR="$(pwd)/data" \
PORT=3000 \
npm start
```

Open `http://localhost:3000` and sign in with `pages`.

For the complete two-container development stack, use:

```bash
docker compose up --build
```

Run the built-in checks with:

```bash
npm run check
npm test
```

The smoke test includes a local Tor-control simulator and validates independent Onion generation, direct host routing, disable/enable behavior, regeneration, and retired-address blocking without contacting the public Tor network.

## Docker images

The Umbrel package uses two multiarch images:

```text
dennysubke/pages:0.1.1
dennysubke/pages-tor:0.1.1
```

Build and push both images and pin their digests with:

```bash
chmod +x build-and-pin.sh docker-entrypoint.sh tor/entrypoint.sh
./build-and-pin.sh ../umbrel/denny-pages/docker-compose.yml
```

## Custom domains

A reverse proxy can forward a custom domain to Pages while preserving the original `Host` header. Add that hostname in the website's **Sharing** tab and Pages will route it automatically.

## Security model

The Pages dashboard uses its own signed session cookie. Public websites remain accessible without the Umbrel app-proxy login. Uploaded ZIP archives are checked for unsafe paths, symbolic links, and excessive extracted size before publication. Website files are constrained to their assigned storage directories, and symbolic-link traversal is rejected.

The QR endpoint accepts only authenticated requests and only HTTP or HTTPS URLs. It invokes `qrencode` directly without a shell.

The web and Tor containers start as root only long enough to initialize ownership of their Umbrel bind mounts. Each entrypoint then replaces itself with the service process running as numeric UID/GID `1000:1000`. Neither container is privileged.

Independent Onion private keys are not returned by the API, shown in logs, or exposed through the website file editor. They are stored outside each site's editable directory. Anyone who obtains one of these keys can impersonate the corresponding Onion service, so the complete app-data backup must be protected.

## Scope

Pages hosts pre-built static HTML, CSS, JavaScript, images, fonts, WebAssembly, and other files. It does not execute uploaded PHP, Node.js, Python, shell, or other server-side code.
