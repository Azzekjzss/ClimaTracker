#!/usr/bin/env python3

import streamlit as st
import math
import pandas as pd
import numpy as np
import requests
import json
import plotly.express as px
import plotly.graph_objects as go
import pathlib
import base64
from pathlib import Path
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from string import Template
import time

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

# Configuración de la página
st.set_page_config(
    page_title="ClimaTracker Chile",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2E8B57;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .city-header {
        background-color: #2E8B57;
        color: white;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 15px;
        text-align: center;
        font-size: 1.5rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 12px;
        border-radius: 8px;
        margin: 5px;
        border-left: 4px solid;
    }
    .temp-card {
        border-left-color: #FFA500;
    }
    .humidity-card {
        border-left-color: #45b7d1;
    }
    .wind-card {
        border-left-color: #4ecdc4;
    }
    .et0-card {
        border-left-color: #2E8B57;
    }
    .alert-high {
        background-color: #ffebee;
        border-left: 5px solid #f44336;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
        color: #d32f2f;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .alert-medium {
        background-color: #fff3e0;
        border-left: 5px solid #ff9800;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
        color: #e65100;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .alert-low {
        background-color: #e8f5e8;
        border-left: 5px solid #4caf50;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
        color: #2e7d32;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .alert-high strong {
        color: #b71c1c;
    }
    .alert-medium strong {
        color: #bf360c;
    }
    .alert-low strong {
        color: #1b5e20;
    }
</style>
""", unsafe_allow_html=True)

# Diccionario de ciudades chilenas con coordenadas
CIUDADES_CHILE = {
    "Santiago": {"lat": -33.4489, "lon": -70.6693, "region": "Metropolitana"},
    "Valparaíso": {"lat": -33.0472, "lon": -71.6127, "region": "Valparaíso"},
    "Concepción": {"lat": -36.8201, "lon": -73.0444, "region": "Biobío"},
    "La Serena": {"lat": -29.9027, "lon": -71.2519, "region": "Coquimbo"},
    "Antofagasta": {"lat": -23.6509, "lon": -70.3975, "region": "Antofagasta"},
    "Temuco": {"lat": -38.7359, "lon": -72.5904, "region": "La Araucanía"},
    "Rancagua": {"lat": -34.1701, "lon": -70.7405, "region": "O'Higgins"},
    "Talca": {"lat": -35.4264, "lon": -71.6554, "region": "Maule"},
    "Arica": {"lat": -18.4783, "lon": -70.3126, "region": "Arica y Parinacota"},
    "Iquique": {"lat": -20.2208, "lon": -70.1431, "region": "Tarapacá"},
    "Copiapó": {"lat": -27.3665, "lon": -70.3316, "region": "Atacama"},
    "Chillán": {"lat": -36.6067, "lon": -72.1034, "region": "Ñuble"},
    "Valdivia": {"lat": -39.8142, "lon": -73.2459, "region": "Los Ríos"},
    "Puerto Montt": {"lat": -41.4717, "lon": -72.9362, "region": "Los Lagos"},
    "Coyhaique": {"lat": -45.5752, "lon": -72.0662, "region": "Aysén"},
    "Punta Arenas": {"lat": -53.1638, "lon": -70.9171, "region": "Magallanes"}
}

@dataclass
class PlantInfo:
    """Clase para estructurar información de plantas"""
    id: int
    common_name: str
    scientific_name: str
    family: str
    genus: str
    image_url: Optional[str]
    # Datos de crecimiento
    minimum_temperature: Optional[float]
    maximum_temperature: Optional[float]
    minimum_precipitation: Optional[float]
    maximum_precipitation: Optional[float]
    ph_minimum: Optional[float]
    ph_maximum: Optional[float]
    light: Optional[str]
    atmospheric_humidity: Optional[int]
    growth_months: Optional[List[str]]
    bloom_months: Optional[List[str]]
    fruit_months: Optional[List[str]]
    # Características físicas
    mature_height: Optional[Dict]
    mature_spread: Optional[Dict]
    root_depth_minimum: Optional[float]
    drought_tolerance: Optional[str]
    salt_tolerance: Optional[str]

class TrefleAPIClient:
    """Cliente mejorado para la API de Trefle"""
    
    def __init__(self):
        # Token hardcodeado
        self.api_key = "CxKZt5ll64flqyjjELXAoI-dEHAH7xVs2brBi611RUY"
        self.base_url = "https://trefle.io/api/v1"
        self.session = requests.Session()
        
        # Headers mejorados
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        })
        
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Realiza petición HTTP mejorada a la API de Trefle"""
        if params is None:
            params = {}
        
        # Agregar token a parámetros
        params['token'] = self.api_key
        
        # Limpiar parámetros vacíos
        clean_params = {k: v for k, v in params.items() if v is not None and v != ''}
        
        try:
            url = f"{self.base_url}/{endpoint}"
            st.write(f"🔍 **URL:** {url}")
            st.write(f"📋 **Parámetros:** {clean_params}")
            
            # Hacer la petición con timeout extendido
            response = self.session.get(
                url,
                params=clean_params,
                timeout=30,  # Timeout más largo
                allow_redirects=True
            )
            
            st.write(f"📡 **Status Code:** {response.status_code}")
            st.write(f"🌐 **URL Final:** {response.url}")
            
            # Log de headers de respuesta para debug
            if st.checkbox("🔧 Mostrar headers de respuesta (debug)", key=f"debug_{endpoint}"):
                st.json(dict(response.headers))
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    st.success(f"✅ Respuesta exitosa - {len(str(data))} caracteres")
                    return data
                except json.JSONDecodeError as e:
                    st.error(f"❌ Error JSON: {str(e)}")
                    st.text("Primeros 500 caracteres de la respuesta:")
                    st.code(response.text[:500])
                    return None
                    
            elif response.status_code == 401:
                st.error("🔑 **Error 401:** Token de API inválido o expirado")
                st.info("💡 Verifica que el token sea correcto")
                return None
                
            elif response.status_code == 404:
                st.warning("🔍 **Error 404:** Endpoint no encontrado")
                st.info(f"💡 Verifica que el endpoint '{endpoint}' sea correcto")
                return None
                
            elif response.status_code == 429:
                st.warning("⏳ **Error 429:** Límite de rate limit excedido")
                st.info("💡 Esperando 5 segundos antes de continuar...")
                time.sleep(5)
                return None
                
            elif response.status_code == 500:
                st.error("🚫 **Error 500:** Error interno del servidor de Trefle")
                st.info("💡 **Posibles causas:**")
                st.write("• El término de búsqueda contiene caracteres especiales")
                st.write("• Los parámetros de filtro no son válidos")
                st.write("• El servidor está sobrecargado")
                st.write("• El endpoint ha cambiado")
                
                # Mostrar respuesta para debug
                st.text("Respuesta del servidor:")
                st.code(response.text[:800])
                return None
                
            elif response.status_code == 503:
                st.error("🔧 **Error 503:** Servicio no disponible")
                st.info("💡 El servidor de Trefle está en mantenimiento")
                return None
                
            else:
                st.error(f"❌ **Error HTTP {response.status_code}**")
                st.text(f"Respuesta: {response.text[:300]}")
                return None
                
        except requests.exceptions.Timeout:
            st.error("⏱️ **Timeout:** La API tardó más de 30 segundos en responder")
            st.info("💡 Intenta con un término más específico o espera un momento")
            return None
            
        except requests.exceptions.ConnectionError:
            st.error("🌐 **Error de conexión:** No se puede conectar con Trefle")
            st.info("💡 Verifica tu conexión a internet")
            return None
            
        except requests.exceptions.RequestException as e:
            st.error(f"🔗 **Error de red:** {str(e)}")
            return None
            
        except Exception as e:
            st.error(f"⚠️ **Error inesperado:** {type(e).__name__}: {str(e)}")
            return None
    
    def test_connection(self) -> bool:
        """Prueba la conexión con la API"""
        st.info("🧪 Probando conexión con Trefle API...")
        
        # Primero probar un endpoint simple
        response = self._make_request("plants")
        
        if response:
            st.success("✅ Conexión exitosa con Trefle API")
            return True
        else:
            st.error("❌ No se pudo conectar con Trefle API")
            return False
    
    def search_plants_simple(self, query: str) -> Optional[List[Dict]]:
        """Búsqueda simple de plantas sin filtros complejos"""
        
        if not query or len(query.strip()) < 3:
            st.warning("⚠️ El término debe tener al menos 3 caracteres")
            return []
        
        query = query.strip().lower()
        
        # Escapar caracteres especiales
        query = query.replace('&', 'and').replace('#', '').replace('$', '')
        
        st.info(f"🔍 Buscando: '{query}'")
        
        # Intentar múltiples estrategias de búsqueda
        strategies = [
            ("plants/search", {"q": query, "per_page": 10}),
            ("plants", {"filter[common_name]": query, "per_page": 5}),
            ("plants", {"filter[scientific_name]": query, "per_page": 5}),
        ]
        
        for i, (endpoint, params) in enumerate(strategies, 1):
            st.write(f"📋 **Estrategia {i}:** {endpoint}")
            
            response = self._make_request(endpoint, params)
            
            if response and 'data' in response and response['data']:
                plants = response['data']
                st.success(f"✅ Encontradas {len(plants)} plantas con estrategia {i}")
                return plants
            
            # Pequeña pausa entre intentos
            time.sleep(1)
        
        st.warning("🔍 No se encontraron resultados con ninguna estrategia")
        return []
    
    def search_by_scientific_name(self, scientific_name: str) -> Optional[List[Dict]]:
        """Búsqueda específica por nombre científico"""
        
        if not scientific_name:
            return []
        
        scientific_name = scientific_name.strip()
        
        params = {
            "filter[scientific_name]": scientific_name,
            "per_page": 5
        }
        
        response = self._make_request("plants", params)
        
        if response and 'data' in response:
            return response['data']
        
        return []
    
    def get_plant_details_safe(self, plant_id: int) -> Optional[Dict]:
        """Obtiene detalles de una planta con manejo de errores mejorado"""
        
        if not plant_id or plant_id <= 0:
            st.error("❌ ID de planta inválido")
            return None
        
        st.info(f"📄 Obteniendo detalles de planta ID: {plant_id}")
        
        response = self._make_request(f"plants/{plant_id}")
        
        if response and 'data' in response:
            return response['data']
        
        return None

# Datos de plantas chilenas precargados como alternativa
PLANTAS_CHILE_BACKUP = {
    "tomate": {
        "common_name": "Tomate",
        "scientific_name": "Solanum lycopersicum",
        "family": "Solanaceae",
        "temp_min": 15, "temp_max": 30,
        "ph_min": 6.0, "ph_max": 7.0,
        "light": "full_sun",
        "season": "Primavera-Verano"
    },
    "maíz": {
        "common_name": "Maíz",
        "scientific_name": "Zea mays",
        "family": "Poaceae", 
        "temp_min": 12, "temp_max": 35,
        "ph_min": 6.0, "ph_max": 7.5,
        "light": "full_sun",
        "season": "Primavera-Verano"
    },
    "papa": {
        "common_name": "Papa",
        "scientific_name": "Solanum tuberosum",
        "family": "Solanaceae",
        "temp_min": 8, "temp_max": 25,
        "ph_min": 5.0, "ph_max": 7.0,
        "light": "full_sun",
        "season": "Primavera"
    },
    "uva": {
        "common_name": "Vid/Uva",
        "scientific_name": "Vitis vinifera",
        "family": "Vitaceae",
        "temp_min": 10, "temp_max": 30,
        "ph_min": 6.0, "ph_max": 8.0,
        "light": "full_sun",
        "season": "Primavera-Verano"
    },
    "trigo": {
        "common_name": "Trigo",
        "scientific_name": "Triticum aestivum",
        "family": "Poaceae",
        "temp_min": 10, "temp_max": 30,
        "ph_min": 6.0, "ph_max": 7.5,
        "light": "full_sun",
        "season": "Otoño-Invierno"
    }
}

def search_backup_plants(query: str) -> List[Dict]:
    """Búsqueda en datos precargados como respaldo"""
    
    query = query.lower().strip()
    results = []
    
    for key, plant_data in PLANTAS_CHILE_BACKUP.items():
        if (query in key.lower() or 
            query in plant_data["common_name"].lower() or 
            query in plant_data["scientific_name"].lower()):
            
            results.append({
                "id": hash(key),  # ID artificial
                "common_name": plant_data["common_name"],
                "scientific_name": plant_data["scientific_name"],
                "family_common_name": plant_data["family"],
                "backup_data": plant_data  # Datos adicionales
            })
    
    return results

def create_plant_search_interface():
    """Interfaz mejorada para búsqueda de plantas"""
    
    st.header("🌱 Búsqueda de plantas")
    
    # Cliente de API
    trefle_client = TrefleAPIClient()
    
    # Opciones de búsqueda
    search_mode = st.radio(
        "Modo de búsqueda:",
        ["🌐 API de Trefle", "💾 Datos locales (Chile)", "🔧 Probar conexión"]
    )
    
    if search_mode == "🔧 Probar conexión":
        if st.button("🧪 Probar Conexión API", type="primary"):
            trefle_client.test_connection()
    
    elif search_mode == "🌐 API de Trefle":
        st.write("**Búsqueda en base de datos internacional Trefle**")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            search_query = st.text_input(
                "Nombre de la planta:",
                placeholder="Ej: tomato, Solanum lycopersicum, corn...",
                help="Mínimo 3 caracteres"
            )
        
        with col2:
            search_button = st.button("🔍 Buscar", type="primary")
        
        if search_query and search_button:
            with st.spinner(f"Buscando '{search_query}' en Trefle..."):
                plants = trefle_client.search_plants_simple(search_query)
                
                if plants:
                    st.success(f"✅ Encontradas {len(plants)} plantas")
                    
                    for plant in plants[:3]:  # Mostrar solo las primeras 3
                        with st.expander(f"🌿 {plant.get('common_name', 'Sin nombre')} - {plant.get('scientific_name', 'N/A')}"):
                            
                            # Información básica
                            st.write(f"**ID:** {plant.get('id', 'N/A')}")
                            st.write(f"**Familia:** {plant.get('family_common_name', 'N/A')}")
                            
                            # Imagen si está disponible
                            if plant.get('image_url'):
                                st.image(plant['image_url'], width=200)
                            
                            # Botón para detalles
                            if st.button(f"📄 Ver detalles", key=f"details_{plant.get('id')}"):
                                with st.spinner("Cargando detalles..."):
                                    details = trefle_client.get_plant_details_safe(plant.get('id'))
                                    if details:
                                        st.json(details)
                                    else:
                                        st.warning("No se pudieron cargar los detalles")
                else:
                    st.warning("❌ No se encontraron plantas")
                    st.info("💡 **Sugerencias:**")
                    st.write("• Usa nombres en inglés (tomato, corn, potato)")
                    st.write("• Prueba nombres científicos completos")
                    st.write("• Verifica la ortografía")
                    st.write("• Usa el modo 'Datos locales' para plantas chilenas")
    
    elif search_mode == "💾 Datos locales (Chile)":
        st.write("**Búsqueda en cultivos comunes de Chile**")
        
        query_local = st.text_input(
            "Buscar cultivo:",
            placeholder="tomate, maíz, papa, uva, trigo..."
        )
        
        if query_local:
            results = search_backup_plants(query_local)
            
            if results:
                st.success(f"✅ Encontrados {len(results)} cultivos")
                
                for plant in results:
                    backup_data = plant.get('backup_data', {})
                    
                    with st.expander(f"🌾 {plant['common_name']} - {plant['scientific_name']}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Familia:** {plant['family_common_name']}")
                            st.write(f"**Temperatura:** {backup_data.get('temp_min', 'N/A')}°C - {backup_data.get('temp_max', 'N/A')}°C")
                            st.write(f"**pH:** {backup_data.get('ph_min', 'N/A')} - {backup_data.get('ph_max', 'N/A')}")
                        
                        with col2:
                            st.write(f"**Luz:** {backup_data.get('light', 'N/A')}")
                            st.write(f"**Temporada:** {backup_data.get('season', 'N/A')}")
                        
                        st.success("✅ Datos disponibles localmente - Sin dependencia de API externa")
            else:
                st.warning("🔍 No se encontraron cultivos con ese nombre")
                st.write("**Cultivos disponibles:**")
                for key in PLANTAS_CHILE_BACKUP.keys():
                    st.write(f"• {key.title()}")

# Función para mostrar en el sistema principal
def show_improved_plant_search():
    """Muestra la interfaz mejorada de búsqueda"""
    create_plant_search_interface()
    
    # Información adicional
    with st.expander("ℹ️ Información sobre los errores de API"):
        st.write("""
        **Problemas comunes con Trefle API:**
        
        **Error 500 - Posibles causas:**
        • Parámetros de búsqueda malformados
        • Sobrecarga del servidor
        • Cambios en la API
        • Caracteres especiales en la búsqueda
        
        **Soluciones implementadas:**
        • Múltiples estrategias de búsqueda
        • Manejo robusto de errores
        • Datos de respaldo locales
        • Timeouts extendidos
        • Limpieza de parámetros
        
        **Alternativas:**
        • Usa el modo "Datos locales" para cultivos chilenos
        • Prueba nombres en inglés
        • Verifica la conexión antes de buscar
        """)

def add_plant_search_tab():
    """Función actualizada para la pestaña de búsqueda de plantas"""
    
    st.header("🌱 Base de datos de plantas")
    
    # Información sobre el estado de la API
    with st.expander("⚠️ Estado actual de Trefle API"):
        st.warning("""
        **Problemas detectados con Trefle API:**
        • Errores HTTP 500 frecuentes
        • Posible sobrecarga del servidor
        • Endpoints que pueden haber cambiado
        
        **Soluciones implementadas:**
        ✅ Múltiples estrategias de búsqueda
        ✅ Datos de cultivos chilenos precargados
        ✅ Manejo robusto de errores
        ✅ Prueba de conexión
        """)
    
    # Inicializar cliente mejorado
    trefle_client = TrefleAPIClient()
    
    # Opciones de búsqueda
    search_mode = st.selectbox(
        "Selecciona el modo de búsqueda:",
        [
            "💾 Cultivos de Chile (Datos locales - Recomendado)",
            "🌐 API Internacional de Trefle",
            "🔧 Diagnóstico de conexión"
        ]
    )
    
    # === MODO 1: DATOS LOCALES DE CHILE ===
    if search_mode == "💾 Cultivos de Chile":
        st.subheader("🇨🇱 Cultivos tradicionales de Chile")
        st.success("✅ Datos disponibles sin conexión a internet")
        
        query_local = st.text_input(
            "Buscar cultivo:",
            placeholder="tomate, maíz, papa, uva, trigo, palta...",
            help="Busca en cultivos comunes de Chile"
        )
        
        if query_local and len(query_local) >= 2:
            results = search_backup_plants(query_local)
            
            if results:
                st.success(f"🌾 Encontrados {len(results)} cultivos")
                
                for plant in results:
                    backup_data = plant.get('backup_data', {})
                    
                    with st.expander(f"🌱 {plant['common_name']} ({plant['scientific_name']})", expanded=True):
                        
                        # Crear métricas visuales
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric(
                                "🌡️ Temperatura",
                                f"{backup_data.get('temp_min', 'N/A')}°C - {backup_data.get('temp_max', 'N/A')}°C",
                                help="Rango de temperatura óptimo"
                            )
                        
                        with col2:
                            st.metric(
                                "🧪 pH del suelo",
                                f"{backup_data.get('ph_min', 'N/A')} - {backup_data.get('ph_max', 'N/A')}",
                                help="Rango de pH recomendado"
                            )
                        
                        with col3:
                            light_icon = "☀️" if backup_data.get('light') == 'full_sun' else "🌤️"
                            st.metric(
                                f"{light_icon} Luz",
                                backup_data.get('light', 'N/A').replace('_', ' ').title(),
                                help="Requerimientos de luz solar"
                            )
                        
                        # Información adicional
                        st.write(f"**👨‍🔬 Familia botánica:** {plant['family_common_name']}")
                        st.write(f"**📅 Temporada de cultivo:** {backup_data.get('season', 'N/A')}")
                        
                        # Análisis de compatibilidad con el clima actual (simulado)
                        current_temp = 20  # Temperatura de ejemplo
                        temp_min = backup_data.get('temp_min', 0)
                        temp_max = backup_data.get('temp_max', 50)
                        
                        if temp_min <= current_temp <= temp_max:
                            st.success("✅ Compatible con temperatura actual")
                        else:
                            st.warning(f"⚠️ Temperatura actual ({current_temp}°C) fuera del rango óptimo")
                        
                        # Recomendaciones específicas
                        st.write("**💡 Recomendaciones:**")
                        if backup_data.get('light') == 'full_sun':
                            st.write("• Plantar en área con máxima exposición solar")
                        
                        if backup_data.get('season') == 'Primavera-Verano':
                            st.write("• Cultivar entre septiembre y marzo")
                        elif backup_data.get('season') == 'Otoño-Invierno':
                            st.write("• Cultivar entre marzo y agosto")
                        
                        ph_avg = (backup_data.get('ph_min', 6.5) + backup_data.get('ph_max', 7.0)) / 2
                        if ph_avg < 6.5:
                            st.write("• Suelo ligeramente ácido recomendado")
                        elif ph_avg > 7.0:
                            st.write("• Suelo ligeramente alcalino recomendado")
                        else:
                            st.write("• Suelo neutro es ideal")
            else:
                st.info("🔍 No se encontraron cultivos con ese nombre")
                st.write("**Cultivos disponibles:**")
                
                # Mostrar cultivos disponibles en columnas
                cols = st.columns(3)
                for i, (key, data) in enumerate(PLANTAS_CHILE_BACKUP.items()):
                    with cols[i % 3]:
                        st.write(f"• **{key.title()}** ({data['scientific_name']})")
        
        # Mostrar todos los cultivos si no hay búsqueda
        if not query_local:
            st.write("**🌾 Cultivos disponibles en la base de datos:**")
            
            for key, data in PLANTAS_CHILE_BACKUP.items():
                with st.expander(f"🌱 {key.title()} - {data['scientific_name']}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Familia:** {data['family']}")
                        st.write(f"**Temperatura:** {data['temp_min']}°C - {data['temp_max']}°C")
                    
                    with col2:
                        st.write(f"**pH:** {data['ph_min']} - {data['ph_max']}")
                        st.write(f"**Temporada:** {data['season']}")
    
    # === MODO 2: API DE TREFLE ===
    elif search_mode == "🌐 API Internacional de Trefle":
        st.subheader("🌍 Búsqueda Internacional (Trefle API)")
        st.warning("⚠️ Esta opción puede presentar errores debido a problemas con el servidor de Trefle")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            search_query = st.text_input(
                "Nombre de la planta (en inglés):",
                placeholder="tomato, corn, potato, rose, oak...",
                help="Usa nombres en inglés para mejores resultados"
            )
        
        with col2:
            search_button = st.button("🔍 Buscar", type="primary")
        
        if search_query and search_button:
            if len(search_query.strip()) < 3:
                st.error("❌ El término debe tener al menos 3 caracteres")
            else:
                with st.spinner(f"🔍 Buscando '{search_query}' en Trefle API..."):
                    
                    # Mostrar información de debug
                    with st.expander("🔧 Información de debug", expanded=False):
                        plants = trefle_client.search_plants_simple(search_query)
                    
                    # Si no se encuentran plantas, mostrar alternativas
                    if not plants:
                        st.error("❌ No se encontraron plantas")
                        
                        st.info("💡 **Alternativas recomendadas:**")
                        st.write("1. Usa el modo 'Cultivos de Chile' para plantas locales")
                        st.write("2. Prueba nombres más generales (ej: 'tomato' en lugar de 'cherry tomato')")
                        st.write("3. Verifica la ortografía en inglés")
                        st.write("4. Prueba nombres científicos completos")
                        
                        # Sugerir plantas similares de la base local
                        st.write("\n**🇨🇱 Plantas similares en nuestra base local:**")
                        local_suggestions = search_backup_plants(search_query)
                        if local_suggestions:
                            for plant in local_suggestions:
                                st.write(f"• {plant['common_name']} ({plant['scientific_name']})")
                    else:
                        st.success(f"✅ Encontradas {len(plants)} plantas")
                        
                        for plant in plants[:3]:  # Mostrar máximo 3 resultados
                            with st.expander(f"🌿 {plant.get('common_name', 'Sin nombre')} - {plant.get('scientific_name', 'N/A')}"):
                                
                                # Información básica
                                st.write(f"**ID:** {plant.get('id', 'N/A')}")
                                st.write(f"**Familia:** {plant.get('family_common_name', 'N/A')}")
                                
                                # Imagen si disponible
                                if plant.get('image_url'):
                                    try:
                                        st.image(plant['image_url'], width=200, caption=plant.get('common_name', 'Planta'))
                                    except:
                                        st.write("🖼️ Imagen no disponible")
                                
                                # Botón para más detalles
                                if st.button(f"📄 Ver detalles completos", key=f"details_{plant.get('id')}"):
                                    with st.spinner("Cargando detalles..."):
                                        details = trefle_client.get_plant_details_safe(plant.get('id'))
                                        if details:
                                            # Mostrar detalles de forma organizada
                                            if 'main_species' in details:
                                                species_data = details['main_species']
                                                if 'growth' in species_data:
                                                    growth = species_data['growth']
                                                    
                                                    st.write("**🌱 Datos de crecimiento:**")
                                                    
                                                    if growth.get('minimum_temperature'):
                                                        temp_data = growth['minimum_temperature']
                                                        if isinstance(temp_data, dict) and 'deg_c' in temp_data:
                                                            min_temp = temp_data['deg_c']
                                                            max_temp_data = growth.get('maximum_temperature', {})
                                                            max_temp = max_temp_data.get('deg_c', 'N/A') if isinstance(max_temp_data, dict) else 'N/A'
                                                            st.write(f"• **Temperatura:** {min_temp}°C - {max_temp}°C")
                                                    
                                                    if growth.get('ph_minimum') and growth.get('ph_maximum'):
                                                        st.write(f"• **pH:** {growth['ph_minimum']} - {growth['ph_maximum']}")
                                                    
                                                    if growth.get('light'):
                                                        light_readable = growth['light'].replace('_', ' ').title()
                                                        st.write(f"• **Luz:** {light_readable}")
                                                    
                                                    if growth.get('atmospheric_humidity'):
                                                        st.write(f"• **Humedad:** {growth['atmospheric_humidity']}%")
                                        else:
                                            st.warning("⚠️ No se pudieron cargar los detalles")
    
    # === MODO 3: DIAGNÓSTICO ===
    elif search_mode == "🔧 Diagnóstico de conexión":
        st.subheader("🔧 Diagnóstico de Trefle API")
        
        if st.button("🧪 Probar conexión", type="primary"):
            with st.spinner("Probando conexión..."):
                
                # Test 1: Conexión básica
                st.write("**Test 1: Conexión básica**")
                connection_ok = trefle_client.test_connection()
                
                if connection_ok:
                    st.success("✅ Conexión exitosa")
                    
                    # Test 2: Búsqueda simple
                    st.write("**Test 2: Búsqueda simple**")
                    test_plants = trefle_client.search_plants_simple("oak")
                    
                    if test_plants:
                        st.success(f"✅ Búsqueda exitosa - {len(test_plants)} resultados")
                    else:
                        st.error("❌ Búsqueda falló")
                        
                        # Test 3: Búsqueda alternativa
                        st.write("**Test 3: Búsqueda alternativa**")
                        alt_plants = trefle_client.search_by_scientific_name("Quercus")
                        
                        if alt_plants:
                            st.success(f"✅ Búsqueda alternativa exitosa - {len(alt_plants)} resultados")
                        else:
                            st.error("❌ Todas las búsquedas fallaron")
                            st.warning("🔧 Recomendación: Usar solo datos locales de Chile")
                else:
                    st.error("❌ No se pudo conectar con Trefle API")
                    st.info("💡 **Posibles causas:**")
                    st.write("• Token de API inválido o expirado")
                    st.write("• Servidor de Trefle no disponible")
                    st.write("• Problemas de conectividad")
                    st.write("• Cambios en la API")
        
        # Información adicional sobre el diagnóstico
        with st.expander("ℹ️ Información sobre errores comunes"):
            st.write("""
            **Error HTTP 500 (Error interno del servidor):**
            • El servidor de Trefle tiene problemas internos
            • Los parámetros de búsqueda pueden ser incorrectos
            • La API puede estar sobrecargada
            
            **Error HTTP 401 (No autorizado):**
            • Token de API inválido o expirado
            • Límites de uso excedidos
            
            **Error HTTP 404 (No encontrado):**
            • El endpoint no existe o cambió
            • La planta específica no está en la base de datos
            
            **Timeout:**
            • El servidor tardó demasiado en responder
            • Problemas de conectividad
            
            **Soluciones recomendadas:**
            1. Usar los datos locales de Chile (más confiable)
            2. Verificar la conexión a internet
            3. Intentar más tarde si el servidor está sobrecargado
            4. Reportar problemas persistentes
            """)
    
    # Footer con información adicional
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("""
        **💡 Recomendación:**
        Usa los 'Cultivos de Chile' para información confiable sobre plantas locales.
        """)
    
    with col2:
        st.warning("""
        **⚠️ Nota sobre Trefle API:**
        La API externa puede presentar fallos intermitentes.
        """)

def integrate_trefle_to_main_system():
    """
    Esta función muestra cómo integrar Trefle en tu sistema principal.
    Agregar como cuarta pestaña en el sistema existente.
    """
    
    # En la función main(), cambiar:
    # tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📈 Gráficos Detallados", "🌾 Recomendaciones Agrícolas"])
    # Por:
    # tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📈 Gráficos Detallados", "🌾 Recomendaciones Agrícolas", "🌱 Base de Datos de Plantas"])
    
    # Y agregar:
    # with tab4:
    #     add_plant_search_tab()
    
    pass

class WeatherAPIClient:
    """Cliente para la API de Open-Meteo"""
    
    def __init__(self):
        self.base_url = "https://api.open-meteo.com/v1/forecast"
        self.session = requests.Session()
    
    def get_weather_data(self, latitude, longitude, days=7):
        """Obtiene datos meteorológicos para una ubicación específica"""
        # Formatear parámetros correctamente para Open-Meteo API
        params = {
            "latitude": f"{latitude:.4f}",
            "longitude": f"{longitude:.4f}",
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,shortwave_radiation,surface_pressure",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,relative_humidity_2m_mean,shortwave_radiation_sum,surface_pressure_mean",
            "timezone": "auto",
            "forecast_days": min(days, 16)  # Open-Meteo límite máximo es 16 días
        }
        
        try:
            response = self.session.get(self.base_url, params=params, timeout=15)
            
            if response.status_code != 200:
                st.error(f"Error HTTP {response.status_code}: {response.text}")
                return None
                
            return response.json()
            
        except requests.exceptions.Timeout:
            st.error("⏱️ Timeout: La API tardó demasiado en responder. Intenta nuevamente.")
            return None
        except requests.exceptions.ConnectionError:
            st.error("🌐 Error de conexión: Verifica tu conexión a internet.")
            return None
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Error al obtener datos meteorológicos: {str(e)}")
            return None
        except Exception as e:
            st.error(f"⚠️ Error inesperado: {str(e)}")
            return None

def safe_float_conversion(value, default=0.0):
    """Convierte de forma segura un valor a float, manejando todos los casos posibles"""
    try:
        # Verificar si es None o NaN
        if value is None or pd.isna(value):
            return default
            
        # Si es una lista o tupla, tomar el primer valor válido
        if isinstance(value, (list, tuple)):
            for v in value:
                if v is not None and not pd.isna(v):
                    try:
                        return float(v)
                    except (ValueError, TypeError):
                        continue
            return default
        
        # Si es string, limpiar y convertir
        if isinstance(value, str):
            # Limpiar caracteres especiales
            clean_value = value.strip().replace('°C', '').replace('%', '').replace('mm', '').replace('km/h', '')
            if clean_value == '' or clean_value == 'N/A':
                return default
            return float(clean_value)
        
        # Conversión directa
        float_value = float(value)
        
        # Verificar si es un número válido
        if math.isnan(float_value) or math.isinf(float_value):
            return default
            
        return float_value
        
    except (ValueError, TypeError, AttributeError):
        return default

def calculate_et0(temp, humidity, radiation, wind_speed, pressure=101.3):
    """
    Calcula ET0 según FAO Penman-Monteith.
    Args:
        temp: Temperatura promedio diaria (°C).
        humidity: Humedad relativa (%).
        radiation: Radiación solar en W/m².
        wind_speed: Velocidad del viento en km/h.
        pressure: Presión atmosférica en kPa.
    Returns:
        ET0 en mm/día.
    """
    try:
        # Conversión segura de todos los valores
        temp = safe_float_conversion(temp, 20.0)
        humidity = safe_float_conversion(humidity, 50.0)
        radiation = safe_float_conversion(radiation, 200.0)
        wind_speed = safe_float_conversion(wind_speed, 10.0)
        pressure = safe_float_conversion(pressure, 101.3)
        
        # Validaciones de rango
        temp = max(-50, min(50, temp))  # Temperatura entre -50 y 50°C
        humidity = max(0, min(100, humidity))  # Humedad entre 0 y 100%
        radiation = max(0, radiation)  # Radiación no negativa
        wind_speed = max(0, wind_speed)  # Velocidad del viento no negativa
        pressure = max(80, min(120, pressure))  # Presión entre 80 y 120 kPa
        
        # Conversión de unidades
        wind_speed_ms = wind_speed / 3.6  # km/h → m/s
        Rn = radiation * 0.0864  # W/m² → MJ/m²/día
        G = 0  # Flujo de calor del suelo (asumido 0 para cálculos diarios)
        gamma = 0.665e-3 * (pressure/101.3)  # Constante psicrométrica (kPa/°C)

        # Prevenir división por cero en denominador de temperatura
        temp_denom = temp + 237.3
        if temp_denom == 0:
            temp_denom = 0.1
            
        # Cálculos intermedios
        delta = (4098 * (0.6108 * np.exp((17.27 * temp) / temp_denom))) / (temp_denom ** 2)
        es = 0.6108 * np.exp((17.27 * temp) / temp_denom)
        ea = (humidity / 100) * es

        # Prevenir división por cero en la temperatura absoluta
        temp_abs = temp + 273
        if temp_abs <= 0:
            temp_abs = 273
            
        # Ecuación FAO Penman-Monteith
        numerator = (0.408 * delta * (Rn - G)) + (gamma * (900 / temp_abs) * wind_speed_ms * (es - ea))
        denominator = delta + (gamma * (1 + 0.34 * wind_speed_ms))
        
        # Prevenir división por cero
        if denominator == 0:
            denominator = 0.001
            
        et0 = numerator / denominator
        return max(0, min(15, et0))  # Limitar ET0 a un rango razonable (0 a 15 mm/día)
    except Exception as e:  
        st.error(f"Error al calcular ET0: {str(e)}")
        return 0.0

def process_weather_data(data):
    """Procesa datos meteorológicos de la API y devuelve DataFrames horarios y diarios"""
    if not data or 'hourly' not in data or 'daily' not in data:
        st.error("❌ Datos meteorológicos incompletos")
        return None, None
    
    try:
        # === DATOS HORARIOS ===
        hourly_required = ['time', 'temperature_2m', 'relative_humidity_2m', 'precipitation', 'wind_speed_10m']
        hourly_data = {}
        
        for key in hourly_required:
            if key not in data['hourly']:
                st.error(f"❌ Falta dato horario requerido: {key}")
                return None, None
            hourly_data[key] = data['hourly'][key]
        
        # Añadir radiación con valor por defecto si no existe
        hourly_data['shortwave_radiation'] = data['hourly'].get('shortwave_radiation', [200.0] * len(hourly_data['time']))
        
        hourly_df = pd.DataFrame({
            'datetime': pd.to_datetime(hourly_data['time']),
            'temperature': [safe_float_conversion(t, 20.0) for t in hourly_data['temperature_2m']],
            'humidity': [safe_float_conversion(h, 50.0) for h in hourly_data['relative_humidity_2m']],
            'precipitation': [safe_float_conversion(p, 0.0) for p in hourly_data['precipitation']],
            'wind_speed': [safe_float_conversion(w, 10.0) for w in hourly_data['wind_speed_10m']],
            'radiation': [safe_float_conversion(r, 200.0) for r in hourly_data['shortwave_radiation']]
        })

        # === DATOS DIARIOS === 
        daily_required = ['time', 'temperature_2m_max', 'temperature_2m_min', 'precipitation_sum',
                         'wind_speed_10m_max', 'relative_humidity_2m_mean']
        daily_data = {}
        
        for key in daily_required:
            if key not in data['daily']:
                st.error(f"❌ Falta dato diario requerido: {key}")
                return None, None
            daily_data[key] = data['daily'][key]
        
        # Datos opcionales con valores por defecto
        daily_data['shortwave_radiation_sum'] = data['daily'].get('shortwave_radiation_sum', 
                                        [200.0] * len(daily_data['time']))
        daily_data['surface_pressure_mean'] = data['daily'].get('surface_pressure_mean', 
                                        [1013.0] * len(daily_data['time']))

        # Crear DataFrame diario
        daily_df = pd.DataFrame({
            'date': pd.to_datetime(daily_data['time']),
            'temp_max': [safe_float_conversion(t, 25.0) for t in daily_data['temperature_2m_max']],
            'temp_min': [safe_float_conversion(t, 15.0) for t in daily_data['temperature_2m_min']],
            'precipitation': [safe_float_conversion(p, 0.0) for p in daily_data['precipitation_sum']],
            'wind_speed': [safe_float_conversion(w, 10.0) for w in daily_data['wind_speed_10m_max']],
            'humidity': [safe_float_conversion(h, 50.0) for h in daily_data['relative_humidity_2m_mean']],
            'radiation': [safe_float_conversion(r, 200.0) for r in daily_data['shortwave_radiation_sum']],
            'pressure': [safe_float_conversion(p/10 if p > 200 else p, 101.3) for p in daily_data['surface_pressure_mean']]
        })

        # Calcular campos derivados
        daily_df['temp_mean'] = (daily_df['temp_max'] + daily_df['temp_min']) / 2
        
        # Calcular ET0 para cada día
        daily_df['et0'] = daily_df.apply(lambda row: calculate_et0(
            temp=row['temp_mean'],
            humidity=row['humidity'],
            radiation=row['radiation'],
            wind_speed=row['wind_speed'],
            pressure=row['pressure']
        ), axis=1)

        # Validaciones y limpieza final
        daily_df['temp_max'] = daily_df['temp_max'].clip(-50, 60)
        daily_df['temp_min'] = daily_df['temp_min'].clip(-60, 50)
        daily_df['temp_mean'] = daily_df['temp_mean'].clip(-55, 55)
        
        # Asegurar temp_max >= temp_min
        mask = daily_df['temp_max'] < daily_df['temp_min']
        daily_df.loc[mask, ['temp_max', 'temp_min']] = daily_df.loc[mask, ['temp_min', 'temp_max']].values
        
        # Limpieza de valores inválidos
        daily_df = daily_df.replace([np.inf, -np.inf], np.nan)
        daily_df = daily_df.fillna(method='ffill').fillna(0)

        # Debug: mostrar estructura final
        print("\n✅ Datos diarios procesados:")
        print(daily_df[['date', 'temp_max', 'temp_min', 'humidity', 'et0']].head())
        
        return hourly_df, daily_df
        
    except Exception as e:
        st.error(f"❌ Error procesando datos: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None
    
def load_weather_template():
    """Carga la plantilla HTML y los recursos necesarios"""
    try:
        # Cargar CSS
        css_path = STATIC_DIR / "css" / "weather_card.css"
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()
        
        # Cargar plantilla HTML
        template_path = STATIC_DIR / "templates" / "weather_card.html"
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()
            
        return css, template
        
    except Exception as e:
        st.error(f"Error cargando plantillas: {str(e)}")
        return "", ""

def truncate_decimals(value, decimals=3):
    """
    Trunca un número a la cantidad específica de decimales sin redondear
    Args:
        value: Valor numérico a truncar
        decimals: Número de decimales (por defecto 3)
    Returns:
        Número truncado
    """
    try:
        if pd.isna(value) or value is None:
            return 0.0
        multiplier = 10 ** decimals
        return int(float(value) * multiplier) / multiplier
    except (ValueError, TypeError):
        return 0.0

WEATHER_CSS, WEATHER_TEMPLATE = load_weather_template()

def render_weather_card(city_name, daily_data):
    """Renderiza una tarjeta climática con estilos uniformes y tamaños de letra aumentados"""
    try:
        # Extraer datos
        temp_max = safe_float_conversion(daily_data.get('temp_max', 0))
        temp_min = safe_float_conversion(daily_data.get('temp_min', 0))
        temp_range = temp_max - temp_min
        humidity = safe_float_conversion(daily_data.get('humidity', 0))
        wind_speed = safe_float_conversion(daily_data.get('wind_speed', 0))
        et0 = safe_float_conversion(daily_data.get('et0', 0))
        
        # Color para temperatura
        temp_color = "#FF4500" if temp_max > 30 else "#1E90FF" if temp_max < 10 else "#FFA500"

        st.markdown(f"""
        <div style="background-color:#12453E; padding:12px; border-radius:8px; margin-bottom:15px;">
            <h3 style="color:white; margin:0; text-align:center; font-size:1.5rem;">
                ⛰️ {city_name.upper()}
            </h3>
        </div>
        """, unsafe_allow_html=True)

        # 1. Inyectar CSS (¡esto es clave!)
        st.markdown("""
        <style>
            .uniform-card {
                padding: 16px;
                border-radius: 8px;
                background: #f8f9fa;
                margin: 5px;
                border-left: 4px solid;
                height: 140px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
            }
            .uniform-title {
                margin: 0;
                font-size: 18px !important;
                color: #666;
                font-weight: 600;
            }
            .uniform-value {
                margin: 8px 0;
                font-size: 32px !important;
                font-weight: bold;
                line-height: 1.2;
            }
            .uniform-extra {
                margin: 0;
                font-size: 16px !important;
                color: #666;
            }
        </style>
        """, unsafe_allow_html=True)

        # 2. Crear las 4 tarjetas
        col1, col2, col3, col4 = st.columns(4)
        
        # Tarjeta 1: Temperatura
        with col1:
            st.markdown(f"""
            <div class="uniform-card" style="border-left-color: {temp_color};">
                <p class="uniform-title">Máx/Mín</p>
                <p class="uniform-value" style="color:{temp_color};">{temp_max:.1f}° / {temp_min:.1f}°</p>
                <p class="uniform-extra">Amplitud: {temp_range:.1f}°</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Tarjeta 2: Humedad
        with col2:
            st.markdown(f"""
            <div class="uniform-card" style="border-left-color: #45b7d1;">
                <p class="uniform-title">Humedad relativa</p>
                <p class="uniform-value" style="color:#45b7d1;">{humidity:.0f}%</p>
                <p class="uniform-extra">&nbsp;</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Tarjeta 3: Viento
        with col3:
            st.markdown(f"""
            <div class="uniform-card" style="border-left-color: #4ecdc4;">
                <p class="uniform-title">Viento</p>
                <p class="uniform-value" style="color:#4ecdc4;">{wind_speed:.1f} km/h</p>
                <p class="uniform-extra">&nbsp;</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Tarjeta 4: ET0
        with col4:
            st.markdown(f"""
            <div class="uniform-card" style="border-left-color: #2E8B57;">
                <p class="uniform-title">Evapostranspiración</p>
                <p class="uniform-value" style="color:#2E8B57;">{et0:.2f} mm/día</p>
                <p class="uniform-extra">&nbsp;</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
    except Exception as e:
        st.error(f"Error mostrando datos para {city_name}: {str(e)}")
    
def generate_agricultural_recommendations(daily_df):
    """Genera recomendaciones agrícolas basadas en los datos meteorológicos"""
    recommendations = []
    alerts = []
    
    if daily_df is None or daily_df.empty:
        return recommendations, alerts
    
    latest_data = daily_df.iloc[0]  # Datos más recientes
    
    # Análisis de temperatura
    temp_max = safe_float_conversion(latest_data.get('temp_max', 0))
    temp_min = safe_float_conversion(latest_data.get('temp_min', 0))
    
    if temp_max > 35:
        alerts.append({
            'type': 'high',
            'title': '🌡️ Alerta de Temperatura Alta',
            'message': f'Temperatura máxima de {temp_max:.1f}°C. Riesgo de estrés térmico en cultivos.'
        })
        recommendations.append("Aumentar la frecuencia de riego, especialmente en horas de la tarde")
        recommendations.append("Considerar el uso de mallas de sombreo para cultivos sensibles")
    
    if temp_min < 0:
        alerts.append({
            'type': 'high',
            'title': '❄️ Alerta de Heladas',
            'message': f'Temperatura mínima de {temp_min:.1f}°C. Riesgo de heladas.'
        })
        recommendations.append("Activar sistemas de protección contra heladas")
        recommendations.append("Cosechar productos sensibles al frío")
    
    # Análisis de humedad
    humidity = safe_float_conversion(latest_data.get('humidity', 0))
    if humidity < 30:
        alerts.append({
            'type': 'medium',
            'title': '💧 Baja Humedad Relativa',
            'message': f'Humedad relativa de {humidity:.1f}%. Aumentar riego.'
        })
        recommendations.append("Incrementar la humedad del suelo mediante riego por goteo")
    elif humidity > 80:
        alerts.append({
            'type': 'medium',
            'title': '🍄 Alta Humedad Relativa',
            'message': f'Humedad relativa de {humidity:.1f}%. Riesgo de enfermedades fúngicas.'
        })
        recommendations.append("Mejorar la ventilación en cultivos bajo invernadero")
        recommendations.append("Aplicar tratamientos preventivos contra hongos")
    
    # Análisis de precipitación
    precipitation = safe_float_conversion(latest_data.get('precipitation', 0))
    if precipitation > 20:
        alerts.append({
            'type': 'medium',
            'title': '🌧️ Precipitación Abundante',
            'message': f'Precipitación de {precipitation:.1f}mm. Monitorear drenaje.'
        })
        recommendations.append("Verificar sistemas de drenaje en cultivos")
        recommendations.append("Posponer aplicaciones de fertilizantes foliares")
    elif precipitation == 0 and humidity < 40:
        recommendations.append("Planificar riego adicional debido a condiciones secas")
    
    # Análisis de viento
    wind_speed = safe_float_conversion(latest_data.get('wind_speed', 0))
    if wind_speed > 25:
        alerts.append({
            'type': 'high', 
            'title': '💨 Vientos Fuertes',
            'message': f'Velocidad del viento de {wind_speed:.1f} km/h. Riesgo de daño mecánico.'
        })
        recommendations.append("Instalar cortavientos para proteger cultivos jóvenes")
        recommendations.append("Posponer aplicaciones de pesticidas y fertilizantes foliares")
    
    # Análisis de ET0
    et0 = safe_float_conversion(latest_data.get('et0', 0))
    if et0 > 6:
        recommendations.append(f"Alta evapotranspiración ({et0:.1f} mm/día). Incrementar riego según tipo de cultivo")
    elif et0 < 2:
        recommendations.append(f"Baja evapotranspiración ({et0:.1f} mm/día). Reducir frecuencia de riego")
    
    # Recomendaciones generales si no hay alertas
    if not alerts:
        alerts.append({
            'type': 'low',
            'title': '✅ Condiciones Favorables',
            'message': 'Las condiciones climáticas actuales son favorables para la agricultura.'
        })
        recommendations.append("Condiciones ideales para actividades agrícolas generales")
        recommendations.append("Buen momento para aplicaciones foliares y mantenimiento de cultivos")
    
    return recommendations, alerts

def create_temperature_chart(hourly_df):
    """Crea gráfico de temperatura por horas"""
    if hourly_df is None or hourly_df.empty:
        return go.Figure()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hourly_df['datetime'],
        y=hourly_df['temperature'],
        mode='lines+markers',
        name='Temperatura (°C)',
        line=dict(color='#ff6b6b', width=3),
        marker=dict(size=6)
    ))
    
    fig.update_layout(
        title="📈 Temperatura por Horas",
        xaxis_title="Fecha y Hora",
        yaxis_title="Temperatura (°C)",
        hovermode='x unified',
        showlegend=False,
        height=400
    )
    
    return fig

def create_humidity_precipitation_chart(hourly_df):
    """Crea gráfico combinado de humedad y precipitación"""
    if hourly_df is None or hourly_df.empty:
        return go.Figure()
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Humedad relativa
    fig.add_trace(
        go.Scatter(
            x=hourly_df['datetime'],
            y=hourly_df['humidity'],
            name="Humedad Relativa (%)",
            line=dict(color='#4ecdc4', width=3)
        ),
        secondary_y=False,
    )
    
    # Precipitación
    fig.add_trace(
        go.Bar(
            x=hourly_df['datetime'],
            y=hourly_df['precipitation'],
            name="Precipitación (mm)",
            marker_color='#45b7d1',
            opacity=0.7
        ),
        secondary_y=True,
    )
    
    fig.update_xaxes(title_text="Fecha y Hora")
    fig.update_yaxes(title_text="Humedad Relativa (%)", secondary_y=False)
    fig.update_yaxes(title_text="Precipitación (mm)", secondary_y=True)
    
    fig.update_layout(
        title="💧 Humedad Relativa y Precipitación",
        hovermode='x unified',
        height=400
    )
    
    return fig
    
def improved_tab1_content(selected_cities, weather_data_dict):
    st.title("🌦️ Pronóstico Climático")
    
    if not weather_data_dict:
        st.warning("No hay datos meteorológicos disponibles")
        return

    for city in selected_cities:
        hourly_df, daily_df = weather_data_dict.get(city, (None, None))
        
        if daily_df is not None and not daily_df.empty:
            latest_data = daily_df.iloc[0].to_dict()
            render_weather_card(city, latest_data)
        else:
            st.warning(f"No hay datos para {city}")

def main():
    """Función principal de la aplicación"""
    
    # Título principal
    st.markdown('<h1 class="main-header">🌾 ClimaTracker Chile</h1>', 
                unsafe_allow_html=True)
    
    # Sidebar para configuración
    st.sidebar.header("⚙️ Configuración")
    
    # Selector de ciudades
    selected_cities = st.sidebar.multiselect(
        "Selecciona las ciudades:",
        options=list(CIUDADES_CHILE.keys()),
        default=["Temuco", "Puerto Montt"],
        help="Puedes seleccionar múltiples ciudades para comparar"
    )
    
    # Días de pronóstico
    forecast_days = st.sidebar.slider(
        "Días de pronóstico:",
        min_value=1,
        max_value=16,
        value=7,
        help="Número de días de pronóstico meteorológico"
    )
    
    # Botón para actualizar datos
    if st.sidebar.button("🔄 Actualizar Datos", type="primary"):
        st.rerun()
    
    if not selected_cities:
        st.warning("⚠️ Por favor selecciona al menos una ciudad para mostrar los datos.")
        return
    
    # Inicializar cliente de API
    weather_client = WeatherAPIClient()
    
    # Contenedor para datos meteorológicos
    weather_data_dict = {}
    
    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Obtener datos para cada ciudad seleccionada
    for i, city in enumerate(selected_cities):
        status_text.text(f"🌡️ Obteniendo datos para {city}...")
        progress_bar.progress((i + 1) / len(selected_cities))
        
        city_coords = CIUDADES_CHILE[city]
        
        # Pequeño delay para evitar rate limiting
        if i > 0:
            time.sleep(0.5)
            
        raw_data = weather_client.get_weather_data(
            city_coords['lat'], 
            city_coords['lon'], 
            forecast_days
        )
        
        if raw_data:
            # *** USAR LA FUNCIÓN MEJORADA AQUÍ ***
            hourly_df, daily_df = process_weather_data(raw_data)
            weather_data_dict[city] = (hourly_df, daily_df)
        else:
            st.warning(f"⚠️ No se pudieron obtener datos para {city}")
            weather_data_dict[city] = (None, None)
    
    progress_bar.empty()
    status_text.empty()
    
    # Tabs para organizar el contenido
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📈 Gráficos Detallados", "🌾 Recomendaciones Agrícolas", "🌱 Base de Datos de Plantas"])
    
    with tab1:
        improved_tab1_content(selected_cities, weather_data_dict)
    
    # Los otros tabs siguen igual
    with tab2:
        st.header("📈 Análisis detallado")
        
        # Selector de ciudad para gráficos detallados
        selected_city_chart = st.selectbox(
            "Selecciona ciudad para análisis detallado:",
            selected_cities
        )
        
        if selected_city_chart:
            hourly_df, daily_df = weather_data_dict.get(selected_city_chart, (None, None))
            
            if hourly_df is not None and daily_df is not None:
                # Gráfico de temperatura
                temp_chart = create_temperature_chart(hourly_df)
                st.plotly_chart(temp_chart, use_container_width=True)

                # Gráfico de humedad y precipitación
                humid_precip_chart = create_humidity_precipitation_chart(hourly_df)
                st.plotly_chart(humid_precip_chart, use_container_width=True)

                # Tabla de resumen diario
                if not daily_df.empty:
                    st.subheader("📋 Resumen de 7 Días")
                    display_df = daily_df[['date', 'temp_max', 'temp_min', 'precipitation', 'wind_speed', 'humidity', 'et0']].copy()
                    display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
                    display_df.columns = ['Fecha', 'Temp. Máx (°C)', 'Temp. Mín (°C)',
                                        'Precipitación (mm)', 'Viento (km/h)', 'Humedad (%)', 'ET0 (mm/día)']
                    
                    st.dataframe(display_df, use_container_width=True)
            else:
                st.error(f"No hay datos disponibles para {selected_city_chart}")
    
    with tab3:
        st.header("🌾 Recomendaciones agrícolas")
        
        for city in selected_cities:
            hourly_df, daily_df = weather_data_dict.get(city, (None, None))
            
            if daily_df is not None and not daily_df.empty:
                st.subheader(f"📍 {city}")
                
                recommendations, alerts = generate_agricultural_recommendations(daily_df)
                
                # Mostrar alertas
                for alert in alerts:
                    alert_class = f"alert-{alert['type']}"
                    st.markdown(f"""
                    <div class="{alert_class}">
                        <strong>{alert['title']}</strong><br>
                        {alert['message']}
                    </div>
                    """, unsafe_allow_html=True)
                
                # Mostrar recomendaciones
                if recommendations:
                    st.write("**Recomendaciones:**")
                    for i, rec in enumerate(recommendations, 1):
                        st.write(f"{i}. {rec}")
                
                st.divider()
    
    with tab4:
        add_plant_search_tab()

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        Datos proporcionados por Open-Meteo API<br>
        Desarrollado por Azzek para apoyar la agricultura en Chile 🇨🇱
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()