import streamlit as st
import pandas as pd
import random
import uuid
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

st.set_page_config(page_title="Clasificación de textos", layout="wide")
st.title("📝 Clasifica los textos: ¿Humano o IA con marca de agua?")

st.markdown("""
Este formulario forma parte de un experimento académico sobre la detección de textos generados por inteligencia artificial (IA).  
A continuación, se te presentarán **dos textos** y tu tarea será clasificarlos mediante **dos encuestas** consecutivas:

1. **Encuesta 1:**  
   ¿Quién crees que ha escrito este texto?  
   - Escrito por humano  
   - Escrito por IA  

2. **Encuesta 2:**  
   Clasificación de la marca de agua:  
   - Escrito por IA con marca de agua  
   - Escrito por IA sin marca de agua  

⚠️ Solo puedes enviar una respuesta por sesión. ¡Gracias por participar!
""")

# --- Conexión con Google Sheets ---
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet_id = "1Kj3IvIoScc2Bkcs_fxQ8p7gbtFqWr3QCbGO9FvJnWNo"
    sheet = client.open_by_key(sheet_id).sheet1
    return sheet

def guardar_respuesta_en_sheets(respuestas):
    sheet = conectar_google_sheets()
    # Cada fila contiene: session_id, timestamp, texto_id, texto,
    # clasificacion_usuario_ia, clasificacion_real_ia,
    # clasificacion_usuario_watermark, clasificacion_real_watermark
    for r in respuestas:
        fila = [
            r["session_id"],
            r["timestamp"],
            r["texto_id"],
            r["texto"],
            r["clasificacion_usuario_ia"],
            r["clasificacion_real_ia"],
            r["clasificacion_usuario_watermark"],
            r["clasificacion_real_watermark"]
        ]
        sheet.append_row(fila)

# --- Carga de textos con separador personalizado ---
@st.cache_data
def load_texts():
    df = pd.read_csv("Textos.csv", sep="|", encoding="utf-8")
    df = df.dropna(subset=["text"])
    df = df[df["text"].str.strip().str.len() > 0]
    return df

textos_df = load_texts()

# Verificación de que haya suficientes textos válidos
if len(textos_df) < 3:
    st.error("No hay suficientes textos válidos para mostrar. Revisa el archivo.")
    st.stop()

# --- Función para obtener la clasificación real a partir del label ---
def obtener_clasificacion_real(label):
    # Se asume que el label "Humanos" indica un texto escrito por humano.
    # Para los textos generados por IA, se diferencia según si su label contiene la palabra "Boost".
    if label.strip().lower() == "humanos":
        ia = "Escrito por humano"
        watermark = ""
    else:
        ia = "Escrito por IA"
        if "Boost" in label:
            watermark = "Escrito por IA con marca de agua"
        else:
            watermark = "Escrito por IA sin marca de agua"
    return ia, watermark

# --- Inicializar estado de sesión ---
if "muestra" not in st.session_state:
    st.session_state.muestra = textos_df.sample(n=2, random_state=random.randint(0, 10000)).reset_index(drop=True)
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.submitted = False
    st.session_state.respuestas = [None] * len(st.session_state.muestra)

# --- Mostrar formulario mientras no se haya enviado ---
if not st.session_state.submitted:
    st.write("Lee los siguientes textos y responde las dos encuestas por cada uno:")

    for idx, row in st.session_state.muestra.iterrows():
        st.markdown(f"### Texto {idx + 1}")
        st.markdown(f"""
        <div style='padding: 1em; background-color: #1e1e1e; color: white; border-radius: 5px; border: 1px solid #444; font-size: 16px;'>
        {row["text"]}
        </div>
        """, unsafe_allow_html=True)

        # Encuesta 1: IA vs Humano
        respuesta_ia = st.radio(
            "¿Quién crees que ha escrito este texto?",
            options=["Escrito por humano", "Escrito por IA"],
            key=f"respuesta_ia_{idx}"
        )

        # Encuesta 2: Clasificación de marca de agua
        respuesta_watermark = st.radio(
            "Clasificación de la marca de agua:",
            options=["Escrito por IA con marca de agua", "Escrito por IA sin marca de agua"],
            key=f"respuesta_watermark_{idx}"
        )

        # Obtención de las clasificaciones reales a partir del label
        ia_real, watermark_real = obtener_clasificacion_real(row["label"])

        st.session_state.respuestas[idx] = {
            "session_id": st.session_state.session_id,
            "timestamp": datetime.now().isoformat(),
            "texto_id": row["id"],
            "texto": row["text"],
            "clasificacion_usuario_ia": respuesta_ia,
            "clasificacion_real_ia": ia_real,
            "clasificacion_usuario_watermark": respuesta_watermark,
            "clasificacion_real_watermark": watermark_real
        }

    # Botón para enviar respuestas
    if st.button("Enviar respuestas"):
        all_answered = all(
            r is not None and r["clasificacion_usuario_ia"] and r["clasificacion_usuario_watermark"]
            for r in st.session_state.respuestas
        )
        if all_answered:
            guardar_respuesta_en_sheets(st.session_state.respuestas)
            st.session_state.submitted = True
            st.success("✅ ¡Gracias! Tus respuestas han sido registradas.")
        else:
            st.warning("❗Por favor, responde a todas las preguntas de cada texto antes de enviar.")

# --- Mensaje final tras envío ---
if st.session_state.submitted:
    st.markdown("---")
    st.success("🎉 Has completado la encuesta. Gracias por tu participación.")
