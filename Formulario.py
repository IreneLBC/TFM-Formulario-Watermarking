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
A continuación, se te presentarán **dos textos** y tu tarea será clasificarlos.

**Paso 1:** Indica quién crees que ha escrito el texto:
- **Escrito por humano**
- **Escrito por IA**

**Paso 2:** Si seleccionas **Escrito por IA**, se desplegará una segunda pregunta para especificar:
- **Escrito por IA con marca de agua**
- **Escrito por IA sin marca de agua**

Una **marca de agua** en este contexto es una modificación sutil introducida en los textos generados por modelos de lenguaje. Esta modificación permite identificar posteriormente si un texto fue producido por una IA y, en ese caso, si posee dicha marca. Los cambios pueden manifestarse en la elección de palabras, la estructura o la puntuación, sin alterar significativamente el contenido original.

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
    # Se guarda: session_id, timestamp, texto_id, texto, respuesta del usuario y la clasificación real
    for r in respuestas:
        fila = [
            r["session_id"],
            r["timestamp"],
            r["texto_id"],
            r["texto"],
            r["clasificacion_usuario"],
            r["clasificacion_real"],
            ""
        ]
        sheet.append_row(fila)

# --- Carga de textos con separador personalizado ---
@st.cache_data
def load_texts():
    df = pd.read_csv("Textos.csv", sep="|", encoding="utf-8")
    df = df.dropna(subset=["text"])
    df = df[df["text"].str.strip().str.len() > 0]
    return df

def obtener_clasificacion_real(label):
    # Se asume que en el data set el label "Humanos" indica un texto escrito por humano.
    # Para los textos generados por IA, si en el label aparece la palabra "Boost" se entiende que tienen marca de agua.
    if label.strip().lower() == "humanos":
        return "Escrito por humano"
    else:
        if "Boost" in label:
            return "Escrito por IA con marca de agua"
        else:
            return "Escrito por IA sin marca de agua"

textos_df = load_texts()

if len(textos_df) < 3:
    st.error("No hay suficientes textos válidos para mostrar. Revisa el archivo.")
    st.stop()

# --- Inicializar estado de sesión ---
if "muestra" not in st.session_state:
    st.session_state.muestra = textos_df.sample(n=2, random_state=random.randint(0, 10000)).reset_index(drop=True)
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.submitted = False
    st.session_state.respuestas = [None, None]

if not st.session_state.submitted:
    st.write("Lee los siguientes textos y responde las preguntas:")

    for idx, row in st.session_state.muestra.iterrows():
        st.markdown(f"### Texto {idx + 1}")
        st.markdown(f"""
        <div style='padding: 1em; background-color: #1e1e1e; color: white; border-radius: 5px; border: 1px solid #444; font-size: 16px;'>
        {row["text"]}
        </div>
        """, unsafe_allow_html=True)

        # Primer pregunta: IA vs Humano
        resp1 = st.radio(
            "¿Quién crees que ha escrito este texto?",
            options=["Escrito por humano", "Escrito por IA"],
            key=f"resp1_{idx}"
        )
        
        # Si el usuario vota "Escrito por IA", mostrar la segunda pregunta para especificar la marca de agua.
        if resp1 == "Escrito por IA":
            resp2 = st.radio(
                "Has seleccionado 'Escrito por IA'. Por favor, especifica:",
                options=["Escrito por IA con marca de agua", "Escrito por IA sin marca de agua"],
                key=f"resp2_{idx}"
            )
            final_resp = resp2
        else:
            final_resp = resp1

        st.session_state.respuestas[idx] = {
            "session_id": st.session_state.session_id,
            "timestamp": datetime.now().isoformat(),
            "texto_id": row["id"],
            "texto": row["text"],
            "clasificacion_usuario": final_resp,
            "clasificacion_real": obtener_clasificacion_real(row["label"])
        }

    if st.button("Enviar respuestas"):
        # Verificar que se haya respondido la primera pregunta y, en caso de seleccionar IA, que se haya respondido la segunda
        all_answered = True
        for r in st.session_state.respuestas:
            if r["clasificacion_usuario"] is None:
                all_answered = False
                break
        if all_answered:
            guardar_respuesta_en_sheets(st.session_state.respuestas)
            st.session_state.submitted = True
            st.success("✅ ¡Gracias! Tus respuestas han sido registradas.")
        else:
            st.warning("❗Por favor, responde a todas las preguntas antes de enviar.")

if st.session_state.submitted:
    st.markdown("---")
    st.success("🎉 Has completado la encuesta. Gracias por tu participación.")
