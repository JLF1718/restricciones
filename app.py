import streamlit as st
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import os

st.subheader("➕ Agregar nueva tarea")

with st.form("agregar_tarea"):
    nueva_tarea = st.text_input("Descripción de la nueva tarea")
    submitted = st.form_submit_button("Agregar")

    if submitted and nueva_tarea.strip() != "":
        # Leer archivo existente
        df = pd.read_csv("estado.csv") if os.path.exists("estado.csv") else pd.DataFrame(columns=["Tarea", "Completado", "Marca de Tiempo"])
        
        # Verificar que no exista ya
        if nueva_tarea in df["Tarea"].values:
            st.warning("⚠️ Esa tarea ya existe.")
        else:
            nueva_fila = pd.DataFrame([{
                "Tarea": nueva_tarea.strip(),
                "Completado": False,
                "Marca de Tiempo": ""
            }])
            df = pd.concat([df, nueva_fila], ignore_index=True)
            df.to_csv("estado.csv", index=False)
            st.success("✅ Tarea agregada correctamente.")
            st.experimental_rerun()  # Recargar app

# === TAREAS PRECARGADAS ===
tareas = [
    '1.1 – Planos de montaje',
    '1.2 – Planos de taller',
    '2.1 - Matriz de Soldadores',
    '2.2 - Verificación de Parámetros de Soldadura',
    '3.1 - Reporte de Montaje',
    '3.2 - Reportes de PND’s (VT, UT, PT)',
    '3.3 - Planos de Mapeo de Soldadura',
    '3.4 - Reporte de Apriete Ajustado',
    '3.5 - Reporte de Liberación Topográfica',
    '4.1 - Certificados de Soldadura',
    '4.2 - Certificados de Tornillería',
    '4.3 - Certificados de Gases',
    '5 - Reporte de Producto Terminado',
    '6 - Matriz de RFI',
    '7 - Planos As-Built'
]

# === PERSISTENCIA ===
archivo_estado = "estado.csv"
if os.path.exists(archivo_estado):
    df_estado = pd.read_csv(archivo_estado)
    tareas = df_estado["Tarea"].tolist()
    estados_cargados = df_estado["Completado"].tolist()
    fechas_cargadas = df_estado["Marca de Tiempo"].fillna("").tolist()
else:
    estados_cargados = [False] * len(tareas)
    fechas_cargadas = [""] * len(tareas)

if "estados" not in st.session_state:
    st.session_state.estados = estados_cargados
    st.session_state.fechas = fechas_cargadas

# === INTERFAZ ===
st.set_page_config(page_title="Checklist de Calidad", layout="centered")
st.title("✅ Checklist de Calidad")
st.markdown("Marca las tareas completadas para registrar su progreso y ver el resumen visual.")

st.subheader("Lista de Tareas")
for i, tarea in enumerate(tareas):
    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        st.session_state.estados[i] = st.checkbox(tarea, value=st.session_state.estados[i], key=f"check_{i}")
    if st.session_state.estados[i] and st.session_state.fechas[i] == "":
        st.session_state.fechas[i] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with col2:
        st.caption(f"🕒 {st.session_state.fechas[i]}" if st.session_state.fechas[i] else "")

df = pd.DataFrame({
    "Tarea": tareas,
    "Completado": st.session_state.estados,
    "Marca de Tiempo": st.session_state.fechas
})
df["Estado"] = df["Completado"].apply(lambda x: "✔ Completado" if x else "✘ Pendiente")

# === GUARDAR CSV LOCAL ===
df[["Tarea", "Completado", "Marca de Tiempo"]].to_csv(archivo_estado, index=False)

# === RESUMEN Y GRÁFICO ===
completadas = sum(st.session_state.estados)
total_tareas = len(st.session_state.estados)
pendientes = total_tareas - completadas

# Evitar división por cero
if total_tareas > 0:
    porcentaje = round(completadas / total_tareas * 100, 2)
else:
    porcentaje = 0

# Mostrar resumen
st.subheader("📊 Resumen")
st.write(f"**Total de tareas:** {total_tareas}")
st.write(f"**Completadas:** {completadas}")
st.write(f"**Pendientes:** {pendientes}")
st.write(f"**Porcentaje completado:** {porcentaje}%")

# Mostrar gráfico solo si hay tareas
if total_tareas > 0:
    fig, ax = plt.subplots()
    ax.pie([completadas, pendientes], labels=["Completadas", "Pendientes"],
           autopct='%1.1f%%', startangle=140)
    ax.axis("equal")
    st.pyplot(fig)
else:
    st.info("No hay tareas cargadas. Asegúrate de que el archivo `estado.csv` tenga contenido válido.")

# === DESCARGA CSV ===
csv = df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Descargar tareas como CSV",
    data=csv,
    file_name='tareas_completadas.csv',
    mime='text/csv'
)
