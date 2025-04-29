import streamlit as st
import pandas as pd
import os

fichier_villes = "bus_stops_data_complet.xlsx"

# Chargement des villes existantes
if os.path.exists(fichier_villes):
    villes_df = pd.read_excel(fichier_villes)
    villes_df.columns = [col.strip().lower() for col in villes_df.columns]
    if villes_df['latitude'].dtype == 'object':
        villes_df['latitude'] = villes_df['latitude'].str.replace(',', '.').astype(float)
    if villes_df['longitude'].dtype == 'object':
        villes_df['longitude'] = villes_df['longitude'].str.replace(',', '.').astype(float)
else:
    villes_df = pd.DataFrame(columns=['cityname', 'latitude', 'longitude'])

# Création du dictionnaire et de la liste de suggestions
villes_dict = {
    row['cityname'].strip().lower(): (row['latitude'], row['longitude'])
    for _, row in villes_df.iterrows()
}
liste_villes = sorted(villes_dict.keys())

st.title("Recherche d’itinéraires")

# Ville de départ
ville_dep = st.selectbox("Ville de départ", options=[""] + liste_villes)
ville_dep_nouvelle = ""
if ville_dep == "":
    ville_dep_nouvelle = st.text_input("Nom de la ville de départ (nouvelle)").strip()
    if ville_dep_nouvelle:
        lat_dep = st.number_input("Latitude de la ville de départ", format="%.6f")
        lon_dep = st.number_input("Longitude de la ville de départ", format="%.6f")
        if st.button("Ajouter ville de départ"):
            nouvelle_ville = {
                'cityname': ville_dep_nouvelle,
                'latitude': lat_dep,
                'longitude': lon_dep
            }
            villes_df = villes_df.append(nouvelle_ville, ignore_index=True)
            villes_df.to_excel(fichier_villes, index=False)
            st.success(f"{ville_dep_nouvelle} ajoutée avec succès.")
            st.experimental_rerun()

# Ville d’arrivée
ville_arr = st.selectbox("Ville d’arrivée", options=[""] + liste_villes)
ville_arr_nouvelle = ""
if ville_arr == "":
    ville_arr_nouvelle = st.text_input("Nom de la ville d’arrivée (nouvelle)").strip()
    if ville_arr_nouvelle:
        lat_arr = st.number_input("Latitude de la ville d’arrivée", format="%.6f", key="lat_arr")
        lon_arr = st.number_input("Longitude de la ville d’arrivée", format="%.6f", key="lon_arr")
        if st.button("Ajouter ville d’arrivée"):
            nouvelle_ville = {
                'cityname': ville_arr_nouvelle,
                'latitude': lat_arr,
                'longitude': lon_arr
            }
            villes_df = villes_df.append(nouvelle_ville, ignore_index=True)
            villes_df.to_excel(fichier_villes, index=False)
            st.success(f"{ville_arr_nouvelle} ajoutée avec succès.")
            st.experimental_rerun()
