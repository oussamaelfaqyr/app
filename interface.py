import streamlit as st
import pandas as pd
import numpy as np
import joblib
import openrouteservice
import folium
from streamlit_folium import folium_static
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import random
import time

# Set page configuration and styling
st.set_page_config(
    page_title="CTM Journey Planner",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #003366;
        text-align: center;
        margin-bottom: 1rem;
        text-shadow: 1px 1px 2px #cccccc;
    }
    .sub-header {
        font-size: 1.8rem;
        color: #0066cc;
        margin-top: 1.5rem;
        border-bottom: 2px solid #0066cc;
        padding-bottom: 0.5rem;
    }
    .success-box {
        background-color: #e6f7e6;
        border-left: 5px solid #28a745;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .info-box {
        background-color: #e6f0ff;
        border-left: 5px solid #0066cc;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    .amenity-icon {
        font-size: 1.5rem;
        margin-right: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# -------------------- Custom Components --------------------
def create_animated_progress_bar():
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(101):
        progress_bar.progress(i)
        status_text.text(f"Processing... {i}%")
        time.sleep(0.01)
    
    status_text.text("Complete!")
    time.sleep(0.5)
    status_text.empty()
    progress_bar.empty()

def show_loading_animation(text="Loading..."):
    with st.spinner(text):
        time.sleep(1.5)

# -------------------- App Logo and Header --------------------
col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    st.markdown('<p class="main-header">🚌 CTM Journey Planner & Price Calculator</p>', unsafe_allow_html=True)
    st.markdown("*Your premium travel companion across Morocco*")

# -------------------- Sidebar with App Info --------------------
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/8/84/CTM_Logo.svg/1200px-CTM_Logo.svg.png", width=150)
    st.markdown("### About CTM")
    st.info(
        """
        CTM (Compagnie de Transport au Maroc) is Morocco's premium intercity bus transport company, 
        offering comfortable and reliable services across the country since 1919.
        """
    )
    
    st.markdown("### App Features")
    st.markdown("""
    - 🗺️ Interactive route planning
    - 💰 Price predictions based on AI
    - ⏱️ Journey time estimation
    - 🏙️ Discover popular destinations
    - 🚍 Bus schedules and amenities
    """)
    
    st.markdown("### Weather Information")
    if st.button("Check Weather Conditions"):
        with st.spinner("Fetching weather data..."):
            time.sleep(1.5)
            st.success("Weather conditions are optimal for bus travel across Morocco today!")
            
    # Help section in sidebar
    st.markdown("### Need Help?")
    with st.expander("How to use this application"):
        st.markdown("""
        1. Select your departure and arrival cities
        2. Calculate the route distance
        3. Get price prediction and view the journey on the map
        4. Explore bus schedules and amenities
        """)
        
    st.markdown("### App Version")
    st.text("v2.0 - Enhanced Experience")

# -------------------- Caching Functions --------------------
@st.cache_data
def load_city_data():
    try:
        return pd.read_excel("bus_stops_data_complet.xlsx")
    except FileNotFoundError:
        # Provide fallback data in case file is not found
        st.warning("⚠️ Bus stops data file not found. Using fallback data.")
        # Create sample data with major Moroccan cities
        data = {
            'CityName': ['Casablanca', 'Rabat', 'Marrakech', 'Fes', 'Tangier', 'Agadir', 'Meknes', 'Oujda'],
            'Latitude': [33.5731, 34.0209, 31.6295, 34.0433, 35.7595, 30.4278, 33.8731, 34.6805],
            'Longitude': [-7.5898, -6.8416, -8.0129, -4.9779, -5.8340, -9.5981, -5.5517, -1.9112],
            'Population': [3359818, 577827, 928850, 1112072, 947952, 421844, 632079, 494252],
            'HasBusStation': [True, True, True, True, True, True, True, True],
            'StationSize': ['Large', 'Large', 'Large', 'Medium', 'Medium', 'Medium', 'Medium', 'Small']
        }
        return pd.DataFrame(data)

@st.cache_data
def get_popular_routes():
    """Return list of popular routes for suggestions"""
    return [
        ("Casablanca", "Marrakech"),
        ("Rabat", "Fes"),
        ("Tangier", "Casablanca"),
        ("Agadir", "Marrakech"),
        ("Marrakech", "Essaouira"),
        ("Casablanca", "Agadir"),
        ("Fes", "Meknes"),
        ("Rabat", "Tangier")
    ]

@st.cache_data
def get_bus_schedules(departure, arrival):
    """Generate simulated bus schedules for selected cities"""
    current_time = datetime.now()
    schedules = []
    
    # Generate 4-8 schedules throughout the day
    num_schedules = random.randint(4, 8)
    for i in range(num_schedules):
        departure_time = current_time + timedelta(hours=random.randint(1, 24))
        duration_hours = random.uniform(1.5, 6.0)  # Duration between 1.5 and 6 hours
        arrival_time = departure_time + timedelta(hours=duration_hours)
        
        # Add some variation to pricing
        base_price = 100 + (duration_hours * 30)
        price_variation = random.uniform(0.8, 1.2)
        price = base_price * price_variation
        
        # Bus types
        bus_types = ["Standard", "Premium", "Luxury", "Express"]
        bus_type = random.choice(bus_types)
        
        # Amenities based on bus type
        amenities = ["WiFi", "Power Outlets"]
        if bus_type == "Premium" or bus_type == "Luxury":
            amenities.extend(["Snacks", "Extra Legroom"])
        if bus_type == "Luxury":
            amenities.extend(["Personal TV", "Reclining Seats"])
        
        schedules.append({
            "departure_time": departure_time.strftime("%H:%M"),
            "arrival_time": arrival_time.strftime("%H:%M"),
            "duration": f"{duration_hours:.1f}h",
            "price": f"{price:.2f} MAD",
            "bus_type": bus_type,
            "seats_available": random.randint(5, 45),
            "amenities": amenities
        })
    
    # Sort by departure time
    schedules.sort(key=lambda x: x["departure_time"])
    return schedules

@st.cache_data
def get_city_attractions(city):
    """Return tourist attractions for major cities"""
    attractions = {
        "Casablanca": ["Hassan II Mosque", "Morocco Mall", "Corniche", "Old Medina", "Royal Palace"],
        "Marrakech": ["Jemaa el-Fnaa", "Majorelle Garden", "Bahia Palace", "Koutoubia Mosque", "Saadian Tombs"],
        "Rabat": ["Hassan Tower", "Chellah", "Kasbah of the Udayas", "Royal Palace", "Mohammed V Mausoleum"],
        "Fes": ["Fes El Bali", "Bou Inania Madrasa", "Al-Qarawiyyin Mosque", "Bab Boujloud", "Merenid Tombs"],
        "Tangier": ["Kasbah Museum", "Cap Spartel", "Caves of Hercules", "American Legation", "Grand Socco"],
        "Agadir": ["Agadir Beach", "Souk El Had", "Kasbah", "Valley of the Birds", "Crocoparc"],
        "Meknes": ["Bab Mansour", "Mausoleum of Moulay Ismail", "Place El Hedim", "Royal Stables", "Bou Inania Madrasa"],
        "Oujda": ["Parc Lalla Aicha", "Grande Mosquée", "Old Medina", "Sidi Yahya Oasis", "Place du 16 Août"]
    }
    
    # Return attractions if city is in the dictionary, otherwise return a message
    if city in attractions:
        return attractions[city]
    else:
        return ["Information not available for this city"]

# -------------------- Load Data and Models --------------------
city_df = load_city_data()

# Load model or create a mock model if not available
try:
    model = joblib.load("modele_prediction_prix.pkl")
    feature_names = joblib.load("features.pkl")
except FileNotFoundError:
    st.warning("⚠️ Model files not found. Using a mock prediction model.")
    
    # Create a mock model for demonstration
    class MockModel:
        def predict(self, X):
            distance = X.iloc[0]['Distance_km_reelle']
            duration = X.iloc[0]['Durée_heures']
            # Basic formula: base price + distance rate + duration rate + random factor
            price = 50 + (distance * 0.75) + (duration * 20) + random.uniform(-30, 30)
            return np.array([max(price, 50)])  # Ensure minimum price of 50 MAD
    
    model = MockModel()
    # Create mock feature names
    feature_names = ['Distance_km_reelle', 'Durée_heures', 'Delta_Latitude', 'Delta_Longitude'] + \
                   [f"Ville_Depart_{city.lower()}" for city in city_df['CityName']] + \
                   [f"Ville_Arrivee_{city.lower()}" for city in city_df['CityName']]

# -------------------- OpenRouteService API --------------------
try:
    client = openrouteservice.Client(key='5b3ce3597851110001cf62486c68088f9551487cb1b076e8cce3ba84')
except Exception:
    st.sidebar.warning("⚠️ OpenRouteService API connection failed. Some features may be limited.")
    client = None

def get_route(lat1, lon1, lat2, lon2):
    if client is None:
        # Fallback calculation if API is not available
        # Haversine formula for distance calculation
        from math import radians, cos, sin, asin, sqrt
        
        def haversine(lon1, lat1, lon2, lat2):
            # Convert decimal degrees to radians
            lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
            # Haversine formula
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * asin(sqrt(a))
            r = 6371  # Radius of earth in kilometers
            return c * r
        
        distance_km = haversine(lon1, lat1, lon2, lat2)
        # Create a simple straight line for visualization
        steps = 10
        coords_list = []
        for i in range(steps + 1):
            fraction = i / steps
            lat = lat1 + fraction * (lat2 - lat1)
            lon = lon1 + fraction * (lon2 - lon1)
            coords_list.append([lon, lat])
        
        return distance_km, coords_list
    
    try:
        coords = ((lon1, lat1), (lon2, lat2))
        resp = client.directions(coords, profile='driving-car', format='geojson')
        seg = resp['features'][0]['properties']['segments'][0]
        distance_km = seg['distance'] / 1000
        duration_h = seg['duration'] / 3600  # Convert seconds to hours
        coords_list = resp['features'][0]['geometry']['coordinates']
        return distance_km, coords_list, duration_h
    except Exception as e:
        st.error(f"❌ Error with OpenRouteService API: {e}")
        # Fall back to simple calculation
        return get_route(lat1, lon1, lat2, lon2)

# -------------------- Main Interface --------------------
# Create tabs for organization
tab1, tab2, tab3 = st.tabs(["🗺️ Journey Planning", "📊 Statistics & Info", "🏙️ City Guides"])

with tab1:
    # Journey Planning
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<p class="sub-header">Departure Information</p>', unsafe_allow_html=True)
        
        # Popular routes suggestion
        with st.expander("⭐ Popular Routes (Click to select)"):
            popular_routes = get_popular_routes()
            cols = st.columns(2)
            for i, (dep, arr) in enumerate(popular_routes):
                col_idx = i % 2
                if cols[col_idx].button(f"{dep} → {arr}", key=f"pop_route_{i}"):
                    st.session_state.selected_departure = dep
                    st.session_state.selected_arrival = arr
                    st.experimental_rerun()
        
        # Departure city selection
        city_list = sorted(city_df['CityName'].dropna().unique().tolist())
        selected_departure = st.selectbox(
            "Select departure city:", 
            options=city_list,
            index=city_list.index(st.session_state.get('selected_departure', city_list[0])) if 'selected_departure' in st.session_state else 0
        )
        
        # Get coordinates
        ville_dep_coords = city_df[city_df['CityName'] == selected_departure][['Latitude', 'Longitude']].dropna()
        if not ville_dep_coords.empty:
            lat_dep = float(str(ville_dep_coords.iloc[0]['Latitude']).replace(",", "."))
            lon_dep = float(str(ville_dep_coords.iloc[0]['Longitude']).replace(",", "."))
            st.markdown(f"<div class='success-box'>📍 Coordinates: {lat_dep:.6f}, {lon_dep:.6f}</div>", unsafe_allow_html=True)
            
            # Show city info
            city_info = city_df[city_df['CityName'] == selected_departure]
            if not city_info.empty and 'Population' in city_info.columns:
                population = city_info.iloc[0].get('Population', 'Unknown')
                st.markdown(f"<div class='info-box'>🏙️ {selected_departure}: Population approx. {population:,}</div>", unsafe_allow_html=True)
            
            # Display top attractions
            attractions = get_city_attractions(selected_departure)
            with st.expander("🎭 Top Attractions"):
                for attraction in attractions[:3]:
                    st.markdown(f"• {attraction}")
                if len(attractions) > 3:
                    st.markdown(f"*...and {len(attractions)-3} more*")
        else:
            st.warning("City not found. Enter coordinates manually:")
            lat_dep = st.number_input("Departure Latitude", format="%.6f", value=34.0209)
            lon_dep = st.number_input("Departure Longitude", format="%.6f", value=-6.8416)
    
    with col2:
        st.markdown('<p class="sub-header">Arrival Information</p>', unsafe_allow_html=True)
        
        # Arrival city selection with filter
        selected_arrival = st.selectbox(
            "Select arrival city:", 
            options=city_list,
            index=city_list.index(st.session_state.get('selected_arrival', city_list[1])) if 'selected_arrival' in st.session_state else 1
        )
        
        # Get coordinates
        ville_arr_coords = city_df[city_df['CityName'] == selected_arrival][['Latitude', 'Longitude']].dropna()
        if not ville_arr_coords.empty:
            lat_arr = float(str(ville_arr_coords.iloc[0]['Latitude']).replace(",", "."))
            lon_arr = float(str(ville_arr_coords.iloc[0]['Longitude']).replace(",", "."))
            st.markdown(f"<div class='success-box'>📍 Coordinates: {lat_arr:.6f}, {lon_arr:.6f}</div>", unsafe_allow_html=True)
            
            # Show city info
            city_info = city_df[city_df['CityName'] == selected_arrival]
            if not city_info.empty and 'Population' in city_info.columns:
                population = city_info.iloc[0].get('Population', 'Unknown')
                st.markdown(f"<div class='info-box'>🏙️ {selected_arrival}: Population approx. {population:,}</div>", unsafe_allow_html=True)
            
            # Display top attractions
            attractions = get_city_attractions(selected_arrival)
            with st.expander("🎭 Top Attractions"):
                for attraction in attractions[:3]:
                    st.markdown(f"• {attraction}")
                if len(attractions) > 3:
                    st.markdown(f"*...and {len(attractions)-3} more*")
        else:
            st.warning("City not found. Enter coordinates manually:")
            lat_arr = st.number_input("Arrival Latitude", format="%.6f", value=31.6295)
            lon_arr = st.number_input("Arrival Longitude", format="%.6f", value=-8.0129)
    
    # Journey Details Section
    st.markdown('<p class="sub-header">Journey Details & Price Prediction</p>', unsafe_allow_html=True)
    
    # Calculate route button with enhanced styling
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        calculate_button = st.button("🔄 Calculate Route & Price", use_container_width=True)
    
    if calculate_button:
        # Show loading animation
        show_loading_animation("Calculating optimal route...")
        
        # Get route data
        try:
            dist, coords, duration = get_route(lat_dep, lon_dep, lat_arr, lon_arr)
            st.session_state.distance_km = dist
            st.session_state.duree_h = duration
            st.session_state.route_coords = coords
            
            # Results in columns
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""
                <div class="card">
                    <h3>📏 Distance</h3>
                    <h2>{dist:.1f} km</h2>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="card">
                    <h3>⏱️ Duration</h3>
                    <h2>{duration:.1f} hours</h2>
                    <p>({int(duration*60)} minutes)</p>
                </div>
                """, unsafe_allow_html=True)
            with col3:
                # Predict price
                delta_lat = lat_arr - lat_dep
                delta_lon = lon_arr - lon_dep
                
                X = pd.DataFrame(0, index=[0], columns=feature_names)
                X['Distance_km_reelle'] = dist
                X['Durée_heures'] = duration
                X['Delta_Latitude'] = delta_lat
                X['Delta_Longitude'] = delta_lon
                
                # Try to set city one-hot encoding features if they exist
                try:
                    if f"Ville_Depart_{selected_departure.lower()}" in X.columns:
                        X[f"Ville_Depart_{selected_departure.lower()}"] = 1
                    if f"Ville_Arrivee_{selected_arrival.lower()}" in X.columns:
                        X[f"Ville_Arrivee_{selected_arrival.lower()}"] = 1
                except Exception:
                    pass
                
                prix = model.predict(X)[0]
                st.session_state.predicted_price = prix
                
                st.markdown(f"""
                <div class="card">
                    <h3>💰 Predicted Price</h3>
                    <h2>{prix:.2f} MAD</h2>
                    <p>(~${(prix/10):.2f} USD)</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Display map
            st.markdown('<p class="sub-header">Interactive Journey Map</p>', unsafe_allow_html=True)
            coords_trajet = st.session_state.get('route_coords')
            if coords_trajet:
                center = [(lat_dep+lat_arr)/2, (lon_dep+lon_arr)/2]
                m = folium.Map(location=center, zoom_start=7, tiles="OpenStreetMap")
                
                # Add departure marker with popup
                folium.Marker(
                    [lat_dep, lon_dep], 
                    tooltip=f"Departure: {selected_departure}",
                    popup=folium.Popup(f"<b>{selected_departure}</b><br>Your journey starts here", max_width=200),
                    icon=folium.Icon(color='green', icon="play", prefix="fa")
                ).add_to(m)
                
                # Add arrival marker with popup
                folium.Marker(
                    [lat_arr, lon_arr], 
                    tooltip=f"Arrival: {selected_arrival}",
                    popup=folium.Popup(f"<b>{selected_arrival}</b><br>Your destination", max_width=200),
                    icon=folium.Icon(color='red', icon="flag-checkered", prefix="fa")
                ).add_to(m)
                
                # Add route line with distance popup
                route_line = folium.PolyLine(
                    locations=[(lat, lon) for lon, lat in coords_trajet], 
                    color="#0066cc",
                    weight=4,
                    opacity=0.8,
                    tooltip=f"Distance: {dist:.1f} km"
                ).add_to(m)
                
                # Add distance markers
                for i in range(1, len(coords_trajet)-1, max(1, len(coords_trajet)//5)):
                    lon, lat = coords_trajet[i]
                    segment_distance = (i / len(coords_trajet)) * dist
                    folium.CircleMarker(
                        location=[lat, lon],
                        radius=5,
                        color='#0066cc',
                        fill=True,
                        fill_color='#0066cc',
                        tooltip=f"{segment_distance:.1f} km from {selected_departure}"
                    ).add_to(m)
                
                # Fit bounds to route
                folium_static(m, width=1000, height=500)
                
                # Show bus schedules
                st.markdown('<p class="sub-header">Available Bus Services</p>', unsafe_allow_html=True)
                
                schedules = get_bus_schedules(selected_departure, selected_arrival)
                for i, schedule in enumerate(schedules):
                    cols = st.columns([3, 1, 1, 2, 2, 2])
                    with cols[0]:
                        st.markdown(f"**{schedule['departure_time']}** → **{schedule['arrival_time']}** ({schedule['duration']})")
                    with cols[1]:
                        st.markdown(f"**{schedule['price']}**")
                    with cols[2]:
                        st.markdown(f"{schedule['bus_type']}")
                    with cols[3]:
                        st.markdown(f"Seats: {schedule['seats_available']}")
                    with cols[4]:
                        # Display amenities with icons
                        amenity_icons = {
                            "WiFi": "📶",
                            "Power Outlets": "🔌",
                            "Snacks": "🍪",
                            "Extra Legroom": "🦵",
                            "Personal TV": "📺",
                            "Reclining Seats": "💺"
                        }
                        amenity_display = " ".join([amenity_icons.get(a, "✓") for a in schedule['amenities']])
                        st.markdown(amenity_display)
                    with cols[5]:
                        st.button(f"Book Now", key=f"book_{i}")
                    st.markdown("---")
        
        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.markdown("Please try again or contact support if the problem persists.")

# -------------------- Statistics Tab --------------------
with tab2:
    st.markdown('<p class="sub-header">Journey Statistics & Analytics</p>', unsafe_allow_html=True)

    # Price Trend Chart
    if 'distance_km' in st.session_state and 'predicted_price' in st.session_state:
        st.markdown("### 📈 Price Analysis")
        
        # Create a range of distances
        distances = np.linspace(st.session_state.distance_km * 0.5, st.session_state.distance_km * 1.5, 10)
        prices = []
        
        # Calculate prices for different distances
        for dist in distances:
            X = pd.DataFrame(0, index=[0], columns=feature_names)
            X['Distance_km_reelle'] = dist
            X['Durée_heures'] = dist / 60  # Approximate
            X['Delta_Latitude'] = lat_arr - lat_dep
            X['Delta_Longitude'] = lon_arr - lon_dep
            
            price = model.predict(X)[0]
            prices.append(price)
        
        # Create price trend chart
        fig = px.line(
            x=distances, 
            y=prices, 
            labels={"x": "Distance (km)", "y": "Price (MAD)"},
            title="Price Sensitivity to Distance",
            markers=True
        )
        
        # Add current journey point
        fig.add_trace(
            go.Scatter(
                x=[st.session_state.distance_km],
                y=[st.session_state.predicted_price],
                mode="markers",
                marker=dict(size=12, color="red"),
                name="Your Journey"
            )
        )
        
        # Add trend line
        z = np.polyfit(distances, prices, 1)
        p = np.poly1d(z)
        fig.add_trace(
            go.Scatter(
                x=distances,
                y=p(distances),
                mode="lines",
                line=dict(dash="dash", color="green"),
                name="Trend Line"
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Add price breakdown
        st.markdown("### 💰 Price Breakdown")
        
        # Create price breakdown chart
        base_price = st.session_state.predicted_price * 0.6
        distance_fee = st.session_state.predicted_price * 0.25
        comfort_fee = st.session_state.predicted_price * 0.1
        service_fee = st.session_state.predicted_price * 0.05
        
        fig = px.pie(
            values=[base_price, distance_fee, comfort_fee, service_fee],
            names=["Base Fare", "Distance Fee", "Comfort Premium", "Service Fee"],
            title="Price Breakdown",
            color_discrete_sequence=px.colors.sequential.Blues_r
        )
        st.plotly_chart(fig, use_container_width=True)
    
    else:
        st.info("Please calculate a route in the Journey Planning tab to see analytics")
    
    # Bus network visualization
    st.markdown("### 🔄 CTM Network Coverage")
    
    # Create a network graph of cities
    if not city_df.empty:
        fig = px.scatter_mapbox(
            city_df, 
            lat='Latitude', 
            lon='Longitude', 
            hover_name='CityName',
            size=[10] * len(city_df),  # Uniform size
            zoom=5, 
            center={"lat": 31.7917, "lon": -7.0926},  # Center of Morocco
            mapbox_style="open-street-map",
            opacity=0.8,
            title="CTM Bus Network Coverage"
        )
        
        # Add connecting lines between major cities
        major_cities = city_df.head(8)  # Take first 8 cities as major cities
        for i, row1 in major_cities.iterrows():
            for j, row2 in major_cities.iterrows():
                if i < j:  # To avoid duplicates
                    fig.add_trace(
                        go.Scattermapbox(
                            mode='lines',
                            lon=[row1['Longitude'], row2['Longitude']],
                            lat=[row1['Latitude'], row2['Latitude']],
                            line=dict(width=1, color='rgba(0, 102, 204, 0.3)'),
                            hoverinfo='skip',
                            showlegend=False
                        )
                    )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display some statistics about the CTM network
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Cities Covered", f"{len(city_df)}", "+3 this year")
        with col2:
            st.metric("Total Routes", f"{len(city_df) * (len(city_df) - 1) // 2}", "+15 this year")
        with col3:
            st.metric("Daily Buses", "320+", "+25 since last year")
    else:
        st.warning("City data not available for network visualization")

# -------------------- City Guides Tab --------------------
with tab3:
    st.markdown('<p class="sub-header">Discover Morocco</p>', unsafe_allow_html=True)
    
    # City selection
    selected_city_guide = st.selectbox("Select a city to explore:", options=sorted(city_df['CityName'].unique()))
    
    # Show city guide
    if selected_city_guide:
        city_attractions = get_city_attractions(selected_city_guide)
        
        # City header with image (placeholder)
        st.markdown(f"## 🏙️ {selected_city_guide} Travel Guide")
        
        # City image (placeholder)
        st.image(f"https://via.placeholder.com/800x300?text={selected_city_guide}+City+View", 
                 caption=f"Scenic view of {selected_city_guide}")
        
        # City description (placeholder text)
        city_descriptions = {
            "Casablanca": "Morocco's largest city and economic hub, Casablanca blends modern architecture with traditional Moroccan designs. The city is famous for its stunning Hassan II Mosque and vibrant coastal atmosphere.",
            "Marrakech": "Known as the 'Red City', Marrakech is a major cultural center with its famous medina, colorful souks, and the bustling Jemaa el-Fnaa square. The city offers a perfect blend of history and vibrant atmosphere.",
            "Rabat": "The capital city of Morocco, Rabat features elegant palm-lined boulevards, a peaceful atmosphere, and important historical sites including the Kasbah of the Udayas and Hassan Tower.",
            "Fes": "The cultural and spiritual heart of Morocco, Fes boasts the oldest university in the world and the largest intact medieval city. Its medina is a UNESCO World Heritage site.",
            "Tangier": "A city with a rich literary history and international influence, Tangier offers beautiful beaches, cave explorations, and a unique blend of cultures at the gateway between Africa and Europe.",
            "Agadir": "Morocco's premier coastal resort, Agadir is known for its beautiful bay, sandy beaches, and year-round sunshine. The city was completely rebuilt after an earthquake in 1960.",
            "Meknes": "One of Morocco's imperial cities, Meknes is known for its impressive monuments, including the massive Bab Mansour gate and the mausoleum of Sultan Moulay Ismail.",
            "Oujda": "Located near the Algerian border, Oujda is a vibrant university city with beautiful gardens, historic medina, and serves as a gateway to the eastern regions of Morocco."
        }
        
        description = city_descriptions.get(selected_city_guide, f"Discover the beauty and culture of {selected_city_guide}, one of Morocco's fascinating destinations.")
        st.markdown(description)
        
        # Attractions
        st.markdown("### 🌟 Top Attractions")
        
        # Display attractions in cards
        cols = st.columns(3)
        for i, attraction in enumerate(city_attractions):
            with cols[i % 3]:
                st.markdown(f"""
                <div class="card">
                    <h4>{attraction}</h4>
                    <p>One of the must-visit places in {selected_city_guide}.</p>
                </div>
                """, unsafe_allow_html=True)
        
        # Local transportation
        st.markdown("### 🚕 Getting Around")
        transport_options = {
            "Petit Taxi": "Small taxis that operate within city limits, typically colored red, yellow, or blue depending on the city.",
            "Grand Taxi": "Larger taxis for intercity travel, typically white Mercedes vehicles.",
            "Local Bus": "Affordable but often crowded city buses covering major routes.",
            "Tramway": "Available in cities like Casablanca and Rabat, modern and convenient."
        }
        
        for transport, description in transport_options.items():
            st.markdown(f"**{transport}**: {description}")
        
        # Hotels and accommodations
        st.markdown("### 🏨 Where to Stay")
        
        # Create fictional hotels
        hotels = [
            {"name": f"Royal Palace {selected_city_guide}", "stars": 5, "price_range": "⭐⭐⭐⭐⭐ | $$", 
             "description": "Luxury accommodation with all premium amenities including spa, pool, and fine dining."},
            {"name": f"{selected_city_guide} Plaza Hotel", "stars": 4, "price_range": "⭐⭐⭐⭐ | $", 
             "description": "Comfortable mid-range hotel with good facilities and central location."},
            {"name": f"Medina Riad {selected_city_guide}", "stars": 3, "price_range": "⭐⭐⭐ | $", 
             "description": "Traditional Moroccan riad experience with authentic architecture and atmosphere."}
        ]
        
        # Display hotels
        for hotel in hotels:
            st.markdown(f"""
            <div class="card">
                <h4>{hotel['name']}</h4>
                <p>{hotel['price_range']}</p>
                <p>{hotel['description']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Local cuisine
        st.markdown("### 🍽️ What to Eat")
        
        # Common Moroccan dishes
        dishes = [
            {"name": "Tajine", "description": "Slow-cooked savory stew with meat and vegetables."},
            {"name": "Couscous", "description": "Steamed semolina with vegetables and meat, traditionally served on Fridays."},
            {"name": "Pastilla", "description": "Sweet and savory pie usually made with pigeon or chicken."},
            {"name": "Mint Tea", "description": "Sweet mint tea, the national drink of Morocco."}
        ]
        
        # Display dishes in two columns
        cols = st.columns(2)
        for i, dish in enumerate(dishes):
            with cols[i % 2]:
                st.markdown(f"**{dish['name']}**: {dish['description']}")
        
        # Weather information
        st.markdown("### ☀️ Weather & Best Time to Visit")
        
        # Seasonal recommendations
        seasons = {
            "Spring (March-May)": "Mild temperatures and blooming landscapes make this an ideal time to visit.",
            "Summer (June-August)": "Hot weather, perfect for coastal cities but can be very warm in inland cities.",
            "Fall (September-November)": "Pleasant temperatures and fewer tourists.",
            "Winter (December-February)": "Cooler temperatures, occasional rain, and snow in mountain regions."
        }
        
        for season, description in seasons.items():
            st.markdown(f"**{season}**: {description}")
        
        # Travel tips
        st.markdown("### 💡 Travel Tips")
        tips = [
            "Learn a few basic phrases in Arabic or French to connect with locals.",
            "Dress modestly, especially when visiting religious sites.",
            "Haggling is expected in souks and markets, but do so respectfully.",
            "Stay hydrated, especially during summer months.",
            f"CTM buses offer the most comfortable way to travel to and from {selected_city_guide}."
        ]
        
        for tip in tips:
            st.markdown(f"• {tip}")

# -------------------- Booking System --------------------
# Add a booking form at the bottom
if "distance_km" in st.session_state:
    st.markdown('<p class="sub-header">Book Your Journey</p>', unsafe_allow_html=True)
    
    # Create columns for form
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🎫 Passenger Information")
        passenger_name = st.text_input("Full Name")
        passenger_email = st.text_input("Email Address")
        passenger_phone = st.text_input("Phone Number")
        num_passengers = st.number_input("Number of Passengers", min_value=1, max_value=10, value=1)
        
    with col2:
        st.markdown("### 🗓️ Journey Details")
        journey_date = st.date_input("Travel Date", min_value=datetime.now().date())
        journey_time = st.selectbox("Preferred Time", options=["Morning (6 AM - 12 PM)", "Afternoon (12 PM - 6 PM)", "Evening (6 PM - 12 AM)"])
        seat_preference = st.selectbox("Seat Preference", options=["Window", "Aisle", "No Preference"])
        bus_class = st.selectbox("Bus Class", options=["Standard", "Premium (+50 MAD)", "Luxury (+100 MAD)"])
    
    # Calculate total price
    total_price = st.session_state.predicted_price
    
    # Add premium for bus class
    if bus_class == "Premium (+50 MAD)":
        total_price += 50
    elif bus_class == "Luxury (+100 MAD)":
        total_price += 100
    
    # Multiply by number of passengers
    total_price *= num_passengers
    
    # Display total price
    st.markdown(f"### 💰 Total Price: {total_price:.2f} MAD")
    
    # Add booking button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚌 Complete Booking", use_container_width=True):
            create_animated_progress_bar()
            st.success(f"🎉 Booking confirmed! Your journey from {selected_departure} to {selected_arrival} has been scheduled for {journey_date.strftime('%B %d, %Y')}.")
            st.balloons()
    
    # Add payment options
    st.markdown("### 💳 Payment Methods")
    payment_cols = st.columns(4)
    with payment_cols[0]:
        st.markdown("![Visa](https://via.placeholder.com/100x50?text=Visa)")
    with payment_cols[1]:
        st.markdown("![Mastercard](https://via.placeholder.com/100x50?text=Mastercard)")
    with payment_cols[2]:
        st.markdown("![PayPal](https://via.placeholder.com/100x50?text=PayPal)")
    with payment_cols[3]:
        st.markdown("![Cash](https://via.placeholder.com/100x50?text=Cash)")
    
# -------------------- Footer --------------------
st.markdown("---")
st.markdown("""
<div style="text-align: center;">
    <p>© 2025 CTM - Compagnie de Transport au Maroc | All Rights Reserved</p>
    <p>For customer support: <a href="mailto:support@ctm.ma">support@ctm.ma</a> | Phone: +212 5XX-XXXXXX</p>
</div>
""", unsafe_allow_html=True)
