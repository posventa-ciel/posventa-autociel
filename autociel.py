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

@st.cache_data(ttl=60)
def cargar_datos(sheet_id):
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
    data = cargar_datos(ID_SHEET)
    for h in data:
        col_f = next((c for c in data[h].columns if 'Fecha' in c), data[h].columns[0])
        data[h]['Fecha_dt'] = pd.to_datetime(data[h][col_f], dayfirst=True, errors='coerce')

    # Filtros de Año y Mes
    años = sorted(data['CALENDARIO']['Fecha_dt'].dt.year.unique(), reverse=True)
    año_sel = st.sidebar.selectbox("📅 Seleccionar Año", años)
    
    meses_nombres = {1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic"}
    meses_disp = sorted(data['CALENDARIO'][data['CALENDARIO']['Fecha_dt'].dt.year == año_sel]['Fecha_dt'].dt.month.unique(), reverse=True)
    mes_sel = st.sidebar.selectbox("📅 Seleccionar Mes", meses_disp, format_func=lambda x: meses_nombres[x])

    # Registros seleccionados
    def get_mes_data(df):
        return df[(df['Fecha_dt'].dt.year == año_sel) & (df['Fecha_dt'].dt.month == mes_sel)].sort_values('Fecha_dt').iloc[-1]

    c_r = get_mes_data(data['CALENDARIO'])
    s_r = get_mes_data(data['SERVICIOS'])
    r_r = get_mes_data(data['REPUESTOS'])
    t_r = get_mes_data(data['TALLER'])
    cj_r = get_mes_data(data['CyP JUJUY'])
    cs_r = get_row_cyp_salta = get_mes_data(data['CyP SALTA'])

    d_t, d_h = float(c_r.get('Días Transcurridos', 1)), float(c_r.get('Días Hábiles Mes', 1))

    st.markdown(f"""<div class="portada-container"><h1>Autociel - Gestión Posventa</h1>
    <p>📅 {meses_nombres[mes_sel]} {año_sel} | Avance Mes: {d_t:g}/{d_h:g} días ({(d_t/d_h):.1%})</p></div>""", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🏠 General", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura"])

    with tab1:
        st.subheader("Cumplimiento de Objetivos Mensuales")
        cols = st.columns(4)
        # Metas y Objetivos
        r_mo = s_r['MO Cliente'] + s_r['MO Garantía'] + s_r['MO Tercero']
        metas = [
            ("M.O. Servicios", r_mo, s_r['Obj MO Total']),
            ("Repuestos", sum([r_r[f'Venta {c}'] for c in ['Mostrador', 'Taller', 'Interna', 'Garantía', 'CyP', 'Mayorista', 'Seguros'] if f'Venta {c}' in r_r]), r_r['Obj Facturación Total']),
            ("CyP Jujuy", cj_r['MO Pura'] + cj_r['MO Tercero'], cj_r['Obj Facturación Total CyP Jujuy']),
            ("CyP Salta", cs_r['MO Pura'] + cs_r['MO Tercero'], cs_r['Obj Facturación Total CyP Salta'])
        ]
        for i, (tit, real, obj) in enumerate(metas):
            p = (real / d_t) * d_h; alc = p / obj if obj > 0 else 0
            cols[i].metric(tit, f"${real:,.0f}", f"Obj: ${obj:,.0f}", delta_color="off")
            cols[i].write(f"**Proy: {alc:.1%}**")

    with tab2:
        st.subheader("Tickets Promedio y Eficiencia")
        cpus = s_r['CPUS'] if s_r['CPUS'] > 0 else 1
        # CÁLCULOS TICKET PROMEDIO
        tp_hs = (t_r['Hs Facturadas CC'] + t_r['Hs Facturadas CG']) / cpus
        tp_mo = (s_r['MO Cliente'] + s_r['MO Garantía']) / cpus
        
        c1, c2 = st.columns(2)
        c1.metric("Ticket Promedio M.O. (Hs)", f"{tp_hs:.2f} hs/OT")
        c2.metric("Ticket Promedio M.O. ($)", f"${tp_mo:,.0f}/OT")

        # Gráfico de Evolución Histórica
        st.markdown("---")
        hist_data = data['SERVICIOS'][data['SERVICIOS']['Fecha_dt'].dt.year == año_sel].copy()
        fig_cpus = px.line(hist_data, x='Fecha_dt', y='CPUS', title="Evolución Histórica CPUS", markers=True)
        st.plotly_chart(fig_cpus, use_container_width=True)

    with tab3:
        st.subheader("Repuestos - Performance")
        tp_rep = (r_r.get('Venta Taller',0) + r_r.get('Venta Garantía',0) + r_r.get('Venta CyP',0)) / cpus
        st.metric("Ticket Promedio Repuestos ($)", f"${tp_rep:,.0f}/OT")
        
        # Histórico de Facturación vs Objetivo
        hist_rep = data['REPUESTOS'][data['REPUESTOS']['Fecha_dt'].dt.year == año_sel].copy()
        # Aquí calculamos la suma de ventas por fila para el gráfico
        canales = ['Venta Mostrador', 'Venta Taller', 'Venta Interna', 'Venta Garantía', 'Venta CyP', 'Venta Mayorista', 'Venta Seguros']
        hist_rep['Total Venta'] = hist_rep[canales].sum(axis=1)
        fig_rep = px.bar(hist_rep, x='Fecha_dt', y=['Total Venta', 'Obj Facturación Total'], barmode='group', title="Facturación vs Objetivo Repuestos")
        st.plotly_chart(fig_rep, use_container_width=True)

    with tab4:
        st.subheader("Chapa y Pintura - Evolución")
        hist_cj = data['CyP JUJUY'][data['CyP JUJUY']['Fecha_dt'].dt.year == año_sel].copy()
        fig_p = px.line(hist_cj, x='Fecha_dt', y=['Paños Propios', 'Obj Paños Propios Mensual'], title="Evolución Paños Jujuy vs Objetivo", markers=True)
        st.plotly_chart(fig_p, use_container_width=True)

except Exception as e:
    st.error(f"Error técnico: {e}")
