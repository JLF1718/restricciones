
import streamlit as st
import pandas as pd
import gspread
from datetime import date
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt

st.set_page_config(page_title="Liberaciones v8.1", layout="centered")
st.title("🔐 Liberaciones conectadas con Google Sheets (via st.secrets)")

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GOOGLE_CREDENTIALS"], scopes=scope)
client = gspread.authorize(credentials)

SHEET_NAME = "Liberaciones_Calidad"
TAB_NAME = "estado"
HEADERS = [
    "Bloque", "Eje", "Nivel",
    "Montaje", "Topografía",
    "Sin soldar", "Soldadas", "Rechazadas", "Liberadas",
    "Reportes de inspección", "Fecha Entrega BAYSA", "Liberó BAYSA",
    "Fecha Recepción INPROS", "Liberó INPROS"
]

st.subheader("🧪 Diagnóstico: hojas de cálculo disponibles")
try:
    all_sheets = client.openall()
    sheet_names = [s.title for s in all_sheets]
    st.write(sheet_names)
    if SHEET_NAME not in sheet_names:
        st.warning(f"⚠️ No se encontró una hoja llamada exactamente: `{SHEET_NAME}`. Verifica el nombre o permisos.")
except Exception as e:
    st.error("❌ Error al listar hojas de cálculo.")
    st.stop()

try:
    sheet = client.open(SHEET_NAME).worksheet(TAB_NAME)
    data = sheet.get_all_values()
    if not data:
        sheet.append_row(HEADERS)
        st.success("✅ Encabezados creados en la hoja.")
    elif data[0] != HEADERS:
        st.warning("⚠️ Los encabezados no coinciden. Revisa manualmente.")
    else:
        st.success("✅ Conexión segura establecida con Google Sheets.")
except Exception as e:
    st.error("❌ Error al conectar con Google Sheets.")
    st.code(str(e), language="bash")
    st.stop()

df = pd.DataFrame(sheet.get_all_records())

def calcular_avance(df):
    df = df.copy()
    for col in ["Sin soldar", "Soldadas", "Rechazadas", "Liberadas"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["Total Juntas"] = df["Sin soldar"] + df["Soldadas"]
    df["Avance Real"] = df["Rechazadas"] + df["Liberadas"]
    df["% Avance"] = df.apply(lambda row: round((row["Avance Real"] / row["Total Juntas"]) * 100, 2)
                              if row["Total Juntas"] > 0 else 0, axis=1)
    return df

def calcular_cumplimiento(row):
    score = sum([
        row.get("Montaje") == "✅",
        row.get("Topografía") == "✅",
        row.get("Reportes de inspección") == "✅"
    ])
    return round((score / 3) * 100, 2)

st.subheader("➕ Nuevo Registro")
with st.form("formulario"):
    col1, col2, col3 = st.columns(3)
    bloque = col1.text_input("Bloque")
    eje = col2.text_input("Eje")
    nivel = col3.text_input("Nivel")

    opciones_estado = ["🅿️", "✅", "❌"]
    col4, col5 = st.columns(2)
    montaje = col4.selectbox("Montaje", opciones_estado)
    topografia = col4.selectbox("Topografía", opciones_estado)
    baysa_libero = col4.selectbox("Liberó BAYSA", opciones_estado)
    inspeccion = col5.selectbox("Reportes de inspección", opciones_estado)
    inpros_libero = col5.selectbox("Liberó INPROS", opciones_estado)

    col6, col7 = st.columns(2)
    sin_soldar = col6.number_input("Sin soldar", min_value=0)
    soldadas = col6.number_input("Soldadas", min_value=0)
    rechazadas = col7.number_input("Rechazadas", min_value=0)
    liberadas = col7.number_input("Liberadas", min_value=0)

    col8, col9 = st.columns(2)
    fecha_baysa = col8.date_input("Fecha Entrega BAYSA", value=date.today())
    fecha_inpros = col9.date_input("Fecha Recepción INPROS", value=date.today())

    enviado = st.form_submit_button("Guardar en Google Sheets")
    if enviado:
        fila = [
            bloque, eje, nivel,
            montaje, topografia,
            int(sin_soldar), int(soldadas), int(rechazadas), int(liberadas),
            inspeccion, str(fecha_baysa), baysa_libero, str(fecha_inpros), inpros_libero
        ]
        sheet.append_row(fila)
        st.success("✅ Registro agregado a Google Sheets.")
        st.rerun()

st.subheader("📋 Tabla de registros")
df = calcular_avance(df)
df["% Cumplimiento"] = df.apply(calcular_cumplimiento, axis=1)
st.dataframe(df)

st.subheader("📊 Cumplimiento por bloque")
if not df.empty:
    resumen = df.groupby("Bloque")["% Cumplimiento"].mean().round(2)
    fig, ax = plt.subplots()
    resumen.plot(kind="bar", ax=ax)
    ax.set_ylabel("% Cumplimiento")
    ax.set_title("Resumen por Bloque")
    st.pyplot(fig)
