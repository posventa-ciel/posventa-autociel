import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Grupo CENOA - Gestión Posventa", layout="wide")

# --- ESTILO ---
st.markdown("""<style>
.main { background-color: #f4f7f9; }
.portada-container { background: linear-gradient(90deg, #00235d 0%, #004080 100%); color: white; padding: 2rem; border-radius: 15px; text-align: center; margin-bottom: 2rem; }
.stMetric { background-color: white; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; }
</style>""", unsafe_allow_html=True)

# --- FUNCIÓN DE CARGA BLINDADA ---
@st.cache_data(ttl=600)
def cargar_datos(sheet_id):
    hojas = ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA']
    data_dict = {}
    for h in hojas:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={h.replace(' ', '%20')}"
        # Cargamos como texto primero para limpiar comas
        df = pd.read_csv(url, dtype=str).fillna("0")
        # Limpieza de comas por puntos en todo el dataframe
        df = df.apply(lambda x: x.str.replace(',', '.') if x.dtype == "object" else x)
        # Intentamos convertir a números lo que se pueda
        for col in df.columns:
            if col not in ['Fecha', 'Fecha Corte', 'Canal', 'Estado']:
                df[col] = pd.to_numeric(df[col], errors='ignore')
        data_dict[h] = df
    return data_dict

ID_SHEET = "1yJgaMR0nEmbKohbT_8Vj627Ma4dURwcQTQcQLPqrFwk"

try:
    df_all = cargar_datos(ID_SHEET)
    
    # Procesar Fechas (dayfirst=True para formato latino)
    for h in df_all:
        col = 'Fecha Corte' if 'Fecha Corte' in df_all[h].columns else 'Fecha'
        df_all[h]['Fecha_dt'] = pd.to_datetime(df_all[h][col], dayfirst=True).dt.date

    fechas = sorted(df_all['CALENDARIO']['Fecha_dt'].unique(), reverse=True)
    f_sel = st.sidebar.selectbox("📅 Seleccionar Fecha", fechas)

    # Datos de Calendario
    c_r = df_all['CALENDARIO'][df_all['CALENDARIO']['Fecha_dt'] == f_sel].iloc[0]
    d_t = float(c_r['Días Transcurridos'])
    d_h = float(c_r['Días Hábiles Mes'])
    
    mes_num = pd.to_datetime(f_sel).month
    meses = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}

    # --- PORTADA ---
    progreso = (d_t/d_h) if d_h > 0 else 0
    st.markdown(f"""<div class="portada-container">
        <h1>Autociel - Resumen Posventa</h1>
        <p style="font-size: 1.2rem;">📍 Mes de {meses[mes_num]} | ⏱️ Avance: {d_t} de {d_h} días ({progreso:.1%})</p>
    </div>""", unsafe_allow_html=True)

    # --- DATOS SERVICIOS Y REPUESTOS ---
    s_r = df_all['SERVICIOS'][df_all['SERVICIOS']['Fecha_dt'] == f_sel].iloc[0]
    r_r = df_all['REPUESTOS'][df_all['REPUESTOS']['Fecha_dt'] == f_sel].iloc[0]
    
    t1, t2 = st.tabs(["📊 Resumen General", "📦 Repuestos Detalle"])
    
    with t1:
        c1, c2 = st.columns(2)
        mo_total = float(s_r['MO Cliente']) + float(s_r['MO Garantía']) + float(s_r['MO Tercero'])
        c1.metric("M.O. Facturada Real", f"${mo_total:,.0f}")
        
        canales = ['Mostrador', 'Taller', 'Interna', 'Garantía', 'CyP', 'Mayorista', 'Seguros']
        total_rep = sum([float(r_r[f'Venta {c}']) for c in canales if f'Venta {c}' in r_r])
        c2.metric("Venta Repuestos Total", f"${total_rep:,.0f}")

    with t2:
        st.subheader("Ventas por Canal (Repuestos)")
        datos_rep = []
        for c in canales:
            if f'Venta {c}' in r_r:
                datos_rep.append({"Canal": c, "Venta": float(r_r[f'Venta {c}'])})
        df_rep = pd.DataFrame(datos_rep)
        st.bar_chart(df_rep.set_index("Canal"))

except Exception as e:
    st.error(f"Error técnico: {e}")
