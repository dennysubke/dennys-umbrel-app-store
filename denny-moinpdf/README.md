# MoinPDF on Umbrel

MoinPDF **0.25.2** provides all **118 tools** through the German and English interfaces. Open the app from Umbrel; its app port remains **8785**.

## Changes since 0.25.1

- WebKit uses a compatible PDF image-data path to prevent blank large-scan previews and missing OCR. Original image dimensions and PDF contents are retained.
- Upstream regression tests also simulate a broken bitmap transfer and verify scan pixels, OCR and exported PDFs. Existing time limits and release gates are retained.
- See the [0.25.2 release](https://github.com/MoinPDF/moinpdf/releases/tag/v0.25.2) and [full changelog](https://github.com/MoinPDF/moinpdf/blob/v0.25.2/CHANGELOG.en.md) for capabilities and limits.

## Update and persistent data

Use Umbrel’s normal app update from 0.25.1 to 0.25.2. No manual data migration is required. The app ID, port, runtime settings, internal credentials, network isolation, storage configuration and lifecycle hook are retained.

Existing data remains under the configured app data root: Caddy data/configuration, trust files, translation models/cache and `data/document-jobs`. Server conversion jobs keep the existing 24-hour retention policy. Browser settings, local projects and drafts remain in the same browser storage; continue using the same app address and browser profile.

## Published images

All four images are taken from the published release source `0249db7ae981ea09b29712d23439c993c99220e8`. Each pinned multi-platform index supports `linux/amd64` and `linux/arm64`. The translation image is shared by the model setup and translation services.

| Image | Immutable digest |
| --- | --- |
| `ghcr.io/moinpdf/moinpdf-web:0.25.2-0249db7ae981` | `sha256:df9e4eee5fd7510a03eaf3e5fb1f48040920489ad1d1af91e2cf9ef34d59e242` |
| `ghcr.io/moinpdf/moinpdf-documents:0.25.2-0249db7ae981` | `sha256:45325ea77fa62f3ff264a80d64ae239e8ebe65609277bcf388f5d56c320cda1c` |
| `ghcr.io/moinpdf/moinpdf-translation:0.25.2-0249db7ae981` | `sha256:c8304843536f997c308ed5c05d05b6a2d570480b63d16e0ed8cfe37d2a642d4c` |
| `ghcr.io/moinpdf/moinpdf-website:0.25.2-0249db7ae981` | `sha256:feb219a30130e69186cbb1246375fcebd6f2773b6ba47fc3b6d5a56b137414d9` |

## Verification

Image verification compares each pinned index with the official GitHub release asset and tag, checks its SHA-256, and verifies the amd64/arm64 platform manifests and source labels. Exact platform digests are saved in each workflow's `image-digests.json` artifact.

The [Umbrel workflow](../.github/workflows/moinpdf.yml) runs fresh installation and a native update from the published 0.25.1 package on separate amd64 and arm64 runners. It verifies all 118 deployed tool IDs against the immutable release source, desktop geometry and mint light mode, protected HTTP/HTTPS routes, real document outputs, Office/website conversion, translation, existing data and credentials, and persistent job results across update/restart. Synthetic files in all six persistent directories retain their exact bytes, owners and permissions across the native update; directory owners and permissions are also checked. These checks use disposable umbrelOS 2.0.0 hosts and automated browsers; physical NAS and mobile devices are outside this test coverage.
