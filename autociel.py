import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Grupo CENOA - Gestión Posventa", layout="wide")

# --- ESTILO CORPORATIVO ---
st.markdown("""<style>
    .main { background-color: #f4f7f9; }
    .portada-container { background: linear-gradient(90deg, #00235d 0%, #004080 100%); color: white; padding: 2rem; border-radius: 15px; text-align: center; margin-bottom: 2rem; }
    .area-box { background-color: white; border: 1px solid #e0e0e0; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); min-height: 250px; margin-bottom: 20px; }
    .stMetric { background-color: white; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; }
    .stTabs [aria-selected="true"] { background-color: #00235d !important; color: white !important; font-weight: bold; }
</style>""", unsafe_allow_html=True)

# --- MOTOR DE BÚSQUEDA INTELIGENTE ---
def find_col(df, include, exclude=[]):
    """Busca columnas de forma flexible pero excluyendo términos no deseados"""
    for col in df.columns:
        if all(inc.upper() in col.upper() for inc in include):
            if not any(exc.upper() in col.upper() for exc in exclude):
                return col
    return ""

# --- CARGA DE DATOS ---
@st.cache_data(ttl=60)
def cargar_datos(sheet_id):
    hojas = ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA']
    data_dict = {}
    for h in hojas:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={h.replace(' ', '%20')}"
        df = pd.read_csv(url, dtype=str).fillna("0")
        df.columns = [c.strip().upper() for c in df.columns]
        for col in df.columns:
            if "FECHA" not in col and "CANAL" not in col:
                df[col] = df[col].astype(str).str.replace(r'[\$%\s]', '', regex=True).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        data_dict[h] = df
    return data_dict

ID_SHEET = "1yJgaMR0nEmbKohbT_8Vj627Ma4dURwcQTQcQLPqrFwk"

