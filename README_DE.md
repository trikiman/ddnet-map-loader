# DDNet Map Loader - Benutzerhandbuch

## Übersicht
DDNet Map Loader ist ein Werkzeug, mit dem Sie schnell Karten auf Ihrem DDNet-Server austauschen können, während die Spielerpositionen durch eine Hot-Reload-Funktion erhalten bleiben.

## Voraussetzungen
1. DDNet-Server auf Ihrem Computer installiert
2. Server mit ECON-Passwort konfiguriert (Anweisungen unten)
3. Karten im DDNet-Kartenverzeichnis (Anweisungen unten)

## Kartenordner-Setup
1. Erstellen Sie das Kartenverzeichnis, falls es nicht existiert:
   ```
   C:\Users\[Benutzername]\AppData\Roaming\DDNet\maps
   ```
2. Kopieren Sie die mitgelieferte `tutorial.map` aus dem `maps`-Ordner nach:
   ```
   C:\Users\[Benutzername]\AppData\Roaming\DDNet\maps\tutorial.map
   ```
   Dies ist erforderlich, da es sich um die Standard-Karte für den Server handelt.

3. Alle zusätzlichen Karten, die Sie verwenden möchten, sollten ebenfalls in dieses Verzeichnis kopiert werden.

Hinweis: Der Kartenordner ist nach der DDNet-Installation standardmäßig leer. Ohne die tutorial-Karte funktionieren Server und Map Loader nicht ordnungsgemäß.

## Server-Setup
1. Navigieren Sie zum DDNet-Serververzeichnis (z.B. `C:\Users\[Benutzername]\Desktop\DDNet-18.7-win64\`)
2. Gehen Sie in den `data`-Ordner
3. Kopieren Sie die mitgelieferte `myServerconfig.cfg` in diesen Ordner
4. Starten Sie den Server mit dem Befehl:
   ```batch
   DDNet-Server.exe -f myServerconfig.cfg
   ```

### Server-Konfigurationsdetails
Die mitgelieferte `myServerconfig.cfg` enthält:
```
sv_name "DDNet Map Loader Server"    # Servername
sv_port 8303                         # Spielport
sv_max_clients 16                    # Maximale Spieler
sv_rcon_password "test123"          # Admin-Passwort
sv_rcon_mod_password "test123"      # Moderator-Passwort
ec_port 8303                        # Externe Konsolen-Port
ec_password "test123"               # Externes Konsolenpasswort (für Map Loader)
ec_bindaddr "127.0.0.1"            # Nur localhost
sv_map "tutorial"                   # Startkarte (muss im maps-Ordner existieren)
```

Bei Änderungen stellen Sie sicher, dass:
1. `ec_port` und `ec_password` mit den Map Loader-Einstellungen übereinstimmen
2. `ec_bindaddr` aus Sicherheitsgründen auf "127.0.0.1" bleibt
3. Passwörter auf sicherere Werte geändert werden
4. `sv_map` auf eine existierende Karte in Ihrem maps-Ordner zeigt

## Installation
1. Platzieren Sie `ddnet_control.exe` in einem beliebigen Ordner
2. Doppelklicken Sie auf eine beliebige `.map`-Datei zur Verwendung

## Verwendung
### Methode 1: Doppelklick
1. Doppelklicken Sie einfach auf die `.map`-Datei, die Sie laden möchten
2. Das Tool wird automatisch:
   - Ein Backup der aktuellen Karte erstellen
   - Die aktuelle Karte durch die neue ersetzen
   - Den Server neu laden, um Spielerpositionen zu erhalten

### Methode 2: Kommandozeile
```batch
ddnet_control.exe [Kartenpfad] [Optionen]
```
Optionen:
- `--skip-backup`: Backup überspringen
- `--restore`: Letztes Backup wiederherstellen statt Karte zu ersetzen

## Verzeichnisstruktur
Hier ist die vollständige Verzeichnisstruktur, die Sie benötigen:
```
C:\Users\[Benutzername]\AppData\Roaming\DDNet\
└── maps\
    ├── tutorial.map      # Erforderliche Standardkarte
    └── [Ihre Karten].map # Ihre zusätzlichen Karten

C:\Users\[Benutzername]\Desktop\DDNet-18.7-win64\
└── data\
    └── myServerconfig.cfg    # Serverkonfiguration
```

## Fehlerbehebung
1. Wenn sich das Programm nicht mit dem Server verbinden kann:
   - Stellen Sie sicher, dass der DDNet-Server mit der richtigen Konfiguration läuft
   - Überprüfen Sie das ECON-Passwort in `myServerconfig.cfg`
   - Überprüfen Sie den korrekten Port (8303)

2. Wenn der Kartenaustausch fehlschlägt:
   - Überprüfen Sie die Zugriffsrechte für das Kartenverzeichnis
   - Stellen Sie sicher, dass die Kartendatei nicht von einem anderen Prozess verwendet wird
   - Überprüfen Sie das Vorhandensein des maps-Verzeichnisses in `%AppData%\DDNet\maps`

3. Wenn der Server nicht startet:
   - Stellen Sie sicher, dass tutorial.map in Ihrem maps-Verzeichnis existiert
   - Überprüfen Sie, ob die in `sv_map` angegebene Karte existiert
   - Überprüfen Sie alle Pfade und Zugriffsrechte

## Sicherheitshinweise
- Die Standard-Passwörter in der Konfigurationsdatei sind nur für Tests gedacht
- Ändern Sie in der Produktionsumgebung alle Passwörter auf sichere, eindeutige Werte
- Die externe Konsole ist aus Sicherheitsgründen nur an localhost gebunden
- Teilen Sie die Serverkonfiguration nur mit vertrauenswürdigen Administratoren

## Anmerkungen
- Das Programm erstellt automatisch Backups vor dem Kartenaustausch
- Spielerpositionen bleiben beim Kartenwechsel erhalten
- Der Server muss für das Tool laufen
- Bewahren Sie immer eine Kopie von tutorial.map in Ihrem maps-Verzeichnis auf
