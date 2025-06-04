# test_creds.py
import gspread
from google.oauth2.service_account import Credentials

# Carga manual de las credenciales tal como lo hace Streamlit:
import os, json

# Simularemos st.secrets extrayendo la variable de entorno STREAMLIT_SECRETS
raw_toml = os.environ.get("STREAMLIT_SECRETS")
# (ver paso 6.3 para cómo inyectar esta variable localmente)

# Convertir TOML a dict (para simular st.secrets["GOOGLE_CREDENTIALS"])
import toml
all_secrets = toml.loads(raw_toml)
creds_dict = all_secrets["GOOGLE_CREDENTIALS"]

try:
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    client = gspread.authorize(creds)
    sheet = client.open("Liberaciones_Calidad").worksheet("estado")
    print("✅ Conexión exitosa. Primera fila:", sheet.row_values(1))
except Exception as e:
    print("❌ Error al autenticar u abrir la hoja:", e)