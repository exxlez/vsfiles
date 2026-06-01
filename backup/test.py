import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import json
import os

Y_VON_UNTEN_NACH_OBEN = True   
X_VON_LINKS_NACH_RECHTS = True  

def load_members(filepath="allianz.json"):
    if not os.path.exists(filepath):
        dummy = [{"name": f"Spieler_{i}", "rang": "R4" if i < 6 else "R3", "power": 100000 - i*1000} for i in range(1, 90)]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(dummy, f, ensure_ascii=False, indent=4)
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_alliance_grid():
    # --- 1. REAL IN-GAME COORDS & SETUP ---
    stronghold_in_game_x, stronghold_in_game_y = 774, 799
    stronghold_size = 13  
    guard_in_game_x, guard_in_game_y = 756, 803
    guard_size = 3
    
    base_size = 3     
    padding = 70      
    
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
        
    def from_game_to_grid_coords(gx, gy):
        mx = int(gx - min_game_x) if X_VON_LINKS_NACH_RECHTS else int(max_game_x - gx - base_size)
        my = int(gy - min_game_y) if Y_VON_UNTEN_NACH_OBEN else int(max_game_y - gy - base_size)
        return mx, my

    # --- 2. VERBOTENE ZONEN ---
    guard_blocked_x = set(range(guard_in_game_x, guard_in_game_x + guard_size))
    guard_blocked_y = set(range(guard_in_game_y, guard_in_game_y + guard_size))
    
    sh_game_start_x = stronghold_in_game_x - 6
    sh_game_start_y = stronghold_in_game_y - 6
    sh_game_ende_x = sh_game_start_x + stronghold_size - 1
    sh_game_ende_y = sh_game_start_y + stronghold_size - 1
    
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

    placed_objects = []
    placed_objects.append({"name": "Stronghold Lv5", "gx": sh_game_start_x, "gy": sh_game_start_y, "w": stronghold_size, "h": stronghold_size, "type": "stronghold"})
    placed_objects.append({"name": "Wache", "gx": guard_in_game_x, "gy": guard_in_game_y, "w": guard_size, "h": guard_size, "type": "guard"})
    
    sh_center_x = stronghold_in_game_x + (stronghold_size / 2)
    sh_center_y = stronghold_in_game_y + (stronghold_size / 2)

    # --- 3. MITGLIEDER LADEN & SORTIEREN ---
    raw_members = load_members("allianz.json")
    raw_members.sort(key=lambda x: (0 if x["rang"].upper() == "R4" else 1, -x["power"]))

    # --- 4. ECKPFEILER (Jetzt EXAKT Kante an Kante zur blockierten Zone) ---
    # Die Ecken grenzen diagonal nun haargenau (0 Felder Lücke zur roten Zone) an.
    corner_game_coords = [
        (sh_game_start_x - base_size, sh_game_ende_y + 1),         # Oben Links
        (sh_game_ende_x + 1, sh_game_ende_y + 1),                 # Oben Rechts
        (sh_game_start_x - base_size, sh_game_start_y - base_size), # Unten Links
        (sh_game_ende_x + 1, sh_game_start_y - base_size)          # Unten Rechts
    ]
    
    # --- 5. VALIDIERUNG: MIN 1, MAX 2 ABSTAND ---
    def is_slot_valid(sx, sy, check_max_distance=False):
        gx, gy = to_game_coords(sx, sy)
        if is_game_position_blocked(gx, gy): return False
        if not (0 <= sx < grid_w - base_size and 0 <= sy < grid_h - base_size): return False
        
        has_valid_neighbor_connection = False if check_max_distance else True
        
        for obj in placed_objects:
            pgx, pgy = obj["gx"], obj["gy"]
            
            # Achsenabstände berechnen
            if gx + base_size <= pgx:
                dist_x = pgx - (gx + base_size)
            elif gx >= pgx + obj["w"]:
                dist_x = gx - (pgx + obj["w"])
            else:
                dist_x = -1
                
            if gy + base_size <= pgy:
                dist_y = pgy - (gy + base_size)
            elif gy >= pgy + obj["h"]:
                dist_y = gy - (pgy + obj["h"])
            else:
                dist_y = -1

            # Kollision / Überlappung
            if dist_x < 0 and dist_y < 0: return False
            
            # Wenn das untersuchte Objekt das Stronghold (die blockierte Zone) selbst ist
            if obj["type"] == "stronghold":
                # Zu den exakten 4 Eckpunkten erlauben wir 0 Abstand zur roten Kante
                ist_eckpunkt = (gx, gy) in corner_game_coords
                if ist_eckpunkt:
                    continue
                
                # Für alle normalen Basen gilt an den Flanken: Mindestens 1, Maximal 2
                if dist_x == -1 and (dist_y < 1 or dist_y > 2): return False
                if dist_y == -1 and (dist_x < 1 or dist_x > 2): return False
            else:
                # Abstände zwischen Spielern untereinander: Immer min 1, max 2
                if dist_x == -1: 
                    if dist_y < 1: return False
                    if dist_y <= 2: has_valid_neighbor_connection = True
                elif dist_y == -1: 
                    if dist_x < 1: return False
                    if dist_x <= 2: has_valid_neighbor_connection = True
                else:
                    if dist_x < 1 or dist_y < 1: return False
                    if dist_x <= 2 and dist_y <= 2: has_valid_neighbor_connection = True
                
        return has_valid_neighbor_connection

    # --- 6. PLATZIERUNG ---
    placed_players = []
    name_to_placed_coords = {}
    remaining_members = list(raw_members)

    # Schritt A: Die 4 Ecken bombenfest verankern
    print("-> Verankere die 4 Eckpfeiler exakt an der Verbotszone...")
    for cg_x, cg_y in corner_game_coords:
        cx, cy = from_game_to_grid_coords(cg_x, cg_y)
        if len(remaining_members) > 0:
            member = remaining_members.pop(0)
            grid[cy : cy + base_size, cx : cx + base_size] = 1
            placed_players.append({"member": member, "x": cx, "y": cy})
            placed_objects.append({"name": member["name"], "gx": cg_x, "gy": cg_y, "w": base_size, "h": base_size, "type": member["rang"].lower()})
            name_to_placed_coords[member["name"].strip().lower()] = (cx, cy)

    # Schritt B: Alle restlichen Slots sammeln und nach Zentrumsnähe sortieren
    all_possible_slots = []
    for target_y in range(0, grid_h - base_size):
        for target_x in range(0, grid_w - base_size):
            gx, gy = to_game_coords(target_x, target_y)
            d_center = np.sqrt((gx + 1.5 - sh_center_x)**2 + (gy + 1.5 - sh_center_y)**2)
            all_possible_slots.append({"x": target_x, "y": target_y, "dist": d_center})

    all_possible_slots.sort(key=lambda s: s["dist"])

    # Schritt C: Restlichen Raum im homogenen Verbund auffüllen
    print("-> Fülle das Raster lückenlos auf (Min 1, Max 2)...")
    for member in remaining_members:
        m_name = member["name"].strip().lower()
        m_rang = member["rang"].upper()
        placed = False
        
        # Durchlauf 1: Maximale Dichte und direkte Nachbarschaft (Verbindung halten)
        for slot in all_possible_slots:
            if is_slot_valid(slot["x"], slot["y"], check_max_distance=True):
                px, py = slot["x"], slot["y"]
                gx, gy = to_game_coords(px, py)
                grid[py : py + base_size, px : px + base_size] = 1
                
                placed_players.append({"member": member, "x": px, "y": py})
                placed_objects.append({"name": member["name"], "gx": gx, "gy": gy, "w": base_size, "h": base_size, "type": m_rang.lower()})
                name_to_placed_coords[m_name] = (px, py)
                placed = True
                break
        
        # Durchlauf 2: Falls Expansion nötig wird
        if not placed:
            for slot in all_possible_slots:
                if is_slot_valid(slot["x"], slot["y"], check_max_distance=False):
                    px, py = slot["x"], slot["y"]
                    gx, gy = to_game_coords(px, py)
                    grid[py : py + base_size, px : px + base_size] = 1
                    
                    placed_players.append({"member": member, "x": px, "y": py})
                    placed_objects.append({"name": member["name"], "gx": gx, "gy": gy, "w": base_size, "h": base_size, "type": m_rang.lower()})
                    name_to_placed_coords[m_name] = (px, py)
                    placed = True
                    break
                    
        if not placed:
            print(f"Warnung: Kein Platz mehr auf der Karte für {member['name']}!")

    # --- 7. PLOTTEN & RENDERN ---
    final_render_objects = []
    final_render_objects.append({"name": "Stronghold Lv5", "x": sh_x, "y": sh_y, "w": stronghold_size, "h": stronghold_size, "type": "stronghold"})
    final_render_objects.append({"name": "Wache", "x": gw_x, "y": gw_y, "w": guard_size, "h": guard_size, "type": "guard"})

    for p in placed_players:
        mx, my = p["x"], p["y"]
        m = p["member"]
        real_x, real_y = to_game_coords(mx, my)
        
        center_x = real_x + 1
        center_y = real_y + 1
        
        final_render_objects.append({
            "name": f"{m['name']}\n{center_x}|{center_y}", 
            "x": mx, "y": my, "w": base_size, "h": base_size, 
            "type": m["rang"].lower(),
            "center_coords": f"{center_x}|{center_y}"
        })

    all_x = [obj["x"] for obj in final_render_objects] + [obj["x"]+obj["w"] for obj in final_render_objects]
    all_y = [obj["y"] for obj in final_render_objects] + [obj["y"]+obj["h"] for obj in final_render_objects]
    view_min_x, view_max_x = max(0, min(all_x) - 4), min(grid_w, max(all_x) + 4)
    view_min_y, view_max_y = max(0, min(all_y) - 4), min(grid_h, max(all_y) + 4)

    fig, ax = plt.subplots(figsize=(30, 30), dpi=300) 
    ax.set_aspect('equal')
    ax.set_facecolor('#1e251c') 
    
    ax.set_xlim(view_min_x, view_max_x)
    ax.set_ylim(view_min_y, view_max_y)
    
    x_ticks_major = np.arange(view_min_x, view_max_x, 5)
    y_ticks_major = np.arange(view_min_y, view_max_y, 5)
    ax.set_xticks(x_ticks_major)
    ax.set_yticks(y_ticks_major)
    ax.set_xticklabels([str(int(x + min_game_x)) for x in x_ticks_major], fontsize=12, color='white', rotation=45)
    ax.set_yticklabels([str(int(min_game_y + y)) for y in y_ticks_major], fontsize=12, color='white')
    
    ax.set_xticks(np.arange(view_min_x, view_max_x, 1), minor=True)
    ax.set_yticks(np.arange(view_min_y, view_max_y, 1), minor=True)
    
    ax.grid(True, which='major', color='#2d382a', linestyle='-', linewidth=0.8) 
    ax.grid(True, which='minor', color="#596157", linestyle=':', linewidth=0.4) 
    
    colors = {"stronghold": "#b22222", "guard": "#ff8c00", "r4": "#1e90ff", "r3": "#2e8b57"}
    
    for obj in final_render_objects:
        rect = patches.Rectangle((obj["x"], obj["y"]), obj["w"], obj["h"], linewidth=1.5, edgecolor='#ffffff', facecolor=colors.get(obj["type"], "#4682b4"), alpha=0.9)
        ax.add_patch(rect)
        font_sz = 10.0 if obj["type"] in ["r4", "r3"] else 20.0
        ax.text(obj["x"] + obj["w"]/2, obj["y"] + obj["h"]/2, obj["name"], color="white", fontsize=font_sz, fontweight='bold', ha='center', va='center', clip_on=True)

    def save_coordinates_to_txt(objects, filename="allianz_koordinaten_2.txt"):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("Allianz Hive Plan - Exakte Ecken (Min 1, Max 2)\n")
            f.write("====================================================\n\n")
            for obj in objects:
                b_type = obj['type'].upper()
                if "center_coords" in obj:
                    clean_name = obj["name"].split('\n')[0]
                    f.write(f"[{b_type}] {clean_name} | X:Y = {obj['center_coords']}\n")
                else:
                    clean_info = obj["name"].replace('\n', ' |  ')
                    f.write(f"[{b_type}] {clean_info}\n")

    save_coordinates_to_txt(final_render_objects)
        
    plt.title("Allianz Hive Plan - Kompakter Hive (Ecken direkt anliegend)", fontsize=24, color='white', pad=35, weight='bold')
    fig.patch.set_facecolor('#121711')
    
    plt.savefig("hive_snake_map_2.png", facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    print(">>> ERFOLG! Karte generiert: 'hive_snake_map_2.png' <<<")

if __name__ == "__main__":
    generate_alliance_grid()