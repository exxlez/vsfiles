# Technische Dokumentation: Allianz-Hive-Layout-Optimierer

Diese Dokumentation beschreibt die mathematischen, algorithmischen und visuellen Prinzipien des Allianz-Hive-Planers basierend auf der vorliegenden Code-Struktur. Das Skript dient dazu, Spielerbasen unter Berücksichtigung von In-Game-Koordinaten, strukturellen Verbotszonen, Partnerbeziehungen und Kampfkraft (Power) strategisch optimal um ein Zentrum zu platzieren.

---

## 1. Koordinatensystem & Matrix-Transformation

Das Spiel verwendet ein globales Koordinatensystem, während die Berechnungen und Platzierungen auf einer optimierten, lokalen 2D-Matrix (`NumPy`-Grid) stattfinden.

### 1.1 Dynamische Matrix-Zentrierung (Bounding Box)
[cite_start]Um Speicherplatz zu sparen und Berechnungen zu beschleunigen, baut der Code ein minimal notwendiges Rechenraster auf[cite: 6]. 
* [cite_start]Es ermittelt die Extrempunkte (Minimum und Maximum) aller permanenten In-Game-Objekte (Hauptstadt und Wache)[cite: 6].
* [cite_start]Ein Sicherheitsabstand (`padding = 60`) wird in alle vier Richtungen addiert, um genügend Raum für die Spieler-Basen zu gewährleisten[cite: 6].
* [cite_start]Die finale Matrix-Größe (`grid_w`, `grid_h`) berechnet sich dynamisch aus der Differenz dieser Werte[cite: 6].

### 1.2 Achsentransformation & Invertierung
[cite_start]Da In-Game-Koordinaten je nach Server-Ausrichtung unterschiedlich ansteigen können, verfügt das System über zwei Konfigurations-Flags (`X_VON_LINKS_NACH_RECHTS`, `Y_VON_UNTEN_NACH_OBEN`)[cite: 2, 3].
* [cite_start]**`to_grid_x(game_x)` / `to_grid_y(game_y)`:** Transformiert eine echte In-Game-Koordinate in einen internen Matrix-Index (beginnend bei `0`)[cite: 7].
* [cite_start]**`to_game_coords(mx, my)`:** Rechnet einen internen Matrix-Index zurück in die echten In-Game-Koordinaten[cite: 7]. [cite_start]Hierbei wird die Achsenrichtung (Invertierung) direkt mathematisch berücksichtigt, um verfälschte Koordinaten-Labels im Plot zu verhindern[cite: 7, 8].

---

## 2. Kollisionsprüfung & Verbotszonen (Sperrbezirke)

Bevor eine Basis platziert werden kann, prüft das System potenzielle Kollisionen mit der Umgebung. Statt rechenintensiver Matrix-Abfragen nutzt der Code hocheffiziente Koordinaten-Mengen (`Sets`).

### 2.1 Set-basierte Blockierung
* **Marshall-Wache:** Die 3x3 Felder der Wache werden direkt als blockiert markiert.
* [cite_start]**Hauptstadt (Stronghold):** Die Hauptstadt hat eine physische Größe von 13x13 Feldern[cite: 5]. Der Code definiert eine logische Sperrzone von `Zentrum - 5` bis `Zentrum + 5` Feldern.
* **`is_game_position_blocked(gx, gy)`:** Diese Funktion generiert für jede anzufragende 3x3 Spielerbasis die X- und Y-Koordinatenbereiche als Set. Mittels der mathematischen Schnittmenge (`&`) wird in konstanter Zeit ($O(1)$) geprüft, ob sich die Spielerbasis mit den Sperrzonen der Wache oder der Hauptstadt überschneidet.

### 2.2 Teilweise Überlappung der Hauptstadt
[cite_start]Das interne Berechnungsraster nutzt einen mathematischen Kniff: Im unsichtbaren Rechen-Grid (`grid`) blockiert die Hauptstadt nur einen geschrumpften Kern (11x11 statt 13x13)[cite: 10]. [cite_start]Dies erlaubt es dem Algorithmus, Spielerbasen bis auf ein Feld an den visuellen Rand der Hauptstadt heranzurücken [cite: 9, 10][cite_start], während im finalen Plot das Gebäude in voller 13x13 Pracht gezeichnet wird[cite: 10, 11].

