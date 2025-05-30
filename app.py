import streamlit as st
import pandas as pd
from datetime import date
import os

st.set_page_config(page_title="Formulario de Liberación", layout="centered")
st.title("📋 Formulario de Liberación de Elementos")

csv_file = "estado.csv"

# Leer estado previo si existe
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

# Formulario
with st.form("formulario"):
    st.subheader("📝 Datos del elemento")
    col1, col2, col3 = st.columns(3)
    with col1:
        bloque = st.text_input("Bloque")
    with col2:
        eje = st.text_input("Eje")
    with col3:
        nivel = st.text_input("Nivel")

    st.subheader("📌 Estado general")
    col4, col5 = st.columns(2)
    with col4:
        montaje = st.selectbox("Montaje", ["✅", "❌"])
        topografia = st.selectbox("Topografía", ["✅", "❌"])
        baysa_libero = st.selectbox("Liberó BAYSA", ["✅", "❌"])
    with col5:
        inspeccion = st.selectbox("Reportes de inspección", ["✅", "❌"])
        inpros_libero = st.selectbox("Liberó INPROS", ["✅", "❌"])

    st.subheader("🔢 Estado de soldadura")
    col6, col7 = st.columns(2)
    with col6:
        sin_soldar = st.number_input("Sin soldar", min_value=0)
        soldadas = st.number_input("Soldadas", min_value=0)
    with col7:
        rechazadas = st.number_input("Rechazadas", min_value=0)
        liberadas = st.number_input("Liberadas", min_value=0)

    st.subheader("📅 Fechas")
    col8, col9 = st.columns(2)
    with col8:
        fecha_baysa = st.date_input("Fecha Entrega BAYSA", value=date.today())
    with col9:
        fecha_inpros = st.date_input("Fecha Recepción INPROS", value=date.today())

    # Botón enviar
    enviado = st.form_submit_button("Agregar fila")

    if enviado:
        nueva_fila = {
            "Bloque": bloque,
            "Eje": eje,
            "Nivel": nivel,
            "Montaje": montaje,
            "Topografía": topografia,
            "Sin soldar": sin_soldar,
            "Soldadas": soldadas,
            "Rechazadas": rechazadas,
            "Liberadas": liberadas,
            "Reportes de inspección": inspeccion,
            "Fecha Entrega BAYSA": fecha_baysa,
            "Liberó BAYSA": baysa_libero,
            "Fecha Recepción INPROS": fecha_inpros,
            "Liberó INPROS": inpros_libero
        }
        df = pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True)
        df.to_csv(csv_file, index=False)
        st.success("✅ Fila agregada correctamente.")
        st.rerun()
st.subheader("🗑️ Eliminar fila por índice")

if not df.empty:
    st.write("Tabla actual con índices:")
    st.dataframe(df.reset_index())

    index_to_delete = st.number_input("Ingrese el índice de la fila a eliminar", min_value=0, max_value=len(df)-1, step=1)

    if st.button("Eliminar fila"):
        df = df.drop(index=index_to_delete).reset_index(drop=True)
        df.to_csv(csv_file, index=False)
        st.success(f"✅ Fila {index_to_delete} eliminada correctamente.")
        st.rerun()
else:
    st.info("No hay datos para eliminar.")

# Mostrar tabla actual
st.subheader("📊 Tabla actual")
st.dataframe(df)

# Descargar
csv = df.to_csv(index=False).encode("utf-8")
st.download_button("📥 Descargar CSV", data=csv, file_name="estado.csv", mime="text/csv")
