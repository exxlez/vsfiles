import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import json
import io
import zipfile

# --- STREAMLIT UI SETUP ---
st.set_page_config(page_title="Last War Hive Generator", layout="wide")
st.title("🛡️ Last War Hive Generator & Planer")
st.write("Adjust the parameters, upload your alliance JSON and generate the hive plan.")

# Standardwerte für In-Game-Richtungen
Y_VON_UNTEN_NACH_OBEN = True   
X_VON_LINKS_NACH_RECHTS = True  

# Initialisiere Session State für die Downloads
if "img_buf" not in st.session_state:
    st.session_state.img_buf = None
if "txt_content" not in st.session_state:
    st.session_state.txt_content = None
if "zip_buffer" not in st.session_state:
    st.session_state.zip_buffer = None

# Ein Formular für alle Eingabeparameter
with st.form("param_form"):
    st.subheader("Set your Coordinate System ")
    col_g4, col_g5 = st.columns(2)
    with col_g4:
        Y_VON_UNTEN_NACH_OBEN = st.checkbox("Y Down to Up?", value=True)
    with col_g5:
        X_VON_LINKS_NACH_RECHTS = st.checkbox("X Down to Up?", value=True)
        
    st.subheader("📍 Marshall Guard / Hive-Center (Always active)")
    st.write("_Note: Use the **LOWER LEFT** corner coordinate._")
    col_g1, col_g2, col_g3= st.columns(3)
    with col_g1:
        guard_x = st.number_input("Marshall Guard/Hive-Center X-Coordinate", value=767)
    with col_g2:
        guard_y = st.number_input("Guard/Hive-Center Y-Coordinate", value=754)
    with col_g3:
        guard_size = st.number_input("Guard Size (Fields)", value=3)

    st.subheader("🏰 Stronghold-Options")
    st.write("_Note: Use the **LOWER LEFT** corner coordinate. **(THIS IS NOW THE HIVE CENTER!)**_")
    stronghold_vorhanden = st.checkbox("Stronghold near Hive?", value=True)
    
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        stronghold_x = st.number_input("Stronghold LOWER LEFT X-Coordinate.", value=765)
    with col_s2:
        stronghold_y = st.number_input("Stronghold LOWER LEFT Y-Coordinate.", value=740)
    with col_s3:
        stronghold_size = st.number_input("Stronghold/City Size (Fields)", value=19)
    with col_s4:
        stronghold_name = st.text_input("Name of City or Stronghold", value="Stronghold Lv5")
    
    st.subheader("🚫 Forbidden Zone (Optional)")
    st.write("_Note: Use the **LOWER LEFT** corner coordinate. Applies ONLY to player bases!_")
    forbidden_vorhanden = st.checkbox("Use Forbidden Zone?", value=True)
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        forbidden_x = st.number_input("Forbidden Zone Lower-Left X", value=766)
    with col_f2:
        forbidden_y = st.number_input("Forbidden Zone Lower-Left Y", value=741)
    with col_f3:
        forbidden_w = st.number_input("Forbidden Zone Width (X-Fields)", value=17)
    with col_f4:
        forbidden_h = st.number_input("Forbidden Zone Height (Y-Fields)", value=17)

    st.subheader("⚠️ Zone Monitoring (Minimum Distance)")
    min_hive_distance = st.number_input("Minimum distance Stronghold to Hive-Center (Radius)", value=0)

    st.subheader("⚙️ General Settings")
    col_a1, col_a2, col_a3 = st.columns(3)
    with col_a1:
        base_size = st.number_input("Base Size (Players)", value=3)
    with col_a2:
        spacing = st.number_input("Spacing between Bases in Fields", value=1)
    with col_a3:
        padding = st.number_input("Padding", value=30)

    st.subheader("📂 Alliance Data")
    uploaded_file = st.file_uploader("Upload your allianz.json", type=["json"])
    submit_button = st.form_submit_button("Generate Hive-Plan")

