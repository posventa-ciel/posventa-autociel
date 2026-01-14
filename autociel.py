import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
import os

st.set_page_config(page_title="Grupo CENOA - Gestión Posventa", layout="wide")

# --- ESTILO CSS ---
st.markdown("""<style>
    .block-container { padding-top: 1rem; padding-bottom: 2rem; }
    .main { background-color: #f4f7f9; }
    .kpi-card { background-color: white; border: 1px solid #e0e0e0; padding: 12px 15px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 8px; min-height: 145px; display: flex; flex-direction: column; justify-content: space-between; }
    .metric-card { background-color: white; border: 1px solid #eee; padding: 10px; border-radius: 8px; text-align: center; min-height: 110px; }
    .cyp-detail { background-color: #f8f9fa; padding: 8px; border-radius: 6px; font-size: 0.8rem; margin-top: 5px; border-left: 3px solid #00235d; }
</style>""", unsafe_allow_html=True)

# --- FUNCIÓN DE BÚSQUEDA ---
def find_col(df, include_keywords, exclude_keywords=[]):
    if df is None: return ""
    for col in df.columns:
        col_upper = str(col).upper()
        if all(k.upper() in col_upper for k in include_keywords):
            if not any(x.upper() in col_upper for x in exclude_keywords):
                return col
    return ""

