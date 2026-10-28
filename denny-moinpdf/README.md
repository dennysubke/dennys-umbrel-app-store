# MoinPDF on Umbrel

MoinPDF **0.25.1** provides all **118 tools** through the German and English interfaces. Open the app from Umbrel; its app port remains **8785**.

## Changes since 0.25.0

- Scan compression reduces supported grayscale, Flate and other image resources while preserving text, links, form values and page geometry. Unsupported images remain unchanged.
- Target-size compression uses local image reduction and displays percentage progress, compression level, image count and cancellation. Every output is checked against the requested size.
- Wide desktop views keep a normally sized compression workspace. Opaque navigation surfaces remove gray blur artifacts in desktop light mode.
- See the [0.25.1 release](https://github.com/MoinPDF/moinpdf/releases/tag/v0.25.1) and [full changelog](https://github.com/MoinPDF/moinpdf/blob/v0.25.1/CHANGELOG.en.md) for capabilities and limits.

## Update and persistent data

Use Umbrel’s normal app update from 0.25.0 to 0.25.1. No manual data migration is required. The app ID, port, runtime settings, internal credentials, network isolation, storage configuration and lifecycle hook are retained.

Existing data remains under the configured app data root: Caddy data/configuration, trust files, translation models/cache and `data/document-jobs`. Server conversion jobs keep the existing 24-hour retention policy. Browser settings, local projects and drafts remain in the same browser storage; continue using the same app address and browser profile.

## Published images

All four images are taken from the published release source `b7aaf77cba38f6a28ba9b01c2d5da633b3ed72f4`. Each pinned multi-platform index supports `linux/amd64` and `linux/arm64`. The translation image is shared by the model setup and translation services.

| Image | Immutable digest |
| --- | --- |
| `ghcr.io/moinpdf/moinpdf-web:0.25.1-b7aaf77cba38` | `sha256:c37f3bacc884535f4e05780b3839d71e200200c10f9e78a9536730fe262e0372` |
| `ghcr.io/moinpdf/moinpdf-documents:0.25.1-b7aaf77cba38` | `sha256:1088ae3fdbf719c6f18e69c039f3d7ce4312d3c02d711efcbb6af27fd96f4728` |
| `ghcr.io/moinpdf/moinpdf-translation:0.25.1-b7aaf77cba38` | `sha256:7a462eb95767ee4ddf730115bbb5fb85ed85021a09090123b7638e8eb5033bcb` |
| `ghcr.io/moinpdf/moinpdf-website:0.25.1-b7aaf77cba38` | `sha256:4fc5809b672195f8043459d7af40bd6677dd10886d294873719d06b7c16bf6c0` |

## Verification

The [Umbrel workflow](../.github/workflows/moinpdf.yml) runs fresh installation and a native update from the published 0.25.0 package on separate amd64 and arm64 runners. It verifies all 118 deployed tool IDs against the immutable release source, desktop geometry and mint light mode, protected HTTP/HTTPS routes, real document outputs, Office/website conversion, translation, existing data and credentials, and persistent job results across update/restart. These checks use disposable umbrelOS 2.0.0 hosts and automated browsers; physical NAS and mobile devices are outside this test coverage.
