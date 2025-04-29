import streamlit as st
import pandas as pd
import joblib
import openrouteservice
import folium
from streamlit_folium import folium_static

# -------------------- Chargement des données --------------------
@st.cache_data
def load_city_data():
    return pd.read_excel("bus_stops_data_complet.xlsx")  # Assure-toi que le fichier est dans le dossier du script

city_df = load_city_data()

# -------------------- Chargement du modèle --------------------
model = joblib.load("modele_prediction_prix.pkl")
feature_names = joblib.load("features.pkl")

# -------------------- Connexion API OpenRouteService --------------------
client = openrouteservice.Client(key='5b3ce3597851110001cf62486c68088f9551487cb1b076e8cce3ba84')

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

# -------------------- Interface utilisateur --------------------
st.title("🚌 CTM : Prédiction du Prix & Trajet Réel")

# Saisie ville de départ
st.header("1. Ville de départ")
city_list = city_df['CityName'].dropna().unique().tolist()
ville_dep = st.selectbox("Choisissez ou tapez le nom de la ville de départ :", options=sorted(city_list))

ville_dep_coords = city_df[city_df['CityName'] == ville_dep][['Latitude', 'Longitude']].dropna()
if not ville_dep_coords.empty:
    lat_dep = float(str(ville_dep_coords.iloc[0]['Latitude']).replace(",", "."))
    lon_dep = float(str(ville_dep_coords.iloc[0]['Longitude']).replace(",", "."))
    st.success(f"📍 Coordonnées de départ : {lat_dep}, {lon_dep}")
else:
    st.warning("Ville non trouvée. Entrez manuellement :")
    lat_dep = st.number_input("Latitude Départ", format="%.6f")
    lon_dep = st.number_input("Longitude Départ", format="%.6f")

# Saisie ville d’arrivée
st.header("2. Ville d’arrivée")
ville_arr = st.selectbox("Choisissez ou tapez le nom de la ville d’arrivée :", options=sorted(city_list))

ville_arr_coords = city_df[city_df['CityName'] == ville_arr][['Latitude', 'Longitude']].dropna()
if not ville_arr_coords.empty:
    lat_arr = float(str(ville_arr_coords.iloc[0]['Latitude']).replace(",", "."))
    lon_arr = float(str(ville_arr_coords.iloc[0]['Longitude']).replace(",", "."))
    st.success(f"📍 Coordonnées d’arrivée : {lat_arr}, {lon_arr}")
else:
    st.warning("Ville non trouvée. Entrez manuellement :")
    lat_arr = st.number_input("Latitude Arrivée", format="%.6f")
    lon_arr = st.number_input("Longitude Arrivée", format="%.6f")

# Calcul distance
st.header("3. Calcul distance et durée")
if st.button("Calculer via API"):
    dist, coords = get_route(lat_dep, lon_dep, lat_arr, lon_arr)
    if dist:
        duree = dist / 60
        st.session_state.distance_km = dist
        st.session_state.duree_h = duree
        st.session_state.route_coords = coords
        st.success(f"📏 Distance : {dist:.2f} km → Durée ≃ {duree:.2f} h")
    else:
        st.warning("Impossible de récupérer les données de l’API.")

dist_input = st.number_input("Distance (km)", value=st.session_state.get('distance_km', 100.0))
duree_input = st.number_input("Durée (h)", value=st.session_state.get('duree_h', 1.5))

# -------------------- Prédiction --------------------
st.header("4. Prédiction du Prix")
if st.button("Prédire le Prix"):
    delta_lat = lat_arr - lat_dep
    delta_lon = lon_arr - lon_dep

    X = pd.DataFrame(0, index=[0], columns=feature_names)
    X['Distance_km_reelle'] = dist_input
    X['Durée_heures'] = duree_input
    X['Delta_Latitude'] = delta_lat
    X['Delta_Longitude'] = delta_lon

    if f"Ville_Depart_{ville_dep.lower()}" in X.columns:
        X[f"Ville_Depart_{ville_dep.lower()}"] = 1
    if f"Ville_Arrivee_{ville_arr.lower()}" in X.columns:
        X[f"Ville_Arrivee_{ville_arr.lower()}"] = 1

    prix = model.predict(X)[0]
    st.success(f"💰 Prix prédit : {prix:.2f} MAD")

    # Carte
    coords_trajet = st.session_state.get('route_coords', None)
    if coords_trajet:
        center = [(lat_dep+lat_arr)/2, (lon_dep+lon_arr)/2]
        m = folium.Map(location=center, zoom_start=7)
        folium.Marker([lat_dep, lon_dep], tooltip="Départ", icon=folium.Icon(color='green')).add_to(m)
        folium.Marker([lat_arr, lon_arr], tooltip="Arrivée", icon=folium.Icon(color='red')).add_to(m)
        folium.PolyLine(locations=[(lat, lon) for lon, lat in coords_trajet], color="blue").add_to(m)
        st.header("🗺️ Trajet sur carte")
        folium_static(m, width=700, height=500)
    else:
        st.info("Veuillez d’abord calculer le trajet pour voir la carte.")
