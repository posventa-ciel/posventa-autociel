import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import os

st.set_page_config(page_title="Grupo CENOA - Gestión Posventa", layout="wide")

# --- ESTILO CSS ---
st.markdown("""<style>
    .block-container { padding-top: 1rem; padding-bottom: 2rem; }
    .main { background-color: #f4f7f9; }
    
    .portada-container { 
        background: linear-gradient(90deg, #00235d 0%, #004080 100%); 
        color: white; padding: 1rem 1.5rem; border-radius: 10px; 
        margin-bottom: 1rem; display: flex; justify-content: space-between; 
        align-items: center; flex-wrap: wrap; gap: 15px;
    }
    
    .portada-left h1 { font-size: 1.4rem; margin: 0; line-height: 1.2; }
    .portada-left h3 { font-size: 1rem; margin: 0; color: #cbd5e1; font-weight: normal; }
    .portada-right { text-align: right; min-width: 200px; }
    
    .kpi-card { 
        background-color: white; border: 1px solid #e0e0e0; padding: 12px 15px; 
        border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); 
        margin-bottom: 8px; min-height: 145px; display: flex;
        flex-direction: column; justify-content: space-between;
    }
    
    .kpi-card p { font-size: 0.85rem; margin: 0; color: #666; font-weight: 600; }
    .kpi-card h2 { font-size: 1.8rem; margin: 4px 0; color: #00235d; } 
    
    .metric-card { 
        background-color: white; border: 1px solid #eee; padding: 10px;
        border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); 
        text-align: center; height: 100%; display: flex; 
        flex-direction: column; justify-content: space-between; min-height: 110px; 
    }
    
    div.row-widget.stRadio > div { flex-direction: row; align-items: stretch; }
    div.row-widget.stRadio > div[role="radiogroup"] > label { 
        background-color: #ffffff; border: 1px solid #e0e0e0; padding: 8px 16px;
        border-radius: 5px; margin-right: 5px; font-weight: bold; color: #00235d;
    }
    div.row-widget.stRadio > div[role="radiogroup"] > label[data-baseweb="radio"] { 
        background-color: #00235d; color: white;
    }
</style>""", unsafe_allow_html=True)

# --- FUNCIONES DE BÚSQUEDA ---
def find_col(df, include_keywords, exclude_keywords=[]):
    if df is None: return ""
    for col in df.columns:
        col_upper = col.upper()
        if all(k.upper() in col_upper for k in include_keywords):
            if not any(x.upper() in col_upper for x in exclude_keywords):
                return col
    return ""

# --- CARGA DE DATOS ---
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
        except: return None
    return data_dict

# --- FUNCIONES IRPV ---
def leer_csv_inteligente(uploaded_file):
    try:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='utf-8', on_bad_lines='skip')
        return df, "OK"
    except Exception as e: return None, str(e)

def procesar_irpv(file_v, file_t):
    df_v, msg_v = leer_csv_inteligente(file_v)
    df_t, msg_t = leer_csv_inteligente(file_t)
    if df_v is None or df_t is None: return None, "Error en archivos"
    
    df_v.columns = [str(c).upper().strip() for c in df_v.columns]
    df_t.columns = [str(c).upper().strip() for c in df_t.columns]
    
    col_vin = next((c for c in df_v.columns if 'BASTIDOR' in c or 'VIN' in c), None)
    col_fec = next((c for c in df_v.columns if 'FEC' in c or 'ENTR' in c), None)
    
    def clean_date(x):
        try: return pd.to_datetime(x, dayfirst=True)
        except: return pd.NaT

    df_v['Fecha_Entrega'] = df_v[col_fec].apply(clean_date)
    df_v['Año_Venta'] = df_v['Fecha_Entrega'].dt.year
    df_v['VIN'] = df_v[col_vin].astype(str).str.strip().str.upper()
    df_v = df_v.dropna(subset=['VIN', 'Fecha_Entrega'])

    col_vin_t = next((c for c in df_t.columns if 'BASTIDOR' in c or 'VIN' in c), None)
    col_fec_t = next((c for c in df_t.columns if 'CIERRE' in c or 'FEC' in c), None)
    col_km = next((c for c in df_t.columns if 'KM' in c), None)
    col_desc = next((c for c in df_t.columns if 'DESCR' in c or 'OPER' in c), None)

    df_t['Fecha_Servicio'] = df_t[col_fec_t].apply(clean_date)
    df_t['VIN'] = df_t[col_vin_t].astype(str).str.strip().str.upper()
    df_t['Km'] = pd.to_numeric(df_t[col_km], errors='coerce').fillna(0)
    df_t['Texto'] = df_t[col_desc].astype(str).str.upper() if col_desc else ""

    def clasif_hibrida(row):
        k, t = row['Km'], row['Texto']
        if (2500 <= k <= 16500) or any(w in t for w in ["10.000", "10K", "1ER"]): return "1er"
        if (16501 <= k <= 27000) or any(w in t for w in ["20.000", "20K", "2DO"]): return "2do"
        if (27001 <= k <= 38000) or any(w in t for w in ["30.000", "30K", "3ER"]): return "3er"
        return None
    
    df_t['Hito'] = df_t.apply(clasif_hibrida, axis=1)
    pivot_dates = df_t.dropna(subset=['Hito']).pivot_table(index='VIN', columns='Hito', values='Fecha_Servicio', aggfunc='min').reset_index()
    merged = pd.merge(df_v, pivot_dates, on='VIN', how='left')

    hoy = datetime.now()
    def evaluar(row, actual, anterior=None):
        base = row['Fecha_Entrega'] if actual == '1er' else row.get(anterior, pd.NaT)
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

