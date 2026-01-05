import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Grupo CENOA - Gestión Posventa", layout="wide")

# --- ESTILO CORPORATIVO ---
st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    .portada-container {
        background: linear-gradient(90deg, #00235d 0%, #004080 100%);
        color: white; padding: 2rem; border-radius: 15px;
        margin-bottom: 2rem; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .titulo-portada { font-size: 2.2rem; font-weight: 800; margin: 10px 0; border:none !important; }
    .status-line { background: rgba(255,255,255,0.1); padding: 5px 15px; border-radius: 50px; display: inline-block; font-size: 0.9rem; }
    .stMetric { background-color: white; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; }
    .stTabs [aria-selected="true"] { background-color: #00235d !important; color: white !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- CARGA Y LIMPIEZA ---
@st.cache_data(ttl=60)
def cargar_datos_sheets(sheet_id):
    hojas = ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA']
    data_dict = {}
    for h in hojas:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={h.replace(' ', '%20')}"
        df = pd.read_csv(url, dtype=str).fillna("0")
        for col in df.columns:
            if col not in ['Fecha', 'Fecha Corte', 'Canal', 'Estado']:
                df[col] = df[col].astype(str).str.replace(r'[\$%\s]', '', regex=True).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        data_dict[h] = df
    return data_dict

ID_SHEET = "1yJgaMR0nEmbKohbT_8Vj627Ma4dURwcQTQcQLPqrFwk"

try:
    data = cargar_datos_sheets(ID_SHEET)

    # Procesar Fechas y crear columnas de mes/año
    for h in data:
        col_f = next((c for c in data[h].columns if 'Fecha' in c), data[h].columns[0])
        data[h]['Fecha_dt'] = pd.to_datetime(data[h][col_f], dayfirst=True, errors='coerce')
        data[h]['Mes'] = data[h]['Fecha_dt'].dt.month
        data[h]['Año'] = data[h]['Fecha_dt'].dt.year

    # --- FILTROS IZQUIERDA ---
    años = sorted(data['CALENDARIO']['Año'].unique(), reverse=True)
    año_sel = st.sidebar.selectbox("📅 Seleccionar Año", años)
    
    meses_nombres = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
    meses_disp = sorted(data['CALENDARIO'][data['CALENDARIO']['Año'] == año_sel]['Mes'].unique(), reverse=True)
    mes_sel = st.sidebar.selectbox("📅 Seleccionar Mes", meses_disp, format_func=lambda x: meses_nombres[x])

    # Datos del mes seleccionado (último registro disponible del mes)
    def filtrar_mes(df):
        return df[(df['Año'] == año_sel) & (df['Mes'] == mes_sel)].sort_values('Fecha_dt').iloc[-1]

    c_r = filtrar_mes(data['CALENDARIO'])
    s_r = filtrar_mes(data['SERVICIOS'])
    r_r = filtrar_mes(data['REPUESTOS'])
    t_r = filtrar_mes(data['TALLER'])
    cj_r = filtrar_mes(data['CyP JUJUY'])
    cs_r = filtrar_mes(data['CyP SALTA'])

    d_t, d_h = c_r.get('Días Transcurridos', 1), c_r.get('Días Hábiles Mes', 1)
    
    # --- PORTADA ---
    st.markdown(f"""<div class="portada-container">
        <div style="letter-spacing: 3px; opacity: 0.8; text-transform: uppercase;">Grupo CENOA</div>
        <div class="titulo-portada">Resumen General de Objetivos de Posventa</div>
        <div class="status-line">📍 Autociel | 📅 {meses_nombres[mes_sel]} {año_sel} | ⏱️ Avance: {d_t:g}/{d_h:g} días ({(d_t/d_h):.1%})</div>
    </div>""", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🏠 General", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura"])

    with tab1:
        # Aquí restauramos visibilidad de objetivos
        cols = st.columns(4)
        r_mo = s_r['MO Cliente'] + s_r['MO Garantía'] + s_r['MO Tercero']
        canales = ['Mostrador', 'Taller', 'Interna', 'Garantía', 'CyP', 'Mayorista', 'Seguros']
        r_rep = sum([r_r[f'Venta {c}'] for c in canales if f'Venta {c}' in r_r])
        
        # Objetivos (buscamos el valor de la fila que tenga el día 1 del mes seleccionado)
        def get_obj_mes(sh, col):
            df = data[sh]
            obj = df[(df['Año'] == año_sel) & (df['Mes'] == mes_sel)]
            return obj[col].max() # Tomamos el máximo reportado para ese mes

        metas = [
            ("Servicios", r_mo, get_obj_mes('SERVICIOS', 'Obj MO Total')),
            ("Repuestos", r_rep, get_obj_mes('REPUESTOS', 'Obj Facturación Total')),
            ("CyP Jujuy", cj_r['MO Pura']+cj_r['MO Tercero'], get_obj_mes('CyP JUJUY', 'Obj Facturación Total CyP Jujuy')),
            ("CyP Salta", cs_r['MO Pura']+cs_r['MO Tercero']+cs_r.get('Fact Repuestos', 0), get_obj_mes('CyP SALTA', 'Obj Facturación Total CyP Salta'))
        ]
        
        for i, (tit, real, obj) in enumerate(metas):
            p = (real / d_t) * d_h; alc = p/obj if obj > 0 else 0
            with cols[i]:
                st.markdown(f"**{tit}**")
                st.markdown(f"<h1 style='margin:0; color:#00235d;'>${real:,.0f}</h1>", unsafe_allow_html=True)
                st.markdown(f"<p style='margin:0; font-weight:bold; color:#444;'>Objetivo: ${obj:,.0f}</p>", unsafe_allow_html=True)
                st.markdown(f"<p style='color:{('#28a745' if alc>0.95 else '#dc3545')}; margin:0;'><b>Proy: {alc:.1%}</b></p>", unsafe_allow_html=True)

    with tab2:
        st.subheader("Tickets Promedio y Eficiencia")
        # Cálculos de Ticket Promedio
        cpus = s_r['CPUS'] if s_r['CPUS'] > 0 else 1
        tp_hs = (t_r['Hs Facturadas CC'] + t_r['Hs Facturadas CG']) / cpus
        tp_pesos = (s_r['MO Cliente'] + s_r['MO Garantía']) / cpus
        
        m1, m2 = st.columns(2)
        m1.metric("Ticket Promedio (Horas)", f"{tp_hs:.2f} hs/OT")
        m2.metric("Ticket Promedio (Pesos)", f"${tp_pesos:,.0f}/OT")

        # Gráfico Histórico (ejemplo de CPUS)
        hist_serv = data['SERVICIOS'][data['SERVICIOS']['Año'] == año_sel].groupby('Mes').last().reset_index()
        fig_hist = px.line(hist_serv, x='Mes', y='CPUS', title="Evolución Histórica CPUS", markers=True)
        st.plotly_chart(fig_hist, use_container_width=True)

    with tab3:
        st.subheader("Repuestos - Ticket Promedio")
        tp_rep = (r_r.get('Venta Taller',0) + r_r.get('Venta Garantía',0) + r_r.get('Venta CyP',0)) / cpus
        st.metric("Ticket Promedio Repuestos", f"${tp_rep:,.0f}/OT")
        
        # Tabla de Márgenes (la que ya teníamos)
        st.markdown("---")
        # Aquí irían los gráficos de torta de stock y canales

    with tab4:
        st.header("Histórico Chapa y Pintura")
        hist_cj = data['CyP JUJUY'][data['CyP JUJUY']['Año'] == año_sel].groupby('Mes').last().reset_index()
        fig_cyp = px.bar(hist_cj, x='Mes', y='Paños Propios', title="Evolución Paños Jujuy")
        st.plotly_chart(fig_cyp, use_container_width=True)

except Exception as e:
    st.error(f"Error técnico: {e}")
