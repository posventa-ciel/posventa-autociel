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
        margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center;
    }
    .kpi-card { 
        background-color: white; border: 1px solid #e0e0e0; padding: 12px 15px; 
        border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 8px; 
        min-height: 145px; display: flex; flex-direction: column; justify-content: space-between;
    }
    .metric-card { 
        background-color: white; border: 1px solid #eee; padding: 10px; border-radius: 8px; 
        text-align: center; height: 100%; display: flex; flex-direction: column; justify-content: space-between; 
    }
</style>""", unsafe_allow_html=True)

# --- FUNCIONES DE APOYO ---
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
            df.columns = [c.strip().upper().replace(".", "").replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U").replace("Ñ", "N") for c in df.columns]
            for col in df.columns:
                if "FECHA" not in col and "CANAL" not in col and "ESTADO" not in col:
                    df[col] = df[col].astype(str).str.replace(r'[\$%\s]', '', regex=True).str.replace(',', '.')
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            data_dict[h] = df
        except: return None
    return data_dict

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
    
    # Simulación lógica IRPV simplificada para el ejemplo
    res = pd.DataFrame(index=df_v['Año_Venta'].unique(), columns=['1er', '2do', '3er']).fillna(0.7) 
    return res, "OK"

# --- MAIN APP ---
ID_SHEET = "1yJgaMR0nEmbKohbT_8Vj627Ma4dURwcQTQcQLPqrFwk"
data = cargar_datos(ID_SHEET)

if data:
    # Preparación de fechas
    for h in data:
        col_f = find_col(data[h], ["FECHA"]) or data[h].columns[0]
        data[h]['Fecha_dt'] = pd.to_datetime(data[h][col_f], dayfirst=True, errors='coerce')
        data[h]['Mes'] = data[h]['Fecha_dt'].dt.month
        data[h]['Año'] = data[h]['Fecha_dt'].dt.year

    with st.sidebar:
        st.header("Filtros")
        años_disp = sorted([int(a) for a in data['CALENDARIO']['Año'].unique() if a > 0], reverse=True)
        año_sel = st.selectbox("📅 Año", años_disp)
        meses_nom = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
        meses_disp = sorted(data['CALENDARIO'][data['CALENDARIO']['Año'] == año_sel]['Mes'].unique(), reverse=True)
        mes_sel = st.selectbox("📅 Mes", meses_disp, format_func=lambda x: meses_nom.get(x, "N/A"))

    # Rows actuales
    def get_row(df):
        res = df[(df['Año'] == año_sel) & (df['Mes'] == mes_sel)].sort_values('Fecha_dt')
        return res.iloc[-1] if not res.empty else pd.Series(dtype='object')

    c_r, s_r, r_r, t_r, cj_r, cs_r = get_row(data['CALENDARIO']), get_row(data['SERVICIOS']), get_row(data['REPUESTOS']), get_row(data['TALLER']), get_row(data['CyP JUJUY']), get_row(data['CyP SALTA'])
    
    d_t = float(c_r.get(find_col(data['CALENDARIO'], ["TRANS"]), 0))
    d_h = float(c_r.get(find_col(data['CALENDARIO'], ["HAB"]), 22))
    prog_t = min(d_t / d_h, 1.0) if d_h > 0 else 0

    # --- PORTADA ---
    st.markdown(f'<div class="portada-container"><div><h1>Autociel - Gestión Posventa</h1><h3>{meses_nom[mes_sel]} {año_sel}</h3></div><div>Avance: {prog_t:.1%}</div></div>', unsafe_allow_html=True)
    
    menu_opts = ["🏠 Objetivos", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura", "📈 Histórico"]
    selected_tab = st.radio("", menu_opts, horizontal=True, label_visibility="collapsed")

    # --- TABLERO DE OBJETIVOS ---
    if selected_tab == "🏠 Objetivos":
        st.write("Contenido de Objetivos...")

    # --- SERVICIOS Y TALLER ---
    elif selected_tab == "🛠️ Servicios y Taller":
        st.markdown("### 🛠️ Gestión de Taller y Calidad")
        # (Aquí irían tus KPIs de MO y TUS...)
        
        st.markdown("---")
        st.markdown("### 🏆 Calidad e Incentivos de Marca")
        val_prima_p = s_r.get(find_col(data['SERVICIOS'], ["PRIMA", "PEUGEOT"], ["OBJ"]), 0)
        val_prima_c = s_r.get(find_col(data['SERVICIOS'], ["PRIMA", "CITROEN"], ["OBJ"]), 0)
        
        col_p, col_c = st.columns(2)
        with col_p:
            st.markdown(f'<div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; text-align: center;"><b>Posible Cobro Peugeot</b><br><span style="color: green; font-size: 1.2rem;">${val_prima_p:,.0f}</span></div>', unsafe_allow_html=True)
        with col_c:
            st.markdown(f'<div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; text-align: center;"><b>Posible Cobro Citroën</b><br><span style="color: green; font-size: 1.2rem;">${val_prima_c:,.0f}</span></div>', unsafe_allow_html=True)

    # --- REPUESTOS (CON SIMULADOR Y VALOR STOCK) ---
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

        # Indicadores
        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(px.pie(df_r, values="Venta Neta", names="Canal", hole=0.4, title="Mix de Venta"), use_container_width=True)
        with c2:
            st.plotly_chart(px.pie(values=[60, 20, 20], names=["Vivo", "Obs", "Muer"], hole=0.4, title="Salud Stock"), use_container_width=True)
            st.markdown(f'<div style="border: 1px solid #e6e9ef; border-radius: 5px; padding: 10px; text-align: center;"><b>VALORACIÓN TOTAL STOCK</b><br><span style="font-size: 1.2rem;">${val_stock:,.0f}</span></div>', unsafe_allow_html=True)

        # Asistente y Simulador
        st.markdown("---")
        st.subheader("🏁 Asistente de Equilibrio y Simulador")
        monto_sim = st.number_input("Monto Venta Especial ($)", value=1000000.0)
        margen_sim = st.slider("% Margen Especial", -10.0, 30.0, 10.0) / 100
        
        nv = vta_total_neta + monto_sim
        nu = util_total_final + (monto_sim * margen_sim)
        st.metric("Nuevo Margen Global Proyectado", f"{(nu/nv):.1%}", delta=f"{(nu/nv - mg_total_final):.1%}")

    # --- CHAPA Y PINTURA ---
    elif selected_tab == "🎨 Chapa y Pintura":
        st.write("Contenido CyP...")

    # --- HISTÓRICO E IRPV (CON MEMORIA) ---
    elif selected_tab == "📈 Histórico":
        st.subheader("📈 Evolución y Fidelización")
        
        # Bloque IRPV con Session State
        st.markdown("### 🔄 Fidelización (IRPV)")
        if 'df_irpv_cache' not in st.session_state: st.session_state.df_irpv_cache = None
        
        u1, u2 = st.columns(2)
        up_v = u1.file_uploader("Ventas (CSV)", type="csv", key="v_irpv")
        up_t = u2.file_uploader("Taller (CSV)", type="csv", key="t_irpv")
        
        if up_v and up_t and st.session_state.df_irpv_cache is None:
            df_res, msg = procesar_irpv(up_v, up_t)
            if df_res is not None: st.session_state.df_irpv_cache = df_res
        
        if st.session_state.df_irpv_cache is not None:
            st.write("Resultados de Fidelización cargados.")
            st.dataframe(st.session_state.df_irpv_cache)
            if st.button("Limpiar IRPV"): 
                st.session_state.df_irpv_cache = None
                st.rerun()

except Exception as e:
    st.error(f"Error: {e}")
