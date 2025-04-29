import streamlit as st
import pandas as pd
import joblib
import openrouteservice
import folium
from streamlit_folium import folium_static

# 1. Chargement du modèle et des noms de features
model = joblib.load(r"modele_prediction_prix.pkl")
feature_names = joblib.load(r"features.pkl")

# 2. Chargement des données des villes
@st.cache_data
def load_city_data():
    try:
        # Chargement du fichier Excel contenant les informations des villes
        df = pd.read_excel("bus_stops_data_complet.xlsx")
        return df
    except Exception as e:
        st.error(f"Erreur lors du chargement des données des villes: {e}")
        # En cas d'erreur, retourner un DataFrame vide
        return pd.DataFrame(columns=["CityName", "Latitude", "Longitude"])

# Chargement des données des villes
cities_data = load_city_data()

# 3. Connexion à l'API OpenRouteService
API_KEY = '5b3ce3597851110001cf62486c68088f9551487cb1b076e8cce3ba84'
client = openrouteservice.Client(key=API_KEY)

# 4. Fonction pour récupérer distance et coordonnées du trajet
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

# Initialisation des variables dans session_state si elles n'existent pas
if 'distance_km' not in st.session_state:
    st.session_state.distance_km = 100.0  # Valeur par défaut
if 'duree_h' not in st.session_state:
    st.session_state.duree_h = 1.5  # Valeur par défaut
if 'route_coords' not in st.session_state:
    st.session_state.route_coords = None

# Création de deux colonnes pour les villes et leurs coordonnées
col1, col2 = st.columns(2)

with col1:
    st.subheader("Ville de départ")
    # Recherche par nom de ville pour le départ
    city_search_dep = st.text_input("Rechercher une ville de départ", "")
    
    if city_search_dep:
        # Filtrer les villes qui contiennent la recherche (insensible à la casse)
        filtered_cities_dep = cities_data[cities_data["CityName"].str.lower().str.contains(city_search_dep.lower())]
        if not filtered_cities_dep.empty:
            selected_city_dep = st.selectbox(
                "Sélectionnez une ville de départ",
                options=filtered_cities_dep["CityName"].tolist(),
                key="city_dep"
            )
            
            # Récupérer les coordonnées de la ville sélectionnée
            city_data_dep = filtered_cities_dep[filtered_cities_dep["CityName"] == selected_city_dep].iloc[0]
            lat_dep = city_data_dep["Latitude"]
            lon_dep = city_data_dep["Longitude"]
        else:
            st.warning("Aucune ville trouvée avec ce nom pour le départ.")
            lat_dep = st.number_input("Latitude Départ", value=33.916957, format="%.6f")
            lon_dep = st.number_input("Longitude Départ", value=-6.927790, format="%.6f")
    else:
        lat_dep = st.number_input("Latitude Départ", value=33.916957, format="%.6f")
        lon_dep = st.number_input("Longitude Départ", value=-6.927790, format="%.6f")

with col2:
    st.subheader("Ville d'arrivée")
    # Recherche par nom de ville pour l'arrivée
    city_search_arr = st.text_input("Rechercher une ville d'arrivée", "")
    
    if city_search_arr:
        # Filtrer les villes qui contiennent la recherche (insensible à la casse)
        filtered_cities_arr = cities_data[cities_data["CityName"].str.lower().str.contains(city_search_arr.lower())]
        if not filtered_cities_arr.empty:
            selected_city_arr = st.selectbox(
                "Sélectionnez une ville d'arrivée",
                options=filtered_cities_arr["CityName"].tolist(),
                key="city_arr"
            )
            
            # Récupérer les coordonnées de la ville sélectionnée
            city_data_arr = filtered_cities_arr[filtered_cities_arr["CityName"] == selected_city_arr].iloc[0]
            lat_arr = city_data_arr["Latitude"]
            lon_arr = city_data_arr["Longitude"]
        else:
            st.warning("Aucune ville trouvée avec ce nom pour l'arrivée.")
            lat_arr = st.number_input("Latitude Arrivée", value=32.250000, format="%.6f")
            lon_arr = st.number_input("Longitude Arrivée", value=-8.533300, format="%.6f")
    else:
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
    value=st.session_state.distance_km
)
duree_input = st.number_input(
    "Durée (h)", min_value=0.0,
    value=st.session_state.duree_h
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

    # Récupération des noms des villes si elles ont été sélectionnées
    dep_city_name = getattr(st, 'city_dep', None) 
    arr_city_name = getattr(st, 'city_arr', None)
    
    # Encodage des villes si elles sont dans les features
    if dep_city_name:
        dep_col = f'Ville_Depart_{dep_city_name.lower()}'
        if dep_col in X.columns:
            X[dep_col] = 1
            
    if arr_city_name:
        arr_col = f'Ville_Arrivee_{arr_city_name.lower()}'
        if arr_col in X.columns:
            X[arr_col] = 1
    
    # Fallback pour les villes d'exemple
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
        st.info("Appuyez d'abord sur « Calculer via API » pour récupérer le trajet.")
