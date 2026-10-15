# Briefkasten privat machen (optional)

Heute landen Einsendungen im Zweig `eingang` dieses **öffentlichen** Repos. Namen und Notizen sind dort für alle lesbar,
und jeder Helfer-Schlüssel darf in dieses Repo schreiben. Mit einem privaten Eingangs-Repo gilt:

- Die Helfer schreiben nur noch in ein privates Repo `wangerooge-eingang`.
- Ins öffentliche Repo, in die Karte und in die Pull Requests kommen nur noch Kürzel („A. M.“) statt Namen.
- Abgelehnte Einsendungen werden im privaten Repo beiseitegelegt.

Die App liest das Ziel beim Start aus `briefkasten.json`. Ein neuer App-Build ist dafür nicht nötig.

Dauer: ca. 15 Minuten. Reihenfolge einhalten.

1. **Privates Repo anlegen**: <https://github.com/new>
   - Name `wangerooge-eingang`
   - **Private**
   - Häkchen bei „Add a README file“
   - „Create repository“
2. **Ordner anlegen**: <https://github.com/JNKersken/wangerooge-eingang/new/main?filename=eingang/.gitkeep>
   - Nichts eintippen, „Commit changes…“ → „Commit changes“.
3. **Schlüssel für den Workflow**: <https://github.com/settings/personal-access-tokens/new>
   - Token name: `Feldcheck Eingang`
   - Expiration: 1 Jahr
   - Repository access: *Only select repositories* → `wangerooge-eingang`
   - Permissions → Repository permissions → **Contents: Read and write**
   - „Generate token“, dann den Schlüssel kopieren.
4. **Als Secret im Karten-Repo speichern**: <https://github.com/JNKersken/wangerooge-feldcheck/settings/secrets/actions/new>
   - Name `INBOX_TOKEN`
   - Secret: den Schlüssel aus 3 einfügen
   - „Add secret“
5. **Umschalten**: <https://github.com/JNKersken/wangerooge-feldcheck/edit/main/briefkasten.json>
   - Inhalt ersetzen durch

     ```json
     {
      "repo": "JNKersken/wangerooge-eingang",
      "zweig": "main",
      "ordner": "eingang",
      "melden": false
     }
     ```

   - „Commit changes…“ → „Create a new branch … and start a pull request“ → „Propose changes“
   - Pull Request anlegen und zusammenführen.
   - Nach ein bis zwei Minuten senden alle Apps beim nächsten Start ins private Repo.
6. **Neue Helfer-Schlüssel**: Jeder Helfer braucht einen Schlüssel für das private Repo.
   - Wie in 3 erstellen, aber pro Helfer, z. B. `Feldcheck Anna`: nur `wangerooge-eingang`, **Contents: Read and write**.
   - Dann in der App: Menü (•••) → Briefkasten → „Helfer einladen“ → Link schicken.
   - Die alten Helfer-Schlüssel für das Karten-Repo löschen: <https://github.com/settings/personal-access-tokens>
7. **Sofort melden (optional)**: Ohne diesen Schritt kommen Einsendungen mit dem täglichen Lauf um 6:17 Uhr. Von Hand geht es hier: <https://github.com/JNKersken/wangerooge-feldcheck/actions/workflows/feldcheck.yml> → „Run workflow“.
   - Schlüssel erstellen: <https://github.com/settings/personal-access-tokens/new>
     - Name `Feldcheck melden`
     - nur `wangerooge-feldcheck`
     - Permissions → **Actions: Read and write**
   - Als Secret `KARTE_TOKEN` im **privaten** Repo speichern: <https://github.com/JNKersken/wangerooge-eingang/settings/secrets/actions/new>
   - Workflow anlegen: <https://github.com/JNKersken/wangerooge-eingang/new/main?filename=.github/workflows/weiterleiten.yml>
     - Inhalt von [`karte/briefkasten/weiterleiten.yml`](briefkasten/weiterleiten.yml) einfügen
     - „Commit changes“
8. **Aufräumen**: Den Zweig `eingang` im Karten-Repo löschen. Er enthält die alten Einsendungen mit Namen: <https://github.com/JNKersken/wangerooge-feldcheck/branches>

Zurück zum öffentlichen Briefkasten: `briefkasten.json` wieder auf
`{"repo": "JNKersken/wangerooge-feldcheck", "zweig": "eingang", "ordner": "karte/data/feldcheck/eingang", "melden": true}` setzen.

## Was die Prüfung am Vorschlag bedeutet

Bevor der Bot einen Pull Request anlegt, laufen drei Prüfungen:

- die Regeln für Einsendungen (`karte/tests`)
- der Zusammenhang von App, Daten und Exporten (`karte/scripts/check.py`)
- die App im Browser (`karte/tests/smoke.js`)

Das Ergebnis steht am Pull Request als „Feldcheck-Prüfung“ (✓ oder ✗) und im Text. Bei ✗ nicht zusammenführen.

Unter „⚠ Bitte genauer ansehen“ listet der Bericht mit Kartenausschnitt:

- Verschiebungen über 75 m
- GPS ungenauer als 20 m
- Bewertungen aus mehr als 150 m Entfernung
- Widersprüche zwischen Helfern
- mögliche Doppelte, auch doppelte SOS-Nummern
