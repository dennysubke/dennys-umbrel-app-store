# MoinPDF on Umbrel

MoinPDF **0.27.2** provides all **121 tools** through the German and English interfaces. Open the app from Umbrel; its app port remains **8785**.

## Changes since 0.26.0

- Bank statement to DATEV reads supported EUR statements in the browser. It detects the statement period and balances, runs local OCR on image pages and checks the postings before export. Select SKR03 or SKR04 and enter the relevant ledger accounts, advisor and client numbers. Document field 1 stays empty.
- The home page and tools open permissions-protected PDFs such as Volksbank statements. A password prompt appears when the file requires an opening password. Unreadable statements show a message.
- Over HTTPS each user can enter a personal OpenAI API key in the tool’s AI posting suggestions panel. The standard web container handles these requests. Users review the booking text before sending it and can store their key encrypted on the device with a passphrase.
- See the [0.27.2 release](https://github.com/MoinPDF/moinpdf/releases/tag/v0.27.2) and [full changelog](https://github.com/MoinPDF/moinpdf/blob/v0.27.2/CHANGELOG.en.md).

## Update and persistent data

Use Umbrel’s normal app update from 0.26.0 to 0.27.2. No manual data migration is required. The app ID, port, runtime settings, internal credentials, network isolation, storage configuration and lifecycle hook are retained.

Existing data remains under the configured app data root: Caddy data/configuration, trust files, translation models/cache and `data/document-jobs`. Server conversion jobs keep the existing 24-hour retention policy. Browser settings, local projects and drafts remain in the same browser storage; continue using the same app address and browser profile.

## Published images

All four images are taken from the published release source `6383b69ad567a23bbff4efdac84d31018be6ff86`. Each pinned multi-platform index supports `linux/amd64` and `linux/arm64`. The translation image is shared by the model setup and translation services.

| Image | Immutable digest |
| --- | --- |
| `ghcr.io/moinpdf/moinpdf-web:0.27.2-6383b69ad567` | `sha256:95b604b6cb724232288cb293ec28fbf3ba8d43f45195301ae6796eb23d3d34c0` |
| `ghcr.io/moinpdf/moinpdf-documents:0.27.2-6383b69ad567` | `sha256:55e6e88061296719ca5de20736956f19d9a25de0e4758f0f4a0ad4d2510172c8` |
| `ghcr.io/moinpdf/moinpdf-translation:0.27.2-6383b69ad567` | `sha256:5a1e1560a2979c8ed627178dd89845e9fcdc0c8c3ac3e727e2ad8068f4aaaa2b` |
| `ghcr.io/moinpdf/moinpdf-website:0.27.2-6383b69ad567` | `sha256:7933e52d61cfeeba61f7b230fe98cb398d30e0454c3b276a46c9c54f570254fb` |

## Verification

Image verification compares each pinned index with the official GitHub release asset and tag, checks its SHA-256, and verifies the amd64/arm64 platform manifests and source labels. Exact platform digests are saved in each workflow's `image-digests.json` artifact.

The [Umbrel workflow](../.github/workflows/moinpdf.yml) runs fresh installation and a native update from the published 0.26.0 package on separate amd64 and arm64 runners. It verifies all 121 deployed tool IDs against the immutable release source, desktop geometry and mint light mode, protected HTTP/HTTPS routes, a permissions-protected synthetic Volksbank statement exported to DATEV CSV, the personal-key service through the gateway, real document outputs, Office/website conversion, translation, existing data and credentials, and persistent job results across update/restart. Synthetic files in all six persistent directories retain their exact bytes, owners and permissions across the native update; directory owners and permissions are also checked. These checks use disposable umbrelOS 2.0.0 hosts and automated browsers; physical NAS and mobile devices are outside this test coverage.
