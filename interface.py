import streamlit as st
import pandas as pd
import joblib
import openrouteservice
import folium
from streamlit_folium import folium_static
import os

# 1. Chargement du modèle
model = joblib.load(r"modele_prediction_prix.pkl")
feature_names = joblib.load(r"features.pkl")

# 2. API OpenRouteService
API_KEY = '5b3ce3597851110001cf62486c68088f9551487cb1b076e8cce3ba84'
client = openrouteservice.Client(key=API_KEY)

# 3. Chargement fichier villes
import pandas as pd
import os

fichier_villes = "bus_stops_data_complet.xlsx"

if os.path.exists(fichier_villes):
    villes_df = pd.read_excel(fichier_villes)

    # Nettoyage des noms de colonnes
    villes_df.columns = [col.strip().lower() for col in villes_df.columns]

    # Conversion sécurisée des coordonnées
    if villes_df['latitude'].dtype == 'object':
        villes_df['latitude'] = villes_df['latitude'].str.replace(',', '.').astype(float)
    if villes_df['longitude'].dtype == 'object':
        villes_df['longitude'] = villes_df['longitude'].str.replace(',', '.').astype(float)

    # Création du dictionnaire pour accès rapide
    villes_dict = {
        row['cityname'].strip().lower(): (row['latitude'], row['longitude'])
        for _, row in villes_df.iterrows()
    }

    # Liste des villes pour suggestions
    liste_villes = sorted(villes_dict.keys())

else:
    villes_df = pd.DataFrame(columns=['cityname', 'latitude', 'longitude'])
    villes_dict = {}
    liste_villes = []


# 4. Interface utilisateur
st.title("🚌 CTM : Prédiction du Prix & Trajet Réel")

st.header("1. Choix des villes")

# Saisie avec suggestions
ville_dep = st.selectbox("Ville de départ", options=[""] + liste_villes, index=0)
ville_arr = st.selectbox("Ville d’arrivée", options=[""] + liste_villes, index=0)

# Champs pour noms manuels
if ville_dep == "":
    ville_dep = st.text_input("Nom de la ville de départ (nouvelle)", key="ville_dep_custom").strip().lower()
if ville_arr == "":
    ville_arr = st.text_input("Nom de la ville d’arrivée (nouvelle)", key="ville_arr_custom").strip().lower()

# Coordonnées
def get_coords(ville, role):
    if ville in villes_dict:
        return villes_dict[ville]
    else:
        lat = st.number_input(f"Latitude {role}", key=f"lat_{role}")
        lon = st.number_input(f"Longitude {role}", key=f"lon_{role}")
        return lat, lon

lat_dep, lon_dep = get_coords(ville_dep, "Départ")
lat_arr, lon_arr = get_coords(ville_arr, "Arrivée")

# Enregistrement des nouvelles villes
def enregistrer_ville(nom, lat, lon):
    if nom not in villes_dict and nom != "":
        new_row = pd.DataFrame([{'nom': nom, 'lat': lat, 'lon': lon}])
        new_row.to_csv(fichier_villes, mode='a', header=not os.path.exists(fichier_villes), index=False)
        st.success(f"✅ Ville enregistrée : {nom}")

if st.button("💾 Enregistrer les nouvelles villes"):
    enregistrer_ville(ville_dep, lat_dep, lon_dep)
    enregistrer_ville(ville_arr, lat_arr, lon_arr)

# Fonction route
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

# Calcul distance
st.header("2. Calcul distance et durée")
if st.button("🚗 Calculer via API"):
    dist, coords = get_route(lat_dep, lon_dep, lat_arr, lon_arr)
    if dist is not None:
        duree = dist / 60
        st.session_state.distance_km = dist
        st.session_state.duree_h = duree
        st.session_state.route_coords = coords
        st.success(f"Distance : {dist:.2f} km → Durée ≃ {duree:.2f} h")
    else:
        st.warning("Échec récupération trajet.")

# Valeurs modifiables
dist_input = st.number_input("Distance (km)", min_value=0.0, value=st.session_state.get('distance_km', 100.0))
duree_input = st.number_input("Durée (h)", min_value=0.0, value=st.session_state.get('duree_h', 1.5))

# Delta
delta_lat = lat_arr - lat_dep
delta_lon = lon_arr - lon_dep

# Prédiction
st.header("3. Prédiction du Prix")
if st.button("📈 Prédire le Prix"):
    X = pd.DataFrame(0, index=[0], columns=feature_names)
    X['Distance_km_reelle'] = dist_input
    X['Durée_heures'] = duree_input
    X['Delta_Latitude'] = delta_lat
    X['Delta_Longitude'] = delta_lon

    # Encodage conditionnel
    if f"Ville_Depart_{ville_dep}" in X.columns:
        X[f"Ville_Depart_{ville_dep}"] = 1
    if f"Ville_Arrivee_{ville_arr}" in X.columns:
        X[f"Ville_Arrivee_{ville_arr}"] = 1

    prix = model.predict(X)[0]
    st.success(f"💰 Prix prédit : {prix:.2f} MAD")

    # Carte
    coords_trajet = st.session_state.get('route_coords')
    if coords_trajet:
        center = [(lat_dep + lat_arr) / 2, (lon_dep + lon_arr) / 2]
        m = folium.Map(location=center, zoom_start=7)
        folium.Marker([lat_dep, lon_dep], popup="Départ", icon=folium.Icon(color='green')).add_to(m)
        folium.Marker([lat_arr, lon_arr], popup="Arrivée", icon=folium.Icon(color='red')).add_to(m)
        folium.PolyLine(locations=[(lat, lon) for lon, lat in coords_trajet], weight=3).add_to(m)
        st.header("🗺️ Trajet Réel")
        folium_static(m, width=700, height=500)
