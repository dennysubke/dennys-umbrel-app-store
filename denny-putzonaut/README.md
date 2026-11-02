# Putzonaut auf Umbrel

Installiere **Putzonaut** aus **Denny´s Umbrel**. Benötigt wird umbrelOS 2.0 oder neuer. Die App startet zunächst mit einer Einrichtungsseite; SSH und manuelle Dateibearbeitung sind nicht erforderlich.

## Einrichtung

Öffne **Einstellungen → App-Einstellungen → Putzonaut → Erweitert**. Die vorgeschlagenen Variablen gelten für den Dienst `web`:

| Variable | Eintrag |
| --- | --- |
| `APP_ORIGIN` | Vollständige HTTPS-Adresse ohne abschließenden `/`; lokal ist die Umbrel-Adresse voreingestellt. Für deinen Tunnel z. B. `https://app.putzonaut.de`. |
| `WEBSITE_ORIGIN` | Adresse der öffentlichen Vorstellungsseite, z. B. `https://putzonaut.de`. |
| `MAIL_FROM` | Bestätigter Absender, z. B. `Putzonaut <info@putzonaut.de>` |
| `SMTP_HOST` | Bei Brevo: `smtp-relay.brevo.com` |
| `SMTP_PORT` | Bei Brevo: `587` |
| `SMTP_USER` | SMTP-Anmeldename aus Brevo |

Unter **Eigene Variablen** ergänzen: **Name** `SMTP_PASSWORD`, **Wert** dein SMTP-Schlüssel. Der Dienst **web** wird bei dieser App automatisch gewählt; deshalb zeigt Umbrel nur die beiden Felder **Name** und **Wert**. Auf **Variable hinzufügen** klicken, danach **Übernehmen und neu starten**. Zugangsdaten gehören ausschließlich in die privaten Umbrel-Einstellungen.

Diese Paketierung erwartet SMTP mit Benutzername und Passwort. Die Verbindung nutzt STARTTLS oder, auf Port 465, direkt TLS. Zertifikatsprüfung bleibt aktiv. Ein unvollständiger Start zeigt die Einrichtung statt eines fehlerhaften Anmeldeformulars.

## Cloudflare Tunnel

Im bestehenden Tunnel die gewünschten Hostnamen zuordnen:

| Öffentlicher Hostname | Service |
| --- | --- |
| `putzonaut.de` | `http://denny-putzonaut_web_1:3081` |
| `www.putzonaut.de` | `http://denny-putzonaut_web_1:3081` (Weiterleitung zur Hauptadresse) |
| `app.putzonaut.de` | `http://denny-putzonaut_web_1:3080` |

In den App-Einstellungen `APP_ORIGIN=https://app.putzonaut.de` und `WEBSITE_ORIGIN=https://putzonaut.de` setzen. Die Website ist eine separate, nur lesbare Oberfläche: keine Kontorouten, Sitzungscookies oder Haushaltsdaten. Sie ist bereits während der SMTP-Einrichtung verfügbar. Links und QR-Code verwenden die eingestellte App-Adresse.

Bei einer anderen öffentlich betriebenen Installation müssen Impressum und Datenschutzerklärung in einem eigenen Image zum tatsächlichen Betreiber passen. Die mitgelieferten Angaben beschreiben den Betrieb auf putzonaut.de.

Der Cloudflare-Connector muss das von Umbrel verwaltete Docker-Netz erreichen. Die öffentliche Route geht direkt zur App mit eigener Kontoanmeldung; der lokale Umbrel-Zugang bleibt durch Umbrel geschützt. Nach der Konfiguration öffnet auch das App-Symbol die eingestellte öffentliche Adresse. Die lokale App-Adresse verwendet Port **8876**. HTTPS-Zertifikat und Domain müssen aktiv sein.

## Daten und Updates

Umbrel verwaltet Installation, Start, Stopp und Updates. Alle veränderlichen App-Daten liegen in `data/`: Konten, Crews, Fotos und die verschlüsselte Mailwarteschlange. Die App läuft als UID/GID 1000 mit schreibgeschütztem Container-Dateisystem. Zusätzlich wird nur ihre eigene Startdatei schreibgeschützt eingebunden; es gibt keinen Docker-Socket und keinen Zugriff auf fremde App-Ordner.

Das Konto- und Mailgeheimnis stammt aus dem stabilen Umbrel-App-Seed. Bei einem Umzug müssen die App-Daten, privaten App-Einstellungen und der zugehörige Umbrel-Seed erhalten bleiben. Eine vollständige Umbrel-Sicherung verwenden; das Kopieren einer einzelnen SQLite-Datei reicht nicht aus. Nicht deinstallieren, um zu aktualisieren: Eine Deinstallation löscht App-Daten.

Das Image für Version `0.22.1` ist für amd64 und arm64 per Manifest-Digest festgelegt. Dieses Update liefert die überarbeitete dunkle Website mit Raketenfigur, animierten Funktionskarten und Hilfe-Bereich aus. Die Startdatei liegt unter `hooks/`, damit Umbrel sie bei Paket-Updates ebenfalls kopiert; sie ist kein Lifecycle-Hook. Es werden keine realen SMTP-Schlüssel im Store gespeichert.

Die eigentliche App verwendet bestätigte E-Mail-Konten. Eigenes Web Push, Änderung der Login-E-Mail und Kontolöschung per Selbstbedienung sind in 0.22.1 noch nicht verfügbar. Bestehende Daten der privaten Testseite werden nicht automatisch importiert.
