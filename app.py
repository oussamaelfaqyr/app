import streamlit as st
import pandas as pd
import joblib
import numpy as np
import openrouteservice
from streamlit_folium import st_folium
import folium

# --- Configuration de la Page ---
st.set_page_config(
    page_title="Prédiction Prix Trajet Avancée",
    page_icon=r"logo_ctm.png",
    layout="wide"
)

# --- Constantes ---
CHEMIN_MODELE = r"regressor_lr_model.joblib"
CHEMIN_VILLES_EXCEL = r"bus_stops_data.xlsx"
ORS_API_KEY = '5b3ce3597851110001cf62486c68088f9551487cb1b076e8cce3ba84'

# --- Initialisation session_state ---
if "distance" not in st.session_state:
    st.session_state["distance"] = 100.0
if "duree" not in st.session_state:
    st.session_state["duree"] = 2.5
if "geom" not in st.session_state:
    st.session_state["geom"] = None

# --- Fonctions Utilitaires ---
@st.cache_resource
def charger_modele(chemin_modele):
    return joblib.load(chemin_modele)

@st.cache_data
def charger_donnees_villes(chemin_excel):
    df_villes = pd.read_excel(chemin_excel)
    cols = ['CityName', 'Latitude', 'Longitude']
    if not all(col in df_villes.columns for col in cols):
        st.error(f"Colonnes requises manquantes. Trouvé : {df_villes.columns.tolist()}")
        return pd.DataFrame(columns=cols)
    df_villes['CityName'] = df_villes['CityName'].astype(str).str.lower().str.strip()
    for col in ['Latitude', 'Longitude']:
        if df_villes[col].dtype == 'object':
            df_villes[col] = df_villes[col].str.replace(',', '.', regex=False)
        df_villes[col] = pd.to_numeric(df_villes[col], errors='coerce')
    return df_villes.dropna().drop_duplicates('CityName')

# --- Chargement ---
modele_prix = charger_modele(CHEMIN_MODELE)
df_villes_data = charger_donnees_villes(CHEMIN_VILLES_EXCEL)
ors_client = openrouteservice.Client(key=ORS_API_KEY)

# --- Interface Utilisateur ---
st.image(r"COVER CTM.png")
st.markdown("""
Cette application prédit le prix d'un trajet. 
Choisissez les villes (ou saisissez leurs coordonnées si non listées), puis calculez la distance/durée via API ou saisissez-les manuellement.
""")

if modele_prix is None or df_villes_data.empty:
    st.warning("Erreur de chargement du modèle ou des données.")
else:
    st.sidebar.header("Sélection des Villes")
    liste_villes = [""] + sorted(df_villes_data['CityName'].unique())
    ville_dep = st.sidebar.text_input("Ville de Départ", "")
    ville_arr = st.sidebar.text_input("Ville d'Arrivée", "")
    options_dep = [v for v in liste_villes if ville_dep.lower() in v.lower()] or [ville_dep]
    options_arr = [v for v in liste_villes if ville_arr.lower() in v.lower()] or [ville_arr]
    selected_dep = st.sidebar.selectbox("Confirmer Ville de Départ", options_dep)
    selected_arr = st.sidebar.selectbox("Confirmer Ville d'Arrivée", options_arr)

    def get_coords(ville):
        row = df_villes_data[df_villes_data['CityName'] == ville.lower()]
        if not row.empty:
            return row.iloc[0]['Latitude'], row.iloc[0]['Longitude']
        return None, None

    lat_dep, lon_dep = get_coords(selected_dep)
    lat_arr, lon_arr = get_coords(selected_arr)

    if lat_dep is None:
        lat_dep = st.sidebar.number_input("Latitude Départ", key="lat_dep")
        lon_dep = st.sidebar.number_input("Longitude Départ", key="lon_dep")
    if lat_arr is None:
        lat_arr = st.sidebar.number_input("Latitude Arrivée", key="lat_arr")
        lon_arr = st.sidebar.number_input("Longitude Arrivée", key="lon_arr")

    methode = st.sidebar.radio("Mode de calcul", ["API", "Manuel"])
    distance_km, duree_h = st.session_state["distance"], st.session_state["duree"]

    if methode == "API" and st.sidebar.button("Calculer via API"):
        try:
            coords = [(lon_dep, lat_dep), (lon_arr, lat_arr)]
            route = ors_client.directions(coords, profile='driving-car', format='geojson')
            distance_km = route['features'][0]['properties']['summary']['distance'] / 1000
            duree_h = route['features'][0]['properties']['summary']['duration'] / 3600
            route_geom = route['features'][0]['geometry']
            st.session_state.update({
                "distance": distance_km,
                "duree": duree_h,
                "geom": route_geom
            })
            st.sidebar.success(f"Distance : {distance_km:.2f} km | Durée : {duree_h:.2f} h")
        except Exception as e:
            st.sidebar.error(f"Erreur API : {e}")
    else:
        distance_km = st.sidebar.number_input("Distance (km)", value=distance_km)
        duree_h = st.sidebar.number_input("Durée (h)", value=duree_h)

    changements = st.sidebar.selectbox("Nombre de changements", [0, 1, 2])

    # --- Carte ---
    st.markdown("---")
    st.subheader("Carte du Trajet")
    route_geom = st.session_state.get("geom", None)

    if route_geom:
        m = folium.Map(location=[lat_dep, lon_dep], zoom_start=10)
        folium.Marker([lat_dep, lon_dep], tooltip="Départ").add_to(m)
        folium.Marker([lat_arr, lon_arr], tooltip="Arrivée").add_to(m)
        folium.GeoJson(route_geom, style_function=lambda x: {'color': 'blue'}).add_to(m)
        st_folium(m, width=800, height=300)
    else:
        st.info("Carte affichée après calcul API.")

    # --- Prédiction ---
    st.markdown("---")
    if st.button("Prédire le Prix", type="primary"):
        if not selected_dep or not selected_arr:
            st.error("Veuillez sélectionner les deux villes.")
        else:
            entree = pd.DataFrame({
                "Durée_heures": [duree_h],
                "Distance_km": [distance_km],
                "Changement": [changements]
            })
            st.subheader("Entrées du Modèle")
            st.dataframe(entree)
            try:
                prediction = modele_prix.predict(entree)[0]
                st.success(f"Prix estimé : {prediction:.2f} MAD")
            except Exception as e:
                st.error(f"Erreur de prédiction : {e}")
