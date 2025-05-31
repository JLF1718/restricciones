import streamlit as st
import pandas as pd
import gspread
from datetime import date
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt

st.set_page_config(page_title="Liberaciones v11", layout="wide")
st.title("🔐 Liberaciones con filtros y edición")

# Autenticación
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
    "Fecha Recepción INPROS", "Liberó INPROS",
    "Total Juntas", "Avance Real", "% Avance", "% Cumplimiento"
]

# Conectar hoja
try:
    sheet = client.open(SHEET_NAME).worksheet(TAB_NAME)
    spreadsheet = client.open(SHEET_NAME)
    sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet.id}"
    st.markdown(f"🔗 [Abrir hoja en Google Sheets]({sheet_url})")
except Exception as e:
    st.error("❌ No se pudo acceder a la hoja.")
    st.code(str(e), language="bash")
    st.stop()

df = pd.DataFrame(sheet.get_all_records())

# Cálculos
def calcular_avance(df):
    df = df.copy()
    for col in ["Sin soldar", "Soldadas", "Rechazadas", "Liberadas"]:
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

# Aplicar cálculos
if not df.empty:
    df = calcular_avance(df)
    df["% Cumplimiento"] = df.apply(calcular_cumplimiento, axis=1)

# Filtros
st.sidebar.header("🔎 Filtros")
filtro_bloque = st.sidebar.multiselect("Filtrar por Bloque", options=sorted(df["Bloque"].unique()), default=None)
min_avance = st.sidebar.slider("Mínimo % Avance", 0, 100, 0)

df_filtrado = df.copy()
if filtro_bloque:
    df_filtrado = df_filtrado[df_filtrado["Bloque"].isin(filtro_bloque)]
df_filtrado = df_filtrado[df_filtrado["% Avance"] >= min_avance]

# Mostrar tabla
st.subheader("📋 Registros filtrados")
st.dataframe(df_filtrado)

# Gráfico
if not df_filtrado.empty:
    resumen = df_filtrado.groupby("Bloque")["% Cumplimiento"].mean().round(2)
    fig, ax = plt.subplots()
    resumen.plot(kind="bar", ax=ax)
    ax.set_ylabel("% Cumplimiento")
    ax.set_title("Resumen por Bloque")
    st.pyplot(fig)

# Editor de registros
st.subheader("✏️ Editar un registro existente")
if not df.empty:
    idx = st.selectbox("Selecciona el índice de fila", df.index)
    registro = df.loc[idx]

    with st.form("editor"):
        col1, col2, col3 = st.columns(3)
        bloque = col1.text_input("Bloque", value=str(registro["Bloque"]))
        eje = col2.text_input("Eje", value=str(registro["Eje"]))
        nivel = col3.text_input("Nivel", value=str(registro["Nivel"]))

        opciones_estado = ["🅿️", "✅", "❌"]
        col4, col5 = st.columns(2)
        montaje = col4.selectbox("Montaje", opciones_estado, index=opciones_estado.index(registro["Montaje"]))
        topografia = col4.selectbox("Topografía", opciones_estado, index=opciones_estado.index(registro["Topografía"]))
        baysa_libero = col4.selectbox("Liberó BAYSA", opciones_estado, index=opciones_estado.index(registro["Liberó BAYSA"]))
        inspeccion = col5.selectbox("Reportes de inspección", opciones_estado, index=opciones_estado.index(registro["Reportes de inspección"]))
        inpros_libero = col5.selectbox("Liberó INPROS", opciones_estado, index=opciones_estado.index(registro["Liberó INPROS"]))

        col6, col7 = st.columns(2)
        sin_soldar = col6.number_input("Sin soldar", min_value=0, value=int(registro["Sin soldar"]))
        soldadas = col6.number_input("Soldadas", min_value=0, value=int(registro["Soldadas"]))
        rechazadas = col7.number_input("Rechazadas", min_value=0, value=int(registro["Rechazadas"]))
        liberadas = col7.number_input("Liberadas", min_value=0, value=int(registro["Liberadas"]))

        col8, col9 = st.columns(2)
        fecha_baysa = col8.date_input("Fecha Entrega BAYSA", value=pd.to_datetime(registro["Fecha Entrega BAYSA"]))
        fecha_inpros = col9.date_input("Fecha Recepción INPROS", value=pd.to_datetime(registro["Fecha Recepción INPROS"]))

        guardar = st.form_submit_button("💾 Guardar cambios")
        if guardar:
            total_juntas = int(sin_soldar) + int(soldadas)
            avance_real = int(rechazadas) + int(liberadas)
            porcentaje_avance = round((avance_real / total_juntas) * 100, 2) if total_juntas > 0 else 0
            score = sum([
                montaje == "✅",
                topografia == "✅",
                inspeccion == "✅"
            ])
            porcentaje_cumplimiento = round((score / 3) * 100, 2)

            nueva_fila = [
                bloque, eje, nivel, montaje, topografia,
                int(sin_soldar), int(soldadas), int(rechazadas), int(liberadas),
                inspeccion, str(fecha_baysa), baysa_libero, str(fecha_inpros), inpros_libero,
                total_juntas, avance_real, porcentaje_avance, porcentaje_cumplimiento
            ]

            sheet.delete_rows(idx + 2)  # +2: header + 0-based idx
            sheet.insert_row(nueva_fila, idx + 2)
            st.success("✅ Fila actualizada correctamente.")
            st.rerun()