---

## 3. Graphen-basierte Gruppenbildung & Initialplatzierung

Die Anordnung der Spieler erfolgt nicht zufällig, sondern bildet soziale Gefüge und Hierarchien ab.

### 3.1 Beziehungs-Clustering (BFS-Graph)
[cite_start]Das Skript liest die `allianz.json` ein[cite: 15]. Das Feld `"partner"` wird als ungerichtete Kante in einer Adjazenzliste (`adj`) interpretiert.
1. Mittels Breitensuche (**Breadth-First Search / BFS**) identifiziert der Code zusammenhängende Komponenten (Spieler-Cluster, die direkt oder indirekt über Partner miteinander verbunden sind).
2. Innerhalb eines Clusters wird eine logische Kette gebildet: Der Einstiegspunkt ("Kopf") ist immer das Mitglied mit dem höchsten Rang (R4) bzw. der höchsten Kampfkraft.
3. Entlang der Verwandtschaftslinien (`adj`) werden die Partner nacheinander in eine Warteschlange eingereiht, damit zusammengehörige Paare im späteren Verlauf beieinanderbleiben.

### 3.2 Slot-Generierung und radiale Vorsortierung
[cite_start]Das System scannt die Karte in Schritten von 5 Feldern ab (`base_size 3` + `spacing 2`)[cite: 12]. Alle freien, nicht blockierten Slots werden in zwei Listen erfasst:
* **`possible_slots_for_r4`:** Sortiert nach euklidischer Distanz zur **Marshall-Wache** (Zentrierung der Führungsebene).
* **`possible_slots_for_r1`:** Sortiert nach euklidischer Distanz zum **mathematischen Hive-Zentrum** (Zentrierung der normalen Mitglieder).

### 3.3 Konzentrische Platzierung (Layer-Wachstum)
* Der Gruppenführer wird auf dem global besten verfügbaren Platz seiner Kategorie gesetzt.
* Alle direkten Nachfolger (Partner) werden nicht global gesucht, sondern in **konzentrischen Ringen (Layer 1 bis 7)** direkt um den Gruppenführer herum platziert. Das garantiert, dass Beziehungsketten geschlossen im selben Quadranten des Hives siedeln.

---

## 4. Der intelligente Gruppen-Optimierer (Block-Swap)

Da die initiale Platzierung durch die sequenzielle Abarbeitung der Warteschlange suboptimal sein kann, besitzt der Code ein evolutionäres Optimierungs-Modul.

### 4.1 Funktionsweise des Block-Tauschs
In bis zu **1500 Iterationen** vergleicht der Algorithmus Paare von Spielern (`p1` und `p2`) desselben Rang-Typs.
1. Er ermittelt die vollständigen Partnergruppen beider Spieler über das Beziehungsnetzwerk.
2. Haben beide Gruppen dieselbe strukturelle Größe (z. B. zwei Paare oder zwei Einzelgänger), evaluiert er einen Tausch.
3. **Das Optimierungsziel:** Wenn die summierte Kampfkraft von Gruppe B größer ist als die von Gruppe A, Gruppe B aber gleichzeitig weiter vom strategischen Ziel (Wache oder Hive-Mitte) entfernt steht, werden die Positionen der gesamten Blöcke testweise getauscht.

### 4.2 Post-Swap-Validierung und Rollback
Nach jedem Tausch prüft das System, ob die harte Restriktion verletzt wurde: Die Partner-Distanz darf nach dem Tausch den Wert von `MAX_PARTNER_DIST = 11.0` nicht überschreiten. Verreißt der Tausch ein Paar über diese Distanz hinaus, wird ein sofortiges **Rollback** (Rückgängigmachen des Tauschs) durchgeführt. Nur valide, verbessernde Swaps werden permanent beibehalten.

---

## 5. Visualisierung & Kamera-Management

