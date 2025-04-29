import streamlit as st
import pandas as pd
import joblib
import openrouteservice
import folium
from streamlit_folium import folium_static
import os

# 1. Chargement du modèle et des noms de features
model = joblib.load(r"modele_prediction_prix.pkl")
feature_names = joblib.load(r"features.pkl")

# 2. Connexion à l'API OpenRouteService
API_KEY = '5b3ce3597851110001cf62486c68088f9551487cb1b076e8cce3ba84'
client = openrouteservice.Client(key=API_KEY)

# 3. Chargement des villes connues
fichier_villes = "villes_coordonnees.csv"
if os.path.exists(fichier_villes):
    villes_df = pd.read_csv(fichier_villes)
    villes_dict = {row['nom'].strip().lower(): (row['lat'], row['lon']) for _, row in villes_df.iterrows()}
else:
    villes_dict = {}

# 4. Titre
st.title("🚌 CTM : Prédiction du Prix & Trajet Réel")

# 5. Saisie des noms de villes
st.header("1. Choix des villes")

ville_dep = st.text_input("Ville de Départ").strip().lower()
ville_arr = st.text_input("Ville d'Arrivée").strip().lower()

lat_dep = lon_dep = lat_arr = lon_arr = None

if ville_dep in villes_dict:
    lat_dep, lon_dep = villes_dict[ville_dep]
    st.success(f"📍 Coordonnées de départ trouvées : ({lat_dep}, {lon_dep})")
else:
    st.warning(f"Ville de départ inconnue : {ville_dep}")
    lat_dep = st.number_input("Latitude Départ (manuelle)", key="lat_dep_man")
    lon_dep = st.number_input("Longitude Départ (manuelle)", key="lon_dep_man")

if ville_arr in villes_dict:
    lat_arr, lon_arr = villes_dict[ville_arr]
    st.success(f"📍 Coordonnées d'arrivée trouvées : ({lat_arr}, {lon_arr})")
else:
    st.warning(f"Ville d'arrivée inconnue : {ville_arr}")
    lat_arr = st.number_input("Latitude Arrivée (manuelle)", key="lat_arr_man")
    lon_arr = st.number_input("Longitude Arrivée (manuelle)", key="lon_arr_man")

# Option : Enregistrement des nouvelles villes
if st.button("💾 Enregistrer les nouvelles villes"):
    new_entries = []
    if ville_dep not in villes_dict:
        new_entries.append({'nom': ville_dep, 'lat': lat_dep, 'lon': lon_dep})
    if ville_arr not in villes_dict:
        new_entries.append({'nom': ville_arr, 'lat': lat_arr, 'lon': lon_arr})
    if new_entries:
        new_df = pd.DataFrame(new_entries)
        if os.path.exists(fichier_villes):
            new_df.to_csv(fichier_villes, mode='a', header=False, index=False)
        else:
            new_df.to_csv(fichier_villes, index=False)
        st.success("✅ Nouvelles villes enregistrées.")

# Fonction pour récupérer distance et coordonnées du trajet
def get_route(lat1, lon1, lat2, lon2):
    try:
        coords = ((lon1, lat1), (lon2, lat2))
        resp = client.directions(coords, profile='driving-car', format='geojson')
        seg = resp['features'][0]['properties']['segments'][0]
        distance_km = seg['distance'] / 1000
        coords_list = resp['features'][0]['geometry']['coordinates']
        return distance_km, coords_list
    except Exception as e:
        st.error(f"❌ Erreur API OpenRouteService : {e}")
        return None, None

# Calcul distance/durée
st.header("2. Calcul distance et durée")
if st.button("🚗 Calculer via API"):
    dist, coords = get_route(lat_dep, lon_dep, lat_arr, lon_arr)
    if dist is not None:
        duree = dist / 60  # estimation à 60 km/h
        st.session_state.distance_km = dist
        st.session_state.duree_h = duree
        st.session_state.route_coords = coords
        st.success(f"Distance réelle : {dist:.2f} km → Durée ≃ {duree:.2f} h")
    else:
        st.warning("Impossible de récupérer le trajet.")

# Valeurs modifiables
dist_input = st.number_input("Distance (km)", min_value=0.0, value=getattr(st.session_state, 'distance_km', 100.0))
duree_input = st.number_input("Durée (h)", min_value=0.0, value=getattr(st.session_state, 'duree_h', 1.5))

# Delta
delta_lat = lat_arr - lat_dep
delta_lon = lon_arr - lon_dep

# Prédiction du prix
st.header("3. Prédiction du Prix")
if st.button("📈 Prédire le Prix"):
    X = pd.DataFrame(0, index=[0], columns=feature_names)
    X['Distance_km_reelle'] = dist_input
    X['Durée_heures'] = duree_input
    X['Delta_Latitude'] = delta_lat
    X['Delta_Longitude'] = delta_lon

    # Exemple d'encodage si des colonnes existent
    if f"Ville_Depart_{ville_dep}" in X.columns:
        X[f"Ville_Depart_{ville_dep}"] = 1
    if f"Ville_Arrivee_{ville_arr}" in X.columns:
        X[f"Ville_Arrivee_{ville_arr}"] = 1

    prix = model.predict(X)[0]
    st.success(f"💰 Prix prédit : {prix:.2f} MAD")

    # Affichage carte
    coords_trajet = getattr(st.session_state, 'route_coords', None)
    if coords_trajet:
        center = [(lat_dep+lat_arr)/2, (lon_dep+lon_arr)/2]
        m = folium.Map(location=center, zoom_start=7)
        folium.Marker([lat_dep, lon_dep], popup="Départ", icon=folium.Icon(color='green')).add_to(m)
        folium.Marker([lat_arr, lon_arr], popup="Arrivée", icon=folium.Icon(color='red')).add_to(m)
        folium.PolyLine(locations=[(lat, lon) for lon, lat in coords_trajet], weight=3, opacity=0.8).add_to(m)
        st.header("🗺️ Trajet Réel")
        folium_static(m, width=700, height=500)
    else:
        st.info("Appuyez d’abord sur « Calculer via API » pour récupérer le trajet.")
