# MoinPDF on Umbrel

MoinPDF **0.26.0** provides all **120 tools** through the German and English interfaces. Open the app from Umbrel; its app port remains **8785**.

## Changes since 0.25.2

- Two new tools: a document checklist with reviewable evidence and CSV export, and printed-date collection with explicit confirmation before ICS calendar export.
- Scan-quality hints, an original-versus-two-edits text comparison, and selective replacement of identical raster logos extend existing tools. Ambiguous matches stay visible; legal deadlines are not calculated.
- Scan-photo separation detects multiple photos locally, supports manual corner/crop/rotation corrections, and exports reviewed images or PDFs.
- German and English instructions describe each workflow and its limits. No external AI services or new production dependencies are required.
- See the [0.26.0 release](https://github.com/MoinPDF/moinpdf/releases/tag/v0.26.0) and [full changelog](https://github.com/MoinPDF/moinpdf/blob/v0.26.0/CHANGELOG.en.md).

## Update and persistent data

Use Umbrel’s normal app update from 0.25.2 to 0.26.0. No manual data migration is required. The app ID, port, runtime settings, internal credentials, network isolation, storage configuration and lifecycle hook are retained.

Existing data remains under the configured app data root: Caddy data/configuration, trust files, translation models/cache and `data/document-jobs`. Server conversion jobs keep the existing 24-hour retention policy. Browser settings, local projects and drafts remain in the same browser storage; continue using the same app address and browser profile.

## Published images

All four images are taken from the published release source `78d4339124ab272a190063dd67c44972001dd3f5`. Each pinned multi-platform index supports `linux/amd64` and `linux/arm64`. The translation image is shared by the model setup and translation services.

| Image | Immutable digest |
| --- | --- |
| `ghcr.io/moinpdf/moinpdf-web:0.26.0-78d4339124ab` | `sha256:518eeb19cd9cf29be4afed63de7f75bf8098c69d7c05cca29a5563873c4b427a` |
| `ghcr.io/moinpdf/moinpdf-documents:0.26.0-78d4339124ab` | `sha256:d738f1abb65db7e2267434b2d0d17f8c18293b610a7ad59dd7239e908fda0df3` |
| `ghcr.io/moinpdf/moinpdf-translation:0.26.0-78d4339124ab` | `sha256:23871842a362d70965f87c0732d608e55166a8584d7e13dd9f741c5c730669c9` |
| `ghcr.io/moinpdf/moinpdf-website:0.26.0-78d4339124ab` | `sha256:751b9648e8742384c7890374c00f99ebdc47e6e72cd2aca53c0e01192d7500e7` |

## Verification

Image verification compares each pinned index with the official GitHub release asset and tag, checks its SHA-256, and verifies the amd64/arm64 platform manifests and source labels. Exact platform digests are saved in each workflow's `image-digests.json` artifact.

The [Umbrel workflow](../.github/workflows/moinpdf.yml) runs fresh installation and a native update from the published 0.25.2 package on separate amd64 and arm64 runners. It verifies all 120 deployed tool IDs against the immutable release source, desktop geometry and mint light mode, protected HTTP/HTTPS routes, real document outputs, Office/website conversion, translation, existing data and credentials, and persistent job results across update/restart. Synthetic files in all six persistent directories retain their exact bytes, owners and permissions across the native update; directory owners and permissions are also checked. These checks use disposable umbrelOS 2.0.0 hosts and automated browsers; physical NAS and mobile devices are outside this test coverage.
