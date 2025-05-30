
import streamlit as st
import pandas as pd
from datetime import date
import os
import matplotlib.pyplot as plt

st.set_page_config(page_title="Liberaciones Avanzadas", layout="centered")
st.title("📋 Registro y Gestión de Liberaciones (v4)")

csv_file = "estado.csv"

# Leer CSV o crear vacío
if os.path.exists(csv_file):
    df = pd.read_csv(csv_file)
else:
    df = pd.DataFrame(columns=[
        "Bloque", "Eje", "Nivel",
        "Montaje", "Topografía",
        "Sin soldar", "Soldadas", "Rechazadas", "Liberadas",
        "Reportes de inspección", "Fecha Entrega BAYSA", "Liberó BAYSA",
        "Fecha Recepción INPROS", "Liberó INPROS"
    ])

# === FUNCIONES ===
def calcular_avance(df):
    df = df.copy()
    df["Total Juntas"] = df["Sin soldar"] + df["Soldadas"]
    df["Avance Real"] = df["Rechazadas"] + df["Liberadas"]
    df["% Avance"] = df.apply(
        lambda row: round((row["Avance Real"] / row["Total Juntas"]) * 100, 2)
        if row["Total Juntas"] > 0 else 0, axis=1)
    return df

# === AGREGAR / EDITAR FILA ===
st.subheader("🆕 Agregar o Editar Fila")
modo = st.radio("¿Qué deseas hacer?", ["Agregar nueva fila", "Editar fila existente"])

if modo == "Editar fila existente" and not df.empty:
    idx = st.selectbox("Selecciona índice de fila a editar", options=df.index)
    fila = df.loc[idx]
else:
    fila = pd.Series(dtype=object)

with st.form("formulario"):
    col1, col2, col3 = st.columns(3)
    bloque = col1.text_input("Bloque", value=fila.get("Bloque", ""))
    eje = col2.text_input("Eje", value=fila.get("Eje", ""))
    nivel = col3.text_input("Nivel", value=fila.get("Nivel", ""))

    opciones_estado = ["🅿️", "✅", "❌"]
    col4, col5 = st.columns(2)
    montaje = col4.selectbox("Montaje", opciones_estado, index=opciones_estado.index(fila.get("Montaje", "🅿️")) if "Montaje" in fila else 0)
    topografia = col4.selectbox("Topografía", opciones_estado, index=opciones_estado.index(fila.get("Topografía", "🅿️")) if "Topografía" in fila else 0)
    baysa_libero = col4.selectbox("Liberó BAYSA", opciones_estado, index=opciones_estado.index(fila.get("Liberó BAYSA", "🅿️")) if "Liberó BAYSA" in fila else 0)
    inspeccion = col5.selectbox("Reportes de inspección", opciones_estado, index=opciones_estado.index(fila.get("Reportes de inspección", "🅿️")) if "Reportes de inspección" in fila else 0)
    inpros_libero = col5.selectbox("Liberó INPROS", opciones_estado, index=opciones_estado.index(fila.get("Liberó INPROS", "🅿️")) if "Liberó INPROS" in fila else 0)

    col6, col7 = st.columns(2)
    sin_soldar = col6.number_input("Sin soldar", min_value=0, value=int(fila.get("Sin soldar", 0)))
    soldadas = col6.number_input("Soldadas", min_value=0, value=int(fila.get("Soldadas", 0)))
    rechazadas = col7.number_input("Rechazadas", min_value=0, value=int(fila.get("Rechazadas", 0)))
    liberadas = col7.number_input("Liberadas", min_value=0, value=int(fila.get("Liberadas", 0)))

    col8, col9 = st.columns(2)
    fecha_baysa = col8.date_input("Fecha Entrega BAYSA", value=pd.to_datetime(fila.get("Fecha Entrega BAYSA", date.today())))
    fecha_inpros = col9.date_input("Fecha Recepción INPROS", value=pd.to_datetime(fila.get("Fecha Recepción INPROS", date.today())))

    enviado = st.form_submit_button("Guardar")

    if enviado:
        nueva = {
            "Bloque": bloque, "Eje": eje, "Nivel": nivel,
            "Montaje": montaje, "Topografía": topografia,
            "Sin soldar": sin_soldar, "Soldadas": soldadas,
            "Rechazadas": rechazadas, "Liberadas": liberadas,
            "Reportes de inspección": inspeccion,
            "Fecha Entrega BAYSA": fecha_baysa,
            "Liberó BAYSA": baysa_libero,
            "Fecha Recepción INPROS": fecha_inpros,
            "Liberó INPROS": inpros_libero
        }
        if modo == "Editar fila existente":
            df.loc[idx] = nueva
            st.success(f"✅ Fila {idx} editada correctamente.")
        else:
            df = pd.concat([df, pd.DataFrame([nueva])], ignore_index=True)
            st.success("✅ Fila agregada correctamente.")
        df.to_csv(csv_file, index=False)
        st.rerun()

# === ELIMINAR ===
st.subheader("🗑️ Eliminar fila por índice")
if not df.empty:
    index_to_delete = st.number_input("Índice a eliminar", min_value=0, max_value=len(df)-1)
    if st.button("Eliminar fila"):
        df = df.drop(index=index_to_delete).reset_index(drop=True)
        df.to_csv(csv_file, index=False)
        st.success("✅ Fila eliminada.")
        st.rerun()
else:
    st.info("Sin filas para eliminar.")

# === APLICAR CÁLCULO Y MOSTRAR TABLA ===
df = calcular_avance(df)

st.subheader("🔍 Filtrar por columnas")
filtro_bloque = st.multiselect("Bloque", options=df["Bloque"].dropna().unique())
filtro_estado = st.multiselect("Montaje", options=["✅", "❌", "🅿️"])

df_filtrado = df.copy()
if filtro_bloque:
    df_filtrado = df_filtrado[df_filtrado["Bloque"].isin(filtro_bloque)]
if filtro_estado:
    df_filtrado = df_filtrado[df_filtrado["Montaje"].isin(filtro_estado)]

st.dataframe(df_filtrado, use_container_width=True)

# === RESUMEN VISUAL ===
st.subheader("📊 Resumen visual de Montaje")
conteo = df["Montaje"].value_counts().reindex(["✅", "❌", "🅿️"], fill_value=0)
fig, ax = plt.subplots()
ax.bar(conteo.index, conteo.values)
st.pyplot(fig)

# === DESCARGA CSV ===
csv = df.to_csv(index=False).encode("utf-8")
st.download_button("📥 Descargar CSV", data=csv, file_name="estado.csv", mime="text/csv")
