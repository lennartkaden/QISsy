# Projektinformationen und Richtlinien

Dieses Repository enthält "QISsy", eine FastAPI-Anwendung zum Zugriff auf ein QIS‑System.
Die API ist versioniert und legt den Fokus auf saubere Pydantic‑Modelle und eine
konsequente Testabdeckung. Die folgenden Richtlinien sollen eingehalten werden:

## Allgemeine Hinweise

- Die Konfiguration wird aus einer `config.json` gelesen. Eine Vorlage
  befindet sich in `config_example.json`. **Keine sensiblen Konfigurationsdaten
  einchecken.**
- Logging erfolgt über das in `app/core/logging.py` definierte `logger`‑Objekt.
  Verwende `logger` statt `print`.
- Tests befinden sich im Verzeichnis `tests/` und werden mit `pytest` ausgeführt.
- Neue API‑Routen liegen im entsprechenden Versionsordner unter `app/api/`.
- Vor jeder neuen Entwicklung muss das Dokument `ARCHITECTURE.md` gelesen
  und die dort beschriebenen Vorgaben berücksichtigt werden.

## Richtlinien für Beiträge

1. **Logging benutzen**
   - Verwende für Ausgaben stets das `logging`‑Modul. Beispiel:
     ```python
     from app.core.logging import logger
     logger.info("Nachricht")
     ```
2. **Unit‑Tests schreiben**
   - Für neue Funktionen oder Bugfixes müssen passende Tests erstellt werden.
   - Nutze `responses` oder `httpx` um HTTP‑Anfragen zu mocken.
   - Führe lokal `pytest -q` aus und stelle sicher, dass alle Tests erfolgreich
     sind, bevor du pushst.
3. **Code‑Stil**
   - Orientiere dich an PEP8 (4 Leerzeichen, sprechende Namen, Typannotationen).
   - Bevorzuge Funktionen mit klaren Rückgabewerten und ausführlicher
     Docstring‑Beschreibung.
4. **Versionierung der API**
   - Erweiterungen der API erfolgen in den vorhandenen Versionsordnern, z.B.
     `app/api/v1/`. Ändere die Versionsnummer nur, wenn eine inkompatible
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
