# 🛡️ Last War: Survival – Hive Generator & Planer

Ein interaktives Web-Tool, entwickelt mit **Streamlit** und **Python**, um das Allianz-HQ (Hive) im Spiel *Last War: Survival* strategisch zu planen. Das Tool liest eine Mitgliederliste im JSON-Format ein und platziert Spielerbasen automatisch basierend auf Allianz-Rängen (R4/R3), Kampfkraft (Power) und gewünschten Partner-Ketten (Nachbarschaften).

---

## 🚀 Features

*   **Zwei-Zentren-Logik:** Unterstützt die gleichzeitige Platzierung um die **Marshall-Wache** (Hive-Center) und eine optionale **Stadt/Stronghold**.
*   **Intelligentes Matchmaking:** Spieler können Wunschpartner in der JSON-Datei angeben (z. B. für Ehepartner oder Kumpels), um automatisch nebeneinander platziert zu werden.
*   **Sicherheitsabstand-Warner:** Überprüft automatisch, ob der Stronghold den Mindestabstand zur Wache einhält, um In-Game-Überschneidungen zu verhindern.
*   **Flexibles Koordinatensystem:** Die Achsenrichtungen (X/Y) lassen sich flexibel spiegeln, um sie exakt an dein In-Game-Layout anzupassen.
*   **High-Res Export:** Generiert eine visuelle Karte (PNG) inklusive In-Game-Koordinatenbeschriftung auf jeder Basis sowie eine exportierbare Textliste (TXT) für die Allianz-Mail.

---

## 📂 JSON-Struktur (`allianz.json`)

Um deine Allianzmitglieder einzulesen, benötigt das Tool eine `.json`-Datei. Du kannst Partner definieren, die nah beieinander stehen möchten. Wenn kein Partner gewünscht ist, trage `"null"` ein.

Hier ist ein Beispiel für die Struktur:

```json
[
  {
    "name": "Spieler 1",
    "rang": "r4",
    "power": 120000000,
    "partner": "null"
  },
  {
    "name": "Spieler 2",
    "rang": "r4",
    "power": 105000000,
    "partner": "Spieler 3"
  },
  {
    "name": "Spieler 3",
    "rang": "r3",
    "power": 95000000,
    "partner": "Spieler 2"
  }
]




git clone [https://github.com/DEIN-GITHUB-NAME/DEIN-REPO-NAME.git](https://github.com/DEIN-GITHUB-NAME/DEIN-REPO-NAME.git)
    cd DEIN-REPO-NAME
    ```

2.  **Abhängigkeiten installieren:**
    Stelle sicher, dass du Python installiert hast. Installiere dann die benötigten Bibliotheken via `requirements.txt`:
```bash
    pip install -r requirements.txt
    ```

3.  **Streamlit App starten:**
```bash
    streamlit run Last_War_Hive_Generator.py
    ```
    Die App öffnet sich anschließend automatisch in deinem Standardbrowser unter `http://localhost:8501`.

---

## 📦 Verwendete Technologien

*   [Python 3](https://www.python.org/) - Die Programmiersprache.
*   [Streamlit](https://streamlit.io/) - Für das interaktive Web-UI.
*   [Matplotlib](https://matplotlib.org/) - Zur Generierung und Zeichnung der Grid-Karte.
*   [NumPy](https://numpy.org/) - Für die Matrix-Berechnungen und Distanzprüfungen.

---

## 📄 Lizenz

Dieses Projekt ist für private Allianz-Zwecke frei verwendbar (MIT License). Guten Wirkungsgrad beim Aufbau deines Hives! 👑