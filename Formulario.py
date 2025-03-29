import streamlit as st
import pandas as pd
import random
import uuid
from datetime import datetime
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

st.set_page_config(page_title="Clasificación de textos", layout="wide")
st.title("📝 Clasifica los textos: ¿Humano o IA con marca de agua?")

# def conectar_google_sheets():
#     scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
#     creds_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])
#     creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
#     client = gspread.authorize(creds)
#     sheet = client.open("Respuestas_Formulario_TFM").sheet1
#     return sheet

def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    # Conexión directa usando el ID del documento
    sheet_id = "1Kj3IvIoScc2Bkcs_fxQ8p7gbtFqWr3QCbGO9FvJnWNo"
    sheet = client.open_by_key(sheet_id).sheet1
    return sheet


def guardar_respuesta_en_sheets(respuestas):
    sheet = conectar_google_sheets()
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

textos_df = load_texts()

# --- Verificación de que haya suficientes textos disponibles ---
if len(textos_df) < 3:
    st.error("No hay suficientes textos válidos para mostrar. Revisa el archivo.")
    st.stop()

# --- Inicializar estado de sesión ---
if "muestra" not in st.session_state:
    st.session_state.muestra = textos_df.sample(n=3, random_state=random.randint(0, 10000)).reset_index(drop=True)
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.submitted = False
    st.session_state.respuestas = [None, None, None]

# --- Mostrar formulario solo si no se ha enviado ---
if not st.session_state.submitted:
    st.write("Lee los siguientes textos y clasifícalos según tu criterio:")

    for idx, row in st.session_state.muestra.iterrows():
        st.markdown(f"### Texto {idx + 1}")
        st.text_area("Contenido:", value=row["text"], height=200, key=f"texto_{idx}", disabled=True)

        respuesta = st.radio(
            "¿Quién crees que ha escrito este texto?",
            options=["Escrito por humano", "Escrito por IA", "Escrito por IA con marca de agua"],
            key=f"respuesta_{idx}",
            index=None
        )

        st.session_state.respuestas[idx] = {
            "session_id": st.session_state.session_id,
            "timestamp": datetime.now().isoformat(),
            "texto_id": row["id"],
            "texto": row["text"],
            "clasificacion_usuario": respuesta,
            "clasificacion_real": row["label"]
        }

    # Botón para enviar
    if st.button("Enviar respuestas"):
        if all(resp and resp["clasificacion_usuario"] for resp in st.session_state.respuestas):
            guardar_respuesta_en_sheets(st.session_state.respuestas)
            st.session_state.submitted = True
            st.success("✅ ¡Gracias! Tus respuestas han sido registradas.")
        else:
            st.warning("❗Por favor, responde a los tres textos antes de enviar.")

# --- Mensaje final si ya respondió ---
if st.session_state.submitted:
    st.markdown("---")
    st.success("🎉 Has completado la encuesta. Gracias por tu participación.")
