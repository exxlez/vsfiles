import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import json
import os

Y_VON_UNTEN_NACH_OBEN = True   
X_VON_LINKS_NACH_RECHTS = True  

def load_members(filepath="allianz.json"):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_alliance_grid():
    # --- 1. REAL IN-GAME COORDS & SETUP ---
    # MITTELPUNKT WÄHLEN!
    stronghold_in_game_x, stronghold_in_game_y = 774, 799
    stronghold_size = 13  
    # ACHTUNG! untere links ecke nehmen!
    guard_in_game_x, guard_in_game_y = 756, 803
    guard_size = 3
    
    spacing = 1 #2        
    base_size = 3     
    padding = 60      
    
    min_game_x = min(stronghold_in_game_x, guard_in_game_x) - padding
    max_game_x = max(stronghold_in_game_x + stronghold_size, guard_in_game_x + guard_size) + padding
    min_game_y = min(stronghold_in_game_y, guard_in_game_y) - padding
    max_game_y = max(stronghold_in_game_y + stronghold_size, guard_in_game_y + guard_size) + padding
    
    grid_w = int(max_game_x - min_game_x)
    grid_h = int(max_game_y - min_game_y)
    
    def to_grid_x(game_x): return int(game_x - min_game_x)
    def to_grid_y(game_y): return int(game_y - min_game_y)
    def to_game_coords(mx, my):
        real_x = int(mx + min_game_x) if X_VON_LINKS_NACH_RECHTS else int(max_game_x - mx - base_size)
        real_y = int(min_game_y + my) if Y_VON_UNTEN_NACH_OBEN else int(max_game_y - my - base_size)
        return real_x, real_y

