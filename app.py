import streamlit as st
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import os

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
pendientes = len(tareas) - completadas
porcentaje = round(completadas / len(tareas) * 100, 2) if len(tareas) > 0 else 0

st.subheader("📊 Resumen")
st.write(f"**Total de tareas:** {len(tareas)}")
st.write(f"**Completadas:** {completadas}")
st.write(f"**Pendientes:** {pendientes}")
st.write(f"**Porcentaje completado:** {porcentaje}%")

fig, ax = plt.subplots()
ax.pie([completadas, pendientes], labels=["Completadas", "Pendientes"],
       autopct='%1.1f%%', startangle=140)
ax.axis("equal")
st.pyplot(fig)

st.subheader("📋 Estado de las Tareas")
st.dataframe(df[['Tarea', 'Estado', 'Marca de Tiempo']], use_container_width=True)

# === DESCARGA CSV ===
csv = df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Descargar tareas como CSV",
    data=csv,
    file_name='tareas_completadas.csv',
    mime='text/csv'
)
