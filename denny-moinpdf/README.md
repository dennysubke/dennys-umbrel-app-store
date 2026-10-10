# MoinPDF als Umbrel-App

MoinPDF ist als **`denny-moinpdf`** in [dem Umbrel Community Store](https://github.com/dennysubke/dennys-umbrel-app-store) verfügbar. Das Paket enthält die Web-App, den Dokumentenserver und die lokale Übersetzung. Umbrel verwaltet Installation, Start, Stopp, Neustarts, Updates und die App-Daten. Eine Pages-Installation, ein ZIP-Import, eine eigene `.env` oder ein manueller Build auf Umbrel sind nicht erforderlich.

## Installation aus dem Community Store

1. Im Umbrel App Store die Community-Stores öffnen und, falls noch nicht vorhanden, diesen Store hinzufügen:

   ```text
   https://github.com/dennysubke/dennys-umbrel-app-store
   ```

2. **MoinPDF** suchen und installieren. Mindestens **8 GB verfügbaren RAM und 20 GB freien Speicher** als Ausgangspunkt vorsehen. Die großen Konverter-Images und Sprachmodelle benötigen beim ersten Start Internetzugang und können mehrere Minuten laden.
3. MoinPDF über das Symbol auf Umbrel öffnen. Der App-Port ist **8785**. Die Oberfläche verbindet sich automatisch mit dem Dokumentenserver; es muss kein API-Schlüssel in den Browser eingetragen werden.
4. Datei auswählen, Werkzeug oder Zielformat wählen und die Verarbeitung starten. Bei „PDF übersetzen“ kann nach der Erstinstallation kurz „Wird vorbereitet“ erscheinen; die übrigen Werkzeuge sind bereits nutzbar.
5. Eine Test-PDF öffnen, eine DOCX in PDF konvertieren und nach abgeschlossener Einrichtung ein kurzes Text-PDF übersetzen.

Die im Store fest hinterlegten Container-Pakete unter `ghcr.io/dennysubke/` sind öffentlich und ohne GitHub-Anmeldung abrufbar. Der Store verwendet feste Image-Versionen mit Prüfsummen für Intel/AMD (`amd64`) und ARM (`arm64`).

## Zugriff und HTTPS

Standardmäßig schützt der **Umbrel-Login** die gesamte App. Es gibt kein zusätzliches MoinPDF-Standardpasswort. Der Zugriff im LAN erfolgt über die Umbrel-App oder `http://UMBREL-IP:8785`.

Kameraaufnahmen erfordern einen sicheren Browserkontext. Auf umbrelOS 2.0 kann der App-Port auch über HTTPS geöffnet werden; über die öffentliche Domain übernimmt Cloudflare HTTPS. Der normale Datei-Upload funktioniert auch im lokalen HTTP-Zugang.

## Direkt mit Cloudflare Tunnel veröffentlichen

Eine eigene Domain oder Subdomain verwenden, zum Beispiel `pdf.example.org`. Im bestehenden Cloudflare Tunnel **eine Published-application-Route** anlegen:

| Einstellung | Wert |
| --- | --- |
| Hostname | `pdf.example.org` |
| Path | leer |
| Service | HTTP |
| Ziel | `UMBREL-IP:8785` |

In einem gemeinsamen URL-Feld lautet das Ziel `http://UMBREL-IP:8785`. Als Ziel die feste LAN-IP des Umbrel verwenden; `localhost` im Tunnel-Container bezeichnet den Tunnel-Container selbst. Die Oberfläche und `/api/documents/*` laufen unter derselben Domain. Zusätzliche API-Routen, eigene öffentliche API-Schlüssel oder Browser-CORS-Freigaben werden nicht benötigt.

**Zugang bewusst auswählen:** Für eine öffentlich zugängliche Website in den MoinPDF-App-Einstellungen von umbrelOS 2.0 „Require Umbrel login“ ausschalten. Danach können Besucher auch Serveraufträge ausführen. Für einen beschränkten Benutzerkreis zuerst eine Cloudflare-Access-Regel für den **gesamten Hostnamen einschließlich API** einrichten. Die Einstellung der MoinPDF-App betrifft nicht den Login der Umbrel-Verwaltung. Auf älteren Umbrel-Versionen unterscheidet sich die Verwaltung des App-Proxy-Logins; der ausgelieferte Standard bleibt geschützt.

Keine Router-Portfreigabe ist für den Tunnel erforderlich. Eine Cloudflare-Regel zum Umgehen des Cache für `/api/documents/*` anlegen und dort `Cache-Control: no-store` nicht überschreiben. Keine zusätzlichen Analyse-Skripte oder Rocket Loader für MoinPDF einschalten.

**Zeitgrenze:** Serveraufträge sind derzeit synchron. Cloudflares standardmäßiger Proxy Read Timeout beträgt 125 Sekunden; lange Übersetzungen können deshalb mit Fehler 524 abbrechen. Für solche Dokumente den direkten LAN-Zugang oder kleinere Dokumente verwenden. Das Paket enthält noch keine asynchrone Warteschlange. Cloudflares Uploadgrenze gilt zusätzlich zum MoinPDF-Limit von 80 MB.

## Was Umbrel automatisch einrichtet

- Ein separater, stabiler API-Schlüssel wird aus Umbrels App-Entropie abgeleitet und nur an Web-Proxy und Dokumentenserver übergeben.
- Web-App, Dokumentenserver und Übersetzung laufen ohne Root-Rechte als UID/GID `1000:1000`.
- Web-App und Modell-Downloader hängen am üblichen Umbrel-Netz. Der Web-Proxy erreicht den Dokumentenserver über ein zusätzliches internes Netz. Dokumentenserver und laufende Übersetzung befinden sich ausschließlich in diesem internen Netz ohne Internetroute. Der Modell-Downloader erhält keine Dokumente.
- Sprachmodelle, Übersetzungscache und Caddy-Daten liegen unter `${APP_DATA_DIR}/data/`; Neustarts und Updates behalten sie. Auf umbrelOS 2.0 kann dieser Datenbereich über Umbrel verschoben werden.
- Unter `data/trust` können bei Bedarf eigene vertrauenswürdige CA-Zertifikate für die Signaturprüfung bereitgestellt werden. Ein eigenes Signaturzertifikat bleibt erforderlich, wenn Dokumente unterschrieben werden sollen.
- Temporäre Dokumentenaufträge liegen im Arbeitsspeicher-Dateisystem des Dokumentenservers und werden nach der Verarbeitung entfernt. MoinPDF ist kein Dokumentenarchiv.
- Docker-Protokolle sind pro Dienst auf drei Dateien zu je 10 MB begrenzt. Dies ist eine Größenbegrenzung, keine Aufbewahrungsfrist in Tagen.

Der Dienst `translation-models` darf mit `Exited (0)` enden: Das bedeutet, dass alle Sprachmodelle vorbereitet sind. Die dauerhaft laufenden Dienste heißen `web`, `documents` und `translation`.

## Impressum, Datenschutz und E-Mail

Die eingebundenen Seiten beschreiben **die ursprüngliche MoinPDF-Instanz mit eigenem Server, Cloudflare und Tuta**. Andere Betreiber müssen diese Angaben vor einer öffentlichen Bereitstellung anpassen. Tatsächlich eingesetzte zusätzliche Anmeldedienste, Statistiken und Aufbewahrungsregeln berücksichtigen. Tuta bleibt das externe Kontaktpostfach; MoinPDF benötigt weder SMTP-Zugangsdaten noch einen Mail-Container. Die DNS-Einträge des Postfachs müssen für diese Installation nicht verändert werden.

## Updates und Prüfung auf dem Zielgerät

Updates über den Umbrel App Store installieren. Die Paketversion verweist auf geprüfte, mit Manifest-Digests festgelegte Images für `linux/amd64` und `linux/arm64`. Ein normales Update behält die App-Daten; eine Deinstallation kann sie löschen.

Der aktuelle Prüfstand wird in [MoinPDF-Prüfstand](https://github.com/MoinPDF/moinpdf/blob/main/VALIDATION.md) beschrieben. Die [GitHub-Actions-Läufe](https://github.com/dennysubke/dennys-umbrel-app-store/actions/workflows/moinpdf.yml) zeigen jeweils den geprüften Commit. Der native Installationstest verwendet eine frische, temporäre **umbrelOS-2.0.0-Umgebung auf amd64** und prüft Login, HTTP/HTTPS, PDF-Vorschau, Office-Konvertierung, Übersetzung und Neustart.

Für `arm64` wurden die veröffentlichten Image-Manifeste geprüft; ein nativer ARM-Lauf steht noch aus. Der physische Umbrel und die öffentliche Cloudflare-Verbindung des Betreibers waren nicht Teil des Tests. Vor der öffentlichen Nutzung auf dem eigenen Gerät einmal App-Start, Office-Konvertierung, Übersetzung und Neustart prüfen; danach dieselben Aufträge über die öffentliche Domain testen.

## Image-Veröffentlichung für den Store-Maintainer

Nach einem erfolgreichen vollständigen Docker-Prüflauf auf `main` baut `.github/workflows/publish-images.yml` die drei Images aus demselben Quellstand für beide Architekturen und veröffentlicht sie mit dem integrierten GitHub-Actions-Token. Zusätzliche Registry-Passwörter im Repository sind nicht nötig. Tags enthalten App-Version und Quell-Commit; die Workflow-Artefakte enthalten die zugehörigen Multiarch-Index-Digests.

Der Quellcode liegt öffentlich unter [MoinPDF/moinpdf](https://github.com/MoinPDF/moinpdf). Neue Images werden unter `ghcr.io/moinpdf/` veröffentlicht. Die Sichtbarkeit des Quellcode-Repositorys und der Container-Pakete wird getrennt verwaltet: Neu angelegte GHCR-Pakete benötigen beim ersten Publish die Freigabe unter **Package settings → Change visibility → Public**.

Die aktuelle Store-Version verwendet weiterhin die öffentlich abrufbaren Images unter `ghcr.io/dennysubke/`. Beim Wechsel zu `ghcr.io/moinpdf/` zuerst alle drei Pakete `moinpdf-web`, `moinpdf-documents` und `moinpdf-translation` öffentlich freigeben, dann die anonyme Abrufbarkeit und beide Plattformen prüfen. Anschließend Image-Referenzen samt Digest, den erwarteten Registry-Namensraum in `.github/tests/moinpdf/verify-images.py` und den Quell-Commit in `.github/tests/moinpdf/asset-checksums.json` gemeinsam aktualisieren und den nativen Umbrel-Test erfolgreich abschließen, bevor die Änderung in `master` übernommen wird.

Quellen: [Umbrel-Paketierung](https://github.com/getumbrel/umbrel-apps/blob/master/.agents/skills/umbrel-package-app/SKILL.md), [GHCR-Paketsichtbarkeit](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility), [Cloudflare 524](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/).

## Paketpflege und Integrationstests

Diese Integration wird ausschließlich im Community-Store gepflegt. MoinPDF selbst
bleibt eine eigenständige Anwendung; die hier referenzierten Images stammen aus
dem allgemeinen Docker-Release des Projekts.

Der Workflow **Verify MoinPDF installation** prüft die Image-Digests und beide
Plattform-Indizes, installiert das Paket in einer frischen umbrelOS-2.0.0-Umgebung
und testet Anmeldung, PDF-Vorschau, Office-Konvertierung, Übersetzung, Sprachausgabe
und Neustart. Er verwendet die veröffentlichten Images und benötigt keine Zugangsdaten
zum Quellcode-Repository.
Er startet bei Änderungen am Paket oder den zugehörigen Tests und lässt sich
zusätzlich über Actions manuell ausführen.

Bei Updates die drei Image-Referenzen samt Digest in `docker-compose.yml` und
die Version in `umbrel-app.yml` gemeinsam pflegen. Ändern sich Favicon oder Video,
auch die SHA-256-Prüfsummen in `.github/tests/moinpdf/asset-checksums.json` anhand
der freigegebenen Quelldateien aktualisieren. Der Office-Test erzeugt sein
künstliches DOCX selbst; private Arbeitsdokumente sind nicht erforderlich.
