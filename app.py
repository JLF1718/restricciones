
import streamlit as st
import pandas as pd
import gspread
from datetime import date
from google.oauth2.service_account import Credentials

# Configuración de la página
st.set_page_config(page_title="Liberaciones v6 - Google Sheets", layout="centered")
st.title("🔗 Liberaciones con conexión a Google Sheets")

# Autenticación con Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_file("credentials.json", scopes=scope)
client = gspread.authorize(credentials)

# Conectarse al Google Sheet
sheet_name = "Liberaciones_Calidad"
try:
    sheet = client.open(sheet_name).worksheet("estado")
except:
    st.error(f"No se encontró la hoja '{sheet_name}' o la pestaña 'estado'. Verifica permisos y nombre.")
    st.stop()

# Obtener datos como DataFrame
data = sheet.get_all_records()
df = pd.DataFrame(data)

# Si está vacío, crear columnas base
if df.empty:
    df = pd.DataFrame(columns=[
        "Bloque", "Eje", "Nivel",
        "Montaje", "Topografía",
        "Sin soldar", "Soldadas", "Rechazadas", "Liberadas",
        "Reportes de inspección", "Fecha Entrega BAYSA", "Liberó BAYSA",
        "Fecha Recepción INPROS", "Liberó INPROS"
    ])

# Funciones de cálculo
def calcular_avance(df):
    df = df.copy()
    df["Sin soldar"] = pd.to_numeric(df["Sin soldar"], errors="coerce").fillna(0)
    df["Soldadas"] = pd.to_numeric(df["Soldadas"], errors="coerce").fillna(0)
    df["Rechazadas"] = pd.to_numeric(df["Rechazadas"], errors="coerce").fillna(0)
    df["Liberadas"] = pd.to_numeric(df["Liberadas"], errors="coerce").fillna(0)

    df["Total Juntas"] = df["Sin soldar"] + df["Soldadas"]
    df["Avance Real"] = df["Rechazadas"] + df["Liberadas"]
    df["% Avance"] = df.apply(
        lambda row: round((row["Avance Real"] / row["Total Juntas"]) * 100, 2)
        if row["Total Juntas"] > 0 else 0, axis=1)
    return df

def calcular_cumplimiento(row):
    score = sum([
        row.get("Montaje") == "✅",
        row.get("Topografía") == "✅",
        row.get("Reportes de inspección") == "✅"
    ])
    return round((score / 3) * 100, 2)

# Agregar nuevo registro
st.subheader("📝 Nuevo registro")

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
        nueva_fila = [
            bloque, eje, nivel,
            montaje, topografia,
            int(sin_soldar), int(soldadas), int(rechazadas), int(liberadas),
            inspeccion, str(fecha_baysa), baysa_libero, str(fecha_inpros), inpros_libero
        ]
        sheet.append_row(nueva_fila)
        st.success("✅ Registro guardado en Google Sheets.")
        st.rerun()

# Mostrar tabla
st.subheader("📋 Datos actuales")
df = calcular_avance(df)
df["% Cumplimiento"] = df.apply(calcular_cumplimiento, axis=1)
st.dataframe(df)

# Gráfico de cumplimiento por bloque
st.subheader("📊 Cumplimiento por Bloque")
if not df.empty and "Bloque" in df.columns:
    resumen = df.groupby("Bloque")["% Cumplimiento"].mean().round(2)
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    resumen.plot(kind="bar", ax=ax)
    ax.set_ylabel("% Cumplimiento")
    ax.set_title("Cumplimiento por Bloque")
    st.pyplot(fig)
