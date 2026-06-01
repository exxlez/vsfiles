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

# Initialisiere Session State für die Downloads, damit sie nicht verschwinden
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
        Y_VON_UNTEN_NACH_OBEN = st.checkbox("Y Down to Up?", value=True,
                                            help="Sets the Coordinate System, try it by yourself!")
    with col_g5:
        X_VON_LINKS_NACH_RECHTS = st.checkbox("X Down to Up?", value=True)
        
    st.subheader("📍 Marshall Guard / Hive-Center (Always active)")
    col_g1, col_g2, col_g3= st.columns(3)
    with col_g1:
        guard_x = st.number_input("Marshall Guard/Hive-Center X-Coordinate. BE AWARE! Take Always the lower left corner", value=756)
    with col_g2:
        guard_y = st.number_input("Guard/Hive-Center Y-Coordinate. BE AWARE! Take Always the lower left corner", value=803)
    with col_g3:
        guard_size = st.number_input("Guard Size (Fields)", value=3)

    st.subheader("🏰 Stronghold-Options, will be the Center if Active!")
    stronghold_vorhanden = st.checkbox("Stronghold near Hive?", value=True)
    
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        stronghold_x = st.number_input("Stronghold X-Coordinate.", value=774)
    with col_s2:
        stronghold_y = st.number_input("Stronghold Y-Coordinate.", value=799)
    with col_s3:
        stronghold_size = st.number_input("Stronghold/City Size (Fields)", value=13)
    with col_s4:
        stronghold_name = st.text_input("Name of City or Stronghold", value="Stronghold Lv5")
    
    st.subheader("⚠️ Zone Monitoring (Minimum Distance)")
    min_hive_distance = st.number_input("Minimum distance Stronghold to Hive-Center (Radius)", value=15)

    st.subheader("⚙️ General Settings")
    col_a1, col_a2, col_a3 = st.columns(3)
    with col_a1:
        base_size = st.number_input("Base Size (Players)", value=3)
    with col_a2:
        spacing = st.number_input("Spacing between Bases in Fields", value=1)
    with col_a3:
        padding = st.number_input("Padding", value=60)

    st.subheader("📂 Alliance Data")
    uploaded_file = st.file_uploader("Upload your allianz.json", type=["json"])
    submit_button = st.form_submit_button("Generate Hive-Plan")

# --- PRÜFUNG: ABSTAND ZUM HIVE-CENTER ---
def check_stronghold_near_hive(sx, sy, ss, gx, gy, gs, min_dist):
    sh_center_x = sx + (ss / 2)
    sh_center_y = sy + (ss / 2)
    hive_center_x = gx + (gs / 2)
    hive_center_y = gy + (gs / 2)
    distance = np.sqrt((sh_center_x - hive_center_x)**2 + (sh_center_y - hive_center_y)**2)
    return distance, distance < min_dist

