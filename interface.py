# app.py

import streamlit as st
import pandas as pd
import joblib
import openrouteservice
import folium
from streamlit_folium import folium_static

# 1. Chargement du modèle et des noms de features
model = joblib.load(r"modele_prediction_prix.pkl")
feature_names = joblib.load(r"modele ai\features.pkl")

# 2. Connexion à l'API OpenRouteService
API_KEY = '5b3ce3597851110001cf62486c68088f9551487cb1b076e8cce3ba84'
client = openrouteservice.Client(key=API_KEY)

# 3. Fonction pour récupérer distance et coordonnées du trajet
def get_route(lat1, lon1, lat2, lon2):
    try:
        coords = ((lon1, lat1), (lon2, lat2))  # (lon, lat) attendu
        resp = client.directions(coords, profile='driving-car', format='geojson')
        seg = resp['features'][0]['properties']['segments'][0]
        distance_km = seg['distance'] / 1000  # mètres → km
        coords_list = resp['features'][0]['geometry']['coordinates']
        return distance_km, coords_list
    except Exception as e:
        st.error(f"❌ Erreur API OpenRouteService : {e}")
        return None, None

# ----------------------------------------------------------------
st.title("🚌 CTM : Prédiction du Prix & Trajet Réel")

st.header("1. Coordonnées géographiques")
col1, col2 = st.columns(2)
with col1:
    lat_dep = st.number_input("Latitude Départ", value=33.916957, format="%.6f")
    lon_dep = st.number_input("Longitude Départ", value=-6.927790, format="%.6f")
with col2:
    lat_arr = st.number_input("Latitude Arrivée", value=32.250000, format="%.6f")
    lon_arr = st.number_input("Longitude Arrivée", value=-8.533300, format="%.6f")

st.header("2. Calcul distance et durée")
if st.button("Calculer via API"):
    dist, coords = get_route(lat_dep, lon_dep, lat_arr, lon_arr)
    if dist is not None:
        duree = dist / 60  # vitesse moyenne 60 km/h
        # On stocke tout dans session_state
        st.session_state.distance_km = dist
        st.session_state.duree_h = duree
        st.session_state.route_coords = coords
        st.success(f"Distance réelle : {dist:.2f} km → Durée ≃ {duree:.2f} h")
    else:
        st.warning("Impossible de récupérer le trajet.")

# Valeurs modifiables par l'utilisateur
dist_input = st.number_input(
    "Distance (km)", min_value=0.0,
    value=getattr(st.session_state, 'distance_km', 100.0)
)
duree_input = st.number_input(
    "Durée (h)", min_value=0.0,
    value=getattr(st.session_state, 'duree_h', 1.5)
)

# Delta latitude/longitude
delta_lat = lat_arr - lat_dep
delta_lon = lon_arr - lon_dep

st.header("3. Prédiction du Prix")
if st.button("Prédire le Prix"):
    # Préparation du DataFrame
    X = pd.DataFrame(0, index=[0], columns=feature_names)
    X['Distance_km_reelle'] = dist_input
    X['Durée_heures']      = duree_input
    X['Delta_Latitude']    = delta_lat
    X['Delta_Longitude']   = delta_lon

    # Encodage conditionnel de quelques villes exemples
    if 'Ville_Depart_rabat' in X.columns and lat_dep == 33.916957 and lon_dep == -6.92779:
        X['Ville_Depart_rabat'] = 1
    if 'Ville_Arrivee_youssoufia' in X.columns and lat_arr == 32.25 and lon_arr == -8.5333:
        X['Ville_Arrivee_youssoufia'] = 1

    # Prédiction
    prix = model.predict(X)[0]
    st.success(f"💰 Prix prédit : {prix:.2f} MAD")

    # Affichage de la carte du trajet réel
    coords_trajet = getattr(st.session_state, 'route_coords', None)
    if coords_trajet:
        # Centrage de la carte
        center = [(lat_dep+lat_arr)/2, (lon_dep+lon_arr)/2]
        m = folium.Map(location=center, zoom_start=7)
        folium.Marker([lat_dep, lon_dep], popup="Départ", icon=folium.Icon(color='green')).add_to(m)
        folium.Marker([lat_arr, lon_arr], popup="Arrivée", icon=folium.Icon(color='red')).add_to(m)
        folium.PolyLine(locations=[(lat, lon) for lon, lat in coords_trajet],
                        weight=3, opacity=0.8).add_to(m)
        st.header("🗺️ Trajet Réel")
        folium_static(m, width=700, height=500)
    else:
        st.info("Appuyez d’abord sur « Calculer via API » pour récupérer le trajet.")
