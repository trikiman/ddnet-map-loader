# DDNet Map Loader v2 (Portable)

Kleines Tool: Doppelklick auf eine `.map` lädt sie per Hot‑Reload auf deinem lokalen DDNet‑Server. Erstellt Backups und schreibt Logs.

## 📋 Anforderungen
- Windows 10/11 (ohne Adminrechte)
- DDNet Client/Server installiert und lokaler Server erreichbar

## 🤔 Was und wozu
- Verknüpft `.map`‑Dateien mit dieser App.
- Beim Doppelklick:
  - Prüft die Map
  - Sichert die aktuelle Map
  - Ersetzt die Arbeits‑Map und sendet `hot_reload`
  - Schreibt nach `%APPDATA%\DDNet\maps\ddnet_control.log`
- Ideal für schnelles Testen beim Mappen.

## 🚀 Schnellstart
1) `myServerconfig.cfg` prüfen/verschieben
2) `.map` mit dieser EXE verknüpfen (empfohlen)
   - Rechtsklick auf `.map` → Öffnen mit → Andere App auswählen → Weitere Apps → Auf diesem PC nach einer anderen App suchen → `ddnet_control.exe`
   - „Diese App immer verwenden…“ aktivieren
3) Doppelklick auf eine `.map` (z. B. `%APPDATA%\DDNet\maps\mapsfortest\anymap.map`)
4) Logs prüfen: `%APPDATA%\DDNet\maps\ddnet_control.log`

## 📁 Wohin mit myServerconfig.cfg
- So findest du den `data`‑Ordner von DDNet:
  1) Rechtsklick auf DDNet‑Verknüpfung (Taskleiste/Start/Desktop) → Dateipfad öffnen
  2) Im geöffneten Ordner nach `ddnet` (neben `DDNet.exe`)
  3) `data` öffnen → `myServerconfig.cfg` hineinkopieren
- Häufige Pfade (Beispiele):
  - Steam Standard: `C:\Program Files (x86)\Steam\steamapps\common\DDraceNetwork\ddnet\data`
  - Andere Steam‑Bibliothek: `<DeineSteamBibliothek>\steamapps\common\DDraceNetwork\ddnet\data`
  - Nicht‑Steam/Portable: `data` neben `DDNet.exe`

## 🧰 Fehlerbehebung
- Fenster blinkt kurz → Pfad wurde nicht übergeben. Schritt 2 erneut ausführen, Explorer neu starten.
- Nicht in „Öffnen mit“ → Über „Auf diesem PC suchen“ `ddnet_control.exe` wählen und „Immer verwenden…“ aktivieren.
- Icon ändert sich nicht → Explorer neu starten (Icon‑Cache).
- Kein Hot‑Reload → Server `127.0.0.1:8303` und RCON prüfen; Log ansehen.
- Verknüpfung entfernen → `registry\remove_map_association_current_user.bat`

## 📂 Inhalt
- `ddnet_control.exe`
- `ddnet_loader.ico`
- `myServerconfig.cfg`
- `registry/`
  - `setup_map_association_current_user.bat`
  - `remove_map_association_current_user.bat`