import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import os

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Grupo CENOA - Gestión Posventa", layout="wide")

# --- ESTILO CSS (Tu estilo original completo) ---
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
    
    .portada-left h1 { font-size: 1.4rem; margin: 0; line-height: 1.2; }
    .portada-left h3 { font-size: 1rem; margin: 0; color: #cbd5e1; font-weight: normal; }
    .portada-right { text-align: right; min-width: 200px; }
    .portada-right div { font-size: 0.9rem; margin-bottom: 5px; }
    
    .kpi-card { 
        background-color: white; 
        border: 1px solid #e0e0e0; 
        padding: 12px 15px; 
        border-radius: 8px; 
        box-shadow: 0 1px 3px rgba(0,0,0,0.05); 
        margin-bottom: 8px; 
        min-height: 145px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    
    .kpi-card p { font-size: 0.85rem; margin: 0; color: #666; font-weight: 600; }
    .kpi-card h2 { font-size: 1.8rem; margin: 4px 0; color: #00235d; } 
    .kpi-subtext { font-size: 0.75rem; color: #888; }
    
    .metric-card { 
        background-color: white; 
        border: 1px solid #eee; 
        padding: 10px 10px 6px 10px;
        border-radius: 8px; 
        box-shadow: 0 1px 2px rgba(0,0,0,0.05); 
        text-align: center; 
        height: 100%; 
        display: flex; 
        flex-direction: column; 
        justify-content: space-between; 
        min-height: 110px; 
    }
    
    .metric-footer {
        border-top: 1px solid #f0f0f0;
        margin-top: 8px;
        padding-top: 6px;
        font-size: 0.7rem;
        display: flex;
        justify-content: space-between;
        color: #666;
    }
    
    div.row-widget.stRadio > div { flex-direction: row; align-items: stretch; }
    div.row-widget.stRadio > div[role="radiogroup"] > label { 
        background-color: #ffffff; 
        border: 1px solid #e0e0e0;
        padding: 8px 16px;
        border-radius: 5px;
        margin-right: 5px;
        font-weight: bold;
        color: #00235d;
    }
    div.row-widget.stRadio > div[role="radiogroup"] > label[data-baseweb="radio"] { 
        background-color: #00235d; 
        color: white;
    }

    .cyp-detail { background-color: #f8f9fa; padding: 8px; border-radius: 6px; font-size: 0.8rem; margin-top: 5px; border-left: 3px solid #00235d; line-height: 1.3; }
    .cyp-header { font-weight: bold; color: #00235d; font-size: 0.85rem; margin-bottom: 2px; display: block; }
</style>""", unsafe_allow_html=True)

# --- FUNCIONES AUXILIARES ORIGINALES ---
def find_col(df, include_keywords, exclude_keywords=[]):
    if df is None: return ""
    for col in df.columns:
        col_upper = col.upper()
        if all(k.upper() in col_upper for k in include_keywords):
            if not any(x.upper() in col_upper for x in exclude_keywords):
                return col
    return ""

@st.cache_data(ttl=60)
def cargar_datos(sheet_id):
    hojas = ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA']
    data_dict = {}
    for h in hojas:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={h.replace(' ', '%20')}"
        try:
            df = pd.read_csv(url, dtype=str).fillna("0")
            df.columns = [
                c.strip().upper()
                .replace(".", "")
                .replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
                .replace("Ñ", "N") 
                for c in df.columns
            ]
            for col in df.columns:
                if "FECHA" not in col and "CANAL" not in col and "ESTADO" not in col:
                    df[col] = df[col].astype(str).str.replace(r'[\$%\s]', '', regex=True).str.replace(',', '.')
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            data_dict[h] = df
        except Exception as e:
            st.error(f"Error cargando hoja {h}: {e}")
            return None
    return data_dict

# --- NUEVAS FUNCIONES PARA IRPV (Fidelización) ---
def leer_csv_inteligente(uploaded_file):
    try:
        uploaded_file.seek(0)
        preview = pd.read_csv(uploaded_file, header=None, nrows=20, sep=None, engine='python', encoding='utf-8', on_bad_lines='skip')
        idx_header = -1
        keywords = ['BASTIDOR', 'VIN', 'CHASIS', 'MATRICULA']
        for i, row in preview.iterrows():
            row_txt = " ".join([str(x).upper() for x in row.values])
            if any(kw in row_txt for kw in keywords):
                idx_header = i
                break
        if idx_header == -1: idx_header = 0
        
        uploaded_file.seek(0)
        try:
            df = pd.read_csv(uploaded_file, header=idx_header, sep=';', encoding='utf-8', on_bad_lines='skip')
            if len(df.columns) < 2: raise Exception
        except:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, header=idx_header, sep=',', encoding='utf-8', on_bad_lines='skip')
        return df, "OK"
    except Exception as e:
        return None, str(e)

def procesar_irpv(file_v, file_t):
    # 1. Ventas
    df_v, msg_v = leer_csv_inteligente(file_v)
    if df_v is None: return None, f"Ventas: {msg_v}"
    df_v.columns = [str(c).upper().strip() for c in df_v.columns]
    
    col_vin = next((c for c in df_v.columns if 'BASTIDOR' in c or 'VIN' in c), None)
    col_fec = next((c for c in df_v.columns if 'FEC' in c or 'ENTR' in c), None)
    
    if not col_vin or not col_fec: return None, "Ventas: Faltan columnas VIN/Fecha"

    def clean_date(x):
        if pd.isna(x) or str(x).strip() == '': return pd.NaT
        try: return pd.to_datetime(x, dayfirst=True)
        except: return pd.NaT

    df_v['Fecha_Entrega'] = df_v[col_fec].apply(clean_date)
    df_v['Año_Venta'] = df_v['Fecha_Entrega'].dt.year
    df_v['VIN'] = df_v[col_vin].astype(str).str.strip().str.upper()
    df_v = df_v.dropna(subset=['VIN', 'Fecha_Entrega'])

    # 2. Taller
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

    # Clasificación Híbrida
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

    # Lógica Secuencial y Madurez
    hoy = datetime.now()
    def evaluar(row, actual, anterior=None):
        if actual == '1er':
            base = row['Fecha_Entrega']
        else:
            base = row.get(anterior, pd.NaT)
            if pd.isna(base): return np.nan # Cadena rota
        
        if pd.isna(base): return np.nan
        limite = base + timedelta(days=365)
        hecho = row.get(actual, pd.NaT)
        
        if not pd.isna(hecho): return 1.0 # Éxito
        if hoy >= limite: return 0.0 # Vencido
        return np.nan # Aún en tiempo (no cuenta)

    merged['R_1er'] = merged.apply(lambda r: evaluar(r, '1er'), axis=1)
    merged['R_2do'] = merged.apply(lambda r: evaluar(r, '2do', '1er'), axis=1)
    merged['R_3er'] = merged.apply(lambda r: evaluar(r, '3er', '2do'), axis=1)

    res = merged.groupby('Año_Venta')[['R_1er', 'R_2do', 'R_3er']].mean()
    res.columns = ['1er', '2do', '3er']
    return res, "OK"

# --- MAIN APP ---
ID_SHEET = "1yJgaMR0nEmbKohbT_8Vj627Ma4dURwcQTQcQLPqrFwk"

try:
    data = cargar_datos(ID_SHEET)
    
    if data:
        # Preprocesamiento fechas
        for h in data:
            col_f = find_col(data[h], ["FECHA"]) or data[h].columns[0]
            data[h]['Fecha_dt'] = pd.to_datetime(data[h][col_f], dayfirst=True, errors='coerce')
            data[h]['Mes'] = data[h]['Fecha_dt'].dt.month
            data[h]['Año'] = data[h]['Fecha_dt'].dt.year

        canales_repuestos = ['MOSTRADOR', 'TALLER', 'INTERNA', 'GAR', 'CYP', 'MAYORISTA', 'SEGUROS']

        with st.sidebar:
            if os.path.exists("logo.png"):
                st.image("logo.png", use_container_width=True)
                
            st.header("Filtros")
            años_disp = sorted([int(a) for a in data['CALENDARIO']['Año'].unique() if a > 0], reverse=True)
            año_sel = st.selectbox("📅 Año", años_disp)
            
            meses_nom = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
            df_year = data['CALENDARIO'][data['CALENDARIO']['Año'] == año_sel]
            meses_disp = sorted(df_year['Mes'].unique(), reverse=True)
            mes_sel = st.selectbox("📅 Mes", meses_disp, format_func=lambda x: meses_nom.get(x, "N/A"))

        # Helpers
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

        # Históricos helper
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

        # Portada
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

        # RENDERIZADORES
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
            html += f'<div style="margin-top:5px;"><div style="width:100%; background:#e0e0e0; height:5px; border-radius:10px;"><div style="width:{min(cumpl_proy*100, 100)}%; background:{color}; height:5px; border-radius:10px;"></div></div></div></div>'
            html += '</div>'
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
                footer_html = f'''<div class="metric-footer"><div>Obj. Mes: <b>{format_str.format(target_mensual)}</b></div><div style="color:{color_proy}">Proy: <b>{format_str.format(projection)}</b></div></div>'''
            
            html = f'<div class="metric-card"><div><p style="color:#666; font-size:0.8rem; margin-bottom:2px;">{title}</p><h3 style="color:#00235d; margin:0; font-size:1.3rem;">{format_str.format(val)}</h3>{subtext_html}</div>{footer_html}</div>'
            return html

        # LOGICA COLUMNAS
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
        
        # --- PESTAÑAS ---
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

            k1, k2, k3, k4 = st.columns(4)
            c_cpus = find_col(data['SERVICIOS'], ["CPUS"], exclude_keywords=["OBJ"])
            c_tus_others = find_col(data['SERVICIOS'], ["OTROS", "CARGOS"], exclude_keywords=["OBJ"])
            real_cpus = s_r.get(c_cpus, 0)
            real_tus = real_cpus + s_r.get(c_tus_others, 0)
            obj_cpus = s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'CPUS']), 1)
            obj_tus = s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'TUS']), 1)
            div = real_cpus if real_cpus > 0 else 1
            tp_mo = real_mo_total / div
            hf_cc = t_r.get(find_col(data['TALLER'], ["FACT", "CC"]), 0)
            hf_cg = t_r.get(find_col(data['TALLER'], ["FACT", "CG"]), 0)
            hf_ci = t_r.get(find_col(data['TALLER'], ["FACT", "CI"]), 0)
            tp_hs = (hf_cc+hf_cg+hf_ci) / div
            tgt_tp_mo = obj_mo_total / obj_cpus if obj_cpus > 0 else 0

            with k1: st.markdown(render_kpi_card("TUS Total", real_tus, obj_tus, is_currency=False, show_daily=True), unsafe_allow_html=True)
            with k2: st.markdown(render_kpi_card("CPUS (Entradas)", real_cpus, obj_cpus, is_currency=False, show_daily=True), unsafe_allow_html=True)
            with k3: st.markdown(render_kpi_small("Ticket Prom. (Hs)", tp_hs, None, None, None, "{:.2f} hs"), unsafe_allow_html=True)
            with k4: st.markdown(render_kpi_small("Ticket Prom. ($)", tp_mo, tgt_tp_mo, None, None, "${:,.0f}"), unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("### 🏆 Calidad")
            
            def get_calidad_data(keyword_main, brand, is_percent=False, prorate_target=False):
                c_real = find_col(data['SERVICIOS'], [keyword_main, brand], exclude_keywords=["OBJ"])
                c_obj = find_col(data['SERVICIOS'], ["OBJ", keyword_main, brand])
                if not c_obj: c_obj = find_col(data['SERVICIOS'], ["OBJ", keyword_main])
                val_real = s_r.get(c_real, 0)
                df_mes = data['SERVICIOS'][(data['SERVICIOS']['Año'] == año_sel) & (data['SERVICIOS']['Mes'] == mes_sel)]
                if not df_mes.empty and c_obj: val_obj_mensual = df_mes[c_obj].max() 
                else: val_obj_mensual = 0
                val_proyeccion = val_real / prog_t if prog_t > 0 else 0
                val_obj_parcial = val_obj_mensual * prog_t if prorate_target else val_obj_mensual
                if not prorate_target: val_proyeccion = val_real
                if is_percent:
                    if val_real > 1.0: val_real /= 100
                    if val_obj_parcial > 1.0: val_obj_parcial /= 100
                    if val_obj_mensual > 1.0: val_obj_mensual /= 100
                    if val_proyeccion > 1.0: val_proyeccion /= 100
                    fmt = "{:.1%}"
                else: fmt = "{:,.0f}" if not prorate_target else "{:,.1f}"
                return val_real, val_obj_parcial, val_obj_mensual, val_proyeccion, fmt

            nps_p_r, nps_p_p, nps_p_m, nps_p_proy, fmt_nps = get_calidad_data("NPS", "PEUGEOT")
            nps_c_r, nps_c_p, nps_c_m, nps_c_proy, _ = get_calidad_data("NPS", "CITROEN")
            vc_p_r, vc_p_p, vc_p_m, vc_p_proy, fmt_vc = get_calidad_data("VIDEO", "PEUGEOT", prorate_target=True)
            vc_c_r, vc_c_p, vc_c_m, vc_c_proy, _ = get_calidad_data("VIDEO", "CITROEN", prorate_target=True)
            ff_p_r, ff_p_p, ff_p_m, ff_p_proy, fmt_ff = get_calidad_data("FORFAIT", "PEUGEOT", prorate_target=True)
            ff_c_r, ff_c_p, ff_c_m, ff_c_proy, _ = get_calidad_data("FORFAIT", "CITROEN", prorate_target=True)

            c_peugeot, c_citroen = st.columns(2)
            with c_peugeot:
                st.markdown("#### 🦁 Peugeot")
                st.markdown(render_kpi_small("NPS", nps_p_r, nps_p_p, None, None, fmt_nps, label_target="Obj"), unsafe_allow_html=True)
                p_row = st.columns(2)
                with p_row[0]: st.markdown(render_kpi_small("Videocheck", vc_p_r, vc_p_p, vc_p_m, vc_p_proy, fmt_vc), unsafe_allow_html=True)
                with p_row[1]: st.markdown(render_kpi_small("Forfait", ff_p_r, ff_p_p, ff_p_m, ff_p_proy, fmt_ff), unsafe_allow_html=True)
            with c_citroen:
                st.markdown("#### 🔴 Citroën")
                st.markdown(render_kpi_small("NPS", nps_c_r, nps_c_p, None, None, fmt_nps, label_target="Obj"), unsafe_allow_html=True)
                c_row = st.columns(2)
                with c_row[0]: st.markdown(render_kpi_small("Videocheck", vc_c_r, vc_c_p, vc_c_m, vc_c_proy, fmt_vc), unsafe_allow_html=True)
                with c_row[1]: st.markdown(render_kpi_small("Forfait", ff_c_r, ff_c_p, ff_c_m, ff_c_proy, fmt_ff), unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("### ⚙️ Eficiencia Taller")
            # --- TALLER LOGIC ---
            col_tecs = find_col(data['TALLER'], ["TECNICOS"], exclude_keywords=["PROD"])
            if not col_tecs: col_tecs = find_col(data['TALLER'], ["DOTACION"])
            cant_tecs = t_r.get(col_tecs, 6) 
            if cant_tecs == 0: cant_tecs = 6
            ht_cc = t_r.get(find_col(data['TALLER'], ["TRAB", "CC"]), 0)
            ht_cg = t_r.get(find_col(data['TALLER'], ["TRAB", "CG"]), 0)
            ht_ci = t_r.get(find_col(data['TALLER'], ["TRAB", "CI"]), 0)
            ef_cc = hf_cc / ht_cc if ht_cc > 0 else 0
            ef_gl = (hf_cc+hf_cg+hf_ci) / (ht_cc+ht_cg+ht_ci) if (ht_cc+ht_cg+ht_ci) > 0 else 0
            prod = t_r.get(find_col(data['TALLER'], ["PRODUCTIVIDAD", "TALLER"]), 0)
            if prod > 2: prod /= 100
            
            e1, e2, e3 = st.columns(3)
            with e1: st.markdown(render_kpi_small("Eficiencia CC", ef_cc, 1.0), unsafe_allow_html=True)
            with e2: st.markdown(render_kpi_small("Eficiencia Global", ef_gl, 0.85), unsafe_allow_html=True)
            with e3: st.markdown(render_kpi_small("Productividad", prod, 0.95), unsafe_allow_html=True)

            # --- SECCIÓN NUEVA: IRPV (Insertada aquí sin romper nada) ---
            st.markdown("---")
            st.subheader("🔄 Fidelización (IRPV)")
            st.info("Sube archivos CSV (UTF-8) para calcular.")
            up_v = st.file_uploader("Entregas 0km", type=["csv"], key="v")
            up_t = st.file_uploader("Historial Taller", type=["csv"], key="t")
            
            if up_v and up_t:
                df_res, msg = procesar_irpv(up_v, up_t)
                if df_res is not None:
                    anios_irpv = sorted(df_res.index, reverse=True)
                    sel_anio = st.selectbox("Año Cohorte:", anios_irpv)
                    vals = df_res.loc[sel_anio]
                    i1, i2, i3 = st.columns(3)
                    with i1: st.metric("1er Service", f"{vals['1er']:.1%}", "Obj: 80%")
                    with i2: st.metric("2do Service", f"{vals['2do']:.1%}", "Obj: 60%")
                    with i3: st.metric("3er Service", f"{vals['3er']:.1%}", "Obj: 40%")
                    with st.expander("Ver Datos"): st.dataframe(df_res.style.format("{:.1%}", na_rep="-"))
                else: st.error(msg)

        elif selected_tab == "📦 Repuestos":
            st.markdown("### 📦 Repuestos")
            col_primas, col_vacia = st.columns([1, 3])
            with col_primas:
                primas_input = st.number_input("💰 Ingresar Primas/Rappels Estimados ($)", min_value=0.0, step=10000.0, format="%.0f")

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
            
            vta_total_neta = df_r['Venta Neta'].sum() if not df_r.empty else 0
            util_total_operativa = df_r['Utilidad $'].sum() if not df_r.empty else 0
            util_total_final = util_total_operativa + primas_input
            mg_total_final = util_total_final / vta_total_neta if vta_total_neta > 0 else 0
            
            st.dataframe(df_r.style.format({"Venta Bruta": "${:,.0f}", "Venta Neta": "${:,.0f}", "Utilidad $": "${:,.0f}", "Margen %": "{:.1%}"}), use_container_width=True, hide_index=True)
            
            k1, k2 = st.columns(2)
            k1.metric("Utilidad Total (+Primas)", f"${util_total_final:,.0f}")
            k2.metric("Margen Global Real", f"{mg_total_final:.1%}", "Obj: 21%")

        elif selected_tab == "🎨 Chapa y Pintura":
            # (Tu código original de CyP, intacto)
            st.markdown("### 🎨 Chapa y Pintura")
            c_mo_j = find_col(data['CyP JUJUY'], ['MO'], exclude_keywords=['TER', 'OBJ', 'PRE'])
            c_mo_t_j = find_col(data['CyP JUJUY'], ['MO', 'TERCERO'], exclude_keywords=['OBJ']) or find_col(data['CyP JUJUY'], ['MO', 'TER'], exclude_keywords=['OBJ'])
            j_f_p = cj_r.get(c_mo_j, 0)
            j_f_t = cj_r.get(c_mo_t_j, 0)
            j_total_fact = j_f_p + j_f_t
            j_obj_fact = cj_r.get(find_col(data['CyP JUJUY'], ["OBJ", "FACT"]), 1)
            c_panos_j = find_col(data['CyP JUJUY'], ['PANOS'], exclude_keywords=['TER', 'OBJ', 'PRE']) or find_col(data['CyP JUJUY'], ['PAÑOS'], exclude_keywords=['TER', 'OBJ', 'PRE'])
            j_panos_prop = cj_r.get(c_panos_j, 0)
            c_mo_s = find_col(data['CyP SALTA'], ['MO'], exclude_keywords=['TER', 'OBJ', 'PRE'])
            c_mo_t_s = find_col(data['CyP SALTA'], ['MO', 'TERCERO'], exclude_keywords=['OBJ']) or find_col(data['CyP SALTA'], ['MO', 'TER'], exclude_keywords=['OBJ'])
            s_f_p = cs_r.get(c_mo_s, 0)
            s_f_t = cs_r.get(c_mo_t_s, 0)
            s_total_fact = s_f_p + s_f_t
            s_obj_fact = cs_r.get(find_col(data['CyP SALTA'], ["OBJ", "FACT"]), 1)
            c_panos_s = find_col(data['CyP SALTA'], ['PANOS'], exclude_keywords=['TER', 'OBJ', 'PRE']) or find_col(data['CyP SALTA'], ['PAÑOS'], exclude_keywords=['TER', 'OBJ', 'PRE'])
            s_panos_prop = cs_r.get(c_panos_s, 0)

            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Jujuy")
                st.markdown(render_kpi_card("Facturación", j_total_fact, j_obj_fact), unsafe_allow_html=True)
                st.metric("Paños Propios", f"{j_panos_prop:.0f}")
            with c2:
                st.subheader("Salta")
                st.markdown(render_kpi_card("Facturación", s_total_fact, s_obj_fact), unsafe_allow_html=True)
                st.metric("Paños Propios", f"{s_panos_prop:.0f}")

        elif selected_tab == "📈 Histórico":
            st.markdown(f"### 📈 Evolución Anual {año_sel}")
            col_cpus = find_col(h_ser, ["CPUS"], exclude_keywords=["OBJ"])
            if col_cpus: st.plotly_chart(px.bar(h_ser, x="NombreMes", y=col_cpus, title="Entradas (CPUS)", color_discrete_sequence=['#00235d']), use_container_width=True)

    else:
        st.warning("No se pudieron cargar los datos.")
except Exception as e:
    st.error(f"Error global: {e}")
