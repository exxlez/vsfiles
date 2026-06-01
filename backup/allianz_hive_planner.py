import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import json
import os
import csv

Y_VON_UNTEN_NACH_OBEN = True   
X_VON_LINKS_NACH_RECHTS = True  

def load_and_sort_members(filepath="allianz.json"):
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        default_data = [{"name": f"Mitglied {i}", "rang": "R1", "power": 10000000, "partner": None} for i in range(1, 92)]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, indent=2, ensure_ascii=False)
        return default_data
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_alliance_grid():
    # --- REAL IN-GAME COORDS ---
    stronghold_in_game_x = 774
    stronghold_in_game_y = 799
    stronghold_size = 13  
    
    guard_in_game_x = 756
    guard_in_game_y = 803
    guard_size = 3
    
    spacing = 2       
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

    placed_objects = []

    # --- DEFINITION DER VERBOTENEN REALE-IN-GAME ZONEN ---
    guard_blocked_x = set(range(guard_in_game_x, guard_in_game_x + guard_size))
    guard_blocked_y = set(range(guard_in_game_y, guard_in_game_y + guard_size))
    
    sh_log_in_game_x1 = stronghold_in_game_x - 5
    sh_log_in_game_x2 = stronghold_in_game_x + 5
    sh_log_in_game_y1 = stronghold_in_game_y - 5
    sh_log_in_game_y2 = stronghold_in_game_y + 5
    
    stronghold_blocked_x = set(range(sh_log_in_game_x1, sh_log_in_game_x2 + 1))
    stronghold_blocked_y = set(range(sh_log_in_game_y1, sh_log_in_game_y2 + 1))

    def is_game_position_blocked(gx, gy):
        player_fields_x = set(range(gx, gx + base_size))
        player_fields_y = set(range(gy, gy + base_size))
        if (player_fields_x & guard_blocked_x) and (player_fields_y & guard_blocked_y): return True
        if (player_fields_x & stronghold_blocked_x) and (player_fields_y & stronghold_blocked_y): return True
        return False

    grid = np.zeros((grid_h, grid_w), dtype=int)
    sh_radius = (stronghold_size - 1) // 2
    sh_x = to_grid_x(stronghold_in_game_x) - sh_radius
    sh_y = to_grid_y(stronghold_in_game_y) - sh_radius
    grid[sh_y+1 : sh_y+stronghold_size-1, sh_x+1 : sh_x+stronghold_size-1] = 1
    gw_x, gw_y = to_grid_x(guard_in_game_x), to_grid_y(guard_in_game_y)
    grid[gw_y : gw_y + guard_size, gw_x : gw_x + guard_size] = 2

    step_x, step_y = base_size + spacing, base_size + spacing
    hive_center_game_x = (stronghold_in_game_x + guard_in_game_x) / 2
    hive_center_game_y = (stronghold_in_game_y + guard_in_game_y) / 2
    
    possible_slots_for_r4, possible_slots_for_r1 = [], []
    for row_idx in range(-45, 45):
        target_y = gw_y + (row_idx * step_y)
        for col_idx in range(-45, 45):
            target_x = gw_x + (col_idx * step_x)
            if (0 <= target_x < grid_w - base_size) and (0 <= target_y < grid_h - base_size):
                gx, gy = to_game_coords(target_x, target_y)
                if is_game_position_blocked(gx, gy): continue
                
                d_guard = np.sqrt((gx - guard_in_game_x)**2 + (gy - guard_in_game_y)**2)
                d_hive = np.sqrt((gx - hive_center_game_x)**2 + (gy - hive_center_game_y)**2)
                possible_slots_for_r4.append({"x": target_x, "y": target_y, "dist": d_guard})
                possible_slots_for_r1.append({"x": target_x, "y": target_y, "dist": d_hive})

    possible_slots_for_r4.sort(key=lambda s: s["dist"])
    possible_slots_for_r1.sort(key=lambda s: s["dist"])

    # --- GRAPHEN-BASIERTE GRUPPENBILDUNG ---
    raw_members = load_and_sort_members("allianz.json")
    name_to_member = {m["name"].strip().lower(): m for m in raw_members}
    
    adj = {m["name"].strip().lower(): set() for m in raw_members}
    for m in raw_members:
        u = m["name"].strip().lower()
        if m.get("partner"):
            v = m["partner"].strip().lower()
            if v in adj:
                adj[u].add(v)
                adj[v].add(u)

    visited = set()
    groups = []
    for m in raw_members:
        start_name = m["name"].strip().lower()
        if start_name not in visited:
            cluster = []
            queue = [start_name]
            visited.add(start_name)
            while queue:
                curr = queue.pop(0)
                cluster.append(name_to_member[curr])
                for nxt in adj[curr]:
                    if nxt not in visited:
                        visited.add(nxt)
                        queue.append(nxt)
            groups.append(cluster)

    processed_groups = []
    for g in groups:
        has_r4 = any(m["rang"].upper() == "R4" for m in g)
        max_power = max(m["power"] for m in g)
        
        sorted_by_relation = []
        g_names = {m["name"].strip().lower(): m for m in g}
        r4_in_group = [m for m in g if m["rang"].upper() == "R4"]
        r4_in_group.sort(key=lambda x: -x["power"])
        
        path_queue = [r4["name"].strip().lower() for r4 in r4_in_group]
        if not path_queue:
            g.sort(key=lambda x: -x["power"])
            path_queue.append(g[0]["name"].strip().lower())
            
        inner_visited = set()
        for name in path_queue:
            if name in inner_visited: continue
            sub_q = [name]
            inner_visited.add(name)
            while sub_q:
                curr = sub_q.pop(0)
                sorted_by_relation.append(g_names[curr])
                for nxt in adj[curr]:
                    if nxt not in inner_visited:
                        inner_visited.add(nxt)
                        sub_q.append(nxt)
                        
        for name, m in g_names.items():
            if m not in sorted_by_relation: sorted_by_relation.append(m)
        
        processed_groups.append({
            "members": sorted_by_relation,
            "is_r4_group": has_r4,
            "sort_priority": 0 if has_r4 else 1,
            "sort_power": max_power
        })

    processed_groups.sort(key=lambda x: (x["sort_priority"], -x["sort_power"]))

    # --- INITIALE PLATZIERUNG ---
    def is_area_free_initial(sx, sy):
        gx, gy = to_game_coords(sx, sy)
        if is_game_position_blocked(gx, gy): return False
        if not (0 <= sx < grid_w - base_size and 0 <= sy < grid_h - base_size): return False
        return not np.any(grid[sy - spacing : sy + base_size + spacing, sx - spacing : sx + base_size + spacing] > 2)

    initial_placed_players = []

    for group_packet in processed_groups:
        members_to_place = group_packet["members"]
        lead_member = members_to_place[0]
        search_pool = possible_slots_for_r4 if group_packet["is_r4_group"] else possible_slots_for_r1
        
        lead_slot = next((s for s in search_pool if is_area_free_initial(s["x"], s["y"])), None)
        if not lead_slot: lead_slot = next((s for s in possible_slots_for_r1 if is_area_free_initial(s["x"], s["y"])), None)
        if not lead_slot: continue

        lx, ly = lead_slot["x"], lead_slot["y"]
        grid[ly : ly + base_size, lx : lx + base_size] = 3 if lead_member["rang"].upper() == "R4" else 4
        initial_placed_players.append({"member": lead_member, "x": lx, "y": ly})

        for follower in members_to_place[1:]:
            step = base_size + spacing
            follower_placed = False
            for layer in range(1, 6): 
                local_slots = []
                for dx in range(-layer, layer + 1):
                    for dy in range(-layer, layer + 1):
                        if abs(dx) == layer or abs(dy) == layer:
                            fx, fy = lx + (dx * step), ly + (dy * step)
                            if 0 <= fx < grid_w - base_size and 0 <= fy < grid_h - base_size:
                                d_to_lead = np.sqrt((fx - lx)**2 + (fy - ly)**2)
                                local_slots.append({"x": fx, "y": fy, "dist": d_to_lead})
                
                local_slots.sort(key=lambda s: s["dist"])
                for f_slot in local_slots:
                    if is_area_free_initial(f_slot["x"], f_slot["y"]):
                        flx, fly = f_slot["x"], f_slot["y"]
                        grid[fly : fly + base_size, flx : flx + base_size] = 3 if follower["rang"].upper() == "R4" else 4
                        initial_placed_players.append({"member": follower, "x": flx, "y": fly})
                        follower_placed = True
                        break
                if follower_placed: break

    # --- 6. OPTIMIERER (ERZWINGT UNTRENNBARE PARTNER-KETTEN) ---
    print("-> Schweiße Partner unwiderruflich aneinander...")
    anzahl_r4 = sum(1 for x in raw_members if x["rang"].upper() == "R4")
    exklusive_r4_coords = set((s["x"], s["y"]) for s in possible_slots_for_r4[:anzahl_r4])

    # Erhöhter Schwellenwert für diagonale Nachbarschaften in In-Game-Kacheln
    MAX_PARTNER_DIST = 11.0 
    improved = True
    iterations = 0
    
    while improved and iterations < 3000:
        improved = False
        iterations += 1
        
        for i in range(len(initial_placed_players)):
            for j in range(i + 1, len(initial_placed_players)):
                p1 = initial_placed_players[i]
                p2 = initial_placed_players[j]
                m1, m2 = p1["member"], p2["member"]
                
                if (m1["rang"].upper() == "R4") != (m2["rang"].upper() == "R4"):
                    continue
                
                # Wenn einer der beiden feste Partner hat, blockieren wir den Einzel-Tausch komplett!
                # Das verhindert, dass der eine wegsortiert wird, während der andere stehen bleibt.
                if len(adj[m1["name"].strip().lower()]) > 0 or len(adj[m2["name"].strip().lower()]) > 0:
                    continue
                    
                orig_x1, orig_y1 = p1["x"], p1["y"]
                orig_x2, orig_y2 = p2["x"], p2["y"]

                if m1["rang"].upper() != "R4" and ((orig_x2, orig_y2) in exklusive_r4_coords or (orig_x1, orig_y1) in exklusive_r4_coords):
                    continue

                gx1, gy1 = to_game_coords(orig_x1, orig_y1)
                gx2, gy2 = to_game_coords(orig_x2, orig_y2)
                
                d1_guard = np.sqrt((gx1 - guard_in_game_x)**2 + (gy1 - guard_in_game_y)**2)
                d1_hive = np.sqrt((gx1 - hive_center_game_x)**2 + (gy1 - hive_center_game_y)**2)
                d2_guard = np.sqrt((gx2 - guard_in_game_x)**2 + (gy2 - guard_in_game_y)**2)
                d2_hive = np.sqrt((gx2 - hive_center_game_x)**2 + (gy2 - hive_center_game_y)**2)
                
                dist1 = d1_guard if m1["rang"].upper() == "R4" else d1_hive
                dist2 = d2_guard if m2["rang"].upper() == "R4" else d2_hive
                
                if (m1["power"] < m2["power"] and dist1 > dist2 + 0.1) or (m2["power"] < m1["power"] and dist2 > dist1 + 0.1):
                    p1["x"], p1["y"] = orig_x2, orig_y2
                    p2["x"], p2["y"] = orig_x1, orig_y1
                    
                    swap_valid = True
                    current_coords = {p["member"]["name"].strip().lower(): to_game_coords(p["x"], p["y"]) for p in initial_placed_players}
                    
                    for check_p in initial_placed_players:
                        cm = check_p["member"]
                        c_name = cm["name"].strip().lower()
                        aktuelle_partner = adj[c_name]
                        
                        for p_name_lower in aktuelle_partner:
                            if p_name_lower in current_coords:
                                cgx, cgy = current_coords[c_name]
                                pgx, pgy = current_coords[p_name_lower]
                                p_dist = np.sqrt((cgx - pgx)**2 + (cgy - pgy)**2)
                                if p_dist > MAX_PARTNER_DIST:
                                    swap_valid = False
                                    break
                        if not swap_valid: break
                    
                    if swap_valid:
                        improved = True
                        break 
                    else:
                        p1["x"], p1["y"] = orig_x1, orig_y1
                        p2["x"], p2["y"] = orig_x2, orig_y2
            if improved: break

    print(f"-> Optimierung abgeschlossen nach {iterations} Durchläufen.")

    # --- 7. DETAILS GENERIEREN & ZEICHNEN ---
    placed_objects.append({"name": f"Stronghold Lv. 5\nX:{stronghold_in_game_x} Y:{stronghold_in_game_y}", "x": sh_x, "y": sh_y, "w": stronghold_size, "h": stronghold_size, "type": "stronghold"})
    placed_objects.append({"name": f"Marshall\nGuard\nX:{guard_in_game_x}\nY:{guard_in_game_y}", "x": gw_x, "y": gw_y, "w": guard_size, "h": guard_size, "type": "guard"})
    export_coords_data = []

    for p in initial_placed_players:
        mx, my = p["x"], p["y"]
        m = p["member"]
        real_x, real_y = to_game_coords(mx, my)
        placed_objects.append({
            "name": f"{m['name']}\nX:{real_x} Y:{real_y}", 
            "x": mx, "y": my, "w": base_size, "h": base_size, 
            "type": m["rang"].lower()
        })
        export_coords_data.append({
            "name": m["name"],
            "rang": m["rang"],
            "x": real_x,
            "y": real_y
        })

    all_x = [obj["x"] for obj in placed_objects] + [obj["x"]+obj["w"] for obj in placed_objects]
    all_y = [obj["y"] for obj in placed_objects] + [obj["y"]+obj["h"] for obj in placed_objects]
    view_min_x, view_max_x = max(0, min(all_x) - 4), min(grid_w, max(all_x) + 4)
    view_min_y, view_max_y = max(0, min(all_y) - 4), min(grid_h, max(all_y) + 4)

    # --- ULTRA-HD VISUALISIERUNG ---
    fig, ax = plt.subplots(figsize=(30, 30), dpi=300) 
    ax.set_aspect('equal')
    ax.set_facecolor('#1e251c') 
    ax.grid(True, color='#2d382a', linestyle='-', linewidth=0.5)
    
    x_ticks = np.arange(view_min_x, view_max_x, 5)
    y_ticks = np.arange(view_min_y, view_max_y, 5)
    ax.set_xticks(x_ticks)
    ax.set_yticks(y_ticks)
    
    ax.set_xticklabels([str(int(x + min_game_x)) for x in x_ticks], fontsize=12, color='white', rotation=45)
    ax.set_xlim(view_min_x, view_max_x)
    ax.set_yticklabels([str(int(min_game_y + y)) for y in y_ticks], fontsize=12, color='white')
    ax.set_ylim(view_min_y, view_max_y)
    
    colors = {"stronghold": "#b22222", "guard": "#ff8c00", "r4": "#1e90ff", "r3": "#4682b4", "r2": "#4682b4", "r1": "#4682b4", "member": "#4682b4"}
    
    for obj in placed_objects:
        rect = patches.Rectangle((obj["x"], obj["y"]), obj["w"], obj["h"], linewidth=1.5, edgecolor='#ffffff', facecolor=colors.get(obj["type"], "#4682b4"), alpha=0.9)
        ax.add_patch(rect)
        font_sz = 12.0 if obj["type"] in ["r4", "r3", "r2", "r1", "member"] else 20.0
        ax.text(obj["x"] + obj["w"]/2, obj["y"] + obj["h"]/2, obj["name"], color="white", fontsize=font_sz, fontweight='bold', ha='center', va='center', clip_on=True)
        
    plt.title("Last War - Allianz Hive Plan (Piero & Glitzer Fix)", fontsize=24, color='white', pad=35, weight='bold')
    fig.patch.set_facecolor('#121711')
    
    output_filename = "allianz_hive_ultra_hd.png"
    plt.savefig(output_filename, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    print(f"\n>>> Hive erstellt! Bild: '{output_filename}' <<<")

# --- NEU: SPEICHERN DER KOORDINATEN ALS CSV ---
    export_coords_data.sort(key=lambda k: (k["rang"], k["name"]))

    csv_output_path = "allianz_koordinaten.csv"
    with open(csv_output_path, 'w', newline='', encoding='utf-8-sig') as f:
        # Semikolon als Trennzeichen ist in Excel auf Deutsch meistens besser
        writer = csv.writer(f, delimiter=';')
        writer.writerow(["Name", "Rang", "X-Koordinate", "Y-Koordinate"])
        for member in export_coords_data:
            writer.writerow([member['name'], member['rang'], member['x'], member['y']])
            
    print(f"-> Koordinaten-Liste als CSV gespeichert unter: '{csv_output_path}'")

if __name__ == "__main__":
    generate_alliance_grid()