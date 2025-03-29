import streamlit as st
import pandas as pd
import random
import uuid
import os
from datetime import datetime

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Clasificación de textos", layout="wide")
st.title("📝 Clasifica los textos: ¿Humano o IA con marca de agua?")

# --- CARGA Y LIMPIEZA DE TEXTOS ---
@st.cache_data
def load_texts():
    df = pd.read_csv("Textos.csv", sep="|", quotechar='"', engine="python", encoding="utf-8")
    df = df.dropna(subset=["text"])
    df = df[df["text"].str.strip().str.len() > 0]
    return df

textos_df = load_texts()

# --- COMPROBACIÓN DE DISPONIBILIDAD ---
if len(textos_df) < 3:
    st.error("No hay suficientes textos válidos para mostrar. Revisa el archivo Textos.csv.")
    st.stop()

# --- SELECCIÓN DE MUESTRA ALEATORIA ---
muestra = textos_df.sample(n=3, random_state=random.randint(0, 10000)).reset_index(drop=True)

# Identificador único de usuario/sesión
session_id = str(uuid.uuid4())

# --- FORMULARIO DE CLASIFICACIÓN ---
respuestas = []

st.write("Lee los siguientes textos y clasifícalos según tu criterio:")

for idx, row in muestra.iterrows():
    st.markdown(f"### Texto {idx + 1}")
    st.text_area("Contenido:", value=row["text"], height=200, key=f"texto_{idx}", disabled=True)

    respuesta = st.radio(
        "¿Quién crees que ha escrito este texto?",
        options=["Escrito por humano", "Escrito por IA", "Escrito por IA con marca de agua"],
        key=f"respuesta_{idx}",
        index=None
    )

    respuestas.append({
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "texto_id": row["id"],
        "texto": row["text"],
        "clasificacion_usuario": respuesta,
        "clasificacion_real": row["label"]
    })

# --- BOTÓN PARA GUARDAR RESPUESTAS ---
if st.button("Enviar respuestas"):
    if all(r["clasificacion_usuario"] for r in respuestas):
        respuestas_df = pd.DataFrame(respuestas)
        
        # Si el fichero ya existe, añadir; si no, crear nuevo
        resultado_path = "respuestas.csv"
        if os.path.exists(resultado_path):
            respuestas_df.to_csv(resultado_path, mode='a', index=False, header=False)
        else:
            respuestas_df.to_csv(resultado_path, index=False)

        st.success("✅ ¡Gracias! Tus respuestas han sido registradas.")
    else:
        st.warning("❗Por favor, clasifica los tres textos antes de enviar.")
