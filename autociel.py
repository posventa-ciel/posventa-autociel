import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Grupo CENOA - Gestión Posventa", layout="wide")

# --- CSS ---
st.markdown("""<style>
.main { background-color: #f4f7f9; }
.portada-container { background: linear-gradient(90deg, #00235d 0%, #004080 100%); color: white; padding: 2rem; border-radius: 15px; text-align: center; }
.stMetric { background-color: white; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; }
</style>""", unsafe_allow_html=True)

# --- CARGA ---
@st.cache_data(ttl=600)
def cargar_datos(sheet_id):
    hojas = ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA']
    data_dict = {}
    for h in hojas:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={h.replace(' ', '%20')}"
        data_dict[h] = pd.read_csv(url).fillna(0)
    return data_dict

# --- LÓGICA PRINCIPAL ---
ID_SHEET = "1yJgaMR0nEmbKohbT_8Vj627Ma4dURwcQTQcQLPqrFwk"

try:
    df_all = cargar_datos(ID_SHEET)
    
    # Procesar Fechas
    for h in df_all:
        col = 'Fecha Corte' if 'Fecha Corte' in df_all[h].columns else 'Fecha'
        df_all[h]['Fecha_dt'] = pd.to_datetime(df_all[h][col]).dt.date

    fechas = sorted(df_all['CALENDARIO']['Fecha_dt'].unique(), reverse=True)
    f_sel = st.sidebar.selectbox("📅 Seleccionar Fecha", fechas)

    # Variables de tiempo
    c_r = df_all['CALENDARIO'][df_all['CALENDARIO']['Fecha_dt'] == f_sel].iloc[0]
    d_t, d_h = int(c_r['Días Transcurridos']), int(c_r['Días Hábiles Mes'])
    mes_num = pd.to_datetime(f_sel).month
    meses = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}

    # --- PORTADA ---
    st.markdown(f"""<div class="portada-container">
        <h1>Autociel - Posventa</h1>
        <p>Mes: {meses[mes_num]} | Avance: {d_t}/{d_h} días ({(d_t/d_h):.1%})</p>
    </div>""", unsafe_allow_html=True)

    # --- DATOS ---
    s_r = df_all['SERVICIOS'][df_all['SERVICIOS']['Fecha_dt'] == f_sel].iloc[0]
    r_r = df_all['REPUESTOS'][df_all['REPUESTOS']['Fecha_dt'] == f_sel].iloc[0]
    
    t1, t2 = st.tabs(["Resumen", "Detalle"])
    
    with t1:
        c1, c2 = st.columns(2)
        mo_total = s_r['MO Cliente'] + s_r['MO Garantía'] + s_r['MO Tercero']
        c1.metric("M.O. Facturada", f"${mo_total:,.0f}")
        
        rep_ventas = ['Mostrador', 'Taller', 'Interna', 'Garantía', 'CyP', 'Mayorista', 'Seguros']
        total_rep = sum([r_r[f'Venta {c}'] for c in rep_ventas if f'Venta {c}' in r_r])
        c2.metric("Repuestos Facturados", f"${total_rep:,.0f}")

except Exception as e:
    st.error(f"Hubo un error al procesar los datos: {e}")
