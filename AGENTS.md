# Projektinformationen und Richtlinien

Dieses Repository enthält "QISsy", eine FastAPI-Anwendung zum Zugriff auf ein QIS‑System.
Die API ist versioniert und legt den Fokus auf saubere Pydantic‑Modelle und eine
konsequente Testabdeckung. Die folgenden Richtlinien sollen eingehalten werden:

## Allgemeine Hinweise

- Die Konfiguration wird aus einer `config.json` gelesen. Eine Vorlage
  befindet sich in `config_example.json`. **Keine sensiblen Konfigurationsdaten
  einchecken.**
- Logging erfolgt über das in `logging_config.py` definierte `logger`‑Objekt.
  Verwende `logger` statt `print`.
- Tests befinden sich im Verzeichnis `tests/` und werden mit `pytest` ausgeführt.
- Neue API‑Routen liegen im entsprechenden Versionsordner unter `versions/`.
- Die QIS‑Kürzel für Leistungsarten (`ScoreType`) und Status (`ScoreStatus`) sind
  in `versions/v1/models.py` als Enums hinterlegt. Die vom QIS verwendeten
  **Vermerke** (z.B. `RTE`, `LAN`, `TA`) sind dort ebenfalls als Kommentarblock
  dokumentiert und sollen in Zukunft als eigenes Enum implementiert werden.

## Richtlinien für Beiträge

1. **Logging benutzen**
   - Verwende für Ausgaben stets das `logging`‑Modul. Beispiel:
     ```python
     from logging_config import logger
     logger.info("Nachricht")
     ```
2. **Unit‑Tests schreiben**
   - Für neue Funktionen oder Bugfixes müssen passende Tests erstellt werden.
   - Nutze `responses` oder `httpx` um HTTP‑Anfragen zu mocken. **Niemals gegen
     den echten QIS‑Server testen.**
   - Test‑Fixtures dürfen **niemals** eine `config.json` im Projektroot anlegen
     oder löschen (die echte Konfiguration würde überschrieben!). Stattdessen
     `tmp_path` zusammen mit `monkeypatch.chdir(tmp_path)` verwenden, siehe
     Fixtures in `tests/test_utils.py` und `tests/test_routes.py`.
   - Führe lokal `pytest -q` aus und stelle sicher, dass alle Tests erfolgreich
     sind, bevor du pushst.
3. **Code‑Stil**
   - Orientiere dich an PEP8 (4 Leerzeichen, sprechende Namen, Typannotationen).
   - Bevorzuge Funktionen mit klaren Rückgabewerten und ausführlicher
     Docstring‑Beschreibung.
4. **Versionierung der API**
   - Erweiterungen der API erfolgen in den vorhandenen Versionsordnern, z.B.
     `versions/v1/`. Ändere die Versionsnummer nur, wenn eine inkompatible
     Änderung notwendig ist.
5. **Dokumentation aktualisieren**
   - Bei neuen Features muss die `README.md` ergänzt werden.
6. **Keine Hard‑Coding von Pfaden**
   - Nutze die Konfigurationsfunktionen aus `config.py` um URLs oder andere
     Einstellungen zu beziehen.
7. **Docker**
   - Der `dockerfile` baut die Anwendung auf Python 3.10 auf. Beim Deployment
     werden Konfigurationswerte über das Build‑Argument `CONFIG_CONTENT`
     eingebunden.

## Tests ausführen

Zum Ausführen der Tests verwende:
```bash
pytest -q
```
Alle Tests müssen erfolgreich sein, bevor ein Pull Request erstellt wird.