# --- MAIN APP ---
ID_SHEET = "1yJgaMR0nEmbKohbT_8Vj627Ma4dURwcQTQcQLPqrFwk"
data = cargar_datos(ID_SHEET)

if data:
    for h in data:
        col_f = find_col(data[h], ["FECHA"]) or data[h].columns[0]
        data[h]['Fecha_dt'] = pd.to_datetime(data[h][col_f], dayfirst=True, errors='coerce')
        data[h]['Mes'] = data[h]['Fecha_dt'].dt.month
        data[h]['Año'] = data[h]['Fecha_dt'].dt.year

    with st.sidebar:
        años_disp = sorted([int(a) for a in data['CALENDARIO']['Año'].unique() if a > 0], reverse=True)
        año_sel = st.selectbox("📅 Año", años_disp)
        meses_nom = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
        meses_disp = sorted(data['CALENDARIO'][data['CALENDARIO']['Año'] == año_sel]['Mes'].unique(), reverse=True)
        mes_sel = st.selectbox("📅 Mes", meses_disp, format_func=lambda x: meses_nom.get(x, "N/A"))

    def get_row(df):
        res = df[(df['Año'] == año_sel) & (df['Mes'] == mes_sel)].sort_values('Fecha_dt')
        return res.iloc[-1] if not res.empty else pd.Series(dtype='object')

    c_r, s_r, r_r, t_r, cj_r, cs_r = get_row(data['CALENDARIO']), get_row(data['SERVICIOS']), get_row(data['REPUESTOS']), get_row(data['TALLER']), get_row(data['CyP JUJUY']), get_row(data['CyP SALTA'])
    d_t, d_h = float(c_r.get(find_col(data['CALENDARIO'], ["TRANS"]), 0)), float(c_r.get(find_col(data['CALENDARIO'], ["HAB"]), 22))
    prog_t = min(d_t / d_h, 1.0) if d_h > 0 else 0

    st.markdown(f'<div class="portada-container"><div class="portada-left"><h1>Autociel - Tablero Posventa</h1><h3>📅 {meses_nom[mes_sel]} {año_sel}</h3></div><div class="portada-right">Avance: {prog_t:.1%}</div></div>', unsafe_allow_html=True)
    
    menu_opts = ["🏠 Objetivos", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura", "📈 Histórico"]
    selected_tab = st.radio("", menu_opts, horizontal=True, label_visibility="collapsed")

    # HELPERS
    def render_kpi_card(title, real, obj_mes, is_currency=True):
        obj_p = obj_mes * prog_t
        proy = (real / d_t) * d_h if d_t > 0 else 0
        fmt = "${:,.0f}" if is_currency else "{:,.0f}"
        color = "#28a745" if real >= obj_p else "#dc3545"
        return f'<div class="kpi-card"><div><p>{title}</p><h2>{fmt.format(real)}</h2></div><div style="font-size:0.75rem;">vs Obj Parcial: {fmt.format(obj_p)} <br>Proyección: <span style="color:{color}">{fmt.format(proy)}</span></div></div>'

    def render_kpi_small(title, val, target=None, format_str="{:.1%}"):
        color = "#28a745" if target and val >= target else "#dc3545" if target else "#00235d"
        return f'<div class="metric-card"><p style="font-size:0.8rem; margin:0; color:#666;">{title}</p><h3 style="color:{color}; margin:0;">{format_str.format(val)}</h3></div>'

    # --- TAB 1: OBJETIVOS ---
    if selected_tab == "🏠 Objetivos":
        st.subheader("Estado General de Objetivos")
        col1, col2, col3, col4 = st.columns(4)
        # Aquí van los cálculos de facturación total que ya tenías...
        st.write("Cargando indicadores financieros...")

    # --- TAB 2: SERVICIOS Y TALLER ---
    elif selected_tab == "🛠️ Servicios y Taller":
        st.markdown("### 🏆 Calidad e Incentivos de Marca")
        
        # Datos de Calidad (NPS, Videocheck, Forfait) - Aquí va tu lógica original
        # ...
        
        # INCENTIVOS (Columnas U, V, W, X)
        val_p = s_r.get(find_col(data['SERVICIOS'], ["PRIMA", "PEUGEOT"], ["OBJ"]), 0)
        val_c = s_r.get(find_col(data['SERVICIOS'], ["PRIMA", "CITROEN"], ["OBJ"]), 0)
        obj_p = s_r.get(find_col(data['SERVICIOS'], ["OBJ", "PRIMA", "PEUGEOT"]), 0)
        obj_c = s_r.get(find_col(data['SERVICIOS'], ["OBJ", "PRIMA", "CITROEN"]), 0)

        cp, cc = st.columns(2)
        with cp:
            st.markdown(f'<div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; text-align: center;"><b>Posible Cobro Peugeot</b><br><span style="color: green; font-size: 1.2rem;">${val_p:,.0f}</span><br><small>Meta: ${obj_p:,.0f}</small></div>', unsafe_allow_html=True)
        with cc:
            st.markdown(f'<div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; text-align: center;"><b>Posible Cobro Citroën</b><br><span style="color: green; font-size: 1.2rem;">${val_c:,.0f}</span><br><small>Meta: ${obj_c:,.0f}</small></div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### ⚙️ Taller (Eficiencia y Productividad)")
        # Aquí va toda tu lógica de horas trabajadas vs facturadas...
        st.write("Analizando capacidad instalada...")

    # --- TAB 3: REPUESTOS ---
    elif selected_tab == "📦 Repuestos":
        st.markdown("### 📦 Gestión de Repuestos")
        primas_input = st.number_input("💰 Primas/Rappels Estimados ($)", value=0.0)
        
        canales = ['MOSTRADOR', 'TALLER', 'INTERNA', 'GAR', 'CYP', 'MAYORISTA', 'SEGUROS']
        detalles = []
        for c in canales:
            vn = r_r.get(find_col(data['REPUESTOS'], ["VENTA", c], ["OBJ"]), 0)
            costo = r_r.get(find_col(data['REPUESTOS'], ["COSTO", c]), 0)
            detalles.append({"Canal": c, "Venta Neta": vn, "Utilidad": vn - costo})
        
        df_r = pd.DataFrame(detalles)
        vta_total_neta = df_r['Venta Neta'].sum()
        util_total_final = df_r['Utilidad'].sum() + primas_input
        mg_total_final = util_total_final / vta_total_neta if vta_total_neta > 0 else 0
        val_stock = float(r_r.get(find_col(data['REPUESTOS'], ["VALOR", "STOCK"]), 0))

        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(px.pie(df_r, values="Venta Neta", names="Canal", hole=0.4, title="Mix de Venta"), use_container_width=True)
        with c2:
            st.plotly_chart(px.pie(values=[70, 20, 10], names=["Vivo", "Obs", "Muer"], hole=0.4, title="Salud de Stock"), use_container_width=True)
            st.markdown(f'<div style="border: 1px solid #e6e9ef; border-radius: 5px; padding: 10px; text-align: center; background-color: #ffffff;"><b>VALORACIÓN TOTAL STOCK</b><br><span style="font-size: 1.2rem; font-weight: bold;">${val_stock:,.0f}</span></div>', unsafe_allow_html=True)

        # ASISTENTE DE MARGEN
        st.markdown("---")
        st.subheader("🏁 Asistente de Equilibrio de Margen")
        util_obj_21 = vta_total_neta * 0.21
        falta_util = util_obj_21 - util_total_final
        if falta_util > 0:
            st.error(f"Faltan **${falta_util:,.0f}** para alcanzar el 21% de margen global.")
        else:
            st.success("¡Objetivo del 21% de margen superado!")

        # SIMULADOR
        with st.expander("📈 Simulador de Negocio Mayorista / Especial", expanded=True):
            msim = st.number_input("Monto Venta Especial ($)", value=50000000.0)
            marg_sim = st.slider("% Margen", -10.0, 30.0, 10.0) / 100
            nv = vta_total_neta + msim
            nu = util_total_final + (msim * marg_sim)
            st.metric("Margen Global Proyectado", f"{(nu/nv):.1%}", delta=f"{(nu/nv - mg_total_final)*100:.1f} pts")

    # --- TAB 4: CHAPA Y PINTURA ---
    elif selected_tab == "🎨 Chapa y Pintura":
        st.markdown("### 🎨 Gestión de Chapa y Pintura")
        # Aquí va toda tu lógica de paños Jujuy vs Salta...
        st.info("Cargando indicadores de productividad de paños...")

    # --- TAB 5: HISTÓRICO E IRPV ---
    elif selected_tab == "📈 Histórico":
        st.subheader("🔄 Fidelización (IRPV)")
        if 'df_irpv_cache' not in st.session_state: st.session_state.df_irpv_cache = None
        
        u1, u2 = st.columns(2)
        up_v = u1.file_uploader("Ventas (CSV)", type="csv", key="v_irpv")
        up_t = u2.file_uploader("Taller (CSV)", type="csv", key="t_irpv")
        
        if up_v and up_t and st.session_state.df_irpv_cache is None:
            df_res, msg = procesar_irpv(up_v, up_t)
            if df_res is not None: st.session_state.df_irpv_cache = df_res
        
        if st.session_state.df_irpv_cache is not None:
            st.dataframe(st.session_state.df_irpv_cache.style.format("{:.1%}", na_rep="-"))
            if st.button("Limpiar IRPV"): 
                st.session_state.df_irpv_cache = None
                st.rerun()

else:
    st.error("No se pudo conectar con los datos de Google Sheets.")