# --- HAUPT-LOGIK NACH SUBMIT ---
if submit_button:
    if not uploaded_file:
        st.error("❌ Upload a valid allianz.json!")
    else:
        st.success("✅ Parameter check successful! Generating data...")
        
        try:
            raw_members = json.load(uploaded_file)
            
            # Absolute Grenzen des virtuellen Grids bestimmen
            min_game_x = min(guard_x, stronghold_x if stronghold_vorhanden else guard_x, forbidden_x if forbidden_vorhanden else guard_x) - padding
            max_game_x = max(guard_x + guard_size, stronghold_x + stronghold_size if stronghold_vorhanden else guard_x, forbidden_x + forbidden_w if forbidden_vorhanden else guard_x) + padding
            min_game_y = min(guard_y, stronghold_y if stronghold_vorhanden else guard_y, forbidden_y if forbidden_vorhanden else guard_y) - padding
            max_game_y = max(guard_y + guard_size, stronghold_y + stronghold_size if stronghold_vorhanden else guard_y, forbidden_y + forbidden_h if forbidden_vorhanden else guard_y) + padding

            grid_w = int(max_game_x - min_game_x)
            grid_h = int(max_game_y - min_game_y)
            
            def to_grid_x(game_x): return int(game_x - min_game_x)
            def to_grid_y(game_y): return int(game_y - min_game_y)
            def to_game_coords(mx, my): return int(mx + min_game_x), int(my + min_game_y)

            # Blockierte Koordinaten-Sets definieren
            guard_blocked_x = set(range(int(guard_x), int(guard_x + guard_size)))
            guard_blocked_y = set(range(int(guard_y), int(guard_y + guard_size)))
            
            forbidden_blocked_x = set(range(int(forbidden_x), int(forbidden_x + forbidden_w))) if forbidden_vorhanden else set()
            forbidden_blocked_y = set(range(int(forbidden_y), int(forbidden_y + forbidden_h))) if forbidden_vorhanden else set()

            grid = np.zeros((grid_h, grid_w), dtype=int)
            step = int(base_size + spacing)
            
            # --- MITTELPUNKT-LOGIK (STRONGHOLD) ---
            if stronghold_vorhanden:
                center_target_x = stronghold_x + (stronghold_size / 2)
                center_target_y = stronghold_y + (stronghold_size / 2)
                anchor_grid_x = to_grid_x(stronghold_x)
                anchor_grid_y = to_grid_y(stronghold_y)
            else:
                center_target_x = guard_x + (guard_size / 2)
                center_target_y = guard_y + (guard_size / 2)
                anchor_grid_x = to_grid_x(guard_x)
                anchor_grid_y = to_grid_y(guard_y)

            # Freie Grid-Slots sammeln
            possible_slots = []
            for row_idx in range(-60, 60):
                target_y = anchor_grid_y + (row_idx * step)
                for col_idx in range(-60, 60):
                    target_x = anchor_grid_x + (col_idx * step)
                    if (0 <= target_x < grid_w - base_size) and (0 <= target_y < grid_h - base_size):
                        gx, gy = to_game_coords(target_x, target_y)
                        
                        p_x = set(range(gx, gx + int(base_size)))
                        p_y = set(range(gy, gy + int(base_size)))
                        
                        if (p_x & guard_blocked_x) and (p_y & guard_blocked_y): continue
                        if forbidden_vorhanden and (p_x & forbidden_blocked_x) and (p_y & forbidden_blocked_y): continue
                        
                        d_center = np.sqrt((gx - center_target_x)**2 + (gy - center_target_y)**2)
                        possible_slots.append({"x": target_x, "y": target_y, "dist": d_center})

            possible_slots.sort(key=lambda s: s["dist"])

            # --- PARTNER-LOGIK REORGANISIEREN ---
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

            # Platzierungs-Check
            def is_area_free(sx, sy):
                if not (0 <= sx < grid_w - base_size and 0 <= sy < grid_h - base_size): return False
                return not np.any(grid[max(0, sy - spacing) : min(grid_h, sy + base_size + spacing), max(0, sx - spacing) : min(grid_w, sx + base_size + spacing)] > 0)

            # --- PARTNER-AWARE PLATZIERUNG ---
            placed_players = []
            name_to_placed_coords = {}

            for snake in snakes:
                for i, member in enumerate(snake["members"]):
                    m_name = member["name"].strip().lower()
                    placed = False
                    
                    # Wenn erster Spieler der Gruppe: Nächsten freien globalen Slot nutzen
                    if i == 0:
                        for slot in possible_slots:
                            if is_area_free(slot["x"], slot["y"]):
                                px, py = slot["x"], slot["y"]
                                grid[py : py + base_size, px : px + base_size] = 1
                                gx, gy = to_game_coords(px, py)
                                placed_players.append({"member": member, "x": px, "y": py, "gx": gx, "gy": gy})
                                name_to_placed_coords[m_name] = (px, py)
                                placed = True
                                break
                    else:
                        # Partner suchen, der schon platziert wurde
                        anchor_x, anchor_y = None, None
                        for placed_name in adj_undirected[m_name]:
                            if placed_name in name_to_placed_coords:
                                anchor_x, anchor_y = name_to_placed_coords[placed_name]
                                break 
                        
                        # In konzentrischen Ringen um den Partner herum nach Platz suchen
                        if anchor_x is not None:
                            for layer in range(1, 12): 
                                local_slots = []
                                for dx in range(-layer, layer + 1):
                                    for dy in range(-layer, layer + 1):
                                        if abs(dx) == layer or abs(dy) == layer:
                                            fx = anchor_x + (dx * step)
                                            fy = anchor_y + (dy * step)
                                            
                                            # Sicherstellen, dass das Feld im Grid liegt und nicht blockiert wird
                                            if (0 <= fx < grid_w - base_size) and (0 <= fy < grid_h - base_size):
                                                fgx, fgy = to_game_coords(fx, fy)
                                                f_px = set(range(fgx, fgx + int(base_size)))
                                                f_py = set(range(fgy, fgy + int(base_size)))
                                                
                                                if (f_px & guard_blocked_x) and (f_py & guard_blocked_y): continue
                                                if forbidden_vorhanden and (f_px & forbidden_blocked_x) and (f_py & forbidden_blocked_y): continue
                                                
                                                local_slots.append({"x": fx, "y": fy, "dist": np.sqrt(dx**2 + dy**2)})
                                
                                local_slots.sort(key=lambda s: s["dist"])
                                for slot in local_slots:
                                    if is_area_free(slot["x"], slot["y"]):
                                        px, py = slot["x"], slot["y"]
                                        grid[py : py + base_size, px : px + base_size] = 1
                                        gx, gy = to_game_coords(px, py)
                                        placed_players.append({"member": member, "x": px, "y": py, "gx": gx, "gy": gy})
                                        name_to_placed_coords[m_name] = (px, py)
                                        placed = True
                                        break
                                if placed: break
                        
                        # Fallback: Wenn kein Platz am Partner frei war, nimm den nächsten normalen Slot
                        if not placed:
                            for slot in possible_slots:
                                if is_area_free(slot["x"], slot["y"]):
                                    px, py = slot["x"], slot["y"]
                                    grid[py : py + base_size, px : px + base_size] = 1
                                    gx, gy = to_game_coords(px, py)
                                    placed_players.append({"member": member, "x": px, "y": py, "gx": gx, "gy": gy})
                                    name_to_placed_coords[m_name] = (px, py)
                                    placed = True
                                    break

            # Objekte für das Zeichnen vorbereiten
            placed_objects = []
            if stronghold_vorhanden:
                placed_objects.append({"name": stronghold_name, "x": to_grid_x(stronghold_x), "y": to_grid_y(stronghold_y), "w": stronghold_size, "h": stronghold_size, "type": "stronghold"})
            placed_objects.append({"name": "Guard", "x": to_grid_x(guard_x), "y": to_grid_y(guard_y), "w": guard_size, "h": guard_size, "type": "guard"})

            colors = {"stronghold": "#b22222", "guard": "#ff8c00", "r4": "#1e90ff", "r3": "#2e8b57"}

            # --- 1. OVERVIEW MAP GENERIEREN ---
            fig, ax = plt.subplots(figsize=(15, 15), dpi=140)
            ax.set_aspect('equal')
            ax.set_facecolor('#1e251c') 
            
            # Sichtbereich berechnen
            all_plot_x = [to_grid_x(guard_x), to_grid_x(guard_x)+guard_size] + [p["x"] for p in placed_players]
            all_plot_y = [to_grid_y(guard_y), to_grid_y(guard_y)+guard_size] + [p["y"] for p in placed_players]
            if stronghold_vorhanden:
                all_plot_x += [to_grid_x(stronghold_x), to_grid_x(stronghold_x)+stronghold_size]
                all_plot_y += [to_grid_y(stronghold_y), to_grid_y(stronghold_y)+stronghold_size]
                
            view_min_x, view_max_x = max(0, min(all_plot_x) - 5), min(grid_w, max(all_plot_x) + 5)
            view_min_y, view_max_y = max(0, min(all_plot_y) - 5), min(grid_h, max(all_plot_y) + 5)
            ax.set_xlim(view_min_x, view_max_x)
            ax.set_ylim(view_min_y, view_max_y)
            
            x_ticks = np.arange(view_min_x, view_max_x, 5)
            y_ticks = np.arange(view_min_y, view_max_y, 5)
            ax.set_xticks(x_ticks)
            ax.set_yticks(y_ticks)
            ax.set_xticklabels([str(int(to_game_coords(x, 0)[0])) for x in x_ticks], fontsize=10, color='white', rotation=45)
            ax.set_yticklabels([str(int(to_game_coords(0, y)[1])) for y in y_ticks], fontsize=10, color='white')
            ax.grid(True, color='#2d382a', linestyle='-', linewidth=0.8)

            # LAYER 1: Verbotene Zone (zorder=1)
            if forbidden_vorhanden:
                fb_rect = patches.Rectangle((to_grid_x(forbidden_x), to_grid_y(forbidden_y)), forbidden_w, forbidden_h, linewidth=2.0, edgecolor='#aaaaaa', facecolor='#444444', alpha=0.35, hatch='//', zorder=1)
                ax.add_patch(fb_rect)
                ax.text(to_grid_x(forbidden_x) + forbidden_w/2, to_grid_y(forbidden_y) + forbidden_h - 0.8, "FORBIDDEN ZONE", color="#aaaaaa", fontsize=11, fontweight='bold', ha='center', va='top', zorder=2)

            # LAYER 2: Stronghold & Guard (zorder=3)
            for obj in placed_objects:
                rect = patches.Rectangle((obj["x"], obj["y"]), obj["w"], obj["h"], linewidth=1.5, edgecolor='#ffffff', facecolor=colors[obj["type"]], alpha=0.9, zorder=3)
                ax.add_patch(rect)
                ax.text(obj["x"] + obj["w"]/2, obj["y"] + obj["h"]/2, obj["name"], color="white", fontsize=14, fontweight='bold', ha='center', va='center', zorder=4)

                if obj["type"] == "stronghold":
                    to = 0.5
                    ax.text(obj["x"] - to, obj["y"] - to, f"{stronghold_x}|{stronghold_y}", color="#ff4d4d", fontsize=11, fontweight='bold', ha='right', va='top', zorder=5)
                    ax.text(obj["x"] + obj["w"] + to, obj["y"] - to, f"{stronghold_x+stronghold_size-1}|{stronghold_y}", color="#ff4d4d", fontsize=11, fontweight='bold', ha='left', va='top', zorder=5)
                    ax.text(obj["x"] - to, obj["y"] + obj["h"] + to, f"{stronghold_x}|{stronghold_y+stronghold_size-1}", color="#ff4d4d", fontsize=11, fontweight='bold', ha='right', va='bottom', zorder=5)
                    ax.text(obj["x"] + obj["w"] + to, obj["y"] + obj["h"] + to, f"{stronghold_x+stronghold_size-1}|{stronghold_y+stronghold_size-1}", color="#ff4d4d", fontsize=11, fontweight='bold', ha='left', va='bottom', zorder=5)

            # LAYER 3: Spielerbasen (zorder=6)
            for p in placed_players:
                m = p["member"]
                bg_c = colors.get(m["rang"].lower(), "#2e8b57")
                rect = patches.Rectangle((p["x"], p["y"]), base_size, base_size, linewidth=1.0, edgecolor='#ffffff', facecolor=bg_c, alpha=0.95, zorder=6)
                ax.add_patch(rect)
                
                label = f"{m['name']}\n{p['gx']}|{p['gy']}"
                ax.text(p["x"] + base_size/2, p["y"] + base_size/2, label, color="white", fontsize=8, fontweight='bold', ha='center', va='center', zorder=7, clip_on=True)

            plt.title("Allianz Hive Plan", fontsize=18, color='white', pad=20, weight='bold')
            fig.patch.set_facecolor('#121711')
            st.pyplot(fig)
            
            img_buf = io.BytesIO()
            plt.savefig(img_buf, format='png', bbox_inches='tight')
            img_buf.seek(0)
            st.session_state.img_buf = img_buf
            plt.close()

            # --- 2. PROGRESS BAR & SPEZIELLE EINZELKARTEN ---
            st.subheader("⏳ Generating individual player maps...")
            progress_bar = st.progress(0.0)
            status_text = st.empty()
            
            total_players = len(placed_players)
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for index, p in enumerate(placed_players):
                    member = p["member"]
                    m_name = member["name"].strip()
                    
                    progress_bar.progress((index + 1) / total_players)
                    status_text.text(f"Processing map {index + 1} of {total_players}: {m_name}")
                    
                    fig_p, ax_p = plt.subplots(figsize=(7, 7), dpi=90) 
                    ax_p.set_aspect('equal')
                    ax_p.set_facecolor('#1e251c')
                    fig_p.patch.set_facecolor('#121711')
                    
                    radius = 16
                    ax_p.set_xlim(p["x"] - radius, p["x"] + radius + base_size)
                    ax_p.set_ylim(p["y"] - radius, p["y"] + radius + base_size)
                    
                    ax_p.set_xticks(np.arange(p["x"] - radius, p["x"] + radius + base_size, 5))
                    ax_p.set_yticks(np.arange(p["y"] - radius, p["y"] + radius + base_size, 5))
                    ax_p.set_xticklabels([str(int(to_game_coords(x, 0)[0])) for x in ax_p.get_xticks()], fontsize=8, color='white')
                    ax_p.set_yticklabels([str(int(to_game_coords(0, y)[1])) for y in ax_p.get_yticks()], fontsize=8, color='white')
                    ax_p.grid(True, color="#596157", linestyle=':', linewidth=0.5)
                    
                    if forbidden_vorhanden:
                        fb_rect_p = patches.Rectangle((to_grid_x(forbidden_x), to_grid_y(forbidden_y)), forbidden_w, forbidden_h, linewidth=2.0, edgecolor='#aaaaaa', facecolor='#444444', alpha=0.25, hatch='//', zorder=1)
                        ax_p.add_patch(fb_rect_p)

                    for obj in placed_objects:
                        r_obj = patches.Rectangle((obj["x"], obj["y"]), obj["w"], obj["h"], linewidth=1.2, edgecolor='#ffffff', facecolor=colors[obj["type"]], alpha=0.85, zorder=3)
                        ax_p.add_patch(r_obj)
                        ax_p.text(obj["x"] + obj["w"]/2, obj["y"] + obj["h"]/2, obj["name"], color="white", fontsize=11, fontweight='bold', ha='center', va='center', zorder=4)

                    for other in placed_players:
                        bg_o = colors.get(other["member"]["rang"].lower(), "#2e8b57")
                        r_o = patches.Rectangle((other["x"], other["y"]), base_size, base_size, linewidth=1.0, edgecolor='#ffffff', facecolor=bg_o, alpha=0.85, zorder=6)
                        ax_p.add_patch(r_o)

                    circle = patches.Circle((p["x"] + base_size/2, p["y"] + base_size/2), radius=3.0, linewidth=4, edgecolor='#00ff00', facecolor='none', zorder=10)
                    ax_p.add_patch(circle)
                    
                    box_text = f"DEINE POSITION:\n{m_name}\n\nX: {p['gx']}\nY: {p['gy']}"
                    ax_p.text(p["x"] - radius + 1, p["y"] + radius + base_size - 1, box_text, color='#00ff00', fontsize=10, fontweight='bold', va='top', ha='left', bbox=dict(facecolor='#121711', alpha=0.9, edgecolor='#00ff00', linewidth=2, pad=5), zorder=11)
                    
                    plt.title(f"Detail-Anfahrtsplan: {m_name}", fontsize=12, color='white', pad=10, weight='bold')
                    
                    player_img_buf = io.BytesIO()
                    plt.savefig(player_img_buf, format='png', facecolor=fig_p.get_facecolor(), bbox_inches='tight')
                    player_img_buf.seek(0)
                    plt.close()
                    
                    safe_name = "".join([c for c in m_name if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                    zip_file.writestr(f"spieler_karten/{safe_name}_hive_pos.png", player_img_buf.getvalue())
            
            zip_buffer.seek(0)
            st.session_state.zip_buffer = zip_buffer
            status_text.success("🎉 All individual maps generated successfully!")
            progress_bar.empty()

            # TXT-Bericht erstellen
            txt_content = "Allianz Hive Plan - Koordinaten & Basen\n=======================================\n\n"
            if stronghold_vorhanden:
                txt_content += f"[STRONGHOLD] {stronghold_name} | SW-Ecke: {stronghold_x}|{stronghold_y}\n"
            txt_content += f"[GUARD] Marshall Guard | SW-Ecke: {guard_x}|{guard_y}\n"
            if forbidden_vorhanden:
                txt_content += f"[FORBIDDEN ZONE] SW-Ecke: {forbidden_x}|{forbidden_y} bis NE-Ecke: {forbidden_x+forbidden_w-1}|{forbidden_y+forbidden_h-1}\n"
            txt_content += "\n[SPIELER BASEN]:\n"
            for p in placed_players:
                txt_content += f"Rang: {p['member']['rang'].upper()} | {p['member']['name']}: {p['gx']}|{p['gy']}\n"
            st.session_state.txt_content = txt_content

        except Exception as e:
            st.error(f"Fehler bei der Verarbeitung: {e}")

# --- DOWNLOAD AREA ---
if st.session_state.img_buf is not None:
    st.markdown("---")
    st.subheader("💾 Ergebnisse herunterladen")
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button(label="🗺️ Hauptkarte als PNG herunterladen", data=st.session_state.img_buf, file_name="hive_map.png", mime="image/png")
        st.write("")
        st.download_button(label="📝 Koordinaten als TXT herunterladen", data=st.session_state.txt_content, file_name="allianz_koordinaten.txt", mime="text/plain")
    with col_dl2:
        st.download_button(label="📦 ALLE EINZELKARTEN HERUNTERLADEN (ZIP)", data=st.session_state.zip_buffer, file_name="alliance_individual_maps.zip", mime="application/zip")