# --- 2. VERBOTENE ZONEN & GRID INIT ---
    guard_blocked_x = set(range(guard_in_game_x, guard_in_game_x + guard_size))
    guard_blocked_y = set(range(guard_in_game_y, guard_in_game_y + guard_size))
    
    # KORREKTUR: Wir nehmen die echten In-Game-Variablen und berechnen 
    # den exakten Startpunkt inklusive des Versatzes von 6 Feldern (-6)
    sh_game_start_x = stronghold_in_game_x - 6
    sh_game_start_y = stronghold_in_game_y - 6
    
    # Das logische Ende berechnet sich aus dem Start + der Größe - 1
    sh_game_ende_x = sh_game_start_x + stronghold_size - 1
    sh_game_ende_y = sh_game_start_y + stronghold_size - 1
    
    # VÖLLIG VARIABEL: Blockierte Zone (immer exakt 1 Feld von den Kanten nach innen versetzt)
    # (Das +1 am Ende sorgt dafür, dass das "sh_game_ende" in der range() inklusive ist)
    stronghold_blocked_x = set(range(sh_game_start_x + 1, sh_game_ende_x))
    stronghold_blocked_y = set(range(sh_game_start_y + 1, sh_game_ende_y))

    def is_game_position_blocked(gx, gy):
        p_x = set(range(gx, gx + base_size))
        p_y = set(range(gy, gy + base_size))
        if (p_x & guard_blocked_x) and (p_y & guard_blocked_y): return True
        if (p_x & stronghold_blocked_x) and (p_y & stronghold_blocked_y): return True
        return False

    grid = np.zeros((grid_h, grid_w), dtype=int)
    sh_x, sh_y = to_grid_x(stronghold_in_game_x) - 6, to_grid_y(stronghold_in_game_y) - 6
    gw_x, gw_y = to_grid_x(guard_in_game_x), to_grid_y(guard_in_game_y)

    # --- 3. HARTE R4 GRENZE & SLOT BERECHNUNG ---
    step = base_size + spacing
    hive_center_game_x = stronghold_in_game_x#(stronghold_in_game_x + guard_in_game_x) / 2
    hive_center_game_y = stronghold_in_game_y#(stronghold_in_game_y + guard_in_game_y) / 2
    
    MAX_R4_DISTANCE = 16.0 
    
    possible_slots_for_r4, possible_slots_for_r3 = [], []
    for row_idx in range(-40, 40):
        target_y = gw_y + (row_idx * step)
        for col_idx in range(-40, 40):
            target_x = gw_x + (col_idx * step)
            if (0 <= target_x < grid_w - base_size) and (0 <= target_y < grid_h - base_size):
                gx, gy = to_game_coords(target_x, target_y)
                if is_game_position_blocked(gx, gy): continue
                
                d_guard = np.sqrt((gx - guard_in_game_x)**2 + (gy - guard_in_game_y)**2)
                d_hive = np.sqrt((gx - hive_center_game_x)**2 + (gy - hive_center_game_y)**2)
                
                if d_guard <= MAX_R4_DISTANCE:
                    possible_slots_for_r4.append({"x": target_x, "y": target_y, "dist": d_guard})
                possible_slots_for_r3.append({"x": target_x, "y": target_y, "dist": d_hive})

    possible_slots_for_r4.sort(key=lambda s: s["dist"])
    possible_slots_for_r3.sort(key=lambda s: s["dist"])

    # --- 4. GRAPHENBILDUNG (GERICHTET FÜR SNAKE-LOGIK) ---
    raw_members = load_members("allianz.json")
    name_to_member = {m["name"].strip().lower(): m for m in raw_members}
    
    adj_undirected = {m["name"].strip().lower(): set() for m in raw_members}
    for m in raw_members:
        u = m["name"].strip().lower()
        p = m.get("partner")
        if p and str(p).lower() != "null":
            v = str(p).strip().lower()
            if v in adj_undirected:
                adj_undirected[u].add(v)
                adj_undirected[v].add(u)

    visited = set()
    snakes = [] 
    
    for m in raw_members:
        start_name = m["name"].strip().lower()
        if start_name not in visited:
            cluster_names = []
            queue = [start_name]
            visited.add(start_name)
            while queue:
                curr = queue.pop(0)
                cluster_names.append(curr)
                for nxt in adj_undirected[curr]:
                    if nxt not in visited:
                        visited.add(nxt)
                        queue.append(nxt)
            
            cluster_members = [name_to_member[n] for n in cluster_names]
            cluster_members.sort(key=lambda x: (0 if x["rang"].upper()=="R4" else 1, -x["power"]))
            
            snake_order = []
            in_snake = set()
            
            snake_order.append(cluster_members[0])
            in_snake.add(cluster_members[0]["name"].strip().lower())
            
            while len(snake_order) < len(cluster_members):
                best_next = None
                for candidate in cluster_members:
                    c_name = candidate["name"].strip().lower()
                    if c_name not in in_snake:
                        if any(s_name in adj_undirected[c_name] for s_name in in_snake):
                            if best_next is None or candidate["power"] > best_next["power"]:
                                best_next = candidate
                
                if best_next:
                    snake_order.append(best_next)
                    in_snake.add(best_next["name"].strip().lower())
                else:
                    for candidate in cluster_members:
                        if candidate["name"].strip().lower() not in in_snake:
                            snake_order.append(candidate)
                            in_snake.add(candidate["name"].strip().lower())
                            break
            
            has_r4 = any(x["rang"].upper() == "R4" for x in snake_order)
            snakes.append({
                "members": snake_order,
                "is_r4_group": has_r4,
                "sort_power": max(x["power"] for x in snake_order)
            })

    snakes.sort(key=lambda x: (0 if x["is_r4_group"] else 1, -x["sort_power"]))

    # --- 5. SNAKE PLATZIERUNG ---
    def is_area_free(sx, sy):
        gx, gy = to_game_coords(sx, sy)
        if is_game_position_blocked(gx, gy): return False
        if not (0 <= sx < grid_w - base_size and 0 <= sy < grid_h - base_size): return False
        return not np.any(grid[sy - spacing : sy + base_size + spacing, sx - spacing : sx + base_size + spacing] > 0)

    placed_players = []
    name_to_placed_coords = {}

    print("-> Starte organische Snake-Platzierung...")
    for snake in snakes:
        for i, member in enumerate(snake["members"]):
            m_name = member["name"].strip().lower()
            m_rang = member["rang"].upper()
            placed = False
            
            if i == 0:
                search_pool = possible_slots_for_r4 if m_rang == "R4" else possible_slots_for_r3
                for slot in search_pool:
                    if is_area_free(slot["x"], slot["y"]):
                        px, py = slot["x"], slot["y"]
                        grid[py : py + base_size, px : px + base_size] = 1
                        placed_players.append({"member": member, "x": px, "y": py})
                        name_to_placed_coords[m_name] = (px, py)
                        placed = True
                        break
            else:
                anchor_x, anchor_y = None, None
                for placed_name in adj_undirected[m_name]:
                    if placed_name in name_to_placed_coords:
                        anchor_x, anchor_y = name_to_placed_coords[placed_name]
                        break 
                
                if anchor_x is not None:
                    for layer in range(1, 10): 
                        local_slots = []
                        for dx in range(-layer, layer + 1):
                            for dy in range(-layer, layer + 1):
                                if abs(dx) == layer or abs(dy) == layer:
                                    fx = anchor_x + (dx * step)
                                    fy = anchor_y + (dy * step)
                                    
                                    if m_rang == "R4":
                                        gx, gy = to_game_coords(fx, fy)
                                        d_guard = np.sqrt((gx - guard_in_game_x)**2 + (gy - guard_in_game_y)**2)
                                        if d_guard > MAX_R4_DISTANCE:
                                            continue 
                                            
                                    local_slots.append({"x": fx, "y": fy, "dist": np.sqrt(dx**2 + dy**2)})
                        
                        local_slots.sort(key=lambda s: s["dist"])
                        for slot in local_slots:
                            if is_area_free(slot["x"], slot["y"]):
                                px, py = slot["x"], slot["y"]
                                grid[py : py + base_size, px : px + base_size] = 1
                                placed_players.append({"member": member, "x": px, "y": py})
                                name_to_placed_coords[m_name] = (px, py)
                                placed = True
                                break
                        if placed: break
                
                if not placed:
                    print(f"Warnung: {member['name']} konnte nicht an Kette andocken. Fallback Global.")
                    search_pool = possible_slots_for_r4 if m_rang == "R4" else possible_slots_for_r3
                    for slot in search_pool:
                        if is_area_free(slot["x"], slot["y"]):
                            px, py = slot["x"], slot["y"]
                            grid[py : py + base_size, px : px + base_size] = 1
                            placed_players.append({"member": member, "x": px, "y": py})
                            name_to_placed_coords[m_name] = (px, py)
                            placed = True
                            break

    # --- 6. DETAILS GENERIEREN & ZEICHNEN ---
    placed_objects = []
    placed_objects.append({"name": f"Stronghold Lv5", "x": sh_x, "y": sh_y, "w": stronghold_size, "h": stronghold_size, "type": "stronghold"})
    placed_objects.append({"name": f"Wache", "x": gw_x, "y": gw_y, "w": guard_size, "h": guard_size, "type": "guard"})

    for p in placed_players:
        mx, my = p["x"], p["y"]
        m = p["member"]
        real_x, real_y = to_game_coords(mx, my)
        
        center_x = real_x + 1
        center_y = real_y + 1
        
        placed_objects.append({
            "name": f"{m['name']}\n{center_x}|{center_y}", 
            "x": mx, "y": my, "w": base_size, "h": base_size, 
            "type": m["rang"].lower(),
            "center_coords": f"{center_x}|{center_y}" # Merken wir uns für die TXT
        })

    # DIESER TEIL HAT GEFEHLT: Kamera-Limits berechnen
    all_x = [obj["x"] for obj in placed_objects] + [obj["x"]+obj["w"] for obj in placed_objects]
    all_y = [obj["y"] for obj in placed_objects] + [obj["y"]+obj["h"] for obj in placed_objects]
    view_min_x, view_max_x = max(0, min(all_x) - 4), min(grid_w, max(all_x) + 4)
    view_min_y, view_max_y = max(0, min(all_y) - 4), min(grid_h, max(all_y) + 4)

    fig, ax = plt.subplots(figsize=(30, 30), dpi=300) 
    ax.set_aspect('equal')
    ax.set_facecolor('#1e251c') 
    
   # DIESER TEIL HAT GEFEHLT: Achsen setzen und Grid zeichnen
    ax.set_xlim(view_min_x, view_max_x)
    ax.set_ylim(view_min_y, view_max_y)
    
    # 1. Haupt-Gitterpunkte (Major) alle 5 Felder mit Beschriftung
    x_ticks_major = np.arange(view_min_x, view_max_x, 5)
    y_ticks_major = np.arange(view_min_y, view_max_y, 5)
    ax.set_xticks(x_ticks_major)
    ax.set_yticks(y_ticks_major)
    ax.set_xticklabels([str(int(x + min_game_x)) for x in x_ticks_major], fontsize=12, color='white', rotation=45)
    ax.set_yticklabels([str(int(min_game_y + y)) for y in y_ticks_major], fontsize=12, color='white')
    
    # 2. NEU: Unter-Gitterpunkte (Minor) exakt für jedes einzelne Feld (1er-Schritte)
    x_ticks_minor = np.arange(view_min_x, view_max_x, 1)
    y_ticks_minor = np.arange(view_min_y, view_max_y, 1)
    ax.set_xticks(x_ticks_minor, minor=True)
    ax.set_yticks(y_ticks_minor, minor=True)
    
    # 3. Beide Gitter unterschiedlich stark zeichnen
    ax.grid(True, which='major', color='#2d382a', linestyle='-', linewidth=0.8) # Dickere 5er Linien
    ax.grid(True, which='minor', color="#596157", linestyle=':', linewidth=0.4) # Sehr feine, gestrichelte 1er Linien
    
    colors = {"stronghold": "#b22222", "guard": "#ff8c00", "r4": "#1e90ff", "r3": "#2e8b57"}
    
    for obj in placed_objects:
        rect = patches.Rectangle((obj["x"], obj["y"]), obj["w"], obj["h"], linewidth=1.5, edgecolor='#ffffff', facecolor=colors.get(obj["type"], "#4682b4"), alpha=0.9)
        ax.add_patch(rect)
        font_sz = 10.0 if obj["type"] in ["r4", "r3"] else 20.0
        ax.text(obj["x"] + obj["w"]/2, obj["y"] + obj["h"]/2, obj["name"], color="white", fontsize=font_sz, fontweight='bold', ha='center', va='center', clip_on=True)

        # --- NEUE FUNKTION: KOORDINATEN IN TXT SPEICHERN ---
    def save_coordinates_to_txt(objects, filename="allianz_koordinaten.txt"):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("Allianz Hive Plan - Koordinaten & Basen\n")
            f.write("=======================================\n\n")
            for obj in objects:
                # Zeilenumbruch aus dem 'name'-Feld (z.B. "Name\nX:123 Y:456") durch ein Trennzeichen ersetzen
                clean_info = obj["name"].replace('\n', ' |  ')
                
                # Basis-Typ formatieren (z.B. r4 -> R4, stronghold -> STRONGHOLD)
                b_type = obj['type'].upper()
                
                f.write(f"[{b_type}] {clean_info}\n")
                
        print(f"-> Koordinaten erfolgreich in '{filename}' gespeichert.")

    # Funktion direkt aufrufen und die Liste 'placed_objects' übergeben
    save_coordinates_to_txt(placed_objects)
        
    plt.title("Allianz Hive Plan - Organische Snake-Platzierung", fontsize=24, color='white', pad=35, weight='bold')
    fig.patch.set_facecolor('#121711')
    
    plt.savefig("hive_snake_map.png", facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    print(">>> ERFOLG! Karte generiert: 'hive_snake_map.png' <<<")



    # =========================================================================
    # NEUER PLOT: DETAILED STRONGHOLD ZONE
    # =========================================================================
    fig_det, ax_det = plt.subplots(figsize=(12, 12), dpi=300)
    ax_det.set_aspect('equal')
    ax_det.set_facecolor('#1e251c')

    # Fokus-Bereich um den Stronghold herum setzen (mit etwas Puffer)
    ax_det.set_xlim(765, 784)
    ax_det.set_ylim(790, 809)

    # Gitter für jedes einzelne Feld (Schrittweite 1)
    ax_det.set_xticks(np.arange(765, 785, 1))
    ax_det.set_yticks(np.arange(790, 810, 1))
    ax_det.grid(True, color='#2d382a', linestyle='-', linewidth=0.7)
    ax_det.tick_params(colors='white', labelsize=10)

    # 1. Äußere reale Grenze (768 bis 780 | 793 bis 805)
    # Da width=13 und height=13, geht die Box exakt bis 781/806 auf den Achsen,
    # umschließt also die Felder 768-780 und 793-805.
    rect_outer = patches.Rectangle((768, 793), 13, 13, linewidth=2.5, 
                                  edgecolor='#ff4747', facecolor='#ff4747', alpha=0.2, 
                                  label='Äußere Grenze (768-780 | 793-805)')
    ax_det.add_patch(rect_outer)

    # 2. Innere BLOCKIERTE Zone (769 bis 779 | 792 bis 804)
    # Start bei 769, Breite 11 (geht bis 780 auf Achse = Feld 779 blockiert)
    # Start bei 792, Höhe 13 (geht bis 805 auf Achse = Feld 804 blockiert)
    rect_blocked = patches.Rectangle((769, 792), 11, 13, linewidth=2, 
                                     edgecolor='#ff0000', facecolor='#ff0000', alpha=0.5, 
                                     linestyle='--', label='Blockierte Zone (Keine Basis!)')
    ax_det.add_patch(rect_blocked)

    # Eckpunkte als Text einzeichnen
    ecken = [
        (768, 805, "Oben Links\n768|805"),
        (780, 805, "Oben Rechts\n780|805"),
        (768, 793, "Unten Links\n768|793"),
        (780, 793, "Unten Rechts\n780|793")
    ]
    for x, y, label in ecken:
        ax_det.plot(x + 0.5, y + 0.5, 'o', color='#ffffff', markersize=8) # Punkt in die Feldmitte
        ax_det.text(x + 0.5, y + 0.5, f" {label}", color='white', fontsize=9, 
                    fontweight='bold', va='center', ha='left', 
                    bbox=dict(facecolor='black', alpha=0.7, edgecolor='none', pad=2))

    # Beschriftung & Legende
    plt.title("Stronghold Detailansicht: Grenzen vs. Blockierte Zone", fontsize=16, color='white', pad=20, weight='bold')
    ax_det.legend(loc='upper right', facecolor='#121711', edgecolor='white', labelcolor='white')
    fig_det.patch.set_facecolor('#121711')

    plt.savefig("stronghold_detail_zone.png", facecolor=fig_det.get_facecolor(), bbox_inches='tight')

    # =========================================================================
    # DYNAMISCHER DETAIL-PLOT: NUR STRONGHOLD & VARIABLE BLOCKIERZONE
    # =========================================================================
    fig_det, ax_det = plt.subplots(figsize=(12, 12), dpi=300)
    ax_det.set_aspect('equal')
    ax_det.set_facecolor('#1e251c')

    # 1. Dynamische Berechnung der blockierten Zone aus deinen Variablen
    min_block_x, max_block_x = min(stronghold_blocked_x), max(stronghold_blocked_x)
    min_block_y, max_block_y = min(stronghold_blocked_y), max(stronghold_blocked_y)
    
    block_width = max_block_x - min_block_x + 1
    block_height = max_block_y - min_block_y + 1

    # 2. Dynamische Berechnung der Stronghold-Außenkanten (Matplotlib-Logik)
    # Startpunkt unten links im Plot ist sh_x + min_game_x, also die echten In-Game-Koordinaten
    sh_plot_x = sh_x + min_game_x
    sh_plot_y = sh_y + min_game_y

    # 3. Kamera-Fokus automatisch um den Stronghold herum anpassen (+4 Felder Puffer)
    ax_det.set_xlim(sh_plot_x - 4, sh_plot_x + stronghold_size + 4)
    ax_det.set_ylim(sh_plot_y - 4, sh_plot_y + stronghold_size + 4)

    # Gitter exakt auf 1er-Schritte für jedes In-Game-Feld einstellen
    ax_det.set_xticks(np.arange(sh_plot_x - 4, sh_plot_x + stronghold_size + 5, 1))
    ax_det.set_yticks(np.arange(sh_plot_y - 4, sh_plot_y + stronghold_size + 5, 1))
    ax_det.grid(True, color='#2d382a', linestyle='-', linewidth=0.7)
    ax_det.tick_params(colors='white', labelsize=10, rotation=45)

    # 4. Den Stronghold zeichnen (Hellrot)
    rect_sh = patches.Rectangle((sh_plot_x, sh_plot_y), stronghold_size, stronghold_size, 
                                linewidth=2.5, edgecolor='#ff4747', facecolor='#ff4747', alpha=0.25, 
                                label='Stronghold (Gebäude-Fläche)')
    ax_det.add_patch(rect_sh)

    # 5. Die variable Blockierzone zeichnen (Dunkelrot gestrichelt)
    rect_blocked = patches.Rectangle((min_block_x, min_block_y), block_width, block_height, 
                                     linewidth=2, edgecolor='#ff0000', facecolor='#ff0000', alpha=0.45, 
                                     linestyle='--', label='Blockierte Zone (Aus Variablen)')
    ax_det.add_patch(rect_blocked)

    # 6. Eckpunkte dynamisch berechnen und beschriften
    # Die tatsächlichen Ecken des gezeichneten Strongholds
    ecken = [
        (sh_plot_x, sh_plot_y + stronghold_size - 1, "Oben Links"),
        (sh_plot_x + stronghold_size - 1,  sh_plot_y + stronghold_size - 1, "Oben Rechts"),
        (sh_plot_x, sh_plot_y, "Unten Links"),
        (sh_plot_x + stronghold_size - 1, sh_plot_y, "Unten Rechts")
    ]
    
    for x, y, label in ecken:
        # Punkt exakt in die Mitte des Feldes setzen (+0.5)
        ax_det.plot(x + 0.5, y + 0.5, 'o', color='#ffffff', markersize=6) 
        ax_det.text(x + 0.5, y + 0.5, f" {label}\n {x}|{y}", color='white', fontsize=8, 
                    fontweight='bold', va='center', ha='left', 
                    bbox=dict(facecolor='black', alpha=0.7, edgecolor='none', pad=2))

    # Titel, Legende und Speichern
    plt.title("Dynamische Stronghold-Zonen & Eckpunkte", fontsize=16, color='white', pad=20, weight='bold')
    ax_det.legend(loc='upper right', facecolor='#121711', edgecolor='white', labelcolor='white')
    fig_det.patch.set_facecolor('#121711')

    plt.savefig("stronghold_detail_zone.png", facecolor=fig_det.get_facecolor(), bbox_inches='tight')
    plt.close()
    print(">>> ERFOLG! Dynamische Detailkarte generiert: 'stronghold_detail_zone.png' <<<")
    plt.close()
    print(">>> ERFOLG! Detailkarte generiert: 'stronghold_detail_zone.png' <<<")

if __name__ == "__main__":
    generate_alliance_grid()