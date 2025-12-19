import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from math import radians, cos, sin, asin, sqrt
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="Recherche Crèche", page_icon="👶", layout="centered")

# --- INITIALISATION DE LA MÉMOIRE (Session State) ---
# C'est ici que la magie opère : on crée une case mémoire pour stocker la carte
if 'donnees_recherche' not in st.session_state:
    st.session_state.donnees_recherche = None

# --- CSS ---
st.markdown("""
    <style>
    div.stButton > button {
        width: 100%;
        background-color: #27ae60;
        color: white;
        font-weight: bold;
        padding: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- FONCTIONS ---
def get_gps(adresse):
    try:
        url = "https://api-adresse.data.gouv.fr/search/"
        res = requests.get(url, params={'q': adresse, 'limit': 1}, timeout=10)
        if res.json()['features']:
            coords = res.json()['features'][0]['geometry']['coordinates']
            return coords[1], coords[0], res.json()['features'][0]['properties']['label']
    except:
        return None, None, None

def distance_haversine(lat1, lon1, lat2, lon2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    a = sin((lat2-lat1)/2)**2 + cos(lat1) * cos(lat2) * sin((lon2-lon1)/2)**2
    return 2 * asin(sqrt(a)) * 6371 * 1000

def get_creches_secure(lat, lon, rayon_metres):
    serveurs = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
    query = f"""
    [out:json][timeout:90];
    (
      node["amenity"~"kindergarten|childcare"](around:{rayon_metres},{lat},{lon});
      node["name"~"Crèche|Creche|Maison Bleue|Babilou|Chaperon|Montessori|Micro|Petite Enfance",i](around:{rayon_metres},{lat},{lon});
    );
    out center;
    """
    for url in serveurs:
        try:
            r = requests.get(url, params={'data': query}, timeout=100)
            if r.status_code == 200: return r.json().get('elements', [])
        except: continue
    return []

# --- INTERFACE ---
st.title("👶 Moteur Crèche Pro")
st.markdown("La carte reste affichée ci-dessous après la recherche.")

col1, col2 = st.columns([3, 1])
with col1:
    adresse = st.text_input("Adresse", placeholder="Ex: 10 rue de la Paix, Paris")
with col2:
    rayon = st.number_input("Rayon (km)", min_value=1, max_value=100, value=5)

# --- BOUTON DE RECHERCHE ---
if st.button("LANCER LA RECHERCHE"):
    if not adresse:
        st.error("❌ Veuillez entrer une adresse.")
    else:
        with st.spinner("🔎 Analyse et mémorisation..."):
            lat_user, lon_user, adresse_legible = get_gps(adresse)
            
            if lat_user:
                raw_data = get_creches_secure(lat_user, lon_user, rayon*1000)
                liste_finale = []
                ids_vus = set()
                
                for item in raw_data:
                    if item['id'] in ids_vus: continue
                    ids_vus.add(item['id'])
                    lat = item.get('lat') or item.get('center', {}).get('lat')
                    lon = item.get('lon') or item.get('center', {}).get('lon')
                    if lat:
                        tags = item.get('tags', {})
                        nom = tags.get('name', 'Structure Petite Enfance')
                        type_c = "Micro" if "micro" in nom.lower() else "Standard"
                        dist = int(distance_haversine(lat_user, lon_user, lat, lon))
                        tps_pied = int((dist/1000)/4.5*60)
                        
                        base_gm = f"https://www.google.com/maps/dir/?api=1&origin={lat_user},{lon_user}&destination={lat},{lon}"
                        q_google = f"{nom} {adresse_legible.split(' ')[-1]}"
                        
                        liste_finale.append({
                            "Nom": nom, "Type": type_c, "Distance": dist,
                            "Pied_min": tps_pied,
                            "Lien_Info": f"https://www.google.com/search?q={q_google}",
                            "lat": lat, "lon": lon
                        })
                
                liste_finale = sorted(liste_finale, key=lambda x: x['Distance'])
                
                # ON SAUVEGARDE TOUT DANS LA MÉMOIRE (SESSION STATE)
                st.session_state.donnees_recherche = {
                    "liste": liste_finale,
                    "lat": lat_user,
                    "lon": lon_user,
                    "adresse": adresse_legible,
                    "rayon": rayon
                }
            else:
                st.error("Adresse introuvable.")

# --- AFFICHAGE (En dehors du bouton, pour que ça reste !) ---
if st.session_state.donnees_recherche is not None:
    data = st.session_state.donnees_recherche
    
    st.success(f"✅ {len(data['liste'])} crèches trouvées autour de {data['adresse']}")
    
    # Construction de la carte à partir de la mémoire
    m = folium.Map(location=[data['lat'], data['lon']], zoom_start=13, tiles="CartoDB positron")
    folium.Marker([data['lat'], data['lon']], popup="Domicile", icon=folium.Icon(color="black", icon="home")).add_to(m)
    folium.Circle([data['lat'], data['lon']], radius=data['rayon']*1000,
