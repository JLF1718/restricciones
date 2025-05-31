import streamlit as st
import pandas as pd
import gspread
from datetime import date
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt

st.set_page_config(page_title="Liberaciones v12", layout="wide")
st.title("🔐 Liberaciones - Visual Mejorada + Sin inspección")

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
except Exception as e:
    st.error("❌ No se pudo acceder a la hoja.")
    st.code(str(e), language="bash")
    st.stop()

df = pd.DataFrame(sheet.get_all_records())

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
    fig, ax = plt.subplots()
    colors = plt.cm.Blues([0.4 + 0.15 * i for i in range(len(resumen))])
    resumen.plot(kind="bar", ax=ax, color=colors, edgecolor='none')
    ax.set_ylabel("% Cumplimiento")
    ax.set_title("Resumen por Bloque")
    for spine in ax.spines.values():
        spine.set_visible(False)
    plt.xticks(rotation=0)
    plt.tight_layout()
    st.pyplot(fig)
