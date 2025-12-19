import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from math import radians, cos, sin, asin, sqrt
import pandas as pd

# --- CONFIGURATION ---
st.set_page_config(page_title="Recherche Crèche", page_icon="👶")

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
st.title("👶 Moteur Crèche")
st.markdown("Indiquez votre adresse pour générer une carte interactive avec temps de trajet.")

col1, col2 = st.columns([3, 1])
with col1:
    adresse = st.text_input("Adresse", placeholder="Ex: 10 rue de la Paix, Paris")
with col2:
    rayon = st.number_input("Rayon (km)", min_value=1, max_value=100, value=5)

if st.button("LANCER LA RECHERCHE", type="primary"):
    if not adresse:
        st.error("L'adresse est vide.")
    else:
        with st.spinner("Analyse en cours..."):
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
                st.success(f"{len(liste_finale)} crèches trouvées !")

                # CARTE
                m = folium.Map(location=[lat_user, lon_user], zoom_start=12 if rayon > 5 else 14, tiles="CartoDB positron")
                folium.Marker([lat_user, lon_user], popup="Maison", icon=folium.Icon(color="black", icon="home")).add_to(m)
                folium.Circle([lat_user, lon_user], radius=rayon*1000, color="#3498db", fill=True, fill_opacity=0.08).add_to(m)

                for idx, c in enumerate(liste_finale):
                    if idx < 300:
                        color = "#9b59b6" if c['Type'] == "Micro" else "#ff5e57"
                        popup_html = f"""
                        <div style="font-family:sans-serif; width:200px;">
                            <h4 style="margin:0; color:{color}">{c['Nom']}</h4>
                            <div style="font-size:12px;">📍 <b>{c['Distance']}m</b> | 🏃 {c['Pied_min']} min</div>
                            <a href="{c['Lien_Info']}" target="_blank">Infos</a>
                        </div>
                        """
                        icon_html = f"""<div style="background:{color};color:white;border-radius:50%;width:24px;height:24px;text-align:center;font-weight:bold;border:2px solid white;box-shadow:0 2px 4px rgba(0,0,0,0.3);">{idx+1}</div>"""
                        folium.Marker([c['lat'], c['lon']], popup=folium.Popup(popup_html, max_width=250), icon=folium.DivIcon(html=icon_html)).add_to(m)

                # AFFICHAGE
                st_folium(m, width=700, height=500)
                
                # BOUTON TELECHARGEMENT CARTE
                nom_fichier = "Ma_Carte.html"
                m.save(nom_fichier)
                with open(nom_fichier, "rb") as file:
                    st.download_button(label="⬇️ TÉLÉCHARGER LA CARTE", data=file, file_name=nom_fichier, mime="text/html")

            else:
                st.error("Adresse introuvable.")
