import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import os

st.set_page_config(page_title="Grupo CENOA - Gestión Posventa", layout="wide")

# --- 1. CONFIGURACIÓN Y MAPEOS ---
ASESORES_MAP = {
    "1": "Claudio Molina", "3": "Belen Juarez", "4": "Fatima Polli", "8": "Daniel Espin",
    "11": "César Oliva", "12": "Hector Corrales", "13": "Nazareno Segovia", "14": "Haydee Garnica",
    "21": "Javier Gutierrez", "22": "Antonio Mogro", "23": "Samuel Antunez", 
    "28": "Fernanda Barranco", "29": "Ricardo Alvarez", "30": "Andrea Martins", "31": "Cristian Portal"
}

CODIGOS_CYP = ['1B', '3G'] 

# --- ESTILO CSS ---
st.markdown("""<style>
    .block-container { padding-top: 1rem; padding-bottom: 2rem; }
    .main { background-color: #f4f7f9; }
    
    .portada-container { 
        background: linear-gradient(90deg, #00235d 0%, #004080 100%); 
        color: white; 
        padding: 1rem 1.5rem; 
        border-radius: 10px; 
        margin-bottom: 1rem; 
        display: flex; 
        justify-content: space-between; 
        align-items: center;
        flex-wrap: wrap;
        gap: 15px;
    }
    .kpi-card { background-color: white; border: 1px solid #e0e0e0; padding: 12px 15px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 8px; min-height: 145px; display: flex; flex-direction: column; justify-content: space-between; }
    .kpi-card p { font-size: 0.85rem; margin: 0; color: #666; font-weight: 600; }
    .kpi-card h2 { font-size: 1.8rem; margin: 4px 0; color: #00235d; } 
    .kpi-subtext { font-size: 0.75rem; color: #888; }
    .metric-card { background-color: white; border: 1px solid #dee2e6; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; height: 100%; display: flex; flex-direction: column; justify-content: center; min-height: 110px; }
    .metric-footer { border-top: 1px solid #f0f0f0; margin-top: 8px; padding-top: 6px; font-size: 0.7rem; display: flex; justify-content: space-between; color: #666; }
    .cyp-detail { background-color: #f8f9fa; padding: 8px; border-radius: 6px; font-size: 0.8rem; margin-top: 5px; border-left: 3px solid #00235d; line-height: 1.3; }
    .cyp-header { font-weight: bold; color: #00235d; font-size: 0.85rem; margin-bottom: 2px; display: block; }
</style>""", unsafe_allow_html=True)

# --- FUNCIÓN DE BÚSQUEDA ---
def find_col(df, include_keywords, exclude_keywords=[]):
    if df is None: return ""
    for col in df.columns:
        col_upper = col.upper()
        if all(k.upper() in col_upper for k in include_keywords):
            if not any(x.upper() in col_upper for x in exclude_keywords):
                return col
    return ""

# --- CARGA DE DATOS ROBUSTA ---
@st.cache_data(ttl=60)
def cargar_datos(sheet_id):
    hojas = ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA', 'WIP']
    data_dict = {}
    
    for h in hojas:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={h.replace(' ', '%20')}"
        try:
            df = pd.read_csv(url, dtype=str).fillna("0")
            
            # Limpieza de Nombres de Columnas
            df.columns = [
                c.strip().upper()
                .replace(".", "")
                .replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
                .replace("Ñ", "N") 
                for c in df.columns
            ]
            
            # --- LIMPIEZA NUMÉRICA FORMATO ARGENTINO ---
            for col in df.columns:
                if not any(x in col for x in ["FECHA", "CANAL", "ESTADO", "MATRICUL", "MODELO", "DESCRIPCION", "TIPO", "VIN", "BASTIDOR", "NOMBRE"]):
                    serie = df[col].astype(str).str.replace(r'[^\d.,-]', '', regex=True)
                    serie = serie.str.replace('.', '', regex=False)
                    serie = serie.str.replace(',', '.', regex=False)
                    df[col] = pd.to_numeric(serie, errors='coerce').fillna(0.0)
            
            data_dict[h] = df
        except Exception as e:
            if h != 'WIP': st.error(f"Error cargando hoja {h}: {e}")
            else: pass 
                
    return data_dict

# --- PROCESAMIENTO IRPV ---
def leer_csv_inteligente(uploaded_file):
    try:
        uploaded_file.seek(0)
        preview = pd.read_csv(uploaded_file, header=None, nrows=20, sep=None, engine='python', encoding='utf-8', on_bad_lines='skip')
        idx_header = -1
        keywords = ['BASTIDOR', 'VIN', 'CHASIS', 'MATRICULA', 'REF.OR']
        for i, row in preview.iterrows():
            row_txt = " ".join([str(x).upper() for x in row.values])
            if any(kw in row_txt for kw in keywords):
                idx_header = i
                break
        if idx_header == -1: idx_header = 0
        
        uploaded_file.seek(0)
        try:
            df = pd.read_csv(uploaded_file, header=idx_header, sep=';', encoding='utf-8', on_bad_lines='skip')
        except:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, header=idx_header, sep=',', encoding='utf-8', on_bad_lines='skip')
        return df, "OK"
    except Exception as e:
        return None, str(e)

def procesar_irpv(file_v, file_t):
    df_v, msg_v = leer_csv_inteligente(file_v)
    if df_v is None: return None, f"Ventas: {msg_v}"
    df_v.columns = [str(c).upper().strip() for c in df_v.columns]
    
    col_vin = next((c for c in df_v.columns if 'BASTIDOR' in c or 'VIN' in c), None)
    col_fec = next((c for c in df_v.columns if 'FEC' in c or 'ENTR' in c), None)
    if not col_vin or not col_fec: return None, "Ventas: Faltan columnas VIN/Fecha"

    def clean_date(x):
        try: return pd.to_datetime(x, dayfirst=True)
        except: return pd.NaT

    df_v['Fecha_Entrega'] = df_v[col_fec].apply(clean_date)
    df_v['Año_Venta'] = df_v['Fecha_Entrega'].dt.year
    df_v['VIN'] = df_v[col_vin].astype(str).str.strip().str.upper()
    df_v = df_v.dropna(subset=['VIN', 'Fecha_Entrega'])

    df_t, msg_t = leer_csv_inteligente(file_t)
    if df_t is None: return None, f"Taller: {msg_t}"
    df_t.columns = [str(c).upper().strip() for c in df_t.columns]
    
    col_vin_t = next((c for c in df_t.columns if 'BASTIDOR' in c or 'VIN' in c), None)
    col_fec_t = next((c for c in df_t.columns if 'CIERRE' in c or 'FEC' in c), None)
    col_km = next((c for c in df_t.columns if 'KM' in c), None)
    col_or = next((c for c in df_t.columns if 'TIPO' in c or 'O.R.' in c), None)
    col_desc = next((c for c in df_t.columns if 'DESCR' in c or 'OPER' in c or 'TRABAJO' in c), None)
    if not col_vin_t or not col_fec_t: return None, "Taller: Faltan columnas VIN/Fecha"

    df_t['Fecha_Servicio'] = df_t[col_fec_t].apply(clean_date)
    df_t['VIN'] = df_t[col_vin_t].astype(str).str.strip().str.upper()
    df_t['Km'] = pd.to_numeric(df_t[col_km], errors='coerce').fillna(0) if col_km else 0
    df_t['Texto'] = df_t[col_desc].astype(str).str.upper() if col_desc else ""

    if col_or:
        mask = ~df_t[col_or].astype(str).str.contains('CHAPA|PINTURA|SINIESTRO', case=False, na=False)
        df_t = df_t[mask]

    def clasif_hibrida(row):
        k = row['Km']
        t = row['Texto']
        if (2500 <= k <= 16500) or any(w in t for w in ["10.000", "10K", "1ER", "PRIMER", "DIEZ MIL"]): return "1er"
        if (16501 <= k <= 27000) or any(w in t for w in ["20.000", "20K", "2DO", "SEGUNDO", "VEINTE MIL"]): return "2do"
        if (27001 <= k <= 38000) or any(w in t for w in ["30.000", "30K", "3ER", "TERCER", "TREINTA MIL"]): return "3er"
        return None
    
    df_t['Hito'] = df_t.apply(clasif_hibrida, axis=1)
    df_validos = df_t.dropna(subset=['Hito'])
    pivot_dates = df_validos.pivot_table(index='VIN', columns='Hito', values='Fecha_Servicio', aggfunc='min').reset_index()
    merged = pd.merge(df_v, pivot_dates, on='VIN', how='left')
    hoy = datetime.now()

    def evaluar(row, actual, anterior=None):
        if actual == '1er': base = row['Fecha_Entrega']
        else: base = row.get(anterior, pd.NaT)
        if pd.isna(base): return np.nan 
        limite = base + timedelta(days=365)
        hecho = row.get(actual, pd.NaT)
        if not pd.isna(hecho): return 1.0 
        if hoy >= limite: return 0.0 
        return np.nan 

    merged['R_1er'] = merged.apply(lambda r: evaluar(r, '1er'), axis=1)
    merged['R_2do'] = merged.apply(lambda r: evaluar(r, '2do', '1er'), axis=1)
    merged['R_3er'] = merged.apply(lambda r: evaluar(r, '3er', '2do'), axis=1)
    res = merged.groupby('Año_Venta')[['R_1er', 'R_2do', 'R_3er']].mean()
    res.columns = ['1er', '2do', '3er']
    return res, "OK"