try:
    data = cargar_datos(ID_SHEET)
    for h in data:
        col_f = find_col(data[h], ["FECHA"]) or data[h].columns[0]
        data[h]['Fecha_dt'] = pd.to_datetime(data[h][col_f], dayfirst=True, errors='coerce')
        data[h]['Mes'] = data[h]['Fecha_dt'].dt.month
        data[h]['Año'] = data[h]['Fecha_dt'].dt.year

    # --- FILTROS ---
    años_disp = sorted([int(a) for a in data['CALENDARIO']['Año'].unique() if a > 0], reverse=True)
    año_sel = st.sidebar.selectbox("📅 Seleccionar Año", años_disp)
    meses_nom = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
    meses_disp = sorted(data['CALENDARIO'][data['CALENDARIO']['Año'] == año_sel]['Mes'].unique(), reverse=True)
    mes_sel = st.sidebar.selectbox("📅 Mes", meses_disp, format_func=lambda x: meses_nom.get(x, "N/A"))

    def get_mes_data(df):
        res = df[(df['Año'] == año_sel) & (df['Mes'] == mes_sel)]
        return res.sort_values('Fecha_dt').iloc[-1] if not res.empty else df.iloc[-1]

    c_r = get_mes_data(data['CALENDARIO'])
    s_r = get_mes_data(data['SERVICIOS'])
    r_r = get_mes_data(data['REPUESTOS'])
    t_r = get_mes_data(data['TALLER'])
    cj_r = get_mes_data(data['CyP JUJUY'])
    cs_r = get_mes_data(data['CyP SALTA'])

    d_t = float(c_r.get(find_col(data['CALENDARIO'], ["DIAS", "TRANS"]), 1))
    d_h = float(c_r.get(find_col(data['CALENDARIO'], ["DIAS", "HAB"]), 1))

    st.markdown(f"""<div class="portada-container"><h1>Gestión Posventa Autociel</h1>
    <p>📅 {meses_nom.get(mes_sel)} {año_sel} | Avance: {d_t:g}/{d_h:g} días ({(d_t/d_h):.1%})</p></div>""", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🏠 General", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura"])

    with tab2:
        st.header("Análisis de Servicios y Taller")
        # Ticket Promedio (HS CC + HS CG) / CPUS
        c_cpus = find_col(data['SERVICIOS'], ["CPUS"], ["OBJ", "META"])
        c_h_cc = find_col(data['TALLER'], ["HS", "FACT", "CC"], ["$"])
        c_h_cg = find_col(data['TALLER'], ["HS", "FACT", "CG"], ["$"])
        real_cpus = s_r.get(c_cpus, 1)
        tp_hs = (t_r.get(c_h_cc, 0) + t_r.get(c_h_cg, 0)) / (real_cpus if real_cpus > 0 else 1)
        
        m1, m2 = st.columns(2)
        m1.metric("Ticket Promedio (Hs)", f"{tp_hs:.2f} hs/CPUS")
        
        # 6 Indicadores de Taller
        st.markdown("---")
        st.subheader("Indicadores de Gestión de Taller")
        cols_ind = st.columns(3)
        cols_ind2 = st.columns(3)
        
        # Cálculos de Eficiencia
        ht_cc = t_r.get(find_col(data['TALLER'], ["HS", "TRAB", "CC"]), 0)
        hf_cc = t_r.get(find_col(data['TALLER'], ["HS", "FACT", "CC"]), 0)
        ef_cc = hf_cc / ht_cc if ht_cc > 0 else 0
        
        h_disp = t_r.get(find_col(data['TALLER'], ["DISP", "REAL"]), 1)
        ht_tot = ht_cc + t_r.get(find_col(data['TALLER'], ["TRAB", "CG"]), 0) + t_r.get(find_col(data['TALLER'], ["TRAB", "CI"]), 0)
        hf_tot = hf_cc + t_r.get(find_col(data['TALLER'], ["FACT", "CG"]), 0) + t_r.get(find_col(data['TALLER'], ["FACT", "CI"]), 0)
        
        ef_gl = hf_tot / ht_tot if ht_tot > 0 else 0
        ocup = ht_tot / h_disp if h_disp > 0 else 0
        prod = t_r.get(find_col(data['TALLER'], ["PRODUCTIVIDAD"]), 0)
        prod = prod/100 if prod > 2 else prod

        cols_ind[0].metric("Eficiencia CC", f"{ef_cc:.1%}")
        cols_ind[1].metric("Eficiencia Global", f"{ef_gl:.1%}")
        cols_ind[2].metric("Grado Ocupación", f"{ocup:.1%}")
        cols_ind2[0].metric("Productividad", f"{prod:.1%}")
        
        # Gráficos Composición
        st.markdown("---")
        g1, g2 = st.columns(2)
        with g1: st.plotly_chart(px.pie(values=[ht_cc, ht_tot-ht_cc], names=["CC", "Otros"], title="Composición Horas Trabajadas", hole=0.4), use_container_width=True)
        with g2: st.plotly_chart(px.pie(values=[hf_cc, hf_tot-hf_cc], names=["CC", "Otros"], title="Composición Horas Facturadas", hole=0.4), use_container_width=True)

    with tab3:
        st.header("Gestión de Repuestos")
        canales = ['MOSTRADOR', 'TALLER', 'INTERNA', 'GARANTIA', 'CYP', 'MAYORISTA', 'SEGUROS']
        detalles = []
        for c in canales:
            v_col = find_col(data['REPUESTOS'], ["VENTA", c], ["OBJ"])
            if v_col:
                vb = r_r.get(v_col, 0)
                d = r_r.get(find_col(data['REPUESTOS'], ["DESC", c]), 0)
                cost = r_r.get(find_col(data['REPUESTOS'], ["COSTO", c]), 0)
                detalles.append({"Canal": c, "Venta": vb, "Costo": cost, "Margen": (vb-d-cost)})
        
        st.table(pd.DataFrame(detalles))
        
        # Stock debajo del gráfico
        st.markdown("---")
        sg1, sg2 = st.columns([2,1])
        with sg1:
            st.plotly_chart(px.bar(pd.DataFrame(detalles), x="Canal", y="Venta", title="Ventas por Canal"), use_container_width=True)
        with sg2:
            val_stock = float(r_r.get(find_col(data['REPUESTOS'], ["VALOR", "STOCK"]), 0))
            st.metric("Valor Total Stock", f"${val_stock:,.0f}")
            st.plotly_chart(px.pie(values=[70, 20, 10], names=["Vivo", "Obs", "Muerto"], hole=0.4, title="Estado Stock"), use_container_width=True)

    with tab4:
        st.header("Chapa y Pintura - Eficiencia por Operario")
        c1, c2 = st.columns(2)
        
        # JUJUY: PAÑOS PROPIOS / CANT TECNICOS (Robusteciendo búsqueda)
        p_j = cj_r.get(find_col(data['CyP JUJUY'], ["PAÑOS", "PROP"], ["OBJ", "META"]), 0)
        t_j = cj_r.get(find_col(data['CyP JUJUY'], ["TEC"], ["OBJ", "META", "PROD", "%"]), 1)
        
        # SALTA: PAÑOS PROPIOS / CANT TECNICOS
        p_s = cs_r.get(find_col(data['CyP SALTA'], ["PAÑOS", "PROP"], ["OBJ", "META"]), 0)
        t_s = cs_r.get(find_col(data['CyP SALTA'], ["TEC"], ["OBJ", "META", "PROD", "%"]), 1)

        with c1:
            st.subheader("Sede Jujuy")
            st.metric("Paños por Técnico", f"{p_j/t_j:.2f}" if t_j > 0 else "0")
            f_ter = cj_r.get(find_col(data['CyP JUJUY'], ["MO", "TER"], ["OBJ"]), 0)
            c_ter = cj_r.get(find_col(data['CyP JUJUY'], ["COSTO", "TER"]), 0)
            st.markdown(f"**Terceros:** Fact: ${f_ter:,.0f} | Costo: ${c_ter:,.0f} | Mg: ${f_ter-c_ter:,.0f}")

        with c2:
            st.subheader("Sede Salta")
            st.metric("Paños por Técnico", f"{p_s/t_s:.2f}" if t_s > 0 else "0")
            f_rep = cs_r.get(find_col(data['CyP SALTA'], ["FACT", "REP"], ["OBJ"]), 0)
            c_rep = cs_r.get(find_col(data['CyP SALTA'], ["COSTO", "REP"]), 0)
            st.markdown(f"**Repuestos:** Fact: ${f_rep:,.0f} | Costo: ${c_rep:,.0f} | Mg: ${f_rep-c_rep:,.0f}")

except Exception as e:
    st.error(f"Error detectado: {e}")