[cite_start]Die Ausgabe erfolgt über ein hochauflösendes `matplotlib`-Diagramm[cite: 23].

* [cite_start]**Dynamischer Viewport:** Um zu verhindern, dass die Karte leer gezeichnet wird, sammelt der Code vor dem Plotten alle minimalen und maximalen X/Y-Koordinaten der tatsächlich platzierten Objekte[cite: 22]. [cite_start]Die Achsenbegrenzung (`ax.set_xlim` / `ax.set_ylim`) wird exakt auf diesen Bereich plus einen kleinen Puffer angepasst[cite: 22, 23].
* [cite_start]**Invertierung:** Entsprechend der Konfiguration am Anfang des Skripts werden die Achsen visuell gespiegelt (`ax.invert_xaxis()` / `ax.invert_yaxis()`), um den In-Game-Blickwinkel exakt zu simulieren[cite: 24].

---

## 6. Architektur-Fahrplan: Integration einer City

Um neben dem Stronghold (Hauptstadt) und der Wache eine zusätzliche strategische **City** (z. B. eine einnehmbare Stadt auf der Karte) einzuplanen, muss die bestehende Code-Architektur an exakt vier Punkten erweitert werden. Da das System modular aufgebaut ist, sind dafür keine strukturellen Änderungen am Algorithmus nötig.

### Schritt 1: Definition der City-Konstanten
Analog zur Hauptstadt und Wache müssen die realen In-Game-Eckdaten der City im Setup-Bereich hinterlegt werden:
* `city_in_game_x` und `city_in_game_y` (Die echten Koordinaten auf der Karte).
* `city_size` (Die physische Kantenlänge der City, z. B. `7` für eine 7x7 Felder große Stadt).

### Schritt 2: Erweiterung der Set-basierten Kollisionsprüfung
Damit keine Spielerbasen in oder auf der City platziert werden, muss eine neue Verbotszone deklariert werden:
1. Erstellen von `city_blocked_x` und `city_blocked_y` als Koordinaten-Sets (unter Verwendung von `range(city_in_game_x, city_in_game_x + city_size)`). Falls gewünscht, kann hier direkt ein zusätzlicher Puffer addiert werden (z. B. `+ 2` für freie Aufmarschwege).
2. In der Funktion `is_game_position_blocked(gx, gy)` muss eine dritte `if`-Bedingung eingefügt werden, die prüft, ob die Schnittmenge (`&`) zwischen den Spielerfeldern und den City-Sets Werte enthält. Wenn ja, gibt die Funktion `True` zurück und sperrt den Slot.

### Schritt 3: Slot-Vorsortierung anpassen (Optional)
Falls bestimmte Spielergruppen (z. B. R2-Kampftruppen) primär an der City und nicht an der Wache oder dem Hauptzentrum siedeln sollen:
1. Eine neue Liste `possible_slots_for_city` erstellen.
2. Während der Slot-Generierungsschleife die euklidische Distanz zwischen dem Slot und den City-Koordinaten berechnen: `d_city = np.sqrt((gx - city_in_game_x)**2 + (gy - city_in_game_y)**2)`.
3. Die Liste nach `dist` sortieren und beim Zuweisen der Spieler-Warteschlange als primären Suchpool für die gewünschte Rang-Klasse definieren.

### Schritt 4: Registrierung im Zeichen-Modul (Plot)
Damit die City auf der finalen Grafik sichtbar ist, muss sie in die Objektliste aufgenommen werden:
1. Berechnen der lokalen Matrix-Koordinaten mittels `to_grid_x(city_in_game_x)` und `to_grid_y(city_in_game_y)`.
2. Das Objekt mit dem Typ `"city"` an die Liste `placed_objects` anhängen (inklusive Name, Breite und Höhe).
3. Im Visualisierungsbereich das Dictionary `colors` um den Eintrag `"city"` erweitern (z. B. mit einem Hex-Farbcode wie `"#8a2be2"` für Lila), damit das Grafikmodul die Stadt automatisch mit der korrekten Farbe und Skalierung zeichnet.