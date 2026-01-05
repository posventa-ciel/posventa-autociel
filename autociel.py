import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Grupo CENOA - Gestión Posventa", layout="wide")

# --- ESTILO CORPORATIVO (Mantenido) ---
st.markdown("""<style>
    .main { background-color: #f4f7f9; }
    .portada-container { background: linear-gradient(90deg, #00235d 0%, #004080 100%); color: white; padding: 2rem; border-radius: 15px; text-align: center; margin-bottom: 2rem; }
    .area-box { background-color: white; border: 1px solid #e0e0e0; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); min-height: 250px; margin-bottom: 20px; }
    .stMetric { background-color: white; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; }
    .stTabs [aria-selected="true"] { background-color: #00235d !important; color: white !important; font-weight: bold; }
</style>""", unsafe_allow_html=True)

# --- FUNCIÓN DE BÚSQUEDA ---
def find_col(df, include_keywords, exclude_keywords=[]):
    for col in df.columns:
        if all(k.upper() in col for k in include_keywords):
            if not any(x.upper() in col for x in exclude_keywords):
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

    c_r = get_mes_data(data['CALENDARIO'])
    s_r = get_mes_data(data['SERVICIOS'])
    r_r = get_mes_data(data['REPUESTOS'])
    t_r = get_mes_data(data['TALLER'])
    cj_r = get_mes_data(data['CyP JUJUY'])
    cs_r = get_mes_data(data['CyP SALTA'])

    d_t = float(c_r.get(find_col(data['CALENDARIO'], ["DIAS", "TRANS"]), 1))
    d_h = float(c_r.get(find_col(data['CALENDARIO'], ["DIAS", "HAB"]), 1))
    prog_t = d_t / d_h if d_h > 0 else 0

    st.markdown(f"""<div class="portada-container"><h1>Autociel - Posventa</h1>
    <p>📅 {meses_nom.get(mes_sel)} {año_sel} | Avance: {d_t:g}/{d_h:g} días ({prog_t:.1%})</p></div>""", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🏠 General", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura"])

    with tab1:
        cols = st.columns(4)
        c_mc = find_col(data['SERVICIOS'], ["MO", "CLI"], exclude_keywords=["OBJ", "HS"])
        c_mg = find_col(data['SERVICIOS'], ["MO", "GAR"], exclude_keywords=["OBJ", "HS"])
        c_mt = find_col(data['SERVICIOS'], ["MO", "TER"], exclude_keywords=["OBJ", "HS"])
        r_mo = s_r.get(c_mc,0) + s_r.get(c_mg,0) + s_r.get(c_mt,0)
        
        canales_totales = ['MOSTRADOR', 'TALLER', 'INTERNA', 'GAR', 'CYP', 'MAYORISTA', 'SEGUROS']
        r_rep = 0
        for canal_rep in canales_totales:
            col_v = find_col(data['REPUESTOS'], ["VENTA", canal_rep], exclude_keywords=["OBJ"])
            if col_v: r_rep += r_r.get(col_v, 0)
        
        metas = [
            ("M.O. Servicios", r_mo, s_r.get(find_col(data['SERVICIOS'], ["OBJ", "MO"]), 1)),
            ("Repuestos", r_rep, r_r.get(find_col(data['REPUESTOS'], ["OBJ", "FACT"]), 1)),
            ("CyP Jujuy", cj_r.get(find_col(data['CyP JUJUY'], ["MO", "PUR"]), 0) + cj_r.get(find_col(data['CyP JUJUY'], ["MO", "TER"]), 0), cj_r.get(find_col(data['CyP JUJUY'], ["OBJ", "FACT"]), 1)),
            ("CyP Salta", cs_r.get(find_col(data['CyP SALTA'], ["MO", "PUR"]), 0) + cs_r.get(find_col(data['CyP SALTA'], ["MO", "TER"]), 0) + cs_r.get('FACTREPUESTOS', 0), cs_r.get(find_col(data['CyP SALTA'], ["OBJ", "FACT"]), 1))
        ]
        
        for i, (tit, real, obj) in enumerate(metas):
            p = (real/d_t)*d_h if d_t > 0 else 0; alc = p/obj if obj > 0 else 0
            color = "#dc3545" if alc < 0.90 else ("#ffc107" if alc < 0.95 else "#28a745")
            with cols[i]:
                st.markdown(f"""<div class="area-box">
                    <p style="font-weight:bold; color:#666; margin-bottom:5px;">{tit}</p>
                    <h2 style="margin:0; color:#00235d;">${real:,.0f}</h2>
                    <p style="margin:0; font-size:13px; color:#999;">Objetivo: ${obj:,.0f}</p>
                    <div style="margin-top:15px;">
                        <p style="color:{color}; margin:0; font-weight:bold;">Proy: {alc:.1%}</p>
                        <p style="color:#666; font-size:13px; margin:0;">Est. al cierre: <b>${p:,.0f}</b></p>
                        <div style="width:100%; background:#e0e0e0; height:8px; border-radius:10px; margin-top:5px;">
                            <div style="width:{min(alc*100, 100)}%; background:{color}; height:8px; border-radius:10px;"></div>
                        </div>
                    </div>
                </div>""", unsafe_allow_html=True)

    with tab2:
        st.header("Performance y Tickets")
        k1, k2, k3, k4 = st.columns(4)
        c_cpus_real = find_col(data['SERVICIOS'], ["CPUS"], exclude_keywords=["OBJ", "META"])
        c_tus_real = find_col(data['SERVICIOS'], ["OTROS", "CARGOS"], exclude_keywords=["OBJ"])
        
        real_tus = s_r.get(c_cpus_real, 0) + s_r.get(c_tus_real, 0)
        obj_tus = s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'TUS']), 1)
        real_cpus = s_r.get(c_cpus_real, 0)
        obj_cpus = s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'CPUS']), 1)

        p_tus = (real_tus/d_t)*d_h if d_t > 0 else 0; alc_tus = p_tus/obj_tus if obj_tus > 0 else 0
        p_cpus = (real_cpus/d_t)*d_h if d_t > 0 else 0; alc_cpus = p_cpus/obj_cpus if obj_cpus > 0 else 0

        # Tarjetas de flujo
        with k1: st.metric("TUS Total", f"{real_tus:,.0f}", f"Proy: {p_tus:,.0f}")
        with k2: st.metric("CPUS Cliente", f"{real_cpus:,.0f}", f"Proy: {p_cpus:,.0f}")

        # Ticket Promedio
        divisor = real_cpus if real_cpus > 0 else 1
        col_hs_cc = find_col(data['TALLER'], ["FACT", "CC"], exclude_keywords=["$", "PESOS", "OBJ"])
        col_hs_cg = find_col(data['TALLER'], ["FACT", "CG"], exclude_keywords=["$", "PESOS", "OBJ"])
        tp_hs = (t_r.get(col_hs_cc, 0) + t_r.get(col_hs_cg, 0)) / divisor
        tp_mo = (s_r.get(c_mc, 0) + s_r.get(c_mg, 0)) / divisor
        
        with k3: st.metric("Ticket Promedio (Hs)", f"{tp_hs:.2f} hs/CPUS")
        with k4: st.metric("Ticket Promedio ($)", f"${tp_mo:,.0f}/CPUS")
        
        st.markdown("---")
        # COMPOSICIÓN DE HORAS
        st.subheader("Composición de Horas")
        col_tr_cc = find_col(data['TALLER'], ["TRAB", "CC"], exclude_keywords=["$"])
        col_tr_cg = find_col(data['TALLER'], ["TRAB", "CG"], exclude_keywords=["$"])
        col_tr_ci = find_col(data['TALLER'], ["TRAB", "CI"], exclude_keywords=["$"])
        col_ft_cc = find_col(data['TALLER'], ["FACT", "CC"], exclude_keywords=["$"])
        col_ft_cg = find_col(data['TALLER'], ["FACT", "CG"], exclude_keywords=["$"])
        col_ft_ci = find_col(data['TALLER'], ["FACT", "CI"], exclude_keywords=["$"])

        g1, g2 = st.columns(2)
        with g1: st.plotly_chart(px.pie(values=[t_r.get(col_tr_cc, 0), t_r.get(col_tr_cg, 0), t_r.get(col_tr_ci, 0)], names=["CC", "CG", "CI"], hole=0.4, title="Hs Trabajadas"), use_container_width=True)
        with g2: st.plotly_chart(px.pie(values=[t_r.get(col_ft_cc, 0), t_r.get(col_ft_cg, 0), t_r.get(col_ft_ci, 0)], names=["CC", "CG", "CI"], hole=0.4, title="Hs Facturadas"), use_container_width=True)

        # INDICADORES DE TALLER
        st.subheader("Indicadores de Taller")
        hf_tot = t_r.get(col_ft_cc, 0) + t_r.get(col_ft_cg, 0) + t_r.get(col_ft_ci, 0)
        ht_tot = t_r.get(col_tr_cc, 0) + t_r.get(col_tr_cg, 0) + t_r.get(col_tr_ci, 0)
        
        ef_cc = t_r.get(col_ft_cc, 0) / t_r.get(col_tr_cc, 0) if t_r.get(col_tr_cc, 0) > 0 else 0
        ef_cg = t_r.get(col_ft_cg, 0) / t_r.get(col_tr_cg, 0) if t_r.get(col_tr_cg, 0) > 0 else 0
        ef_gl = hf_tot / ht_tot if ht_tot > 0 else 0
        
        h_disp = t_r.get(find_col(data['TALLER'], ["DISPONIBLES", "REAL"]), 0)
        ocup = ht_tot / h_disp if h_disp > 0 else 0
        prod = t_r.get(find_col(data['TALLER'], ["PRODUCTIVIDAD", "TALLER"]), 0)
        if prod > 2: prod /= 100

        e_cols = st.columns(3)
        e_cols[0].metric("Eficiencia CC", f"{ef_cc:.1%}")
        e_cols[1].metric("Eficiencia CG", f"{ef_cg:.1%}")
        e_cols[2].metric("Eficiencia Global", f"{ef_gl:.1%}")
        
        o_cols = st.columns(3)
        o_cols[0].metric("Grado Presencia (Est.)", f"{(h_disp/(6*9*d_t)):.1%}" if d_t > 0 else "0%")
        o_cols[1].metric("Grado Ocupación", f"{ocup:.1%}")
        o_cols[2].metric("Productividad", f"{prod:.1%}")

        st.markdown("---")
        st.subheader("Evolución de Indicadores")
        hist_t = data['TALLER'][data['TALLER']['Año'] == año_sel].copy().groupby('Mes').last().reset_index()
        if not hist_t.empty:
            hist_t['EF_GL'] = (hist_t[col_ft_cc]+hist_t[col_ft_cg]+hist_t[col_ft_ci]) / (hist_t[col_tr_cc]+hist_t[col_tr_cg]+hist_t[col_tr_ci]).replace(0,1)
            hist_t['OCUP'] = (hist_t[col_tr_cc]+hist_t[col_tr_cg]+hist_t[col_tr_ci]) / hist_t[find_col(data['TALLER'],["DISP"])].replace(0,1)
            fig_ev = go.Figure()
            fig_ev.add_trace(go.Scatter(x=hist_t['Mes'], y=hist_t['EF_GL'], name='Eficiencia', mode='lines+markers'))
            fig_ev.add_trace(go.Scatter(x=hist_t['Mes'], y=hist_t['OCUP'], name='Ocupación', mode='lines+markers'))
            fig_ev.update_layout(yaxis_tickformat='.0%')
            st.plotly_chart(fig_ev, use_container_width=True)

    with tab3:
        st.header("Análisis de Repuestos")
        canales_r = ['MOSTRADOR', 'TALLER', 'INTERNA', 'GAR', 'CYP', 'MAYORISTA', 'SEGUROS']
        detalles = []
        for c in canales_r:
            v_col = find_col(data['REPUESTOS'], ["VENTA", c], exclude_keywords=["OBJ"])
            if v_col:
                vb = r_r.get(v_col, 0)
                d = r_r.get(find_col(data['REPUESTOS'], ["DESC", c]), 0)
                cost = r_r.get(find_col(data['REPUESTOS'], ["COSTO", c]), 0)
                detalles.append({"Canal": c.replace("GAR", "GARANTÍA"), "Bruta": vb, "Desc": d, "Costo": cost, "Margen $": (vb-d-cost), "% Mg": ((vb-d-cost)/(vb-d) if (vb-d)>0 else 0)})
        df_r = pd.DataFrame(detalles)
        st.dataframe(df_r.style.format({"Bruta":"${:,.0f}","Desc":"${:,.0f}","Costo":"${:,.0f}","Margen $":"${:,.0f}","% Mg":"{:.1%}"}), use_container_width=True)
        
        r1, r2 = st.columns(2)
        with r1: st.plotly_chart(px.pie(df_r, values="Bruta", names="Canal", hole=0.4, title="Participación"), use_container_width=True)
        with r2:
            val_stock = float(r_r.get(find_col(data['REPUESTOS'], ["VALOR", "STOCK"]), 0))
            st.metric("Valor Total del Stock", f"${val_stock:,.0f}")
            st.plotly_chart(px.pie(values=[70, 20, 10], names=["Vivo", "Obsoleto", "Muerto"], hole=0.4, title="Estado Stock"), use_container_width=True)

    with tab4:
        st.header("Chapa y Pintura")
        # --- LÓGICA DE PAÑOS POR TÉCNICO ---
        c1, c2 = st.columns(2)
        for i, (nom, row, sh) in enumerate([('Jujuy', cj_r, 'CyP JUJUY'), ('Salta', cs_r, 'CyP SALTA')]):
            with (c1 if i == 0 else c2):
                st.subheader(f"Sede {nom}")
                # 1. Obtener Paños Propios
                col_p_prop = find_col(data[sh], ["PAÑOS", "PROP"], exclude_keywords=["OBJ", "META"])
                paños_valor = row.get(col_p_prop, 0)
                
                # 2. Obtener Cantidad de Técnicos (Excluyendo Productividad %)
                col_tec = find_col(data[sh], ["CANT", "TEC"], exclude_keywords=["OBJ", "META", "PROD", "%"])
                if not col_tec: col_tec = find_col(data[sh], ["TECNICOS"], exclude_keywords=["OBJ", "PROD", "%"])
                tec_valor = row.get(col_tec, 1) # Usamos 1 de fallback para no dividir por 0
                
                # 3. Cálculo del Ratio
                ratio = paños_valor / tec_valor if tec_valor > 0 else 0
                
                st.metric("Paños por Técnico", f"{ratio:.1f}")
                st.caption(f"Calculado sobre {paños_valor:,.0f} paños y {tec_valor:g} técnicos.")
                
                # Facturación
                f_p = row.get(find_col(data[sh], ['MO', 'PUR']), 0)
                f_t = row.get(find_col(data[sh], ['MO', 'TER']), 0)
                st.metric(f"Facturación Total {nom}", f"${(f_p+f_t):,.0f}")
                
                c_ter = row.get(find_col(data[sh], ['COSTO', 'TER']), 0)
                st.markdown(f"<div style='background:#f1f3f6; padding:10px; border-radius:8px;'><b>Terceros:</b> Fact: ${f_t:,.0f} | Costo: ${c_ter:,.0f} | <b>Mg: ${(f_t-c_ter):,.0f}</b></div>", unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error técnico detectado: {e}")