# --- TRANSFORMACIÓN DE DATOS WIP DESDE SHEET ---
def preparar_wip_desde_sheet(df):
    if df is None or df.empty: return None
    
    col_saldo = find_col(df, ['TOTAL', 'IMPTO']) or find_col(df, ['SALDO'])
    if not col_saldo: return None
    
    col_matricula = find_col(df, ['MATRICUL'])
    col_idv = find_col(df, ['IDV'])
    col_rec = find_col(df, ['REC'])
    col_tipo = find_col(df, ['TIPO'])
    col_fecha = find_col(df, ['FEC', 'AP'])
    col_modelo = find_col(df, ['MODELO'])

    df['Saldo'] = df[col_saldo] 
    
    if col_matricula and col_idv:
        df['Identificador'] = df[col_matricula].replace('0', np.nan).fillna(df[col_idv].astype(str))
    elif col_matricula:
        df['Identificador'] = df[col_matricula]
    else:
        df['Identificador'] = "S/D"
    df['Identificador'] = df['Identificador'].astype(str).str.strip().str.upper()

    def obtener_nombre_asesor(val):
        try:
            val_clean = str(val).split('.')[0] 
            return ASESORES_MAP.get(val_clean, f"Asesor {val_clean}")
        except:
            return "Sin Asesor"
            
    if col_rec:
        df['Nombre_Asesor'] = df[col_rec].apply(obtener_nombre_asesor)
    else:
        df['Nombre_Asesor'] = "Desconocido"

    def clasificar_taller(texto_tipo):
        if pd.isna(texto_tipo): return 'Mecánica'
        codigo = str(texto_tipo).strip().upper()[:2]
        if codigo in CODIGOS_CYP: return 'Chapa y Pintura'
        return 'Mecánica'

    if col_tipo:
        df['Tipo_Taller'] = df[col_tipo].apply(clasificar_taller)
        df['Tipo'] = df[col_tipo] 
    else:
        df['Tipo_Taller'] = 'Mecánica'
        df['Tipo'] = 'S/D'

    if col_fecha:
        df['Fecha_Alta'] = pd.to_datetime(df[col_fecha], dayfirst=True, errors='coerce')
    else:
        df['Fecha_Alta'] = pd.NaT

    if col_modelo: df['Modelo'] = df[col_modelo]
    else: df['Modelo'] = ""
    
    col_ref = find_col(df, ['REF', 'OR'])
    if col_ref: df['Ref.OR'] = df[col_ref]
    else: df['Ref.OR'] = ""

    return df

# --- MAIN APP ---
ID_SHEET = "1yJgaMR0nEmbKohbT_8Vj627Ma4dURwcQTQcQLPqrFwk"