# --- HAUPT-LOGIK NACH SUBMIT ---
if submit_button:
    if not uploaded_file:
        st.error("❌ Upload a valid allianz.json!")
    else:
        is_too_near = False
        if stronghold_vorhanden:
            actual_dist, is_too_near = check_stronghold_near_hive(
                stronghold_x, stronghold_y, stronghold_size, 
                guard_x, guard_y, guard_size, min_hive_distance
            )
        
        if stronghold_vorhanden and is_too_near:
            st.error(f"⚠️ **ERROR: Stronghold near hive!** Pls replace your Guard or Stronghold Coordinates!")
        else:
            st.success("✅ Parameter check successful! Generating data...")
            
            try:
                raw_members = json.load(uploaded_file)
                
                if stronghold_vorhanden:
                    min_game_x = min(stronghold_x, guard_x) - padding
                    max_game_x = max(stronghold_x + stronghold_size, guard_x + guard_size) + padding
                    min_game_y = min(stronghold_y, guard_y) - padding
                    max_game_y = max(stronghold_y + stronghold_size, guard_y + guard_size) + padding
                else:
                    min_game_x = guard_x - padding
                    max_game_x = guard_x + guard_size + padding
                    min_game_y = guard_y - padding
                    max_game_y = guard_y + guard_size + padding
                
                grid_w = int(max_game_x - min_game_x)
                grid_h = int(max_game_y - min_game_y)
                
                def to_grid_x(game_x): return int(game_x - min_game_x)
                def to_grid_y(game_y): return int(game_y - min_game_y)
                def to_game_coords(mx, my):
                    real_x = int(mx + min_game_x) if X_VON_LINKS_NACH_RECHTS else int(max_game_x - mx - base_size)
                    real_y = int(min_game_y + my) if Y_VON_UNTEN_NACH_OBEN else int(max_game_y - my - base_size)
                    return real_x, real_y

                guard_blocked_x = set(range(int(guard_x), int(guard_x + guard_size)))
                guard_blocked_y = set(range(int(guard_y), int(guard_y + guard_size)))
                
                if stronghold_vorhanden:
                    sh_game_start_x = stronghold_x - 6
                    sh_game_start_y = stronghold_y - 6
                    sh_game_ende_x = sh_game_start_x + stronghold_size - 1
                    sh_game_ende_y = sh_game_start_y + stronghold_size - 1
                    stronghold_blocked_x = set(range(int(sh_game_start_x + 1), int(sh_game_ende_x)))
                    stronghold_blocked_y = set(range(int(sh_game_start_y + 1), int(sh_game_ende_y)))
                else:
                    stronghold_blocked_x = set()
                    stronghold_blocked_y = set()

                def is_game_position_blocked(gx, gy):
                    p_x = set(range(gx, gx + int(base_size)))
                    p_y = set(range(gy, gy + int(base_size)))
                    if (p_x & guard_blocked_x) and (p_y & guard_blocked_y): return True
                    if stronghold_vorhanden:
                        if (p_x & stronghold_blocked_x) and (p_y & stronghold_blocked_y): return True
                    return False

                grid = np.zeros((grid_h, grid_w), dtype=int)
                gw_x, gw_y = to_grid_x(guard_x), to_grid_y(guard_y)
                if stronghold_vorhanden:
                    sh_x, sh_y = to_grid_x(stronghold_x) - 6, to_grid_y(stronghold_y) - 6

                step = int(base_size + spacing)
                hive_center_game_x = stronghold_x if stronghold_vorhanden else guard_x
                hive_center_game_y = stronghold_y if stronghold_vorhanden else guard_y
                
                MAX_R4_DISTANCE = 16.0 
                
                possible_slots_for_r4, possible_slots_for_r3 = [], []
                for row_idx in range(-40, 40):
                    target_y = gw_y + (row_idx * step)
                    for col_idx in range(-40, 40):
                        target_x = gw_x + (col_idx * step)
                        if (0 <= target_x < grid_w - base_size) and (0 <= target_y < grid_h - base_size):
                            gx, gy = to_game_coords(target_x, target_y)
                            if is_game_position_blocked(gx, gy): continue
                            
                            d_guard = np.sqrt((gx - guard_x)**2 + (gy - guard_y)**2)
                            d_hive = np.sqrt((gx - hive_center_game_x)**2 + (gy - hive_center_game_y)**2)
                            
                            if d_guard <= MAX_R4_DISTANCE:
                                possible_slots_for_r4.append({"x": target_x, "y": target_y, "dist": d_guard})
                            possible_slots_for_r3.append({"x": target_x, "y": target_y, "dist": d_hive})

                possible_slots_for_r4.sort(key=lambda s: s["dist"])
                possible_slots_for_r3.sort(key=lambda s: s["dist"])

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

                def is_area_free(sx, sy):
                    gx, gy = to_game_coords(sx, sy)
                    if is_game_position_blocked(gx, gy): return False
                    if not (0 <= sx < grid_w - base_size and 0 <= sy < grid_h - base_size): return False
                    return not np.any(grid[sy - spacing : sy + base_size + spacing, sx - spacing : sx + base_size + spacing] > 0)

                placed_players = []
                name_to_placed_coords = {}

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
                                                    d_guard = np.sqrt((gx - guard_x)**2 + (gy - guard_y)**2)
                                                    if d_guard > MAX_R4_DISTANCE: continue 
                                                        
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
                                search_pool = possible_slots_for_r4 if m_rang == "R4" else possible_slots_for_r3
                                for slot in search_pool:
                                    if is_area_free(slot["x"], slot["y"]):
                                        px, py = slot["x"], slot["y"]
                                        grid[py : py + base_size, px : px + base_size] = 1
                                        placed_players.append({"member": member, "x": px, "y": py})
                                        name_to_placed_coords[m_name] = (px, py)
                                        placed = True
                                        break

                placed_objects = []
                if stronghold_vorhanden:
                    placed_objects.append({"name": stronghold_name, "x": sh_x, "y": sh_y, "w": stronghold_size, "h": stronghold_size, "type": "stronghold"})
                
                placed_objects.append({"name": f"Guard", "x": gw_x, "y": gw_y, "w": guard_size, "h": guard_size, "type": "guard"})

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
                        "real_center_x": center_x,
                        "real_center_y": center_y
                    })

                colors = {"stronghold": "#b22222", "guard": "#ff8c00", "r4": "#1e90ff", "r3": "#2e8b57"}

                # --- 1. OVERVIEW MAP GENERIEREN ---
                all_x = [obj["x"] for obj in placed_objects] + [obj["x"]+obj["w"] for obj in placed_objects]
                all_y = [obj["y"] for obj in placed_objects] + [obj["y"]+obj["h"] for obj in placed_objects]
                view_min_x, view_max_x = max(0, min(all_x) - 4), min(grid_w, max(all_x) + 4)
                view_min_y, view_max_y = max(0, min(all_y) - 4), min(grid_h, max(all_y) + 4)

                fig, ax = plt.subplots(figsize=(15, 15), dpi=140)
                ax.set_aspect('equal')
                ax.set_facecolor('#1e251c') 
                ax.set_xlim(view_min_x, view_max_x)
                ax.set_ylim(view_min_y, view_max_y)
                
                x_ticks_major = np.arange(view_min_x, view_max_x, 5)
                y_ticks_major = np.arange(view_min_y, view_max_y, 5)
                ax.set_xticks(x_ticks_major)
                ax.set_yticks(y_ticks_major)
                ax.set_xticklabels([str(int(x + min_game_x)) for x in x_ticks_major], fontsize=10, color='white', rotation=45)
                ax.set_yticklabels([str(int(min_game_y + y)) for y in y_ticks_major], fontsize=10, color='white')
                
                ax.grid(True, which='major', color='#2d382a', linestyle='-', linewidth=0.8)
                
                for obj in placed_objects:
                    rect = patches.Rectangle((obj["x"], obj["y"]), obj["w"], obj["h"], linewidth=1.2, edgecolor='#ffffff', facecolor=colors.get(obj["type"], "#4682b4"), alpha=0.9)
                    ax.add_patch(rect)
                    font_sz = 8 if obj["type"] in ["r4", "r3"] else 14
                    ax.text(obj["x"] + obj["w"]/2, obj["y"] + obj["h"]/2, obj["name"], color="white", fontsize=font_sz, fontweight='bold', ha='center', va='center', clip_on=True, wrap=True)

                plt.title("Allianz Hive Plan", fontsize=18, color='white', pad=20, weight='bold')
                fig.patch.set_facecolor('#121711')
                
                # Plot anzeigen
                st.pyplot(fig)
                
                # Hauptkarte speichern
                img_buf = io.BytesIO()
                plt.savefig(img_buf, format='png', bbox_inches='tight')
                img_buf.seek(0)
                st.session_state.img_buf = img_buf
                plt.close()
                
                # --- 2. PROGRESS BAR & MAPS GENERIERUNG (OPTIMIERT & NÄHER RAN GEZOOMT) ---
                st.subheader("⏳ Generating individual player maps...")
                progress_bar = st.progress(0.0)
                status_text = st.empty()
                
                total_players = len(placed_players)
                zip_buffer = io.BytesIO()
                
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    for index, p in enumerate(placed_players):
                        member = p["member"]
                        m_name = member["name"].strip()
                        mx, my = p["x"], p["y"]
                        
                        # Update progress bar & status text
                        percent_complete = (index + 1) / total_players
                        progress_bar.progress(percent_complete)
                        status_text.text(f"Processing map {index + 1} of {total_players}: {m_name}")
                        
                        center_x = int(mx + min_game_x) + 1
                        center_y = int(my + min_game_y) + 1
                        
                        # Plot für Einzelkarte aufbauen
                        fig_p, ax_p = plt.subplots(figsize=(7, 7), dpi=90) # Kleinere Auflösung (90 DPI) für rasante Generierung
                        ax_p.set_aspect('equal')
                        ax_p.set_facecolor('#1e251c')
                        fig_p.patch.set_facecolor('#121711')
                        
                        # NÄHER RAN GEZOOMT: Radius von 25 auf 14 reduziert für besseren Fokus
                        radius = 14 
                        ax_p.set_xlim(mx - radius, mx + radius + 2)
                        ax_p.set_ylim(my - radius, my + radius + 2)
                        
                        ax_p.set_xticks(np.arange(mx - radius, mx + radius + 3, 5))
                        ax_p.set_yticks(np.arange(my - radius, my + radius + 3, 5))
                        ax_p.set_xticklabels([str(int(x + min_game_x)) for x in ax_p.get_xticks()], fontsize=8, color='white')
                        ax_p.set_yticklabels([str(int(y + min_game_y)) for y in ax_p.get_yticks()], fontsize=8, color='white')
                        ax_p.grid(True, color="#596157", linestyle=':', linewidth=0.5)
                        
                        # Objekte im engen Radius einzeichnen
                        for obj in placed_objects:
                            if (mx - radius - 10 < obj["x"] < mx + radius + 10) and (my - radius - 10 < obj["y"] < my + radius + 10):
                                rect_obj = patches.Rectangle(
                                    (obj["x"], obj["y"]), obj["w"], obj["h"], 
                                    linewidth=1.2, edgecolor='#ffffff', 
                                    facecolor=colors.get(obj["type"], "#4682b4"), alpha=0.85
                                )
                                ax_p.add_patch(rect_obj)
                                
                                font_sz_obj = 7 if obj["type"] in ["r4", "r3"] else 11
                                ax_p.text(obj["x"] + obj["w"]/2, obj["y"] + obj["h"]/2, obj["name"], 
                                          color="white", fontsize=font_sz_obj, fontweight='bold', ha='center', va='center', clip_on=True, wrap=True)

                        # HIGHLIGHT 1: Grüner Kreis um die Basis
                        circle = patches.Circle((mx + 1.5, my + 1.5), radius=2.8, linewidth=4, edgecolor='#00ff00', facecolor='none', zorder=10)
                        ax_p.add_patch(circle)
                        
                        # HIGHLIGHT 2: Markante Koordinaten-Box im freien Raum (oben links fixiert)
                        box_text = f"DEINE POSITION:\n{m_name}\n\nX: {center_x}\nY: {center_y}"
                        ax_p.text(
                            mx - radius + 1, my + radius - 1, box_text, 
                            color='#00ff00', fontsize=11, fontweight='bold', va='top', ha='left',
                            bbox=dict(facecolor='#121711', alpha=0.9, edgecolor='#00ff00', linewidth=2, pad=6),
                            zorder=11
                        )
                        
                        plt.title(f"Detail-Anfahrtsplan: {m_name}", fontsize=12, color='white', pad=10, weight='bold')
                        
                        player_img_buf = io.BytesIO()
                        plt.savefig(player_img_buf, format='png', facecolor=fig_p.get_facecolor(), bbox_inches='tight')
                        player_img_buf.seek(0)
                        plt.close()
                        
                        safe_name = "".join([c for c in m_name if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                        zip_file.writestr(f"spieler_karten/{safe_name}_hive_pos.png", player_img_buf.getvalue())
                
                zip_buffer.seek(0)
                st.session_state.zip_buffer = zip_buffer
                
                # Fortschritts-UI aufräumen
                status_text.success("🎉 All individual maps generated successfully!")
                progress_bar.empty()

                # --- 3. TXT DATEI GENERIEREN ---
                txt_content = "Allianz Hive Plan - Koordinaten & Basen\n=======================================\n\n"
                for obj in placed_objects:
                    clean_info = obj["name"].replace('\n', ' |  ')
                    txt_content += f"[{obj['type'].upper()}] {clean_info}\n"
                st.session_state.txt_content = txt_content

            except Exception as e:
                st.error(f"Fehler bei der Verarbeitung der JSON-Datei: {e}")

# --- DOWNLOAD AREA (AUßERHALB DER BUTTON-BEDINGUNG) ---
# Zeigt den Download-Bereich dauerhaft an, sobald die Daten im Session State existieren!
if st.session_state.img_buf is not None:
    st.markdown("---")
    st.subheader("💾 Ergebnisse herunterladen")
    col_dl1, col_dl2 = st.columns(2)
    
    with col_dl1:
        st.download_button(
            label="🗺️ Hauptkarte als PNG herunterladen", 
            data=st.session_state.img_buf, 
            file_name="hive_map.png", 
            mime="image/png"
        )
        st.write("")
        st.download_button(
            label="📝 Koordinaten als TXT herunterladen", 
            data=st.session_state.txt_content, 
            file_name="allianz_koordinaten.txt", 
            mime="text/plain"
        )
        
    with col_dl2:
        st.download_button(
            label="📦 ALLE EINZELKARTEN HERUNTERLADEN (ZIP)", 
            data=st.session_state.zip_buffer, 
            file_name="alliance_individual_maps.zip", 
            mime="application/zip"
        )