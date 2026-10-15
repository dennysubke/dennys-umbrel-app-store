# MoinPDF on Umbrel

This package installs the complete [MoinPDF 0.13.25 release](https://github.com/MoinPDF/moinpdf/releases/tag/v0.13.25) through Denny's Umbrel Community Store. Open MoinPDF from the Umbrel dashboard; the app uses port **8785** and Umbrel login by default. No manual image build, `.env` file or API-key entry is needed.

## What is included

- The PDF workspace with German and English interfaces, local browser tools and documentation.
- The document server for extended conversion, invoice validation, speech and other server tools.
- LibreTranslate and persistent models for German, English, French, Spanish, Italian, Dutch and Polish.
- A separate Chromium service for **public website links to PDF**, including images, fonts, CSS and print options.

All four images use the release's immutable multi-architecture digests for `linux/amd64` and `linux/arm64`. The model downloader reuses the translation image. Updates preserve the existing model, cache, trust and Caddy directories under `data/` and the per-install API key derived by `exports.sh`.

## Resources and browser access

Start with **8 GB of available RAM and 20 GB of free disk space**. Initial installation downloads images and translation models; document translation becomes available once the models are ready. Browser tools remain available while model setup completes. The website converter is limited to 1 GiB RAM and two jobs at a time.

Local browser Office conversion needs HTTPS or localhost, cross-origin isolation and sufficient browser memory. When using a plain HTTP LAN address or a low-memory device, select the included document server in the Office converter. Camera access also requires HTTPS or localhost. The app supports a dedicated root domain; preserve both `/api/documents/*` and `/api/website/*` when configuring an additional reverse proxy.

## Processing and networks

Browser tools process documents on the user's device. Server tools send the selected job to this Umbrel installation. Document converters and the running translation service remain on an **internal network without internet access**. The model downloader uses Umbrel's normal network during setup. The website converter has a separate network shared only with the web container, with internet access for public pages; it does not join the document network.

Website requests do not inherit browser logins or cookies. The converter blocks private network destinations and credentials in URLs; cookie banners, bot protection and dynamic content can affect the result. Review important outputs against their originals.

Server jobs use temporary directories. MoinPDF is not a document archive: download results or save a browser project before closing your session. Local projects and `.moinpdf` project files are unencrypted and include originals and editing history.

## Verification

The [store installation workflow](../.github/workflows/moinpdf.yml) checks anonymous image access and both architecture manifests, then performs a fresh native installation on a disposable **umbrelOS 2.0.0 amd64** host. It checks Umbrel login, HTTP/HTTPS access, the displayed version, PDF upload, language switching, real Office/website conversion, PDF translation, speech and restart persistence. Image availability does not establish a native ARM execution test. See the current PR's checks for the result on this package revision.

[Upstream Docker guide](https://github.com/MoinPDF/moinpdf/blob/main/DOCKER.en.md) · [Features and limitations](https://github.com/MoinPDF/moinpdf/blob/main/docs/FEATURES.en.md)
