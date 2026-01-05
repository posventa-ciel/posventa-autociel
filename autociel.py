import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Grupo CENOA - Gestión Posventa", layout="wide")

# --- ESTILO ---
st.markdown("""<style>
    .main { background-color: #f4f7f9; }
    .portada-container { background: linear-gradient(90deg, #00235d 0%, #004080 100%); color: white; padding: 2rem; border-radius: 15px; text-align: center; margin-bottom: 2rem; }
    .area-box { background-color: white; border: 1px solid #e0e0e0; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); min-height: 250px; margin-bottom: 20px; }
    .stMetric { background-color: white; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; }
    .stTabs [aria-selected="true"] { background-color: #00235d !important; color: white !important; font-weight: bold; }
</style>""", unsafe_allow_html=True)

# --- MOTOR DE BÚSQUEDA ---
def find_col(df, include_keywords, exclude_keywords=[]):
    for col in df.columns:
        if all(k.upper() in col for k in include_keywords):
            if not any(x.upper() in col for x in exclude_keywords):
                return col
    return ""

@st.cache_data(ttl=60)
def cargar_datos(sheet_id):
    hojas = ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA']
    data_dict = {}
    for h in hojas:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={h.replace(' ', '%20')}"
        df = pd.read_csv(url, dtype=str).fillna("0")
        df.columns = [c.strip().upper().replace(".", "") for c in df.columns]
        for col in df.columns:
            if "FECHA" not in col and "CANAL" not in col and "ESTADO" not in col:
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
    año_sel = st.sidebar.selectbox("📅 Año", años_disp)
    meses_nom = {1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic"}
    meses_disp = sorted(data['CALENDARIO'][data['CALENDARIO']['Año'] == año_sel]['Mes'].unique(), reverse=True)
    mes_sel = st.sidebar.selectbox("📅 Mes", meses_disp, format_func=lambda x: meses_nom.get(x, "N/A"))

    def get_mes_data(df):
        res = df[(df['Año'] == año_sel) & (df['Mes'] == mes_sel)]
        return res.sort_values('Fecha_dt').iloc[-1] if not res.empty else df.iloc[-1]

    c_r, s_r, r_r, t_r = get_mes_data(data['CALENDARIO']), get_mes_data(data['SERVICIOS']), get_mes_data(data['REPUESTOS']), get_mes_data(data['TALLER'])
    cj_r, cs_r = get_mes_data(data['CyP JUJUY']), get_mes_data(data['CyP SALTA'])

    d_t = float(c_r.get(find_col(data['CALENDARIO'], ["DIAS", "TRANS"]), 1))
    d_h = float(c_r.get(find_col(data['CALENDARIO'], ["DIAS", "HAB"]), 1))
    prog_t = d_t / d_h if d_h > 0 else 0

    st.markdown(f"""<div class="portada-container"><h1>Autociel - Posventa</h1>
    <p>📅 {meses_nom.get(mes_sel)} {año_sel} | Avance: {d_t:g}/{d_h:g} días ({prog_t:.1%})</p></div>""", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🏠 General", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura"])

    with tab1:
        cols = st.columns(4)
        c_mc = find_col(data['SERVICIOS'], ["MO", "CLI"], ["OBJ", "HS"])
        c_mg = find_col(data['SERVICIOS'], ["MO", "GAR"], ["OBJ", "HS"])
        c_mt = find_col(data['SERVICIOS'], ["MO", "TER"], ["OBJ", "HS"])
        r_mo = s_r.get(c_mc,0) + s_r.get(c_mg,0) + s_r.get(c_mt,0)
        
        canales_totales = ['MOSTRADOR', 'TALLER', 'INTERNA', 'GAR', 'CYP', 'MAYORISTA', 'SEGUROS']
        r_rep = sum([r_r.get(find_col(data['REPUESTOS'], ["VENTA", c], ["OBJ"]), 0) for c in canales_totales])
        
        metas = [
            ("M.O. Servicios", r_mo, s_r.get(find_col(data['SERVICIOS'], ["OBJ", "MO"]), 1)),
            ("Repuestos", r_rep, r_r.get(find_col(data['REPUESTOS'], ["OBJ", "FACT"]), 1)),
            ("CyP Jujuy", cj_r.get(find_col(data['CyP JUJUY'], ["MO", "PUR"]), 0) + cj_r.get(find_col(data['CyP JUJUY'], ["MO", "TER"]), 0), cj_r.get(find_col(data['CyP JUJUY'], ["OBJ", "FACT"]), 1)),
            ("CyP Salta", cs_r.get(find_col(data['CyP SALTA'], ["MO", "PUR"]), 0) + cs_r.get(find_col(data['CyP SALTA'], ["MO", "TER"]), 0) + cs_r.get('FACTREPUESTOS', 0), cs_r.get(find_col(data['CyP SALTA'], ["OBJ", "FACT"]), 1))
        ]
        for i, (tit, real, obj) in enumerate(metas):
            p = (real/d_t)*d_h if d_t > 0 else 0; alc = p/obj if obj > 0 else 0
            color = "#dc3545" if alc < 0.90 else ("#ffc107" if alc < 0.95 else "#28a745")
            cols[i].markdown(f"""<div class="area-box">
                <p style="font-weight:bold; color:#666;">{tit}</p><h2>${real:,.0f}</h2>
                <p style="color:{color}; font-weight:bold;">Proy: {alc:.1%}</p>
                <div style="width:100%; background:#e0e0e0; height:8px; border-radius:10px;"><div style="width:{min(alc*100, 100)}%; background:{color}; height:8px; border-radius:10px;"></div></div>
            </div>""", unsafe_allow_html=True)

    with tab2:
        st.header("Performance y Tickets")
        k1, k2, k3, k4 = st.columns(4)
        c_cpus_r = find_col(data['SERVICIOS'], ["CPUS"], ["OBJ", "META"])
        real_cpus = s_r.get(c_cpus_r, 0)
        real_tus = real_cpus + s_r.get(find_col(data['SERVICIOS'], ["OTROS", "CARGOS"], ["OBJ"]), 0)
        obj_tus, obj_cpus = s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'TUS']), 1), s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'CPUS']), 1)
        
        # COLORES SEGÚN OBJETIVO
        c_tus_color = "normal" if (real_tus/obj_tus) >= (d_t/d_h) else "inverse"
        c_cpus_color = "normal" if (real_cpus/obj_cpus) >= (d_t/d_h) else "inverse"

        k1.metric("TUS Real", f"{real_tus:,.0f}", f"Obj: {obj_tus:,.0f}", delta_color=c_tus_color)
        k2.metric("CPUS Real", f"{real_cpus:,.0f}", f"Obj: {obj_cpus:,.0f}", delta_color=c_cpus_color)
        
        divisor = real_cpus if real_cpus > 0 else 1
        h_cc = t_r.get(find_col(data['TALLER'], ["FACT", "CC"], ["$"]), 0)
        h_cg = t_r.get(find_col(data['TALLER'], ["FACT", "CG"], ["$"]), 0)
        tp_hs = (h_cc + h_cg) / divisor
        tp_mo = (s_r.get(c_mc, 0) + s_r.get(c_mg, 0)) / divisor
        
        k3.metric("Ticket Promedio (Hs)", f"{tp_hs:.2f}")
        k4.metric("Ticket Promedio ($)", f"${tp_mo:,.0f}")

        st.markdown("---")
        st.subheader("Indicadores de Taller")
        col_tr_cc, col_tr_cg, col_tr_ci = find_col(data['TALLER'], ["TRAB", "CC"], ["$"]), find_col(data['TALLER'], ["TRAB", "CG"], ["$"]), find_col(data['TALLER'], ["TRAB", "CI"], ["$"])
        col_ft_cc, col_ft_cg, col_ft_ci = find_col(data['TALLER'], ["FACT", "CC"], ["$"]), find_col(data['TALLER'], ["FACT", "CG"], ["$"]), find_col(data['TALLER'], ["FACT", "CI"], ["$"])
        
        ht_tot = t_r.get(col_tr_cc, 0) + t_r.get(col_tr_cg, 0) + t_r.get(col_tr_ci, 0)
        hf_tot = t_r.get(col_ft_cc, 0) + t_r.get(col_ft_cg, 0) + t_r.get(col_ft_ci, 0)
        h_disp = t_r.get(find_col(data['TALLER'], ["DISP"]), 1)
        
        i1, i2, i3 = st.columns(3)
        i1.metric("Eficiencia Global", f"{(hf_tot/ht_tot if ht_tot>0 else 0):.1%}")
        i2.metric("Ocupación", f"{(ht_tot/h_disp if h_disp>0 else 0):.1%}")
        prod_val = t_r.get(find_col(data['TALLER'], ["PRODUCTIVIDAD"]), 0)
        i3.metric("Productividad", f"{(prod_val/100 if prod_val>2 else prod_val):.1%}")
        
        g1, g2 = st.columns(2)
        with g1: st.plotly_chart(px.pie(values=[t_r.get(col_tr_cc, 0), t_r.get(col_tr_cg, 0), t_r.get(col_tr_ci, 0)], names=["CC", "CG", "CI"], hole=0.4, title="Hs Trabajadas"), use_container_width=True)
        with g2: st.plotly_chart(px.pie(values=[t_r.get(col_ft_cc, 0), t_r.get(col_ft_cg, 0), t_r.get(col_ft_ci, 0)], names=["CC", "CG", "CI"], hole=0.4, title="Hs Facturadas"), use_container_width=True)

    with tab3:
        st.header("Repuestos")
        canales_r = ['MOSTRADOR', 'TALLER', 'INTERNA', 'GAR', 'CYP', 'MAYORISTA', 'SEGUROS']
        detalles = []
        for c in canales_r:
            v_col = find_col(data['REPUESTOS'], ["VENTA", c], ["OBJ"])
            if v_col:
                vb, d, cost = r_r.get(v_col, 0), r_r.get(find_col(data['REPUESTOS'], ["DESC", c]), 0), r_r.get(find_col(data['REPUESTOS'], ["COSTO", c]), 0)
                detalles.append({"Canal": c.replace("GAR", "GARANTÍA"), "Bruta": vb, "Desc": d, "Costo": cost, "Margen $": (vb-d-cost), "% Mg": ((vb-d-cost)/(vb-d) if (vb-d)>0 else 0)})
        st.dataframe(pd.DataFrame(detalles).style.format({"Bruta":"${:,.0f}", "Desc":"${:,.0f}", "Costo":"${:,.0f}", "Margen $":"${:,.0f}", "% Mg":"{:.1%}"}), use_container_width=True)
        
        rg1, rg2 = st.columns(2)
        with rg1: st.plotly_chart(px.pie(pd.DataFrame(detalles), values="Bruta", names="Canal", hole=0.4, title="Mix de Venta"), use_container_width=True)
        with rg2:
            v_stock = float(r_r.get(find_col(data['REPUESTOS'], ["VALOR", "STOCK"]), 0))
            st.metric("Valor Total Stock", f"${v_stock:,.0f}")
            st.plotly_chart(px.pie(values=[70, 20, 10], names=["Vivo", "Obsoleto", "Muerto"], hole=0.4, title="Composición Stock"), use_container_width=True)

    with tab4:
        st.header("Chapa y Pintura")
        c1, c2 = st.columns(2)
        for i, (nom, row, sh) in enumerate([('Jujuy', cj_r, 'CyP JUJUY'), ('Salta', cs_r, 'CyP SALTA')]):
            with (c1 if i == 0 else c2):
                st.subheader(f"Sede {nom}")
                # --- RATIO PAÑOS ---
                p_prop = row.get(find_col(data[sh], ["PAÑOS", "PROP"], ["OBJ"]), 0)
                col_t = find_col(data[sh], ["TEC"], ["OBJ", "META", "PROD", "%", "PAÑO", "HS"])
                cant_t = row.get(col_t, 1)
                
                st.metric("Paños por Técnico", f"{(p_prop/cant_t if cant_t > 0 else 0):.2f}")
                
                f_p, f_t = row.get(find_col(data[sh], ['MO', 'PUR']), 0), row.get(find_col(data[sh], ['MO', 'TER']), 0)
                # FACTURACIÓN COMPLETA (SALTA SUMA REPUESTOS)
                f_r_extra = row.get(find_col(data[sh], ['FACT', 'REP']), 0) if nom == 'Salta' else 0
                st.metric(f"Facturación Total {nom}", f"${(f_p + f_t + f_r_extra):,.0f}")
                
                st.markdown(f"<div style='background:#f1f3f6; padding:10px; border-radius:8px; border-left: 5px solid #00235d;'><b>Terceros:</b> Fact: ${f_t:,.0f} | Mg: ${(f_t - row.get(find_col(data[sh], ['COSTO', 'TER']), 0)):,.0f}</div>", unsafe_allow_html=True)
                if nom == 'Salta':
                    st.markdown(f"<div style='background:#e8f5e9; padding:10px; border-radius:8px; border-left: 5px solid #28a745;'><b>Repuestos CyP:</b> Fact: ${f_r_extra:,.0f} | Mg: ${(f_r_extra - row.get(find_col(data[sh], ['COSTO', 'REP']), 0)):,.0f}</div>", unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error detectado: {e}")
