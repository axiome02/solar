import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import shapely.geometry
from shapely.geometry import box
from shapely.affinity import rotate
import pyproj
from shapely.ops import transform
import numpy as np

# --- CONFIGURATION PAGE ---
st.set_page_config(layout="wide", page_title="Solar JIMA", page_icon="☀️")

st.title("☀️ Solar JIMA")
st.markdown("""
    Tracez une zone sur la carte (toiture ou sol) pour simuler une implantation réelle 
    tenant compte de l'orientation, de l'inclinaison et de l'espacement.
""")

# --- SIDEBAR : PARAMÈTRES TECHNIQUES ---
st.sidebar.header("🔧 Paramètres Panneaux")
p_nominale = st.sidebar.number_input("Puissance unitaire (Wc)", value=400)
p_larg = st.sidebar.number_input("Largeur du panneau (m)", value=1.13)
p_long = st.sidebar.number_input("Longueur du panneau (m)", value=1.72)

st.sidebar.header("📐 Configuration")
pose = st.sidebar.selectbox("Mode de pose", ["Portrait", "Paysage"])
inclinaison = st.sidebar.slider("Inclinaison des panneaux (°)", 0, 45, 30)
azimut = st.sidebar.slider("Azimut (0°=Nord, 180°=Sud)", 0, 360, 180)

st.sidebar.header("📏 Espacement & Pas")
gap_lateral = st.sidebar.slider("Écart latéral entre panneaux (m)", 0.01, 0.10, 0.02, step=0.01)

# Calcul automatique du pas (Pitch) pour éviter l'ombre (simplifié)
# Au sol, on veut souvent un pas plus large. Sur toit plat, environ 2.5m.
pas_entre_rangees = st.sidebar.number_input("Pas (Pitch) entre rangées (m)", value=2.5, help="Distance entre le bas d'une rangée et le bas de la suivante.")

# --- LOGIQUE DE CALCUL ---

# Ajustement selon mode de pose
if pose == "Paysage":
    w_effective, h_effective = p_long, p_larg
else:
    w_effective, h_effective = p_larg, p_long

# Calcul de la projection horizontale de la hauteur du panneau incliné
h_projetee = h_effective * np.cos(np.radians(inclinaison))

def generer_layout_pro(zone_poly, p_w, p_h_proj, azimut, pitch, gap_x):
    """Génère une grille de panneaux orientée et filtrée par la zone."""
    bounds = zone_poly.bounds # (minx, miny, maxx, maxy)
    center = zone_poly.centroid
    
    # On crée une grille large autour de la zone pour couvrir après rotation
    # On utilise un buffer pour être sûr de couvrir toute la zone tracée
    x_range = np.arange(bounds[0] - 50, bounds[2] + 50, p_w + gap_x)
    y_range = np.arange(bounds[1] - 50, bounds[3] + 50, pitch)
    
    panneaux_finaux = []
    
    for x in x_range:
        for y in y_range:
            # Création du rectangle (panneau)
            p = box(x, y, x + p_w, y + p_h_proj)
            
            # Rotation selon l'Azimut (Folium/Shapely rotation est anti-horaire)
            # On ajuste pour que 180° = Sud
            p_rot = rotate(p, -(azimut - 180), origin=center)
            
            # Vérification d'intersection : le panneau doit être à 100% dans la zone
            if zone_poly.contains(p_rot):
                panneaux_finaux.append(p_rot)
                
    return panneaux_finaux

# --- INTERFACE CARTE ---

col_map, col_res = st.columns([3, 1])

with col_map:
    m = folium.Map(location=[43.92241523798851, 2.1789539963687803], zoom_start=17, max_zoom=30)
    #m = folium.Map(location=[46.2, 2.2], zoom_start=6, max_zoom=22)
    # Fond Satellite Google
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google Satellite', name='Satellite', overlay=False
    ).add_to(m)

    draw = Draw(
        export=False,
        draw_options={
            'polyline': False, 'rectangle': True, 'polygon': True, 
            'circle': False, 'marker': False, 'circlemarker': False
        }
    )
    draw.add_to(m)
    
    output = st_folium(m, width="100%", height=600, key="main_map")

# --- TRAITEMENT DES DONNÉES ---

if output['last_active_drawing']:
    # 1. Géométrie
    geom = output['last_active_drawing']['geometry']
    poly_gps = shapely.geometry.shape(geom)
    
    # 2. Projection Métrique
    to_meters = pyproj.Transformer.from_crs("epsg:4326", "epsg:3857", always_xy=True).transform
    to_gps = pyproj.Transformer.from_crs("epsg:3857", "epsg:4326", always_xy=True).transform
    
    poly_metrique = transform(to_meters, poly_gps)
    
    # 3. Génération du Layout
    liste_panneaux_metriques = generer_layout_pro(
        poly_metrique, w_effective, h_projetee, azimut, pas_entre_rangees, gap_lateral
    )
    
    # 4. Conversion GPS pour affichage
    panneaux_gps = [transform(to_gps, p) for p in liste_panneaux_metriques]
    
    # 5. Mise à jour de la vue
    with col_res:
        nb = len(panneaux_gps)
        puissance_totale = (nb * p_nominale) / 1000
        
        st.metric("Nombre de panneaux", f"{nb}")
        st.metric("Puissance Totale", f"{puissance_totale:.2f} kWc")
        st.info(f"Surface zone : {poly_metrique.area:.1f} m²")
        
        if st.button("Réinitialiser"):
            st.rerun()

    # Dessiner les panneaux sur la carte après calcul
    # On recrée une petite carte de visualisation pour confirmer l'implantation
    st.subheader("Visualisation de l'implantation technique")
    m2 = folium.Map(location=[poly_gps.centroid.y, poly_gps.centroid.x], zoom_start=20, max_zoom=22)
    folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attr='Google').add_to(m2)
    
    # Zone jaune
    folium.GeoJson(poly_gps, style_function=lambda x: {'color': 'yellow', 'fillOpacity': 0.2}).add_to(m2)
    
    # Panneaux bleus
    for p_gps in panneaux_gps:
        folium.GeoJson(p_gps, style_function=lambda x: {'color': '#1f77b4', 'weight': 1, 'fillOpacity': 0.7}).add_to(m2)
    
    st_folium(m2, width=1100, height=500, key="view_map")
else:
    with col_res:
        st.warning("En attente d'un tracé sur la carte...")