# --- CARGA DATOS GSHEETS ---
@st.cache_data(ttl=60)
def cargar_datos(sheet_id):
    hojas = ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA']
    data_dict = {}
    for h in hojas:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={h.replace(' ', '%20')}"
        try:
            df = pd.read_csv(url, dtype=str).fillna("0")
            df.columns = [c.strip().upper().replace(".", "").replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U").replace("Ñ", "N") for c in df.columns]
            for col in df.columns:
                if "FECHA" not in col and "CANAL" not in col and "ESTADO" not in col:
                    df[col] = df[col].astype(str).str.replace(r'[\$%\s]', '', regex=True).str.replace(',', '.')
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            data_dict[h] = df
        except Exception as e:
            st.error(f"Error hoja {h}: {e}")
            return None
    return data_dict

# --- SÚPER CARGADOR DE ARCHIVOS (HTML / EXCEL / CSV) ---
def super_cargador(uploaded_file):
    try:
        # 1. Intentar lectura como HTML (Típico de Quiter viejo exportado a Excel)
        uploaded_file.seek(0)
        try:
            dfs = pd.read_html(uploaded_file, header=0)
            if dfs: return dfs[0], "HTML Detectado"
        except: pass
        
        # 2. Intentar Excel estándar
        uploaded_file.seek(0)
        try:
            return pd.read_excel(uploaded_file), "Excel Estándar"
        except: pass

        # 3. CSV con punto y coma
        uploaded_file.seek(0)
        try:
            return pd.read_csv(uploaded_file, sep=';', encoding='latin-1'), "CSV Punto y Coma"
        except: pass

        # 4. CSV con tabulaciones (Otro formato falso Excel)
        uploaded_file.seek(0)
        try:
            return pd.read_csv(uploaded_file, sep='\t', encoding='latin-1'), "CSV Tabulado"
        except: pass

        # 5. CSV estándar
        uploaded_file.seek(0)
        try:
            return pd.read_csv(uploaded_file, encoding='latin-1'), "CSV Coma"
        except: pass

        return None, "Formato Desconocido"
    except Exception as e:
        return None, str(e)

# --- PROCESAMIENTO IRPV ---
def procesar_irpv(file_v, file_t):
    # Cargar Ventas
    df_v, tipo_v = super_cargador(file_v)
    if df_v is None: return None, f"Error Ventas: {tipo_v}"
    
    # Limpieza Columnas Ventas
    df_v.columns = [str(c).upper().strip() for c in df_v.columns]
    
    # Buscar columnas clave (flexible)
    col_vin = next((c for c in df_v.columns if 'BASTIDOR' in c or 'VIN' in c or 'CHASIS' in c), None)
    col_fec = next((c for c in df_v.columns if 'FEC' in c or 'ENTR' in c), None)
    
    if not col_vin or not col_fec:
        return None, f"Ventas: No se encontraron columnas 'Bastidor' ni 'Fecha'. (Cols: {list(df_v.columns)})"

    # Procesar Fechas Ventas
    def clean_date(x):
        if pd.isna(x) or x == '': return None
        try: return pd.to_datetime(x, dayfirst=True)
        except:
            try: return datetime(1899, 12, 30) + pd.Timedelta(days=float(x))
            except: return None

    df_v['Fecha_Entrega'] = df_v[col_fec].apply(clean_date)
    df_v['Año_Venta'] = df_v['Fecha_Entrega'].dt.year
    df_v['VIN'] = df_v[col_vin].astype(str).str.strip().str.upper()
    df_v = df_v.dropna(subset=['VIN', 'Fecha_Entrega'])

    # Cargar Taller
    df_t, tipo_t = super_cargador(file_t)
    if df_t is None: return None, f"Error Taller: {tipo_t}"
    
    # Limpieza Columnas Taller
    df_t.columns = [str(c).upper().strip() for c in df_t.columns]
    
    col_vin_t = next((c for c in df_t.columns if 'BASTIDOR' in c or 'VIN' in c), None)
    col_fec_t = next((c for c in df_t.columns if 'CIERRE' in c or 'FEC' in c), None)
    col_km = next((c for c in df_t.columns if 'KM' in c), None)
    col_or = next((c for c in df_t.columns if 'TIPO' in c or 'O.R.' in c), None)

    if not col_vin_t or not col_fec_t:
        return None, f"Taller: Faltan columnas clave (Bastidor/Cierre). (Cols: {list(df_t.columns)})"

    df_t['Fecha_Servicio'] = df_t[col_fec_t].apply(clean_date)
    df_t['VIN'] = df_t[col_vin_t].astype(str).str.strip().str.upper()
    
    if col_km:
        df_t['Km'] = df_t[col_km].astype(str).str.replace('.','').str.replace(',','.')
        df_t['Km'] = pd.to_numeric(df_t['Km'], errors='coerce').fillna(0)
    else: df_t['Km'] = 0

    # Filtro Chapa
    if col_or:
        mask = ~df_t[col_or].astype(str).str.contains('CHAPA|PINTURA|SINIESTRO', case=False, na=False)
        df_t = df_t[mask]

    # Clasificar
    def clasif(k):
        if 5000 <= k <= 15000: return "1er"
        elif 15001 <= k <= 25000: return "2do"
        elif 25001 <= k <= 35000: return "3er"
        return None
    
    df_t['Hito'] = df_t['Km'].apply(clasif)
    df_validos = df_t.dropna(subset=['Hito'])

    # Cruzar
    merged = pd.merge(df_v, df_validos[['VIN', 'Hito']], on='VIN', how='left')
    pivot = merged.pivot_table(index=['VIN', 'Año_Venta'], columns='Hito', aggfunc='size', fill_value=0).reset_index()
    
    for c in ['1er', '2do', '3er']:
        if c not in pivot.columns: pivot[c] = 0
        else: pivot[c] = pivot[c].apply(lambda x: 1 if x > 0 else 0)
        
    res = pivot.groupby('Año_Venta')[['1er', '2do', '3er']].mean()
    return res, "OK"

# --- MAIN APP ---
ID_SHEET = "1yJgaMR0nEmbKohbT_8Vj627Ma4dURwcQTQcQLPqrFwk"

try:
    data = cargar_datos(ID_SHEET)
    
    if data:
        # Preprocesamiento Básico
        for h in data:
            col_f = find_col(data[h], ["FECHA"]) or data[h].columns[0]
            data[h]['Fecha_dt'] = pd.to_datetime(data[h][col_f], dayfirst=True, errors='coerce')
            data[h]['Mes'] = data[h]['Fecha_dt'].dt.month
            data[h]['Año'] = data[h]['Fecha_dt'].dt.year

        with st.sidebar:
            if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
            st.header("Filtros")
            anios = sorted([int(x) for x in data['CALENDARIO']['Año'].unique() if x > 0], reverse=True)
            anio_sel = st.selectbox("📅 Año", anios)
            
            meses_nom = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
            df_y = data['CALENDARIO'][data['CALENDARIO']['Año'] == anio_sel]
            mes_sel = st.selectbox("📅 Mes", sorted(df_y['Mes'].unique(), reverse=True), format_func=lambda x: meses_nom.get(x))

        # Helpers de obtención de datos
        def get_val(df, keys):
            if df is None: return 0
            row = df[(df['Año'] == anio_sel) & (df['Mes'] == mes_sel)]
            if row.empty: return 0
            col = find_col(df, keys, exclude_keywords=["OBJ"])
            return float(row[col].iloc[0]) if col else 0

        def get_obj(df, keys):
            if df is None: return 1
            row = df[(df['Año'] == anio_sel) & (df['Mes'] == mes_sel)]
            if row.empty: return 1
            col = find_col(df, ["OBJ"] + keys)
            return float(row[col].iloc[0]) if col else 1

        # Avance temporal
        dias_hab = get_obj(data['CALENDARIO'], ["HAB"])
        dias_trans = get_val(data['CALENDARIO'], ["TRANS"])
        prog_t = min(dias_trans / dias_hab if dias_hab > 0 else 0, 1.0)
        
        # --- UI LAYOUT ---
        st.title(f"Tablero Posventa - {meses_nom.get(mes_sel)} {anio_sel}")
        tabs = st.tabs(["🏠 Objetivos", "🛠️ Servicios", "📦 Repuestos", "🎨 Chapa y Pintura", "📈 Histórico"])

        with tabs[0]: # OBJETIVOS
            c1, c2, c3, c4 = st.columns(4)
            
            # MO Servicios
            real_mo = sum([get_val(data['SERVICIOS'], ["MO", k]) for k in ["CLI", "GAR", "INT", "TER"]])
            obj_mo = get_obj(data['SERVICIOS'], ["MO"])
            c1.metric("