try:
    data = cargar_datos(ID_SHEET)
    
    if data:
        for h in ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA']:
            if h in data:
                col_f = find_col(data[h], ["FECHA"]) or data[h].columns[0]
                data[h]['Fecha_dt'] = pd.to_datetime(data[h][col_f], dayfirst=True, errors='coerce')
                data[h]['Mes'] = data[h]['Fecha_dt'].dt.month
                data[h]['Año'] = data[h]['Fecha_dt'].dt.year

        canales_repuestos = ['MOSTRADOR', 'TALLER', 'INTERNA', 'GAR', 'CYP', 'MAYORISTA', 'SEGUROS']

        with st.sidebar:
            if os.path.exists("logo.png"):
                st.image("logo.png", use_container_width=True)
                
            st.header("1. Filtros Temporales")
            años_disp = sorted([int(a) for a in data['CALENDARIO']['Año'].unique() if a > 0], reverse=True)
            año_sel = st.selectbox("📅 Año", años_disp)
            
            meses_nom = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
            df_year = data['CALENDARIO'][data['CALENDARIO']['Año'] == año_sel]
            meses_disp = sorted(df_year['Mes'].unique(), reverse=True)
            mes_sel = st.selectbox("📅 Mes", meses_disp, format_func=lambda x: meses_nom.get(x, "N/A"))

            st.markdown("---")
            st.header("2. Carga IRPV")
            
            if 'df_irpv_cache' not in st.session_state: st.session_state.df_irpv_cache = None

            with st.expander("🔄 Historial IRPV", expanded=False):
                up_v = st.file_uploader("Entregas 0km", type=["csv"], key="v_uploader")
                up_t = st.file_uploader("Historial Taller", type=["csv"], key="t_uploader")
                
                if up_v and up_t:
                    if st.session_state.df_irpv_cache is None:
                        df_irpv, msg_irpv = procesar_irpv(up_v, up_t)
                        if df_irpv is not None:
                            st.session_state.df_irpv_cache = df_irpv
                            st.success("IRPV Procesado OK")
                        else:
                            st.error(msg_irpv)
                else:
                    st.session_state.df_irpv_cache = None

        def get_row(df):
            res = df[(df['Año'] == año_sel) & (df['Mes'] == mes_sel)].sort_values('Fecha_dt')
            return res.iloc[-1] if not res.empty else pd.Series(dtype='object')

        c_r = get_row(data['CALENDARIO'])
        s_r = get_row(data['SERVICIOS'])
        r_r = get_row(data['REPUESTOS'])
        t_r = get_row(data['TALLER'])
        cj_r = get_row(data['CyP JUJUY'])
        cs_r = get_row(data['CyP SALTA'])

        col_trans = find_col(data['CALENDARIO'], ["TRANS"]) 
        col_hab = find_col(data['CALENDARIO'], ["HAB"])
        d_t = float(c_r.get(col_trans, 0))
        d_h = float(c_r.get(col_hab, 22))
        
        hoy = datetime.now()
        if (año_sel < hoy.year) or (año_sel == hoy.year and mes_sel < hoy.month):
             if d_t < d_h: d_t = d_h

        prog_t = d_t / d_h if d_h > 0 else 0
        prog_t = min(prog_t, 1.0)

        # DATA HISTORICO
        def get_hist_data(sheet_name):
            df = data[sheet_name]
            df = df[df['Año'] == año_sel].sort_values('Mes')
            df = df.groupby('Mes').last().reset_index()
            df['NombreMes'] = df['Mes'].map(meses_nom)
            return df

        h_cal = get_hist_data('CALENDARIO')
        h_ser = get_hist_data('SERVICIOS')
        h_rep = get_hist_data('REPUESTOS')
        h_tal = get_hist_data('TALLER')
        h_cyp_j = get_hist_data('CyP JUJUY')
        h_cyp_s = get_hist_data('CyP SALTA')

        # --- PORTADA ---
        st.markdown(f'''
        <div class="portada-container">
            <div class="portada-left">
                <h1>Autociel - Tablero Posventa</h1>
                <h3>📅 {meses_nom.get(mes_sel)} {año_sel}</h3>
            </div>
            <div class="portada-right">
                <div>Avance: <b>{d_t:g}</b>/{d_h:g} días ({prog_t:.1%})</div>
                <div style="background: rgba(255,255,255,0.3); height: 6px; border-radius: 4px; width: 100%;">
                    <div style="background: #fff; width: {prog_t*100}%; height: 100%; border-radius: 4px;"></div>
                </div>
            </div>
        </div>
        ''', unsafe_allow_html=True)

        menu_opts = ["🏠 Objetivos", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura", "📈 Histórico"]
        selected_tab = st.radio("", menu_opts, horizontal=True, label_visibility="collapsed")
        st.markdown("---")

        # --- HELPERS VISUALES ---
        def render_kpi_card(title, real, obj_mes, is_currency=True, unit="", show_daily=False):
            obj_parcial = obj_mes * prog_t
            proy = (real / d_t) * d_h if d_t > 0 else 0
            cumpl_proy = proy / obj_mes if obj_mes > 0 else 0
            fmt = "${:,.0f}" if is_currency else "{:,.0f}"
            if unit: fmt += f" {unit}"
            color = "#dc3545" if cumpl_proy < 0.90 else ("#ffc107" if cumpl_proy < 0.98 else "#28a745")
            icon = "✅" if real >= obj_parcial else "🔻"
            cumpl_parcial_pct = real / obj_parcial if obj_parcial > 0 else 0
            daily_html = ""
            if show_daily:
                daily_val = real / d_t if d_t > 0 else 0
                fmt_daily = "${:,.0f}" if is_currency else "{:,.1f}"
                daily_html = f'<div style="font-size:0.75rem; color:#00235d; background-color:#eef2f7; padding: 1px 6px; border-radius:4px; display:inline-block; margin-bottom:4px;">Prom: <b>{fmt_daily.format(daily_val)}</b> /día</div>'

            html = '<div class="kpi-card">'
            html += f'<div><p>{title}</p><h2>{fmt.format(real)}</h2>{daily_html}</div>'
            html += f'<div><div class="kpi-subtext">vs Obj. Parcial: <b>{fmt.format(obj_parcial)}</b> <span style="color:{"#28a745" if real >= obj_parcial else "#dc3545"}">({cumpl_parcial_pct:.1%})</span> {icon}</div>'
            html += '<hr style="margin:5px 0; border:0; border-top:1px solid #eee;">'
            html += f'<div style="display:flex; justify-content:space-between; font-size:0.75rem; margin-bottom:2px;"><span>Obj. Mes:</span><b>{fmt.format(obj_mes)}</b></div>'
            html += f'<div style="display:flex; justify-content:space-between; font-size:0.75rem; color:{color}; font-weight:bold;"><span>Proyección:</span><span>{fmt.format(proy)} ({cumpl_proy:.1%})</span></div>'
            html += f'<div style="margin-top:5px;"><div style="width:100%; background:#e0e0e0; height:5px; border-radius:10px;"><div style="width:{min(cumpl_proy*100, 100)}%; background:{color}; height:5px; border-radius:10px;"></div></div></div></div></div>'
            return html

        def render_kpi_small(title, val, target=None, target_mensual=None, projection=None, format_str="{:.1%}", label_target="Obj. Parcial"):
            subtext_html = "<div style='height:15px;'></div>"
            footer_html = ""
            if target is not None:
                delta = val - target
                color = "#28a745" if delta >= 0 else "#dc3545"
                icon = "▲" if delta >= 0 else "▼"
                subtext_html = f"<div style='margin-top:4px; display:flex; justify-content:center; align-items:center; gap:5px; font-size:0.7rem;'><span style='color:#888;'>{label_target}: {format_str.format(target)}</span><span style='color:{color}; font-weight:bold; background-color:{color}15; padding:1px 4px; border-radius:3px;'>{icon} {format_str.format(abs(delta))}</span></div>"
            if target_mensual is not None and projection is not None:
                proy_delta = projection - target_mensual
                color_proy = "#28a745" if proy_delta >= 0 else "#dc3545"
                footer_html = f'<div class="metric-footer"><div>Obj. Mes: <b>{format_str.format(target_mensual)}</b></div><div style="color:{color_proy}">Proy: <b>{format_str.format(projection)}</b></div></div>'
            html = f'<div class="metric-card"><div><p style="color:#666; font-size:0.8rem; margin-bottom:2px;">{title}</p><h3 style="color:#00235d; margin:0; font-size:1.3rem;">{format_str.format(val)}</h3>{subtext_html}</div>{footer_html}</div>'
            return html

        # --- LÓGICA DE COLUMNAS (SERVICIOS) ---
        c_cli = find_col(data['SERVICIOS'], ["MO", "CLI"], exclude_keywords=["OBJ"])
        c_gar = find_col(data['SERVICIOS'], ["MO", "GAR"], exclude_keywords=["OBJ"])
        c_int = find_col(data['SERVICIOS'], ["MO", "INT"], exclude_keywords=["OBJ"])
        if not c_int: c_int = find_col(data['SERVICIOS'], ["INTERNA"], exclude_keywords=["OBJ", "MO"])
        c_ter = find_col(data['SERVICIOS'], ["MO", "TERCERO"], exclude_keywords=["OBJ"])
        if not c_ter: c_ter = find_col(data['SERVICIOS'], ["MO", "TERCEROS"], exclude_keywords=["OBJ"])
        if not c_ter: c_ter = find_col(data['SERVICIOS'], ["MO", "TER"], exclude_keywords=["OBJ"])
        if not c_ter: c_ter = find_col(data['SERVICIOS'], ["TERCERO"], exclude_keywords=["OBJ", "MO", "COSTO"])

        val_cli = s_r.get(c_cli, 0) if c_cli else 0
        val_gar = s_r.get(c_gar, 0) if c_gar else 0
        val_int = s_r.get(c_int, 0) if c_int else 0
        val_ter = s_r.get(c_ter, 0) if c_ter else 0
        real_mo_total = val_cli + val_gar + val_int + val_ter
        
        # --- TAB 1: OBJETIVOS ---
        if selected_tab == "🏠 Objetivos":
            cols = st.columns(4)
            real_rep = sum([r_r.get(find_col(data['REPUESTOS'], ["VENTA", c], exclude_keywords=["OBJ"]), 0) for c in canales_repuestos])
            def get_cyp_total(row, df_nom):
                mo = row.get(find_col(data[df_nom], ["MO", "PUR"]), 0) + row.get(find_col(data[df_nom], ["MO", "TER"]), 0)
                rep = row.get(find_col(data[df_nom], ["FACT", "REP"]), 0) 
                return mo + rep
            metas = [
                ("M.O. Servicios", real_mo_total, s_r.get(find_col(data['SERVICIOS'], ["OBJ", "MO"]), 1)),
                ("Repuestos", real_rep, r_r.get(find_col(data['REPUESTOS'], ["OBJ", "FACT"]), 1)),
                ("CyP Jujuy", get_cyp_total(cj_r, 'CyP JUJUY'), cj_r.get(find_col(data['CyP JUJUY'], ["OBJ", "FACT"]), 1)),
                ("CyP Salta", get_cyp_total(cs_r, 'CyP SALTA'), cs_r.get(find_col(data['CyP SALTA'], ["OBJ", "FACT"]), 1))
            ]
            for i, (tit, real, obj) in enumerate(metas):
                with cols[i]: st.markdown(render_kpi_card(tit, real, obj, True), unsafe_allow_html=True)

        elif selected_tab == "🛠️ Servicios y Taller":
            col_main, col_breakdown = st.columns([1, 2])
            obj_mo_total = s_r.get(find_col(data['SERVICIOS'], ["OBJ", "MO"]), 1)
            with col_main: st.markdown(render_kpi_card("Facturación M.O.", real_mo_total, obj_mo_total, show_daily=True), unsafe_allow_html=True)
            with col_breakdown:
                df_mo = pd.DataFrame({"Cargo": ["Cliente", "Garantía", "Interno", "Terceros"], "Facturación": [val_cli, val_gar, val_int, val_ter]})
                fig_mo = px.bar(df_mo, x="Facturación", y="Cargo", orientation='h', text_auto='.2s', title="", color="Cargo", color_discrete_sequence=["#00235d", "#28a745", "#ffc107", "#17a2b8"])
                fig_mo.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=160) 
                st.plotly_chart(fig_mo, use_container_width=True)

            k1, k2, k3, k4, k5 = st.columns(5)
            c_cpus = find_col(data['SERVICIOS'], ["CPUS"], exclude_keywords=["OBJ"])
            c_tus_others = find_col(data['SERVICIOS'], ["OTROS", "CARGOS"], exclude_keywords=["OBJ"])
            real_cpus = s_r.get(c_cpus, 0)
            real_tus = real_cpus + s_r.get(c_tus_others, 0)
            obj_cpus = s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'CPUS']), 1)
            obj_tus = s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'TUS']), 1)
            div = real_cpus if real_cpus > 0 else 1
            tp_mo = real_mo_total / div
            tgt_tp_mo = obj_mo_total / obj_cpus if obj_cpus > 0 else 0
            
            hf_cc = t_r.get(find_col(data['TALLER'], ["FACT", "CC"]), 0)
            hf_cg = t_r.get(find_col(data['TALLER'], ["FACT", "CG"]), 0)
            hf_ci = t_r.get(find_col(data['TALLER'], ["FACT", "CI"]), 0)
            tp_hs = (hf_cc+hf_cg+hf_ci) / div
            
            v_rep_taller = r_r.get(find_col(data['REPUESTOS'], ["VENTA", "TALLER"], exclude_keywords=["OBJ"]), 0)
            v_rep_gar = r_r.get(find_col(data['REPUESTOS'], ["VENTA", "GAR"], exclude_keywords=["OBJ"]), 0)
            v_rep_int = r_r.get(find_col(data['REPUESTOS'], ["VENTA", "INT"], exclude_keywords=["OBJ"]), 0)
            tp_rep = (v_rep_taller + v_rep_gar + v_rep_int) / div

            with k1: st.markdown(render_kpi_card("TUS Total", real_tus, obj_tus, is_currency=False, show_daily=True), unsafe_allow_html=True)
            with k2: st.markdown(render_kpi_card("CPUS (Entradas)", real_cpus, obj_cpus, is_currency=False, show_daily=True), unsafe_allow_html=True)
            with k3: st.markdown(render_kpi_small("Ticket Prom. (Hs)", tp_hs, None, None, None, "{:.2f} hs"), unsafe_allow_html=True)
            with k4: st.markdown(render_kpi_small("Ticket Prom. MO", tp_mo, tgt_tp_mo, None, None, "${:,.0f}"), unsafe_allow_html=True)
            with k5: st.markdown(render_kpi_small("Ticket Prom. Rep", tp_rep, None, None, None, "${:,.0f}"), unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("### 🏆 Calidad e Incentivos de Marca")
            val_prima_p = s_r.get(find_col(data['SERVICIOS'], ["PRIMA", "PEUGEOT"], exclude_keywords=["OBJ"]), 0)
            val_prima_c = s_r.get(find_col(data['SERVICIOS'], ["PRIMA", "CITROEN"], exclude_keywords=["OBJ"]), 0)
            obj_prima_p = s_r.get(find_col(data['SERVICIOS'], ["OBJ", "PRIMA", "PEUGEOT"]), 0)
            obj_prima_c = s_r.get(find_col(data['SERVICIOS'], ["OBJ", "PRIMA", "CITROEN"]), 0)

            def get_calidad_data(keyword_main, brand, is_percent=False, prorate_target=False):
                c_real = find_col(data['SERVICIOS'], [keyword_main, brand], exclude_keywords=["OBJ"])
                c_obj = find_col(data['SERVICIOS'], ["OBJ", keyword_main, brand])
                if not c_obj: c_obj = find_col(data['SERVICIOS'], ["OBJ", keyword_main])
                val_real = s_r.get(c_real, 0)
                df_mes = data['SERVICIOS'][(data['SERVICIOS']['Año'] == año_sel) & (data['SERVICIOS']['Mes'] == mes_sel)]
                if not df_mes.empty and c_obj: val_obj_mensual = df_mes[c_obj].max() 
                else: val_obj_mensual = 0
                val_proyeccion = val_real / prog_t if prog_t > 0 else 0
                if prorate_target: val_obj_parcial = val_obj_mensual * prog_t
                else: val_obj_parcial = val_obj_mensual; val_proyeccion = val_real 
                if is_percent:
                    if val_real > 1.0: val_real /= 100
                    if val_obj_parcial > 1.0: val_obj_parcial /= 100
                    if val_obj_mensual > 1.0: val_obj_mensual /= 100
                    if val_proyeccion > 1.0: val_proyeccion /= 100
                    fmt = "{:.1%}"
                else: fmt = "{:,.0f}" if not prorate_target else "{:,.1f}" 
                return val_real, val_obj_parcial, val_obj_mensual, val_proyeccion, fmt

            nps_p_r, nps_p_p, nps_p_m, nps_p_proy, fmt_nps = get_calidad_data("NPS", "PEUGEOT", is_percent=False, prorate_target=False)
            nps_c_r, nps_c_p, nps_c_m, nps_c_proy, _ = get_calidad_data("NPS", "CITROEN", is_percent=False, prorate_target=False)
            vc_p_r, vc_p_p, vc_p_m, vc_p_proy, fmt_vc = get_calidad_data("VIDEO", "PEUGEOT", is_percent=False, prorate_target=True)
            vc_c_r, vc_c_p, vc_c_m, vc_c_proy, _ = get_calidad_data("VIDEO", "CITROEN", is_percent=False, prorate_target=True)
            ff_p_r, ff_p_p, ff_p_m, ff_p_proy, fmt_ff = get_calidad_data("FORFAIT", "PEUGEOT", is_percent=False, prorate_target=True)
            ff_c_r, ff_c_p, ff_c_m, ff_c_proy, _ = get_calidad_data("FORFAIT", "CITROEN", is_percent=False, prorate_target=True)

            c_peugeot, c_citroen = st.columns(2)
            with c_peugeot:
                st.markdown("#### 🦁 Peugeot")
                st.markdown(render_kpi_small("NPS", nps_p_r, nps_p_p, None, None, fmt_nps, label_target="Obj"), unsafe_allow_html=True)
                p_row = st.columns(2)
                with p_row[0]: st.markdown(render_kpi_small("Videocheck", vc_p_r, vc_p_p, vc_p_m, vc_p_proy, fmt_vc), unsafe_allow_html=True)
                with p_row[1]: st.markdown(render_kpi_small("Forfait", ff_p_r, ff_p_p, ff_p_m, ff_p_proy, fmt_ff), unsafe_allow_html=True)
                st.markdown(f'<div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; padding: 10px; margin-top: 10px; text-align: center;"><p style="margin: 0; color: #666; font-size: 0.75rem; font-weight: bold; text-transform: uppercase;">Posible Cobro Peugeot</p><p style="margin: 0; color: #28a745; font-size: 1.1rem; font-weight: bold;">${val_prima_p:,.0f}</p><p style="margin: 0; color: #999; font-size: 0.65rem;">Techo de Meta: ${obj_prima_p:,.0f}</p></div>', unsafe_allow_html=True)

            with c_citroen:
                st.markdown("#### 🔴 Citroën")
                st.markdown(render_kpi_small("NPS", nps_c_r, nps_c_p, None, None, fmt_nps, label_target="Obj"), unsafe_allow_html=True)
                c_row = st.columns(2)
                with c_row[0]: st.markdown(render_kpi_small("Videocheck", vc_c_r, vc_c_p, vc_c_m, vc_c_proy, fmt_vc), unsafe_allow_html=True)
                with c_row[1]: st.markdown(render_kpi_small("Forfait", ff_c_r, ff_c_p, ff_c_m, ff_c_proy, fmt_ff), unsafe_allow_html=True)
                st.markdown(f'<div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; padding: 10px; margin-top: 10px; text-align: center;"><p style="margin: 0; color: #666; font-size: 0.75rem; font-weight: bold; text-transform: uppercase;">Posible Cobro Citroën</p><p style="margin: 0; color: #28a745; font-size: 1.1rem; font-weight: bold;">${val_prima_c:,.0f}</p><p style="margin: 0; color: #999; font-size: 0.65rem;">Techo de Meta: ${obj_prima_c:,.0f}</p></div>', unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("### ⚙️ Taller")
            col_tecs = find_col(data['TALLER'], ["TECNICOS"], exclude_keywords=["PROD"])
            if not col_tecs: col_tecs = find_col(data['TALLER'], ["DOTACION"])
            cant_tecs = t_r.get(col_tecs, 6) 
            if cant_tecs == 0: cant_tecs = 6
            ht_cc = t_r.get(find_col(data['TALLER'], ["TRAB", "CC"]), 0)
            ht_cg = t_r.get(find_col(data['TALLER'], ["TRAB", "CG"]), 0)
            ht_ci = t_r.get(find_col(data['TALLER'], ["TRAB", "CI"]), 0)
            ef_cc = hf_cc / ht_cc if ht_cc > 0 else 0
            ef_cg = hf_cg / ht_cg if ht_cg > 0 else 0
            ef_ci = hf_ci / ht_ci if ht_ci > 0 else 0
            ef_gl = (hf_cc+hf_cg+hf_ci) / (ht_cc+ht_cg+ht_ci) if (ht_cc+ht_cg+ht_ci) > 0 else 0
            hs_disp = t_r.get(find_col(data['TALLER'], ["DISPONIBLES", "REAL"]), 0)
            hs_teoricas = cant_tecs * 8 * d_t 
            presencia = hs_disp / hs_teoricas if hs_teoricas > 0 else 0
            ocup = (ht_cc+ht_cg+ht_ci) / hs_disp if hs_disp > 0 else 0
            prod = t_r.get(find_col(data['TALLER'], ["PRODUCTIVIDAD", "TALLER"]), 0)
            if prod > 2: prod /= 100

            e1, e2, e3, e4 = st.columns(4)
            with e1: st.markdown(render_kpi_small("Eficiencia CC", ef_cc, 1.0), unsafe_allow_html=True)
            with e2: st.markdown(render_kpi_small("Eficiencia Gar.", ef_cg, 1.0), unsafe_allow_html=True)
            with e3: st.markdown(render_kpi_small("Eficiencia Int.", ef_ci, 0.20), unsafe_allow_html=True)
            with e4: st.markdown(render_kpi_small("Eficiencia Global", ef_gl, 0.85), unsafe_allow_html=True)

            u1, u2, u3 = st.columns(3)
            with u1: st.markdown(render_kpi_small("Presencia", presencia, 0.95), unsafe_allow_html=True)
            with u2: st.markdown(render_kpi_small("Ocupación", ocup, 0.95), unsafe_allow_html=True)
            with u3: st.markdown(render_kpi_small("Productividad", prod, 0.95), unsafe_allow_html=True)

            g1, g2 = st.columns(2)
            with g1: st.plotly_chart(px.pie(values=[ht_cc, ht_cg, ht_ci], names=["CC", "CG", "CI"], hole=0.4, title="Hs Trabajadas"), use_container_width=True)
            with g2: st.plotly_chart(px.pie(values=[hf_cc, hf_cg, hf_ci], names=["CC", "CG", "CI"], hole=0.4, title="Hs Facturadas"), use_container_width=True)

            # --- MÓDULO WIP (ÓRDENES ABIERTAS) - AHORA DESDE GOOGLE SHEETS ---
            st.markdown("---")
            st.markdown("### 📂 Gestión de Órdenes Abiertas (WIP)")
            
            if 'WIP' in data and not data['WIP'].empty:
                df_w = preparar_wip_desde_sheet(data['WIP'])
                
                if df_w is not None and not df_w.empty:
                    lista_asesores = sorted(df_w['Nombre_Asesor'].unique().tolist())
                    col_filtro, col_metricas_mini = st.columns([1, 3])
                    with col_filtro:
                        asesor_seleccionado = st.selectbox("👤 Filtrar por Asesor:", ["Todos"] + lista_asesores)
                    
                    df_filtrado = df_w[df_w['Nombre_Asesor'] == asesor_seleccionado] if asesor_seleccionado != "Todos" else df_w

                    f_plata = df_filtrado['Saldo'].sum()
                    f_autos = df_filtrado['Identificador'].nunique()
                    f_mec = df_filtrado[df_filtrado['Tipo_Taller'] == 'Mecánica']
                    f_cyp = df_filtrado[df_filtrado['Tipo_Taller'] == 'Chapa y Pintura']
                    f_plata_mec = f_mec['Saldo'].sum()
                    f_autos_mec = f_mec['Identificador'].nunique()
                    f_plata_cyp = f_cyp['Saldo'].sum()
                    f_autos_cyp = f_cyp['Identificador'].nunique()

                    kw1, kw2, kw3, kw4 = st.columns(4)
                    with kw1: st.markdown(f'<div class="metric-card"><div style="font-size:0.85rem; color:#666; font-weight:600;">Dinero Abierto ({asesor_seleccionado})</div><div style="font-size:1.5rem; color:#00235d; font-weight:bold; margin-top:5px;">${f_plata:,.0f}</div><div style="font-size:0.75rem; color:#888;">Saldo pendiente</div></div>', unsafe_allow_html=True)
                    with kw2: st.markdown(f'<div class="metric-card"><div style="font-size:0.85rem; color:#666; font-weight:600;">Autos en Taller ({asesor_seleccionado})</div><div style="font-size:1.8rem; color:#00235d; font-weight:bold; margin-top:5px;">{f_autos}</div><div style="font-size:0.75rem; color:#888;">Vehículos físicos</div></div>', unsafe_allow_html=True)
                    with kw3: st.markdown(f'<div class="metric-card"><div style="font-size:0.85rem; color:#666; font-weight:600;">Mecánica</div><div style="font-size:1.2rem; color:#00235d; font-weight:bold; margin-top:5px;">${f_plata_mec:,.0f}</div><div style="font-size:0.8rem; color:#28a745; font-weight:bold; margin-top:2px;">🚗 {f_autos_mec} autos</div></div>', unsafe_allow_html=True)
                    with kw4: st.markdown(f'<div class="metric-card"><div style="font-size:0.85rem; color:#666; font-weight:600;">Chapa y Pintura</div><div style="font-size:1.2rem; color:#00235d; font-weight:bold; margin-top:5px;">${f_plata_cyp:,.0f}</div><div style="font-size:0.8rem; color:#17a2b8; font-weight:bold; margin-top:2px;">🚙 {f_autos_cyp} autos</div></div>', unsafe_allow_html=True)
                    
                    col_graf_asesor, col_graf_cargo = st.columns([2, 1])
                    with col_graf_asesor:
                        st.markdown("##### 👥 Saldo Abierto por Asesor (Ranking Global)")
                        df_asesor = df_w.groupby('Nombre_Asesor').agg(Dinero=('Saldo', 'sum'), Autos=('Identificador', 'nunique')).reset_index().sort_values('Dinero', ascending=True)
                        df_asesor['Etiqueta'] = df_asesor.apply(lambda x: f"{x['Autos']} autos (${x['Dinero']/1000:.0f}k)", axis=1)
                        fig_wip = px.bar(df_asesor, x='Dinero', y='Nombre_Asesor', text='Etiqueta', orientation='h', title="", color='Dinero', color_continuous_scale='Blues')
                        fig_wip.update_traces(textposition='outside')
                        fig_wip.update_layout(height=500, xaxis_title="Monto ($)", yaxis_title="")
                        st.plotly_chart(fig_wip, use_container_width=True)

                    with col_graf_cargo:
                        st.markdown(f"##### 📊 Cantidad por Cargo ({asesor_seleccionado})")
                        df_filtrado['Codigo_Cargo'] = df_filtrado['Tipo'].astype(str).str.split().str[0]
                        df_cargos = df_filtrado.groupby('Codigo_Cargo').agg(Cantidad=('Identificador', 'count'), Dinero=('Saldo', 'sum')).reset_index().sort_values('Cantidad', ascending=True)
                        fig_cargos = px.bar(df_cargos, x='Cantidad', y='Codigo_Cargo', text='Cantidad', orientation='h', title="", hover_data={'Dinero':':$,.0f'}, color='Cantidad', color_continuous_scale='Reds')
                        fig_cargos.update_layout(height=500, xaxis_title="Cant. Órdenes", yaxis_title="", showlegend=False)
                        st.plotly_chart(fig_cargos, use_container_width=True)
                    
                    st.markdown(f"##### 📋 Detalle de Autos: {asesor_seleccionado}")
                    cols_ver = ['Ref.OR', 'Fecha_Alta', 'Tipo', 'Nombre_Asesor', 'Identificador', 'Modelo', 'Saldo']
                    cols_finales = [c for c in cols_ver if c in df_filtrado.columns]
                    st.dataframe(df_filtrado[cols_finales].style.format({'Saldo': "${:,.2f}", 'Fecha_Alta': '{:%d-%m-%Y}'}), use_container_width=True)
                else:
                    st.warning("⚠️ La hoja 'WIP' está vacía o no tiene las columnas correctas.")
            else:
                st.info("ℹ️ Para ver el WIP, crea una hoja llamada 'WIP' en tu Google Sheet y pega ahí los datos del reporte.")

        elif selected_tab == "📦 Repuestos":
            st.markdown("### 📦 Repuestos")
            
            # --- SECCIÓN 1: DETALLE OPERATIVO Y STOCK ---
            col_primas, col_vacia = st.columns([1, 3])
            with col_primas:
                primas_input = st.number_input("💰 Ingresar Primas/Rappels Estimados ($)", min_value=0.0, step=10000.0, format="%.0f", help="Este valor se sumará a la utilidad para calcular el margen real final.")

            detalles = []
            for c in canales_repuestos:
                v_col = find_col(data['REPUESTOS'], ["VENTA", c], exclude_keywords=["OBJ"])
                if v_col:
                    vb = r_r.get(v_col, 0)
                    d = r_r.get(find_col(data['REPUESTOS'], ["DESC", c]), 0)
                    cost = r_r.get(find_col(data['REPUESTOS'], ["COSTO", c]), 0)
                    vn = vb - d
                    ut = vn - cost
                    detalles.append({"Canal": c, "Venta Bruta": vb, "Desc.": d, "Venta Neta": vn, "Costo": cost, "Utilidad $": ut, "Margen %": (ut/vn if vn>0 else 0)})
            df_r = pd.DataFrame(detalles)
            
            vta_total_bruta = df_r['Venta Bruta'].sum() if not df_r.empty else 0
            vta_total_neta = df_r['Venta Neta'].sum() if not df_r.empty else 0
            util_total_operativa = df_r['Utilidad $'].sum() if not df_r.empty else 0
            util_total_final = util_total_operativa + primas_input
            mg_total_final = util_total_final / vta_total_neta if vta_total_neta > 0 else 0
            obj_rep_total = r_r.get(find_col(data['REPUESTOS'], ["OBJ", "FACT"]), 1)
            costo_total_mes_actual = df_r['Costo'].sum() if not df_r.empty else 0
            val_stock = float(r_r.get(find_col(data['REPUESTOS'], ["VALOR", "STOCK"]), 0))
            
            c_main, c_kpis = st.columns([1, 3])
            with c_main: st.markdown(render_kpi_card("Fact. Bruta", vta_total_bruta, obj_rep_total), unsafe_allow_html=True)
            with c_kpis:
                r2, r3, r4 = st.columns(3)
                meses_stock = val_stock / costo_total_mes_actual if costo_total_mes_actual > 0 else 0
                with r2: st.markdown(render_kpi_small("Utilidad Total (+Primas)", util_total_final, None, None, None, "${:,.0f}"), unsafe_allow_html=True)
                with r3: st.markdown(render_kpi_small("Margen Global Real", mg_total_final, 0.21, None, None, "{:.1%}"), unsafe_allow_html=True)
                with r4: st.markdown(render_kpi_small("Meses Stock", meses_stock, 4.0, None, None, "{:.1f}"), unsafe_allow_html=True)

            if not df_r.empty:
                t_vb = df_r['Venta Bruta'].sum()
                t_desc = df_r['Desc.'].sum()
                t_vn = df_r['Venta Neta'].sum()
                t_cost = df_r['Costo'].sum()
                t_ut = df_r['Utilidad $'].sum()
                t_mg = t_ut / t_vn if t_vn != 0 else 0
                df_show = pd.concat([df_r, pd.DataFrame([{"Canal": "TOTAL OPERATIVO", "Venta Bruta": t_vb, "Desc.": t_desc, "Venta Neta": t_vn, "Costo": t_cost, "Utilidad $": t_ut, "Margen %": t_mg}])], ignore_index=True)
                st.dataframe(df_show.style.format({"Venta Bruta": "${:,.0f}", "Desc.": "${:,.0f}", "Venta Neta": "${:,.0f}", "Costo": "${:,.0f}", "Utilidad $": "${:,.0f}", "Margen %": "{:.1%}"}), use_container_width=True, hide_index=True)
            
            c1, c2 = st.columns(2)
            with c1: 
                if not df_r.empty: st.plotly_chart(px.pie(df_r, values="Venta Bruta", names="Canal", hole=0.4, title="Participación"), use_container_width=True)
            with c2:
                p_vivo = float(r_r.get(find_col(data['REPUESTOS'], ["VIVO"]), 0))
                p_obs = float(r_r.get(find_col(data['REPUESTOS'], ["OBSOLETO"]), 0))
                p_muerto = float(r_r.get(find_col(data['REPUESTOS'], ["MUERTO"]), 0))
                f = 1 if p_vivo <= 1 else 100
                df_s = pd.DataFrame({"Estado": ["Vivo", "Obsoleto", "Muerto"], "Valor": [val_stock*(p_vivo/f), val_stock*(p_obs/f), val_stock*(p_muerto/f)]})
                st.plotly_chart(px.pie(df_s, values="Valor", names="Estado", hole=0.4, title="Salud del Stock", color="Estado", color_discrete_map={"Vivo": "#28a745", "Obsoleto": "#ffc107", "Muerto": "#dc3545"}), use_container_width=True)
                st.markdown(f'<div style="border: 1px solid #e6e9ef; border-radius: 5px; padding: 10px; text-align: center; background-color: #ffffff; margin-top: 10px;"><p style="margin: 0; color: #666; font-size: 0.8rem; text-transform: uppercase; font-weight: bold;">Valoración Total Stock</p><p style="margin: 0; color: #00235d; font-size: 1.2rem; font-weight: bold;">${val_stock:,.0f}</p></div>', unsafe_allow_html=True)
            
            # --- SECCIÓN 2: CONTROL DE FLUJO: COMPRAS VS COSTO (UBICACIÓN SOLICITADA) ---
            st.markdown("---")
            st.markdown("#### 📉 Control de Flujo: Compras vs Costo de Venta")
            
            # Lectura automática de Columna AB (Compra/Entrada)
            col_compra_sheet = find_col(data['REPUESTOS'], ["COMPRA", "ENTRADA"], exclude_keywords=["OBJ", "COSTO", "VENTA"])
            compra_real_sheet = float(r_r.get(col_compra_sheet, 0)) if col_compra_sheet else 0.0

            # Objetivo Terminal (Manual)
            col_obj_term_in, _ = st.columns([1, 2])
            with col_obj_term_in:
                obj_compra_terminal = st.number_input("🎯 Objetivo Compra Stellantis ($)", min_value=0.0, step=1000000.0, value=0.0)

            # Cálculos de Comparación
            costo_venta_total = df_r['Costo'].sum() if not df_r.empty else 0
            diferencia_flujo = compra_real_sheet - costo_venta_total
            
            # Regla del 20%: Costo de Venta debe ser mayor a Compras en un 20%
            # Es decir: Costo >= Compra * 1.20
            ratio_reduccion = costo_venta_total / compra_real_sheet if compra_real_sheet > 0 else 0
            objetivo_ratio = 1.20 # 20% más

            k_f1, k_f2, k_f3 = st.columns(3)
            k_f1.metric("Compra Real (Sheet)", f"${compra_real_sheet:,.0f}", help="Dato tomado de Columna AB del Excel")
            k_f2.metric("Costo de Venta Total", f"${costo_venta_total:,.0f}")
            
            if diferencia_flujo > 0:
                k_f3.metric("Flujo de Stock", f"+${diferencia_flujo:,.0f}", "📈 Stock Subiendo", delta_color="inverse")
            else:
                k_f3.metric("Flujo de Stock", f"-${abs(diferencia_flujo):,.0f}", "📉 Stock Bajando", delta_color="normal")

            # Alertas
            st.markdown("##### 🚦 Semáforo de Reducción")
            if compra_real_sheet == 0:
                st.warning("⚠️ No se detectaron compras en la columna del Excel (Busco columnas llamadas 'COMPRA' o 'ENTRADA').")
            else:
                if ratio_reduccion >= objetivo_ratio:
                    st.success(f"✅ **OBJETIVO CUMPLIDO:** Estás vendiendo un {((ratio_reduccion-1)*100):.1f}% más de lo que compras (Meta: 20%). El stock baja correctamente.")
                elif ratio_reduccion > 1.0:
                    st.info(f"⚠️ **ALERTA LEVE:** El stock baja, pero lento. Vendes solo un {((ratio_reduccion-1)*100):.1f}% más de lo que compras (Meta: 20%).")
                else:
                    st.error(f"❌ **ALERTA CRÍTICA:** Estás comprando más de lo que vendes. El stock está subiendo.")

            # Scoring check
            piso_scoring = obj_compra_terminal * 0.60
            if obj_compra_terminal > 0:
                st.caption(f"Referencia Scoring: Debes comprar al menos ${piso_scoring:,.0f} (60% del obj). Compra actual: ${compra_real_sheet:,.0f}")
                if compra_real_sheet < piso_scoring:
                    st.error("⚠️ Cuidado: Estás por debajo del piso de compra para el Scoring.")

            # --- SECCIÓN 3: SIMULADORES Y ESTRATEGIA (AL FINAL) ---
            st.markdown("---")
            st.subheader("🏁 Asistente de Equilibrio y Simulador")
            canales_premium = ['TALLER', 'MOSTRADOR', 'INTERNA']
            vta_premium = df_r[df_r['Canal'].isin(canales_premium)]['Venta Neta'].sum()
            util_premium = df_r[df_r['Canal'].isin(canales_premium)]['Utilidad $'].sum()
            utilidad_objetivo_total = vta_total_neta * 0.21
            margen_necesario_volumen = utilidad_objetivo_total - util_premium - primas_input
            vta_volumen = df_r[df_r['Canal'].str.contains('MAYORISTA|SEGUROS|GAR', na=False)]['Venta Neta'].sum()
            margen_critico = (margen_necesario_volumen / vta_volumen) if vta_volumen > 0 else 0
            
            col_asist1, col_asist2 = st.columns([2, 1])
            with col_asist1:
                if mg_total_final < 0.21: st.error(f"🔴 **Alerta:** Mix actual {mg_total_final:.1%}. Canales volumen necesitan marginar **{margen_critico:.1%}**.")
                else: st.success(f"🟢 **OK:** Mix actual {mg_total_final:.1%}. Margen crítico volumen: **{max(0, margen_critico):.1%}**.")

            st.markdown("#### 📈 Simulador de Operación Especial")
            with st.expander("Abrir Simulador", expanded=True):
                c_sim1, c_sim2 = st.columns(2)
                with c_sim1: monto_especial = st.number_input("Monto Venta ($)", min_value=0.0, value=50000000.0, step=1000000.0)
                with c_sim2: margen_especial = st.slider("% Margen Operación", -10.0, 30.0, 10.0, 0.5) / 100
                nueva_venta_total = vta_total_neta + monto_especial
                nueva_utilidad_total = util_total_final + (monto_especial * margen_especial)
                nuevo_margen_global = nueva_utilidad_total / nueva_venta_total if nueva_venta_total > 0 else 0
                col_res1, col_res2 = st.columns(2)
                with col_res1:
                    puntos_dif = (nuevo_margen_global - mg_total_final) * 100
                    st.metric("Nuevo Margen Global", f"{nuevo_margen_global:.1%}", delta=f"{puntos_dif:.1f} pts vs actual")
                with col_res2:
                    dif_objetivo = nueva_utilidad_total - (nueva_venta_total * 0.21)
                    if nuevo_margen_global >= 0.21: st.success(f"✅ **Viable:** Sobran **${dif_objetivo:,.0f}** sobre el 21%.")
                    else: st.error(f"❌ **Riesgoso:** Faltan **${abs(dif_objetivo):,.0f}** para el 21%.")

            st.markdown("### 🎯 Calculadora de Mix y Estrategia Ideal")
            st.info("Define tu participación ideal por canal y el margen al que aspiras vender.")
            col_mix_input, col_mix_res = st.columns([3, 2])
            default_mix = {}
            default_margin = {}
            if vta_total_neta > 0:
                for idx, row in df_r.iterrows():
                    default_mix[row['Canal']] = (row['Venta Neta'] / vta_total_neta) * 100
                    default_margin[row['Canal']] = row['Margen %'] * 100
            mix_ideal = {}
            margin_ideal = {}
            sum_mix = 0
            with col_mix_input:
                for c in canales_repuestos:
                    val_def_mix = float(default_mix.get(c, 0.0))
                    val_def_marg = float(default_margin.get(c, 25.0))
                    c1_s, c2_s = st.columns([2, 1])
                    with c1_s: val_mix = st.slider(f"% Mix {c}", 0.0, 100.0, val_def_mix, 0.5, key=f"mix_{c}")
                    with c2_s: val_marg = st.number_input(f"% Margen {c}", 0.0, 100.0, val_def_marg, 0.5, key=f"marg_{c}")
                    mix_ideal[c] = val_mix / 100
                    margin_ideal[c] = val_marg / 100
                    sum_mix += val_mix
            with col_mix_res:
                st.markdown(f"#### Objetivo Mensual: ${obj_rep_total:,.0f}")
                delta_sum = sum_mix - 100.0
                color_sum = "off"
                if abs(delta_sum) < 0.1: color_sum = "normal"
                else: color_sum = "inverse"
                st.metric("Suma del Mix Total", f"{sum_mix:.1f}%", f"{delta_sum:.1f}%", delta_color=color_sum)
                if abs(delta_sum) > 0.1: st.error(f"⚠️ El mix debe sumar 100%")
                total_profit_ideal = 0
                for c, share in mix_ideal.items():
                    total_profit_ideal += (obj_rep_total * share) * margin_ideal.get(c, 0)
                global_margin_ideal = total_profit_ideal / obj_rep_total if obj_rep_total > 0 else 0
                st.markdown("#### Resultado Estratégico:")
                st.info(f"Con esta estrategia, tu **Margen Global** sería del **{global_margin_ideal:.1%}**")

        elif selected_tab == "🎨 Chapa y Pintura":
            st.markdown("### 🎨 Chapa y Pintura")
            c_mo_j = find_col(data['CyP JUJUY'], ['MO'], exclude_keywords=['TER', 'OBJ', 'PRE'])
            c_mo_t_j = find_col(data['CyP JUJUY'], ['MO', 'TERCERO'], exclude_keywords=['OBJ'])
            if not c_mo_t_j: c_mo_t_j = find_col(data['CyP JUJUY'], ['MO', 'TER'], exclude_keywords=['OBJ'])
            j_f_p = cj_r.get(c_mo_j, 0)
            j_f_t = cj_r.get(c_mo_t_j, 0)
            j_total_fact = j_f_p + j_f_t
            j_obj_fact = cj_r.get(find_col(data['CyP JUJUY'], ["OBJ", "FACT"]), 1)
            c_panos_j = find_col(data['CyP JUJUY'], ['PANOS'], exclude_keywords=['TER', 'OBJ', 'PRE'])
            if not c_panos_j: c_panos_j = find_col(data['CyP JUJUY'], ['PAÑOS'], exclude_keywords=['TER', 'OBJ', 'PRE'])
            j_panos_prop = cj_r.get(c_panos_j, 0)
            j_obj_panos = cj_r.get(find_col(data['CyP JUJUY'], ['OBJ', 'PANOS']), 1)
            c_tec_j = find_col(data['CyP JUJUY'], ['TECNICO'], exclude_keywords=['PRODUCTIVIDAD'])
            if not c_tec_j: c_tec_j = find_col(data['CyP JUJUY'], ['DOTACION'])
            j_cant_tec = cj_r.get(c_tec_j, 1)
            j_ratio = j_panos_prop / j_cant_tec if j_cant_tec > 0 else 0
            j_panos_ter = cj_r.get(find_col(data['CyP JUJUY'], ['PANOS', 'TER']), 0)
            j_c_ter = cj_r.get(find_col(data['CyP JUJUY'], ['COSTO', 'TER']), 0)
            j_m_ter = j_f_t - j_c_ter
            j_mg_ter_pct = j_m_ter/j_f_t if j_f_t > 0 else 0
            c_mo_s = find_col(data['CyP SALTA'], ['MO'], exclude_keywords=['TER', 'OBJ', 'PRE'])
            c_mo_t_s = find_col(data['CyP SALTA'], ['MO', 'TERCERO'], exclude_keywords=['OBJ'])
            if not c_mo_t_s: c_mo_t_s = find_col(data['CyP SALTA'], ['MO', 'TER'], exclude_keywords=['OBJ'])
            s_f_p = cs_r.get(c_mo_s, 0)
            s_f_t = cs_r.get(c_mo_t_s, 0)
            s_f_r = cs_r.get(find_col(data['CyP SALTA'], ['FACT', 'REP']), 0)
            s_total_fact = s_f_p + s_f_t + s_f_r
            s_obj_fact = cs_r.get(find_col(data['CyP SALTA'], ["OBJ", "FACT"]), 1)
            c_panos_s = find_col(data['CyP SALTA'], ['PANOS'], exclude_keywords=['TER', 'OBJ', 'PRE'])
            if not c_panos_s: c_panos_s = find_col(data['CyP SALTA'], ['PAÑOS'], exclude_keywords=['TER', 'OBJ', 'PRE'])
            s_panos_prop = cs_r.get(c_panos_s, 0)
            s_obj_panos = cs_r.get(find_col(data['CyP SALTA'], ['OBJ', 'PANOS']), 1)
            c_tec_s = find_col(data['CyP SALTA'], ['TECNICO'], exclude_keywords=['PRODUCTIVIDAD'])
            if not c_tec_s: c_tec_s = find_col(data['CyP SALTA'], ['DOTACION'])
            s_cant_tec = cs_r.get(c_tec_s, 1)
            s_ratio = s_panos_prop / s_cant_tec if s_cant_tec > 0 else 0
            s_panos_ter = cs_r.get(find_col(data['CyP SALTA'], ['PANOS', 'TER']), 0)
            s_c_ter = cs_r.get(find_col(data['CyP SALTA'], ['COSTO', 'TER']), 0)
            s_m_ter = s_f_t - s_c_ter
            s_mg_ter_pct = s_m_ter/s_f_t if s_f_t > 0 else 0
            s_c_rep = cs_r.get(find_col(data['CyP SALTA'], ['COSTO', 'REP']), 0)
            s_m_rep = s_f_r - s_c_rep
            s_mg_rep_pct = s_m_rep/s_f_r if s_f_r > 0 else 0

            c_jujuy, c_salta = st.columns(2)
            with c_jujuy:
                st.subheader("Sede Jujuy")
                st.markdown(render_kpi_card("Fact. Total Jujuy", j_total_fact, j_obj_fact), unsafe_allow_html=True)
                st.markdown(render_kpi_card("Paños Propios", j_panos_prop, j_obj_panos, is_currency=False, unit="u"), unsafe_allow_html=True)
                st.markdown(render_kpi_small("Paños/Técnico", j_ratio, None, None, None, "{:.1f}"), unsafe_allow_html=True)
                html_ter_j = f'<div class="cyp-detail"><span class="cyp-header">👨‍🔧 Gestión Terceros</span>Cant: <b>{j_panos_ter:,.0f}</b> | Fact: ${j_f_t:,.0f}<br>Mg: <b>${j_m_ter:,.0f}</b> ({j_mg_ter_pct:.1%})</div>'
                st.markdown(html_ter_j, unsafe_allow_html=True)
            with c_salta:
                st.subheader("Sede Salta")
                st.markdown(render_kpi_card("Fact. Total Salta", s_total_fact, s_obj_fact), unsafe_allow_html=True)
                st.markdown(render_kpi_card("Paños Propios", s_panos_prop, s_obj_panos, is_currency=False, unit="u"), unsafe_allow_html=True)
                st.markdown(render_kpi_small("Paños/Técnico", s_ratio, None, None, None, "{:.1f}"), unsafe_allow_html=True)
                html_ter_s = f'<div class="cyp-detail"><span class="cyp-header">👨‍🔧 Gestión Terceros</span>Cant: <b>{s_panos_ter:,.0f}</b> | Fact: ${s_f_t:,.0f}<br>Mg: <b>${s_m_ter:,.0f}</b> ({s_mg_ter_pct:.1%})</div>'
                st.markdown(html_ter_s, unsafe_allow_html=True)
                if s_f_r > 0: st.markdown(f'<div class="cyp-detail" style="border-left-color: #28a745;"><span class="cyp-header" style="color:#28a745">📦 Repuestos</span>Fact: ${s_f_r:,.0f} | Mg: <b>${s_m_rep:,.0f}</b> ({s_mg_rep_pct:.1%})</div>', unsafe_allow_html=True)

            g_jujuy, g_salta = st.columns(2)
            with g_jujuy: st.plotly_chart(px.pie(values=[j_f_p, j_f_t], names=["MO Pura", "Terceros"], hole=0.4, title="Facturación Jujuy", color_discrete_sequence=["#00235d", "#00A8E8"]), use_container_width=True)
            with g_salta: 
                vals_s, nams_s = [s_f_p, s_f_t], ["MO Pura", "Terceros"]
                if s_f_r > 0: vals_s.append(s_f_r); nams_s.append("Repuestos")
                st.plotly_chart(px.pie(values=vals_s, names=nams_s, hole=0.4, title="Facturación Salta", color_discrete_sequence=["#00235d", "#00A8E8", "#28a745"]), use_container_width=True)

        elif selected_tab == "📈 Histórico":
            st.markdown(f"### 📈 Evolución Anual {año_sel}")
            st.markdown("#### 🛠️ Servicios")
            
            # --- MÓDULO IRPV CON MEMORIA (SESSION STATE) ---
            st.markdown("---")
            st.subheader("🔄 Fidelización (IRPV)")
            
            if st.session_state.df_irpv_cache is not None:
                df_res = st.session_state.df_irpv_cache
                anios_irpv = sorted(df_res.index, reverse=True)
                sel_anio = st.selectbox("Seleccionar Año de Venta (Cohorte):", anios_irpv)
                vals = df_res.loc[sel_anio]
                k1, k2, k3 = st.columns(3)
                with k1: st.metric("1er Service", f"{vals['1er']:.1%}", "Obj: 80%")
                with k2: st.metric("2do Service", f"{vals['2do']:.1%}", "Obj: 60%")
                with k3: st.metric("3er Service", f"{vals['3er']:.1%}", "Obj: 40%")
                with st.expander("Ver Matriz de Retención Completa"):
                    st.dataframe(df_res.style.format("{:.1%}", na_rep="-"), use_container_width=True)
                if st.button("🗑️ Borrar datos y cargar nuevos archivos"):
                    st.session_state.df_irpv_cache = None
                    st.rerun()
            else:
                 st.info("👈 Sube los archivos 'Ventas' y 'Taller' en la barra lateral para ver este análisis.")
            
            st.markdown("---")
            st.markdown("#### 📊 Análisis Histórico Mensual")

            col_hab_hist = find_col(h_cal, ["HAB"])
            col_tecs_hist = find_col(h_tal, ["TECNICOS"], exclude_keywords=["PROD", "EFIC"])
            if not col_tecs_hist: col_tecs_hist = find_col(h_tal, ["MECANICOS"], exclude_keywords=["PROD"])
            col_disp_hist = find_col(h_tal, ["DISPONIBLES", "REAL"])
            if not col_disp_hist: col_disp_hist = find_col(h_tal, ["DISP", "REAL"])
            if not col_disp_hist: col_disp_hist = find_col(h_tal, ["DISPONIBLE"]) 
            if col_hab_hist and col_disp_hist:
                df_capacidad = pd.merge(h_tal, h_cal[['Mes', col_hab_hist]], on='Mes', suffixes=('', '_cal'))
                if col_tecs_hist: cant_tecnicos_series = df_capacidad[col_tecs_hist].astype(float)
                else: cant_tecnicos_series = 6
                df_capacidad['Hs Ideales'] = cant_tecnicos_series * 8 * df_capacidad[col_hab_hist].astype(float)
                df_capacidad['Hs Reales'] = df_capacidad[col_disp_hist].astype(float)
                cols_trab_h = [c for c in [find_col(h_tal, ["TRAB", k]) for k in ["CC", "CG", "CI"]] if c]
                df_capacidad['Hs Ocupadas'] = df_capacidad[cols_trab_h].sum(axis=1) if cols_trab_h else 0
                fig_cap = go.Figure()
                fig_cap.add_trace(go.Scatter(x=df_capacidad['NombreMes'], y=df_capacidad['Hs Ideales'], name='Ideal (Teórico)', line=dict(color='gray', dash='dash')))
                fig_cap.add_trace(go.Bar(x=df_capacidad['NombreMes'], y=df_capacidad['Hs Reales'], name='Presencia Real', marker_color='#00235d'))
                fig_cap.add_trace(go.Bar(x=df_capacidad['NombreMes'], y=df_capacidad['Hs Ocupadas'], name='Hs Ocupadas', marker_color='#28a745'))
                st.plotly_chart(fig_cap.update_layout(title="Análisis de Capacidad", barmode='group', height=350), use_container_width=True)
            
            col_prod = find_col(h_tal, ["PRODUCTIVIDAD", "TALLER"])
            h_tal['Productividad'] = h_tal[col_prod].apply(lambda x: x/100 if x > 2 else x) if col_prod else 0
            cols_trab = [c for c in [find_col(h_tal, ["TRAB", k]) for k in ["CC", "CG", "CI"]] if c]
            h_tal['Hs Trabajadas'] = h_tal[cols_trab].sum(axis=1) if cols_trab else 0
            h_tal['Hs Vendidas'] = 0
            cols_hs_fact = [c for c in [find_col(h_tal, ["FACT", k]) for k in ["CC", "CG", "CI"]] if c]
            if cols_hs_fact: h_tal['Hs Vendidas'] = h_tal[cols_hs_fact].sum(axis=1)
            h_tal['Eficiencia Global'] = h_tal.apply(lambda row: row['Hs Vendidas'] / row['Hs Trabajadas'] if row['Hs Trabajadas'] > 0 else 0, axis=1)
            
            fig_efi = go.Figure()
            fig_efi.add_trace(go.Scatter(x=h_tal['NombreMes'], y=h_tal['Eficiencia Global'], name='Efic. Global', mode='lines+markers', line=dict(color='#28a745')))
            fig_efi.add_trace(go.Scatter(x=h_tal['NombreMes'], y=h_tal['Productividad'], name='Productividad', mode='lines+markers', line=dict(color='#17a2b8', dash='dot')))
            st.plotly_chart(fig_efi.update_layout(title="Eficiencia y Productividad", yaxis_tickformat='.0%', height=300), use_container_width=True)

            c_h1, c_h2 = st.columns(2)
            col_cpus = find_col(h_ser, ["CPUS"], exclude_keywords=["OBJ"])
            if col_cpus:
                c_h1.plotly_chart(px.bar(h_ser, x="NombreMes", y=col_cpus, title="Entradas (CPUS)", color_discrete_sequence=['#00235d']), use_container_width=True)
                h_ser_tal = pd.merge(h_ser, h_tal, on="Mes")
                h_ser_tal['Ticket Hs'] = h_ser_tal.apply(lambda row: row['Hs Vendidas'] / row[col_cpus] if row[col_cpus] > 0 else 0, axis=1)
                c_h2.plotly_chart(px.bar(h_ser_tal, x="NombreMes_x", y="Ticket Hs", title="Ticket Promedio (Hs)", color_discrete_sequence=['#6c757d']), use_container_width=True)

            st.markdown("#### 📦 Repuestos")
            col_vivo, col_obs, col_muerto = find_col(h_rep, ["VIVO"]), find_col(h_rep, ["OBSOLETO"]), find_col(h_rep, ["MUERTO"])
            fig_stk = go.Figure()
            if col_vivo: fig_stk.add_trace(go.Bar(x=h_rep['NombreMes'], y=h_rep[col_vivo], name='Vivo', marker_color='#28a745'))
            if col_obs: fig_stk.add_trace(go.Bar(x=h_rep['NombreMes'], y=h_rep[col_obs], name='Obsoleto', marker_color='#ffc107'))
            if col_muerto: fig_stk.add_trace(go.Bar(x=h_rep['NombreMes'], y=h_rep[col_muerto], name='Muerto', marker_color='#dc3545'))
            st.plotly_chart(fig_stk.update_layout(barmode='stack', title="Salud de Stock", height=300), use_container_width=True)

            fig_mix = go.Figure()
            for c in canales_repuestos:
                col_vta = find_col(h_rep, ["VENTA", c], exclude_keywords=["OBJ"])
                if col_vta: fig_mix.add_trace(go.Bar(x=h_rep['NombreMes'], y=h_rep[col_vta], name=c))
            st.plotly_chart(fig_mix.update_layout(barmode='stack', title="Venta Total por Canal (Apilado)", height=300), use_container_width=True)
            
            h_rep['CostoTotalMes'] = 0
            for c in canales_repuestos:
                 col_costo = find_col(h_rep, ["COSTO", c], exclude_keywords=["OBJ"])
                 if col_costo: h_rep['CostoTotalMes'] += h_rep[col_costo]
            
            h_rep['CostoPromedio3M'] = h_rep['CostoTotalMes'].rolling(window=3, min_periods=1).mean()
            col_val_stock = find_col(h_rep, ["VALOR", "STOCK"])
            if col_val_stock:
                h_rep['MesesStock'] = h_rep.apply(lambda row: row[col_val_stock] / row['CostoPromedio3M'] if row['CostoPromedio3M'] > 0 else 0, axis=1)
                st.plotly_chart(go.Figure(go.Scatter(x=h_rep['NombreMes'], y=h_rep['MesesStock'], name='Meses Stock', mode='lines+markers', line=dict(color='#6610f2', width=3))).update_layout(title="Evolución Meses de Stock (Stock / Costo Prom. 3 meses)", height=300), use_container_width=True)
            
            c_hist_j, c_hist_s = st.columns(2)
            col_pp_j = find_col(h_cyp_j, ['PANOS'], exclude_keywords=['TER', 'OBJ', 'PRE']) or find_col(h_cyp_j, ['PAÑOS'], exclude_keywords=['TER', 'OBJ'])
            col_pt_j = find_col(h_cyp_j, ['PANOS', 'TER']) or find_col(h_cyp_j, ['PAÑOS', 'TER'])
            h_cyp_j['Paños Propios'] = h_cyp_j[col_pp_j] if col_pp_j else 0
            h_cyp_j['Paños Terceros'] = h_cyp_j[col_pt_j] if col_pt_j else 0
            col_pp_s = find_col(h_cyp_s, ['PANOS'], exclude_keywords=['TER', 'OBJ']) or find_col(h_cyp_s, ['PAÑOS'], exclude_keywords=['TER', 'OBJ'])
            col_pt_s = find_col(h_cyp_s, ['PANOS', 'TER']) or find_col(h_cyp_s, ['PAÑOS', 'TER'])
            h_cyp_s['Paños Propios'] = h_cyp_s[col_pp_s] if col_pp_s else 0
            h_cyp_s['Paños Terceros'] = h_cyp_s[col_pt_s] if col_pt_s else 0
            
            with c_hist_j:
                fig_pj = go.Figure()
                fig_pj.add_trace(go.Bar(x=h_cyp_j['NombreMes'], y=h_cyp_j['Paños Propios'], name='Propios', marker_color='#00235d'))
                fig_pj.add_trace(go.Bar(x=h_cyp_j['NombreMes'], y=h_cyp_j['Paños Terceros'], name='Terceros', marker_color='#17a2b8'))
                st.plotly_chart(fig_pj.update_layout(barmode='stack', title="Evolución Jujuy (Paños)", height=300), use_container_width=True)
            with c_hist_s:
                fig_ps = go.Figure()
                fig_ps.add_trace(go.Bar(x=h_cyp_s['NombreMes'], y=h_cyp_s['Paños Propios'], name='Propios', marker_color='#00235d'))
                fig_ps.add_trace(go.Bar(x=h_cyp_s['NombreMes'], y=h_cyp_s['Paños Terceros'], name='Terceros', marker_color='#17a2b8'))
                st.plotly_chart(fig_ps.update_layout(barmode='stack', title="Evolución Salta (Paños)", height=300), use_container_width=True)

    else:
        st.warning("No se pudieron cargar los datos.")
except Exception as e:
    st.error(f"Error global: {e}")
