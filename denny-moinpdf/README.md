# MoinPDF on Umbrel

MoinPDF **0.25.0** provides all **118 tools** through the German and English interfaces. Open the app from Umbrel; its app port remains **8785**.

## Changes since 0.23.0

- Desktop content expands responsively up to 1,760 px, with larger navigation, search, upload controls, categories and quick-access cards. Desktop light mode uses a richer mint-green background. Mobile/tablet layouts and PDF rendering retain their behavior.
- Includes the 0.24.0 additions: Change colors & background, Process large PDFs, supported text-preserving redaction, reusable Clear Deck rules, and form/page improvements.
- See the [0.25.0 release](https://github.com/MoinPDF/moinpdf/releases/tag/v0.25.0) and [full changelog](https://github.com/MoinPDF/moinpdf/blob/v0.25.0/CHANGELOG.en.md) for capabilities and limits.

## Update and persistent data

Use Umbrel’s normal app update from 0.23.0 directly to 0.25.0. No intermediate 0.24.0 installation or manual data migration is required. The app ID, port, runtime settings, internal credentials, network isolation, storage configuration and lifecycle hook are retained.

Existing data remains under the configured app data root: Caddy data/configuration, trust files, translation models/cache and `data/document-jobs`. Server conversion jobs keep the existing 24-hour retention policy. Browser settings, local projects and drafts remain in the same browser storage; continue using the same app address and browser profile.

## Published images

All four images are taken from the published release source `0ddd7b40e03759816022c1cb9fb887fc6fd150a7`. Each pinned multi-platform index supports `linux/amd64` and `linux/arm64`. The translation image is shared by the model setup and translation services.

| Image | Immutable digest |
| --- | --- |
| `ghcr.io/moinpdf/moinpdf-web:0.25.0-0ddd7b40e037` | `sha256:679dec124239b8038d982ae460ddd15cb55e39ac471aa685b61e13bd54a689f7` |
| `ghcr.io/moinpdf/moinpdf-documents:0.25.0-0ddd7b40e037` | `sha256:806327ca1ee706cf4fbb560d0d44ff1ee1293e29a4412d899dcddbfde45d9f8d` |
| `ghcr.io/moinpdf/moinpdf-translation:0.25.0-0ddd7b40e037` | `sha256:c619df358dd1521f267e51d3013b5f92dcb104a31cdc2090788b5616e5f0d46f` |
| `ghcr.io/moinpdf/moinpdf-website:0.25.0-0ddd7b40e037` | `sha256:cca042a9b17f34f56ab2bba6a082d1d44c6e5181c554c3db51d1281ea991eed0` |

## Verification

The [Umbrel workflow](../.github/workflows/moinpdf.yml) runs fresh installation and a native update from the published 0.23.0 package on separate amd64 and arm64 runners. It verifies all 118 deployed tool IDs against the immutable release source, desktop geometry and mint light mode, protected HTTP/HTTPS routes, real document outputs, Office/website conversion, translation, existing data and credentials, and persistent job results across update/restart. These checks use disposable umbrelOS 2.0.0 hosts and automated browsers; physical NAS and mobile devices are outside this test coverage.
