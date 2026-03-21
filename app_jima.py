import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import shapely.geometry
from shapely.geometry import Polygon, box
import pyproj
from shapely.ops import transform
import numpy as np
from shapely.affinity import rotate, translate

# Configuration de la page
st.set_page_config(layout="wide")
st.title("☀️ Simulateur de Potentiel Solaire")

# --- SIDEBAR : Paramètres ---
st.sidebar.header("Paramètres des Panneaux")
p_unitaire = st.sidebar.number_input("Puissance (Wc)", value=400)
# Inversion possible Largeur/Longueur pour Portrait/Paysage
p_larg = st.sidebar.number_input("Largeur du panneau (m)", value=1.1)
p_long = st.sidebar.number_input("Longueur du panneau (m)", value=1.7)
orientation = st.sidebar.radio("Orientation", ["Portrait", "Paysage"])

if orientation == "Paysage":
    p_w, p_h = p_long, p_larg
else:
    p_w, p_h = p_larg, p_long

# Espacement de sécurité/maintenance entre les panneaux (en mètres)
espacement = st.sidebar.slider("Espacement entre panneaux (m)", 0.0, 0.5, 0.1)

# --- CARTE INTERACTIVE ---
st.subheader("1. Dessinez la zone")
# Initialisation de la carte centrée sur un exemple (on peut ajouter le géocodage plus tard)
m = folium.Map(location=[43.92241523798851, 2.1789539963687803], zoom_start=19, max_zoom=30) #43.92241523798851, 2.1789539963687803
# Tuiles Satellite Google
folium.TileLayer(
    tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
    attr='Google', name='Google Satellite', overlay=False, control=True
).add_to(m)

draw = Draw(export=False, draw_options={'polyline': False, 'rectangle': True, 'polygon': True, 'circle': False, 'marker': False, 'circlemarker': False})
draw.add_to(m)

# --- LOGIQUE DE PAVAGE (Fonction complexe) ---
def panner_zone(polygon_metrique, p_w, p_h, esp):
    """Calcule les rectangles de panneaux à l'intérieur du polygone."""
    minx, miny, maxx, maxy = polygon_metrique.bounds
    
    panneaux_metriques = []
    
    # Génération d'une grille de points
    x_coords = np.arange(minx, maxx, p_w + esp)
    y_coords = np.arange(miny, maxy, p_h + esp)
    
    for x in x_coords:
        for y in y_coords:
            # Création du rectangle du panneau potentiel
            panneau_bbox = box(x, y, x + p_w, y + p_h)
            
            # Vérification : le panneau est-il ENTIÈREMENT dans la zone dessinée ?
            if polygon_metrique.contains(panneau_bbox):
                panneaux_metriques.append(panneau_bbox)
                
    return panneaux_metriques

# --- AFFICHAGE ET CALCULS ---
output = st_folium(m, width=1100, height=600)

if output['last_active_drawing']:
    # 1. Récupération de la géométrie
    geom = output['last_active_drawing']['geometry']
    poly_gps = shapely.geometry.shape(geom)
    
    # 2. Projection en mètres (EPSG:3857 est standard pour les cartes web)
    project_to_meters = pyproj.Transformer.from_crs("epsg:4326", "epsg:3857", always_xy=True).transform
    project_to_gps = pyproj.Transformer.from_crs("epsg:3857", "epsg:4326", always_xy=True).transform
    poly_metrique = transform(project_to_meters, poly_gps)
    
    # 3. Calcul du pavage (Pannage)
    liste_panneaux_metriques = panner_zone(poly_metrique, p_w, p_h, espacement)
    nb_panneaux = len(liste_panneaux_metriques)
    
    # 4. Conversion des panneaux en GPS pour l'affichage
    panneaux_gps = []
    for p_met in liste_panneaux_metriques:
        panneaux_gps.append(transform(project_to_gps, p_met))

    # 5. Ré-affichage de la carte AVEC LES PANNEAUX
    st.subheader("2. Visualisation de l'implantation")
    
    # Créer une nouvelle carte centrée sur le dessin
    centroid = poly_gps.centroid
    m2 = folium.Map(location=[centroid.y, centroid.x], zoom_start=20, max_zoom=30)
    folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attr='Google', name='Google Satellite').add_to(m2)
    
    # Dessiner la zone originale
    folium.GeoJson(poly_gps, style_function=lambda x: {'fillColor': '#ffff00', 'color': '#ffff00', 'weight': 2, 'fillOpacity': 0.3}).add_to(m2)
    
    # Dessiner chaque panneau
    for p_gps in panneaux_gps:
        folium.GeoJson(p_gps, style_function=lambda x: {'fillColor': '#0000ff', 'color': '#0000ff', 'weight': 1, 'fillOpacity': 0.6}).add_to(m2)
        
    st_folium(m2, width=1100, height=600, key="map_visu")

    # 6. Résultats numériques
    puissance_totale = (nb_panneaux * p_unitaire) / 1000
    st.success(f"Analyse terminée.")
    col1, col2 = st.columns(2)
    col1.metric("Nombre de panneaux visualisés", f"{nb_panneaux}")
    col2.metric("Puissance Totale Estimée", f"{puissance_totale:.2f} kWc")

else:
    st.info("Utilisez l'outil polygone ou rectangle sur la carte pour délimiter la zone d'installation.")