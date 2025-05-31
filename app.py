import streamlit as st
import pandas as pd
import gspread
from datetime import date
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(page_title="Liberaciones v13.4", layout="centered")
st.title("🔐 Liberaciones - Sin inspección visible y validaciones")

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GOOGLE_CREDENTIALS"], scopes=scope)
client = gspread.authorize(credentials)

SHEET_NAME = "Liberaciones_Calidad"
TAB_NAME = "estado"
HEADERS = [
    "Bloque", "Eje", "Nivel",
    "Montaje", "Topografía",
    "Sin soldar", "Soldadas", "Sin inspección", "Rechazadas", "Liberadas",
    "Reportes de inspección", "Fecha Entrega BAYSA", "Liberó BAYSA",
    "Fecha Recepción INPROS", "Liberó INPROS",
    "Total Juntas", "Avance Real", "% Avance", "% Cumplimiento"
]

try:
    sheet = client.open(SHEET_NAME).worksheet(TAB_NAME)
    spreadsheet = client.open(SHEET_NAME)
    sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet.id}"
    st.markdown(f"🔗 [Abrir hoja en Google Sheets]({sheet_url})")

    encabezados_actuales = sheet.row_values(1)
    if encabezados_actuales != HEADERS:
        sheet.delete_rows(1)
        sheet.insert_row(HEADERS, 1)
        st.info("ℹ️ Encabezados actualizados automáticamente.")
except Exception as e:
    st.error("❌ No se pudo acceder a la hoja.")
    st.code(str(e), language="bash")
    st.stop()

df = pd.DataFrame(sheet.get_all_records())

# ------------------ FORMULARIO --------------------
st.subheader("➕ Nuevo Registro")
with st.form("formulario"):
    st.markdown("### 📌 Identificación")
    col1, col2, col3 = st.columns(3)
    bloque = col1.text_input("Bloque")
    eje = col2.text_input("Eje")
    nivel = col3.text_input("Nivel")

    st.markdown("### 🧱 Estado General")
    opciones_estado = ["🅿️", "✅", "❌"]
    col4, col5 = st.columns(2)
    montaje = col4.selectbox("Montaje", opciones_estado)
    topografia = col4.selectbox("Topografía", opciones_estado)
    baysa_libero = col4.selectbox("Liberó BAYSA", opciones_estado)
    inspeccion = col5.selectbox("Reportes de inspección", opciones_estado)
    inpros_libero = col5.selectbox("Liberó INPROS", opciones_estado)

    st.markdown("### 🔢 Progreso numérico")
    sin_soldar = st.number_input("Sin soldar", min_value=0)
    soldadas = st.number_input("Soldadas", min_value=0)
    sin_inspeccion = st.number_input("Sin inspección", min_value=0)
    rechazadas = st.number_input("Rechazadas", min_value=0)
    liberadas = st.number_input("Liberadas", min_value=0)

    st.markdown("### 📅 Fechas")
    col8, col9 = st.columns(2)
    fecha_baysa = col8.date_input("Fecha Entrega BAYSA", value=date.today())
    fecha_inpros = col9.date_input("Fecha Recepción INPROS", value=date.today())

    enviado = st.form_submit_button("Guardar en Google Sheets")
    if enviado:
        errores = []

        if soldadas != rechazadas + liberadas + sin_inspeccion:
            errores.append("❌ Soldadas debe ser igual a Rechazadas + Liberadas + Sin inspección.")
        if fecha_baysa > fecha_inpros:
            errores.append("❌ La Fecha de Entrega BAYSA no puede ser posterior a la de Recepción INPROS.")

        if errores:
            for e in errores:
                st.error(e)
        else:
            fila = [
                bloque, eje, nivel,
                montaje, topografia,
                int(sin_soldar), int(soldadas), int(sin_inspeccion), int(rechazadas), int(liberadas),
                inspeccion, str(fecha_baysa), baysa_libero, str(fecha_inpros), inpros_libero,
                "", "", "", ""
            ]
            if len(fila) == len(HEADERS):
                sheet.append_row(fila)
                st.success("✅ Registro agregado correctamente.")
                st.rerun()
            else:
                st.error("❌ La fila no coincide con la cantidad esperada de columnas.")

# ------------------ CÁLCULOS Y VISUAL --------------------
def calcular_avance(df):
    df = df.copy()
    for col in ["Sin soldar", "Soldadas", "Sin inspección", "Rechazadas", "Liberadas"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["Total Juntas"] = df["Sin soldar"] + df["Soldadas"]
    df["Avance Real"] = df["Rechazadas"] + df["Liberadas"]
    df["% Avance"] = df.apply(
        lambda row: round((row["Avance Real"] / row["Total Juntas"]) * 100, 2)
        if row["Total Juntas"] > 0 else 0, axis=1
    )
    return df

def calcular_cumplimiento(row):
    score = sum([
        row.get("Montaje") == "✅",
        row.get("Topografía") == "✅",
        row.get("Reportes de inspección") == "✅"
    ])
    return round((score / 3) * 100, 2)

if not df.empty:
    df = calcular_avance(df)
    df["% Cumplimiento"] = df.apply(calcular_cumplimiento, axis=1)

st.subheader("📋 Registros")
st.dataframe(df)

st.subheader("📊 Cumplimiento por bloque")
if not df.empty:
    resumen = df.groupby("Bloque")["% Cumplimiento"].mean().round(2)
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = plt.cm.Blues(np.linspace(0.5, 1, len(resumen)))
    resumen.plot(kind="bar", ax=ax, color=colors, edgecolor='none')
    ax.set_ylabel("% Cumplimiento")
    ax.set_title("Resumen por Bloque")
    ax.set_facecolor("white")
    ax.grid(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(True)
    for i, val in enumerate(resumen):
        ax.text(i, val + 1, f"{val:.1f}%", ha='center', va='bottom', fontsize=10)
    plt.xticks(rotation=0)
    plt.tight_layout()
    st.pyplot(fig)
