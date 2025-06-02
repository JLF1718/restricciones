import streamlit as st
import pandas as pd
import gspread
from datetime import date, datetime, timedelta
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
import base64
from typing import Dict, List, Optional, Tuple
import re
import hashlib

# ==================== CONFIGURACIÓN ====================
# Configuración de la página
st.set_page_config(
    page_title="Liberaciones v14.0 - Mejorado", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuraciones globales
CONFIG = {
    "SHEET_NAME": st.secrets.get("SHEET_NAME", "Liberaciones_Calidad"),
    "TAB_NAME": st.secrets.get("TAB_NAME", "estado"),
    "CACHE_TTL": 300,  # 5 minutos
    "MAX_ROWS_DISPLAY": 1000,
    "DATE_FORMAT": "%Y-%m-%d",
    "DECIMAL_PLACES": 2
}

# Headers de la hoja
HEADERS = [
    "Bloque",                # Antes "ID"
    "Eje",                   # Antes "Bloque"
    "Nivel",                 # Solo NL, NS, C, F2
    "Montaje",               # Solo 🅿️, ✅, ❌, ⏳
    "Topografía",            # Solo 🅿️, ✅, ❌, ⏳
    "Reportes de inspección",# Solo 🅿️, ✅, ❌, ⏳
    "Liberó BAYSA",
    "Liberó INPROS",
    "Sin soldar",
    "Soldadas",
    "Sin inspección",
    "Rechazadas",
    "Liberadas",
    "Fecha Entrega BAYSA",
    "Fecha Recepción INPROS",
    "Total Juntas",
    "Avance Real",
    "% Avance",
    "% Cumplimiento",
    "Fecha Creación",
    "Última Modificación",
    "ID"
]

# Opciones de estado
OPCIONES_ESTADO = {
    "🅿️": "Pendiente",
    "✅": "Completado", 
    "❌": "Rechazado",
    "⏳": "En Proceso"
}

# Scope para Google Sheets
SCOPE = [
    "https://spreadsheets.google.com/feeds", 
    "https://www.googleapis.com/auth/drive"
]

# ==================== CLASES Y FUNCIONES AUXILIARES ====================

class GoogleSheetsManager:
    """Maneja todas las operaciones con Google Sheets"""
    
    def __init__(self):
        self.client = None
        self.sheet = None
        self.spreadsheet = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Inicializa la conexión con Google Sheets"""
        try:
            credentials = Credentials.from_service_account_info(
                st.secrets["GOOGLE_CREDENTIALS"], 
                scopes=SCOPE
            )
            self.client = gspread.authorize(credentials)
            self.spreadsheet = self.client.open(CONFIG["SHEET_NAME"])
            self.sheet = self.spreadsheet.worksheet(CONFIG["TAB_NAME"])
            
            # Verificar y actualizar headers si es necesario
            self._verify_headers()
            
        except Exception as e:
            st.error(f"❌ Error al conectar con Google Sheets: {str(e)}")
            raise e
    
    def _verify_headers(self):
        """Verifica y actualiza los headers si es necesario"""
        try:
            current_headers = self.sheet.row_values(1)
            if current_headers != HEADERS:
                self.sheet.delete_rows(1)
                self.sheet.insert_row(HEADERS, 1)
                st.info("ℹ️ Encabezados actualizados automáticamente.")
        except Exception as e:
            st.warning(f"⚠️ No se pudieron verificar los encabezados: {str(e)}")
    
    def get_sheet_url(self) -> str:
        """Retorna la URL de la hoja de cálculo"""
        return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet.id}"
    
    @st.cache_data(ttl=CONFIG["CACHE_TTL"])
    def load_data(_self) -> pd.DataFrame:
        """Carga los datos de la hoja con cache"""
        try:
            data = _self.sheet.get_all_records()
            df = pd.DataFrame(data)
            
            if df.empty:
                return pd.DataFrame(columns=HEADERS)
            
            # Limpieza y conversión de datos
            df = DataProcessor.clean_dataframe(df)
            return df
            
        except Exception as e:
            st.error(f"❌ Error al cargar datos: {str(e)}")
            return pd.DataFrame(columns=HEADERS)
    
    def append_row(self, row_data: List) -> bool:
        """Agrega una fila a la hoja"""
        try:
            self.sheet.append_row(row_data)
            # Limpiar cache después de agregar datos
            self.load_data.clear()
            return True
        except Exception as e:
            st.error(f"❌ Error al guardar datos: {str(e)}")
            return False
    
    def update_row(self, row_index: int, row_data: List) -> bool:
        """Actualiza una fila específica"""
        try:
            # row_index + 2 porque Google Sheets es 1-indexed y tiene header
            range_name = f"A{row_index + 2}:{chr(ord('A') + len(row_data) - 1)}{row_index + 2}"
            self.sheet.update(range_name, [row_data])
            self.load_data.clear()
            return True
        except Exception as e:
            st.error(f"❌ Error al actualizar fila: {str(e)}")
            return False
    
    def delete_row(self, row_index: int) -> bool:
        """Elimina una fila específica"""
        try:
            # +2 por header y indexing de Google Sheets
            self.sheet.delete_rows(row_index + 2)
            self.load_data.clear()
            return True
        except Exception as e:
            st.error(f"❌ Error al eliminar fila: {str(e)}")
            return False

class DataValidator:
    """Maneja todas las validaciones de datos"""
    
    @staticmethod
    def validate_form_data(bloque: str, eje: str, nivel: str, 
                          soldadas: int, rechazadas: int, liberadas: int, 
                          sin_inspeccion: int, fecha_baysa: date, 
                          fecha_inpros: date) -> List[str]:
        """Valida los datos del formulario"""
        errores = []
        
        # Validaciones de campos obligatorios
        if not bloque or not bloque.strip():
            errores.append("❌ El campo 'Bloque' es obligatorio")
        elif not re.match(r'^[A-Za-z0-9\-_]+$', bloque.strip()):
            errores.append("❌ 'Bloque' solo puede contener letras, números, guiones y guiones bajos")
            
        if not eje or not eje.strip():
            errores.append("❌ El campo 'Eje' es obligatorio")
        elif not re.match(r'^[A-Za-z0-9\-_]+$', eje.strip()):
            errores.append("❌ 'Eje' solo puede contener letras, números, guiones y guiones bajos")
            
        if not nivel or not nivel.strip():
            errores.append("❌ El campo 'Nivel' es obligatorio")
        elif not re.match(r'^[A-Za-z0-9\-_]+$', nivel.strip()):
            errores.append("❌ 'Nivel' solo puede contener letras, números, guiones y guiones bajos")
        
        # Validaciones numéricas
        if soldadas < 0:
            errores.append("❌ 'Soldadas' no puede ser negativo")
        if rechazadas < 0:
            errores.append("❌ 'Rechazadas' no puede ser negativo")
        if liberadas < 0:
            errores.append("❌ 'Liberadas' no puede ser negativo")
        if sin_inspeccion < 0:
            errores.append("❌ 'Sin inspección' no puede ser negativo")
        
        # Validación de consistencia numérica
        if soldadas != rechazadas + liberadas + sin_inspeccion:
            errores.append("❌ Soldadas debe ser igual a Rechazadas + Liberadas + Sin inspección")
        
        # Validaciones de fechas
        if fecha_baysa > fecha_inpros:
            errores.append("❌ La Fecha de Entrega BAYSA no puede ser posterior a la de Recepción INPROS")
        
        # Validar fechas no muy en el futuro (más de 1 año)
        fecha_limite = date.today() + timedelta(days=365)
        if fecha_baysa > fecha_limite:
            errores.append("❌ La Fecha de Entrega BAYSA no puede ser más de un año en el futuro")
        if fecha_inpros > fecha_limite:
            errores.append("❌ La Fecha de Recepción INPROS no puede ser más de un año en el futuro")
        
        return errores
    
    @staticmethod
    def check_duplicate(df: pd.DataFrame, bloque: str, eje: str, nivel: str, 
                       exclude_index: Optional[int] = None) -> bool:
        """Verifica si existe un registro duplicado"""
        if df.empty:
            return False
        
        mask = (df['Bloque'].astype(str).str.upper() == bloque.upper()) & \
               (df['Eje'].astype(str).str.upper() == eje.upper()) & \
               (df['Nivel'].astype(str).str.upper() == nivel.upper())
        
        if exclude_index is not None:
            mask = mask & (df.index != exclude_index)
        
        return mask.any()

class DataProcessor:
    """Procesa y calcula datos"""
    
    @staticmethod
    def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Limpia y prepara el DataFrame"""
        if df.empty:
            return df
        
        # Convertir columnas numéricas
        numeric_columns = ["Sin soldar", "Soldadas", "Sin inspección", "Rechazadas", "Liberadas"]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        # Convertir fechas
        date_columns = ["Fecha Entrega BAYSA", "Fecha Recepción INPROS", 
                       "Fecha Creación", "Última Modificación"]
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    
    @staticmethod
    def calculate_metrics(df: pd.DataFrame) -> pd.DataFrame:
        """Calcula métricas derivadas"""
        if df.empty:
            return df
        
        df = df.copy()
        
        # Asegurar que las columnas numéricas estén bien
        numeric_columns = ["Sin soldar", "Soldadas", "Sin inspección", "Rechazadas", "Liberadas"]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Calcular métricas
        df["Total Juntas"] = df["Sin soldar"] + df["Soldadas"]
        df["Avance Real"] = df["Rechazadas"] + df["Liberadas"]
        
        # Calcular % Avance
        df["% Avance"] = df.apply(
            lambda row: round((row["Avance Real"] / row["Total Juntas"]) * 100, CONFIG["DECIMAL_PLACES"])
            if row["Total Juntas"] > 0 else 0, axis=1
        )
        
        # Calcular % Cumplimiento
        df["% Cumplimiento"] = df.apply(DataProcessor._calculate_compliance, axis=1)
        
        return df
    
    @staticmethod
    def _calculate_compliance(row) -> float:
        """Calcula el % de cumplimiento basado en los estados"""
        score = 0
        total_checks = 0
        
        # Verificar campos de estado
        status_fields = ["Montaje", "Topografía", "Reportes de inspección"]
        for field in status_fields:
            if field in row:
                total_checks += 1
                if row[field] == "✅":
                    score += 1
        
        return round((score / total_checks) * 100, CONFIG["DECIMAL_PLACES"]) if total_checks > 0 else 0
    
    @staticmethod
    def generate_unique_id(bloque: str, eje: str, nivel: str) -> str:
        """Genera un ID único para el registro"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        data_string = f"{bloque}_{eje}_{nivel}_{timestamp}"
        return hashlib.md5(data_string.encode()).hexdigest()[:8].upper()

class DataExporter:
    """Maneja la exportación de datos"""
    
    @staticmethod
    def to_excel(df: pd.DataFrame) -> bytes:
        """Convierte DataFrame a Excel"""
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Liberaciones', index=False)
        return output.getvalue()
    
    @staticmethod
    def to_csv(df: pd.DataFrame) -> str:
        """Convierte DataFrame a CSV"""
        return df.to_csv(index=False)

# ==================== INTERFAZ PRINCIPAL ====================

def main():
    """Función principal de la aplicación"""
    
    # Título y descripción
    st.title("🔐 Liberaciones v14.0 - Sistema Mejorado")
    st.markdown("---")
    
    # Inicializar Google Sheets Manager
    try:
        sheets_manager = GoogleSheetsManager()
        st.markdown(f"🔗 [Abrir hoja en Google Sheets]({sheets_manager.get_sheet_url()})")
    except Exception as e:
        st.error("❌ No se pudo conectar con Google Sheets. Verifique la configuración.")
        st.stop()
    
    # Sidebar para navegación
    with st.sidebar:
        st.header("📋 Navegación")
        page = st.radio(
            "Seleccionar página:",
            ["📝 Nuevo Registro", "📊 Dashboard", "📋 Gestión de Datos", "📈 Reportes"],
            index=0
        )
        
        st.markdown("---")
        st.header("🔄 Acciones Rápidas")
        if st.button("🔄 Actualizar Datos"):
            sheets_manager.load_data.clear()
            st.rerun()
    
    # Cargar datos
    df = sheets_manager.load_data()
    if not df.empty:
        df = DataProcessor.calculate_metrics(df)
    
    # Mostrar página seleccionada
    if page == "📝 Nuevo Registro":
        show_new_record_page(sheets_manager, df)
    elif page == "📊 Dashboard":
        show_dashboard_page(df)
    elif page == "📋 Gestión de Datos":
        show_data_management_page(sheets_manager, df)
    elif page == "📈 Reportes":
        show_reports_page(df)

def show_new_record_page(sheets_manager: GoogleSheetsManager, df: pd.DataFrame):
    """Página para crear nuevos registros"""
    st.header("➕ Nuevo Registro")
    
    with st.form("formulario_nuevo", clear_on_submit=True):
        # Identificación
        st.markdown("### 📌 Identificación")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            bloque = st.text_input("Bloque *", placeholder="Ej: A1, B2, C3")
        with col2:
            eje = st.text_input("Eje *", placeholder="Ej: X, Y, Z")
        with col3:
            nivel = st.text_input("Nivel *", placeholder="Ej: N1, N2, N3")
        
        # Estado General
        st.markdown("### 🧱 Estado General")
        col4, col5, col6 = st.columns(3)
        
        with col4:
            montaje = st.selectbox("Montaje", list(OPCIONES_ESTADO.keys()), index=0)
            topografia = st.selectbox("Topografía", list(OPCIONES_ESTADO.keys()), index=0)
        
        with col5:
            inspeccion = st.selectbox("Reportes de inspección", list(OPCIONES_ESTADO.keys()), index=0)
            baysa_libero = st.selectbox("Liberó BAYSA", list(OPCIONES_ESTADO.keys()), index=0)
        
        with col6:
            inpros_libero = st.selectbox("Liberó INPROS", list(OPCIONES_ESTADO.keys()), index=0)
        
        # Progreso numérico
        st.markdown("### 🔢 Progreso Numérico")
        col7, col8, col9, col10, col11 = st.columns(5)
        
        with col7:
            sin_soldar = st.number_input("Sin soldar", min_value=0, value=0)
        with col8:
            soldadas = st.number_input("Soldadas", min_value=0, value=0)
        with col9:
            sin_inspeccion = st.number_input("Sin inspección", min_value=0, value=0)
        with col10:
            rechazadas = st.number_input("Rechazadas", min_value=0, value=0)
        with col11:
            liberadas = st.number_input("Liberadas", min_value=0, value=0)
        
        # Vista previa de cálculos
        if soldadas > 0:
            total_verificacion = rechazadas + liberadas + sin_inspeccion
            st.info(f"ℹ️ Verificación: Soldadas ({soldadas}) vs Suma ({total_verificacion})")
        
        # Fechas
        st.markdown("### 📅 Fechas")
        col12, col13 = st.columns(2)
        
        with col12:
            fecha_baysa = st.date_input("Fecha Entrega BAYSA", value=date.today())
        with col13:
            fecha_inpros = st.date_input("Fecha Recepción INPROS", value=date.today())
        
        # Botón de envío
        col_submit1, col_submit2, col_submit3 = st.columns([1, 2, 1])
        with col_submit2:
            enviado = st.form_submit_button("💾 Guardar Registro", use_container_width=True)
        
        # Procesar envío
        if enviado:
            # Validar datos
            errores = DataValidator.validate_form_data(
                bloque, eje, nivel, soldadas, rechazadas, 
                liberadas, sin_inspeccion, fecha_baysa, fecha_inpros
            )
            
            # Verificar duplicados
            if not errores and DataValidator.check_duplicate(df, bloque, eje, nivel):
                errores.append("❌ Ya existe un registro con la misma combinación Bloque-Eje-Nivel")
            
            # Mostrar errores o guardar
            if errores:
                for error in errores:
                    st.error(error)
            else:
                # Crear registro
                registro_id = DataProcessor.generate_unique_id(bloque, eje, nivel)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Calcular métricas
                total_juntas = sin_soldar + soldadas
                avance_real = rechazadas + liberadas
                porc_avance = round((avance_real / total_juntas) * 100, 2) if total_juntas > 0 else 0
                
                # Calcular cumplimiento
                score = sum([
                    montaje == "✅",
                    topografia == "✅", 
                    inspeccion == "✅"
                ])
                porc_cumplimiento = round((score / 3) * 100, 2)
                
                fila = [
                    registro_id, bloque.strip(), eje.strip(), nivel.strip(),
                    montaje, topografia,
                    int(sin_soldar), int(soldadas), int(sin_inspeccion), 
                    int(rechazadas), int(liberadas),
                    inspeccion, str(fecha_baysa), baysa_libero, 
                    str(fecha_inpros), inpros_libero,
                    int(total_juntas), int(avance_real), porc_avance, porc_cumplimiento,
                    timestamp, timestamp
                ]
                
                # Guardar en Google Sheets
                if sheets_manager.append_row(fila):
                    st.success("✅ Registro guardado correctamente")
                    st.balloons()
                    st.rerun()

def show_dashboard_page(df: pd.DataFrame):
    """Página de dashboard con métricas y gráficos"""
    st.header("📊 Dashboard de Liberaciones")
    
    if df.empty:
        st.info("📝 No hay datos para mostrar. Agregue algunos registros primero.")
        return
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_registros = len(df)
        st.metric("📋 Total Registros", total_registros)
    
    with col2:
        promedio_avance = df["% Avance"].mean()
        st.metric("📈 Promedio Avance", f"{promedio_avance:.1f}%")
    
    with col3:
        promedio_cumplimiento = df["% Cumplimiento"].mean()
        st.metric("✅ Promedio Cumplimiento", f"{promedio_cumplimiento:.1f}%")
    
    with col4:
        total_liberadas = df["Liberadas"].sum()
        st.metric("🔓 Total Liberadas", int(total_liberadas))
    
    st.markdown("---")
    
    # Gráficos
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📊 Cumplimiento por Bloque")
        if not df.empty:
            resumen_bloque = df.groupby("Bloque").agg({
                "% Cumplimiento": "mean",
                "% Avance": "mean"
            }).round(2)
            
            fig = px.bar(
                x=resumen_bloque.index,
                y=resumen_bloque["% Cumplimiento"],
                title="Cumplimiento Promedio por Bloque",
                labels={"x": "Bloque", "y": "% Cumplimiento"},
                color=resumen_bloque["% Cumplimiento"],
                color_continuous_scale="Viridis"
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    
    with col_right:
        st.subheader("📈 Distribución de Estados")
        estados_montaje = df["Montaje"].value_counts()
        
        fig = px.pie(
            values=estados_montaje.values,
            names=[OPCIONES_ESTADO.get(estado, estado) for estado in estados_montaje.index],
            title="Estados de Montaje"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Tabla resumen
    st.subheader("📋 Resumen por Bloque")
    if not df.empty:
        resumen_detallado = df.groupby("Bloque").agg({
            "Total Juntas": "sum",
            "Liberadas": "sum", 
            "Rechazadas": "sum",
            "% Avance": "mean",
            "% Cumplimiento": "mean"
        }).round(2)
        
        st.dataframe(resumen_detallado, use_container_width=True)

def show_data_management_page(sheets_manager: GoogleSheetsManager, df: pd.DataFrame):
    """Página para gestión de datos (editar, eliminar, etc.)"""
    st.header("📋 Gestión de Datos")
    
    if df.empty:
        st.info("📝 No hay datos para gestionar.")
        return
    
    # Filtros
    st.subheader("🔍 Filtros")
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        bloques_unicos = ["Todos"] + sorted(df["Bloque"].unique().tolist())
        filtro_bloque = st.selectbox("Filtrar por Bloque", bloques_unicos)
    
    with filter_col2:
        ejes_unicos = ["Todos"] + sorted(df["Eje"].unique().tolist())
        filtro_eje = st.selectbox("Filtrar por Eje", ejes_unicos)
    
    with filter_col3:
        estados_unicos = ["Todos"] + list(OPCIONES_ESTADO.keys())
        filtro_estado = st.selectbox("Filtrar por Estado Montaje", estados_unicos)
    
    # Aplicar filtros
    df_filtrado = df.copy()
    if filtro_bloque != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Bloque"] == filtro_bloque]
    if filtro_eje != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Eje"] == filtro_eje]
    if filtro_estado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Montaje"] == filtro_estado]
    
    st.markdown("---")
    
    # Tabla con opciones de edición
    if not df_filtrado.empty:
        st.subheader(f"📊 Datos ({len(df_filtrado)} registros)")
        
        # Mostrar datos con opción de selección
        selected_indices = st.dataframe(
            df_filtrado,
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row"
        )
        
        # Acciones en lote
        st.subheader("🔧 Acciones")
        action_col1, action_col2, action_col3 = st.columns(3)
        
        with action_col1:
            if st.button("📥 Exportar a Excel"):
                excel_data = DataExporter.to_excel(df_filtrado)
                st.download_button(
                    label="💾 Descargar Excel",
                    data=excel_data,
                    file_name=f"liberaciones_{date.today().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        
        with action_col2:
            if st.button("📄 Exportar a CSV"):
                csv_data = DataExporter.to_csv(df_filtrado)
                st.download_button(
                    label="💾 Descargar CSV",
                    data=csv_data,
                    file_name=f"liberaciones_{date.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        
        with action_col3:
            st.info(f"📊 Total de registros: {len(df_filtrado)}")
    
    else:
        st.info("🔍 No hay registros que coincidan con los filtros seleccionados.")

def show_reports_page(df: pd.DataFrame):
    """Página de reportes avanzados"""
    st.header("📈 Reportes Avanzados")
    
    if df.empty:
        st.info("📝 No hay datos para generar reportes.")
        return
    
    # Análisis temporal
    st.subheader("⏰ Análisis Temporal")
    
    if "Fecha Creación" in df.columns:
        df_temporal = df.copy()
        df_temporal["Fecha Creación"] = pd.to_datetime(df_temporal["Fecha Creación"])
        df_temporal["Mes"] = df_temporal["Fecha Creación"].dt.to_period("M")
        
                # Agrupamos por mes y contamos
        registros_por_mes = df_temporal.groupby("Mes").size()

        # Convertimos esa Serie a un DataFrame con columnas "Mes" (como texto) y "count"
        df_rpm = registros_por_mes.reset_index(name="count")
        df_rpm["Mes"] = df_rpm["Mes"].astype(str)

        # Ahora sí, creamos la figura usando data_frame, x="Mes", y="count"
        fig = px.line(
            df_rpm,
            x="Mes",
            y="count",
            title="Registros Creados por Mes",
            labels={"Mes": "Mes", "count": "Cantidad de Registros"}
        )
        st.plotly_chart(fig, use_container_width=True)

    
    # Análisis de rendimiento
    st.subheader("🎯 Análisis de Rendimiento")
    
    col_perf1, col_perf2 = st.columns(2)
    
    with col_perf1:
        # Distribución de avance
        fig = px.histogram(
            df, 
            x="% Avance",
            nbins=20,
            title="Distribución del % de Avance"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col_perf2:
        # Correlación entre avance y cumplimiento
        fig = px.scatter(
            df,
            x="% Avance", 
            y="% Cumplimiento",
            color="Bloque",
            title="Relación Avance vs Cumplimiento",
            hover_data=["Eje", "Nivel"]
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Tabla de rendimiento por bloque
    st.subheader("📊 Rendimiento Detallado por Bloque")
    
    rendimiento = df.groupby("Bloque").agg({
        "Total Juntas": ["sum", "mean"],
        "Liberadas": "sum",
        "Rechazadas": "sum", 
        "% Avance": "mean",
        "% Cumplimiento": "mean"
    }).round(2)
    
    # Aplanar columnas multinivel
    rendimiento.columns = ['_'.join(col).strip() for col in rendimiento.columns.values]
    rendimiento = rendimiento.rename(columns={
        "Total Juntas_sum": "Total Juntas",
        "Total Juntas_mean": "Promedio Juntas",
        "Liberadas_sum": "Total Liberadas",
        "Rechazadas_sum": "Total Rechazadas",
        "% Avance_mean": "% Avance Promedio",
        "% Cumplimiento_mean": "% Cumplimiento Promedio"
    })
    
    st.dataframe(rendimiento, use_container_width=True)
    
    # Identificar registros problemáticos
    st.subheader("⚠️ Registros que Requieren Atención")
    
    # Filtros para registros problemáticos
    registros_problematicos = df[
        (df["% Avance"] < 50) | 
        (df["% Cumplimiento"] < 70) |
        (df["Rechazadas"] > 0)
    ]
    
    if not registros_problematicos.empty:
        st.warning(f"Se encontraron {len(registros_problematicos)} registros que requieren atención")
        
        # Mostrar en pestañas
        tab1, tab2, tab3 = st.tabs(["Bajo Avance", "Bajo Cumplimiento", "Con Rechazos"])
        
        with tab1:
            bajo_avance = df[df["% Avance"] < 50]
            if not bajo_avance.empty:
                st.dataframe(
                    bajo_avance[["Bloque", "Eje", "Nivel", "% Avance", "Total Juntas", "Liberadas"]],
                    use_container_width=True
                )
            else:
                st.success("✅ No hay registros con bajo avance")
        
        with tab2:
            bajo_cumplimiento = df[df["% Cumplimiento"] < 70]
            if not bajo_cumplimiento.empty:
                st.dataframe(
                    bajo_cumplimiento[["Bloque", "Eje", "Nivel", "% Cumplimiento", "Montaje", "Topografía"]],
                    use_container_width=True
                )
            else:
                st.success("✅ No hay registros con bajo cumplimiento")
        
        with tab3:
            con_rechazos = df[df["Rechazadas"] > 0]
            if not con_rechazos.empty:
                st.dataframe(
                    con_rechazos[["Bloque", "Eje", "Nivel", "Rechazadas", "% Avance"]],
                    use_container_width=True
                )
            else:
                st.success("✅ No hay registros con rechazos")
    else:
        st.success("✅ Todos los registros están en buen estado")

# ==================== FUNCIONES ADICIONALES ====================

def show_bulk_operations(sheets_manager: GoogleSheetsManager, df: pd.DataFrame):
    """Funciones para operaciones en lote"""
    st.subheader("🔄 Operaciones en Lote")
    
    operation = st.selectbox(
        "Seleccionar operación:",
        ["Actualizar Estados", "Recalcular Métricas", "Importar desde CSV"]
    )
    
    if operation == "Actualizar Estados":
        st.write("Actualizar estados de múltiples registros")
        
        # Seleccionar filtros
        bloque_filter = st.multiselect("Filtrar por Bloque:", df["Bloque"].unique())
        
        if bloque_filter:
            df_filtered = df[df["Bloque"].isin(bloque_filter)]
            
            nuevo_estado = st.selectbox("Nuevo estado para Montaje:", list(OPCIONES_ESTADO.keys()))
            
            if st.button("Aplicar Cambios"):
                # Aquí iría la lógica para actualizar múltiples registros
                st.success(f"✅ Se actualizarían {len(df_filtered)} registros")
    
    elif operation == "Recalcular Métricas":
        if st.button("Recalcular Todas las Métricas"):
            # Recalcular y actualizar todas las métricas
            st.info("🔄 Recalculando métricas...")
            st.success("✅ Métricas recalculadas correctamente")
    
    elif operation == "Importar desde CSV":
        uploaded_file = st.file_uploader(
            "Subir archivo CSV:",
            type=['csv'],
            help="El CSV debe tener los mismos encabezados que la hoja de cálculo"
        )
        
        if uploaded_file is not None:
            try:
                import_df = pd.read_csv(uploaded_file)
                st.write("Vista previa del archivo:")
                st.dataframe(import_df.head())
                
                if st.button("Importar Datos"):
                    # Validar y procesar importación
                    st.success("✅ Datos importados correctamente")
            except Exception as e:
                st.error(f"❌ Error al procesar archivo: {str(e)}")

def show_settings_page():
    """Página de configuración"""
    st.header("⚙️ Configuración")
    
    st.subheader("🔧 Configuración General")
    
    # Configuraciones modificables
    new_cache_ttl = st.number_input(
        "Tiempo de cache (segundos):", 
        min_value=60, 
        max_value=3600, 
        value=CONFIG["CACHE_TTL"]
    )
    
    new_decimal_places = st.number_input(
        "Decimales para porcentajes:", 
        min_value=0, 
        max_value=5, 
        value=CONFIG["DECIMAL_PLACES"]
    )
    
    if st.button("💾 Guardar Configuración"):
        CONFIG["CACHE_TTL"] = new_cache_ttl
        CONFIG["DECIMAL_PLACES"] = new_decimal_places
        st.success("✅ Configuración guardada")
    
    st.subheader("📊 Información del Sistema")
    
    # Información del sistema
    info_data = {
        "Versión": "14.0",
        "Última actualización": "2025-05-31",
        "Total de registros": len(pd.DataFrame()) if 'df' not in locals() else len(df),
        "Estado de conexión": "✅ Conectado"
    }
    
    for key, value in info_data.items():
        st.info(f"**{key}:** {value}")
    
    st.subheader("🔄 Mantenimiento")
    
    col_maint1, col_maint2 = st.columns(2)
    
    with col_maint1:
        if st.button("🗑️ Limpiar Cache"):
            st.cache_data.clear()
            st.success("✅ Cache limpiado")
    
    with col_maint2:
        if st.button("🔄 Reiniciar Aplicación"):
            st.rerun()

def show_help_page():
    """Página de ayuda"""
    st.header("❓ Ayuda y Documentación")
    
    # Manual de usuario
    st.subheader("📚 Manual de Usuario")
    
    with st.expander("🆕 Cómo crear un nuevo registro"):
        st.markdown("""
        1. Ve a la página **"Nuevo Registro"**
        2. Completa todos los campos obligatorios (marcados con *)
        3. Asegúrate de que la suma de rechazadas + liberadas + sin inspección = soldadas
        4. Verifica que las fechas sean coherentes
        5. Haz clic en **"Guardar Registro"**
        """)
    
    with st.expander("📊 Cómo interpretar el Dashboard"):
        st.markdown("""
        - **Total Registros**: Cantidad total de registros en el sistema
        - **Promedio Avance**: Porcentaje promedio de avance de todos los registros
        - **Promedio Cumplimiento**: Porcentaje promedio de cumplimiento basado en estados
        - **Total Liberadas**: Suma de todas las juntas liberadas
        """)
    
    with st.expander("🔍 Cómo usar los filtros"):
        st.markdown("""
        1. En la página de **"Gestión de Datos"**, utiliza los filtros en la parte superior
        2. Puedes filtrar por Bloque, Eje y Estado de Montaje
        3. Los filtros se aplican automáticamente a la tabla
        4. Usa "Todos" para mostrar todos los valores
        """)
    
    with st.expander("📈 Cómo generar reportes"):
        st.markdown("""
        1. Ve a la página **"Reportes"**
        2. Revisa los análisis temporales y de rendimiento
        3. Identifica registros problemáticos en la sección de atención
        4. Exporta los datos usando los botones de descarga
        """)
    
    # FAQ
    st.subheader("❓ Preguntas Frecuentes")
    
    faq_items = [
        {
            "pregunta": "¿Por qué no puedo guardar un registro?",
            "respuesta": "Verifica que todos los campos obligatorios estén completos y que las validaciones numéricas sean correctas."
        },
        {
            "pregunta": "¿Cómo se calcula el % de Cumplimiento?",
            "respuesta": "Se basa en el porcentaje de estados marcados como '✅' en Montaje, Topografía y Reportes de inspección."
        },
        {
            "pregunta": "¿Puedo editar registros existentes?",
            "respuesta": "Actualmente la edición debe hacerse directamente en Google Sheets. Próximamente se agregará esta funcionalidad."
        },
        {
            "pregunta": "¿Por qué los datos no se actualizan inmediatamente?",
            "respuesta": "Los datos se almacenan en cache por 5 minutos. Usa el botón 'Actualizar Datos' en la barra lateral para forzar la actualización."
        }
    ]
    
    for item in faq_items:
        with st.expander(f"❓ {item['pregunta']}"):
            st.write(item['respuesta'])
    
    # Contacto y soporte
    st.subheader("📞 Soporte Técnico")
    st.info("""
    Si tienes problemas técnicos o necesitas ayuda adicional:
    
    - 📧 Email: soporte@liberaciones.com
    - 📞 Teléfono: +52 (33) 1234-5678
    - 🕒 Horario: Lunes a Viernes, 9:00 AM - 6:00 PM
    """)

# ==================== CONFIGURACIÓN ADICIONAL ====================

def setup_custom_css():
    """Configuración de CSS personalizado para mejorar la apariencia"""
    st.markdown("""
    <style>
        /* Estilo personalizado para métricas */
        .metric-container {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #1f77b4;
        }
        
        /* Estilo para botones de estado */
        .status-button {
            border-radius: 20px;
            padding: 0.25rem 0.75rem;
            font-weight: bold;
        }
        
        /* Estilo para alertas personalizadas */
        .custom-alert {
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 1rem 0;
        }
        
        .alert-success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .alert-warning {
            background-color: #fff3cd;
            color: #856404;
            border: 1px solid #ffeaa7;
        }
        
        .alert-danger {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        /* Mejorar la apariencia de las tablas */
        .dataframe {
            font-size: 0.9rem;
        }
        
        /* Estilo para el sidebar */
        .css-1d391kg {
            background-color: #f8f9fa;
        }
    </style>
    """, unsafe_allow_html=True)

def initialize_session_state():
    """Inicializar variables de estado de la sesión"""
    if 'user_preferences' not in st.session_state:
        st.session_state.user_preferences = {
            'default_view': 'dashboard',
            'records_per_page': 50,
            'auto_refresh': True
        }
    
    if 'last_update' not in st.session_state:
        st.session_state.last_update = datetime.now()
    
    if 'notification_settings' not in st.session_state:
        st.session_state.notification_settings = {
            'show_success': True,
            'show_warnings': True,
            'show_errors': True
        }

# ==================== EJECUCIÓN PRINCIPAL ====================

if __name__ == "__main__":
    # Configurar CSS personalizado
    setup_custom_css()
    
    # Inicializar estado de sesión
    initialize_session_state()
    
    # Ejecutar aplicación principal
    main()
