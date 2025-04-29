# app.py
import streamlit as st
import pandas as pd
import joblib
import openrouteservice
import folium
from streamlit_folium import st_folium

# --- Chargement du modèle et des features ---
model = joblib.load("modele_ai/modele_prediction_prix.pkl")
feature_names = joblib.load("modele_ai/features.pkl")

# --- Clé API OpenRouteService ---
client = openrouteservice.Client(key="5b3ce3597851110001cf62486c68088f9551487cb1b076e8cce3ba84")

# --- Fonction pour obtenir la distance réelle ---
def get_route(lat1, lon1, lat2, lon2):
    try:
        coords = ((lon1, lat1), (lon2, lat2))
        resp = client.directions(coords, profile='driving-car', format='geojson')
        segment = resp['features'][0]['properties']['segments'][0]
        distance_km = segment['distance'] / 1000
        geometry = resp['features'][0]['geometry']['coordinates']
        return distance_km, geometry
    except Exception as e:
        st.error(f"Erreur API OpenRouteService : {e}")
        return None, None

# --- Fonction de reverse géocoding (affiche nom de ville approximatif) ---
def get_city_name(lat, lon):
    try:
        result = client.pelias_reverse((lon, lat))
        return result['features'][0]['properties']['locality']
    except:
        return "(ville inconnue)"

# --- Interface Streamlit ---
st.set_page_config(page_title="Prédicteur de Prix CTM", layout="centered")
st.title("🚌 Prédicteur de Prix pour les Trajets CTM")

st.subheader("1. Choisissez deux points sur la carte")
defaut_location = [33.5731, -7.5898]  # Casablanca

m = folium.Map(location=defaut_location, zoom_start=6)
folium.Marker(location=defaut_location, tooltip="Cliquez pour définir le départ", icon=folium.Icon(color='green')).add_to(m)
m.add_child(folium.LatLngPopup())

map_data = st_folium(m, width=700, height=500)

# --- Stocker les clics ---
if 'clicks' not in st.session_state:
    st.session_state.clicks = []

if map_data and map_data['last_clicked']:
    clicked = map_data['last_clicked']
    if len(st.session_state.clicks) < 2:
        st.session_state.clicks.append(clicked)

# --- Affichage des coordonnées sélectionnées ---
if len(st.session_state.clicks) == 2:
    point1 = st.session_state.clicks[0]
    point2 = st.session_state.clicks[1]

    lat_dep, lon_dep = point1['lat'], point1['lng']
    lat_arr, lon_arr = point2['lat'], point2['lng']

    city_dep = get_city_name(lat_dep, lon_dep)
    city_arr = get_city_name(lat_arr, lon_arr)

    st.markdown(f"**Départ** : {lat_dep:.4f}, {lon_dep:.4f} → _{city_dep}_")
    st.markdown(f"**Arrivée** : {lat_arr:.4f}, {lon_arr:.4f} → _{city_arr}_")

    if st.button("Calculer via API"):
        distance_km, coords = get_route(lat_dep, lon_dep, lat_arr, lon_arr)
        if distance_km:
            duree = distance_km / 60
            st.session_state.distance_km = distance_km
            st.session_state.duree_h = duree
            st.session_state.coords = coords
            st.success(f"Distance: {distance_km:.2f} km | Durée estimée: {duree:.2f} h")

    distance_km = st.number_input("Distance (modifiable)", value=st.session_state.get('distance_km', 100.0))
    duree_h = st.number_input("Durée (modifiable)", value=st.session_state.get('duree_h', 2.0))
    delta_lat = lat_arr - lat_dep
    delta_lon = lon_arr - lon_dep

    if st.button("Prédire le Prix"):
        X = pd.DataFrame(0, index=[0], columns=feature_names)
        X['Distance_km_reelle'] = distance_km
        X['Durée_heures'] = duree_h
        X['Delta_Latitude'] = delta_lat
        X['Delta_Longitude'] = delta_lon

        if 'Ville_Depart_rabat' in X.columns and city_dep.lower() == 'rabat':
            X['Ville_Depart_rabat'] = 1
        if 'Ville_Arrivee_youssoufia' in X.columns and city_arr.lower() == 'youssoufia':
            X['Ville_Arrivee_youssoufia'] = 1

        prix = model.predict(X)[0]
        st.success(f"💰 Prix prédit : {prix:.2f} MAD")

        if 'coords' in st.session_state:
            st.subheader("🗺️ Visualisation du Trajet")
            m2 = folium.Map(location=[(lat_dep+lat_arr)/2, (lon_dep+lon_arr)/2], zoom_start=7)
            folium.Marker([lat_dep, lon_dep], popup="Départ", icon=folium.Icon(color='green')).add_to(m2)
            folium.Marker([lat_arr, lon_arr], popup="Arrivée", icon=folium.Icon(color='red')).add_to(m2)
            folium.PolyLine([(lat, lon) for lon, lat in st.session_state.coords], color='blue').add_to(m2)
            st_folium(m2, width=700, height=500)
else:
    st.info("Cliquez deux fois sur la carte pour sélectionner le départ et l'arrivée.")
