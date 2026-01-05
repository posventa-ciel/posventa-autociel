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

# --- FUNCIÓN DE BÚSQUEDA ---
def find_col(df, keywords):
    for col in df.columns:
        if all(k.upper() in col for k in keywords):
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
    
    # Procesar Fechas
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

    # Días
    col_dt = find_col(data['CALENDARIO'], ["DIAS", "TRANS"])
    col_dh = find_col(data['CALENDARIO'], ["DIAS", "HAB"])
    d_t, d_h = float(c_r.get(col_dt, 1)), float(c_r.get(col_dh, 1))
    prog_t = d_t / d_h if d_h > 0 else 0

    st.markdown(f"""<div class="portada-container"><h1>Autociel - Posventa</h1>
    <p>📅 {meses_nom.get(mes_sel)} {año_sel} | Avance: {d_t:g}/{d_h:g} días ({prog_t:.1%})</p></div>""", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🏠 General", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura"])

    with tab1:
        cols = st.columns(4)
        c_mc, c_mg, c_mt = find_col(data['SERVICIOS'], ["MO", "CLI"]), find_col(data['SERVICIOS'], ["MO", "GAR"]), find_col(data['SERVICIOS'], ["MO", "TER"])
        r_mo = s_r[c_mc] + s_r[c_mg] + s_r[c_mt]
        r_rep = sum([r_r[c] for c in r_r.index if "VENTA" in c and "OBJ" not in c])
        
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
                    <p style="margin:0; font-size:13px; color:#999;">Obj: ${obj:,.0f}</p>
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
        c_cpus = find_col(data['SERVICIOS'], ["CPUS"])
        real_tus = s_r.get(c_cpus, 0) + s_r.get(find_col(data['SERVICIOS'], ["OTROS", "CARGOS"]), 0)
        obj_tus = s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'TUS']), 1)
        p_tus = (real_tus/d_t)*d_h if d_t > 0 else 0; alc_tus = p_tus/obj_tus if obj_tus > 0 else 0
        
        real_cpus = s_r.get(c_cpus, 0)
        obj_cpus = s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'CPUS']), 1)
        p_cpus = (real_cpus/d_t)*d_h if d_t > 0 else 0; alc_cpus = p_cpus/obj_cpus if obj_cpus > 0 else 0

        def card(col, t, r, o, p, a):
            c = "#dc3545" if a < 0.90 else ("#ffc107" if a < 0.95 else "#28a745")
            with col:
                st.markdown(f'<div style="border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; background-color: white;">'
                            f'<p style="font-weight:bold; color:#666; font-size:13px;">{t}</p>'
                            f'<h3>{r:,.0f} <span style="font-size:14px; color:#999;">/ {o:,.0f}</span></h3>'
                            f'<p style="color:{c}; font-weight:bold; margin:0; font-size:14px;">↑ Proy: {p:,.0f} ({a:.1%})</p></div>', unsafe_allow_html=True)

        card(k1, "TUS Total", real_tus, obj_tus, p_tus, alc_tus)
        card(k2, "CPUS (Cargos Cliente)", real_cpus, obj_cpus, p_cpus, alc_cpus)

        # --- CORRECCIÓN TICKET PROMEDIO ---
        # Numerador: Hs Facturadas CC + Hs Facturadas CG
        hs_fact_cc = t_r.get(find_col(data['TALLER'], ["FACT", "CC"]), 0)
        hs_fact_cg = t_r.get(find_col(data['TALLER'], ["FACT", "CG"]), 0)
        
        # Denominador: CPUS
        divisor = real_cpus if real_cpus > 0 else 1
        
        tp_hs = (hs_fact_cc + hs_fact_cg) / divisor
        tp_mo = (s_r.get(c_mc, 0) + s_r.get(c_mg, 0)) / divisor
        
        k3.metric("Ticket Promedio M.O. (Hs)", f"{tp_hs:.2f} hs/CPUS")
        k4.metric("Ticket Promedio M.O. ($)", f"${tp_mo:,.0f}/CPUS")
        
        st.markdown("---")
        # --- INDICADORES DE TALLER RESTAURADOS ---
        st.subheader("Indicadores de Taller")
        e1, e2, e3 = st.columns(3)
        
        # Eficiencia Global (Total Facturado / Total Trabajado)
        ht_tot = t_r.get(find_col(data['TALLER'], ["TRAB", "CC"]), 0) + t_r.get(find_col(data['TALLER'], ["TRAB", "CG"]), 0) + t_r.get(find_col(data['TALLER'], ["TRAB", "CI"]), 0)
        hf_tot = hs_fact_cc + hs_fact_cg + t_r.get(find_col(data['TALLER'], ["FACT", "CI"]), 0)
        ef_gl = hf_tot / ht_tot if ht_tot > 0 else 0
        
        # Ocupación (Total Trabajado / Disponibles)
        hs_disp = t_r.get(find_col(data['TALLER'], ["DISPONIBLES", "REAL"]), 0)
        ocup = ht_tot / hs_disp if hs_disp > 0 else 0
        
        # Productividad (Dato directo del sheet)
        prod = t_r.get(find_col(data['TALLER'], ["PRODUCTIVIDAD", "TALLER"]), 0)
        if prod > 2: prod /= 100
        
        e1.metric("Eficiencia Global", f"{ef_gl:.1%}", delta=f"{(ef_gl-0.85):.1%}")
        e2.metric("Grado Ocupación", f"{ocup:.1%}", delta=f"{(ocup-0.95):.1%}")
        e3.metric("Productividad", f"{prod:.1%}", delta=f"{(prod-0.95):.1%}")

        st.markdown("---")
        # --- GRÁFICOS DE EVOLUCIÓN ---
        st.subheader("Evolución de Indicadores Clave")
        # Necesitamos unir Taller y Servicios por fecha para graficar
        hist_taller = data['TALLER'][data['TALLER']['Año'] == año_sel].copy().groupby('Mes').last().reset_index()
        
        if not hist_taller.empty:
            # Recalcular indicadores históricos para el gráfico
            col_ht_cc = find_col(data['TALLER'], ["TRAB", "CC"])
            col_ht_cg = find_col(data['TALLER'], ["TRAB", "CG"])
            col_ht_ci = find_col(data['TALLER'], ["TRAB", "CI"])
            col_hf_cc = find_col(data['TALLER'], ["FACT", "CC"])
            col_hf_cg = find_col(data['TALLER'], ["FACT", "CG"])
            col_hf_ci = find_col(data['TALLER'], ["FACT", "CI"])
            col_disp = find_col(data['TALLER'], ["DISPONIBLES"])
            col_prod = find_col(data['TALLER'], ["PRODUCTIVIDAD"])

            # Cálculos en el dataframe histórico
            hist_taller['Total_Trab'] = hist_taller[col_ht_cc] + hist_taller[col_ht_cg] + hist_taller[col_ht_ci]
            hist_taller['Total_Fact'] = hist_taller[col_hf_cc] + hist_taller[col_hf_cg] + hist_taller[col_hf_ci]
            
            hist_taller['Eficiencia'] = hist_taller['Total_Fact'] / hist_taller['Total_Trab'].replace(0,1)
            hist_taller['Ocupación'] = hist_taller['Total_Trab'] / hist_taller[col_disp].replace(0,1)
            
            # Normalizar productividad histórica
            hist_taller['Prod_Final'] = hist_taller[col_prod].apply(lambda x: x/100 if x > 2 else x)

            fig_evol = go.Figure()
            fig_evol.add_trace(go.Scatter(x=hist_taller['Mes'], y=hist_taller['Eficiencia'], mode='lines+markers', name='Eficiencia'))
            fig_evol.add_trace(go.Scatter(x=hist_taller['Mes'], y=hist_taller['Ocupación'], mode='lines+markers', name='Ocupación'))
            fig_evol.add_trace(go.Scatter(x=hist_taller['Mes'], y=hist_taller['Prod_Final'], mode='lines+markers', name='Productividad'))
            fig_evol.update_layout(title="Evolución Mensual (Eficiencia, Ocupación, Productividad)", yaxis_tickformat='.0%')
            st.plotly_chart(fig_evol, use_container_width=True)

    with tab3:
        st.header("Repuestos")
        canales_r = ['MOSTRADOR', 'TALLER', 'INTERNA', 'GARANTIA', 'CYP', 'MAYORISTA', 'SEGUROS']
        detalles = []
        for c in canales_r:
            vb = r_r.get(find_col(data['REPUESTOS'], ["VENTA", c]), 0)
            d = r_r.get(find_col(data['REPUESTOS'], ["DESC", c]), 0)
            cost = r_r.get(find_col(data['REPUESTOS'], ["COSTO", c]), 0)
            vn = vb - d; ut = vn - cost
            detalles.append({"Canal": c, "Bruta": vb, "Desc": d, "Costo": cost, "Margen $": ut, "% Mg": (ut/vn if vn>0 else 0)})
        df_r = pd.DataFrame(detalles)
        
        r1, r2, r3, r4 = st.columns(4)
        vbt = df_r['Bruta'].sum()
        mgt = df_r['Margen $'].sum()
        mgp = mgt / (vbt - df_r['Desc'].sum()) if (vbt - df_r['Desc'].sum())>0 else 0
        
        # Ticket Repuestos
        v_taller = r_r.get(find_col(data['REPUESTOS'], ["VENTA", "TALLER"]), 0)
        v_gar = r_r.get(find_col(data['REPUESTOS'], ["VENTA", "GAR"]), 0)
        v_cyp = r_r.get(find_col(data['REPUESTOS'], ["VENTA", "CYP"]), 0)
        tp_rep = (v_taller + v_gar + v_cyp) / divisor
        
        r1.metric("Facturación Bruta", f"${vbt:,.0f}")
        r2.metric("Margen Total $", f"${mgt:,.0f}")
        r3.metric("Margen %", f"{mgp:.1%}")
        r4.metric("Ticket Prom. Rep.", f"${tp_rep:,.0f}/CPUS")
        
        st.dataframe(df_r.style.format({"Bruta":"${:,.0f}","Desc":"${:,.0f}","Costo":"${:,.0f}","Margen $":"${:,.0f}","% Mg":"{:.1%}"}), use_container_width=True)
        # --- VALOR STOCK RESTAURADO ---
        c_val_stock = find_col(data['REPUESTOS'], ["VALOR", "STOCK"])
        val_stock = float(r_r.get(c_val_stock, 0))
        st.info(f"💰 **VALOR TOTAL DEL STOCK:** ${val_stock:,.0f}")
        
        rg1, rg2 = st.columns(2)
        with rg1: st.plotly_chart(px.pie(df_r, values="Bruta", names="Canal", hole=0.4, title="Participación por Canal"), use_container_width=True)
        with rg2:
            p_vivo = float(r_r.get(find_col(data['REPUESTOS'], ["VIVO"]), 0))
            p_obs = float(r_r.get(find_col(data['REPUESTOS'], ["OBSOLETO"]), 0))
            p_muerto = float(r_r.get(find_col(data['REPUESTOS'], ["MUERTO"]), 0))
            f = 1 if p_vivo <= 1 else 100
            df_s = pd.DataFrame({"Estado": ["Vivo", "Obsoleto", "Muerto"], "Valor": [val_stock*(p_vivo/f), val_stock*(p_obs/f), val_stock*(p_muerto/f)]})
            st.plotly_chart(px.pie(df_s, values="Valor", names="Estado", hole=0.4, title="Conformación Stock", color="Estado", color_discrete_map={"Vivo":"#28a745","Obsoleto":"#ffc107","Muerto":"#dc3545"}), use_container_width=True)

        st.subheader("Evolución Facturación")
        hist_r = data['REPUESTOS'][data['REPUESTOS']['Año'] == año_sel].copy().groupby('Mes').last().reset_index()
        if not hist_r.empty:
             st.plotly_chart(px.bar(hist_r, x='Mes', y=find_col(data['REPUESTOS'],['OBJ','FACT']), title="Histórico Objetivos"), use_container_width=True)

    with tab4:
        st.header("Chapa y Pintura")
        cp1, cp2 = st.columns(2)
        for i, (nom, row, sh) in enumerate([('Jujuy', cj_r, 'CyP JUJUY'), ('Salta', cs_r, 'CyP SALTA')]):
            r_p = row.get(find_col(data[sh], ['PAÑOS', 'PROP']), 0)
            o_p = row.get(find_col(data[sh], ['OBJ', 'PAÑO']), 1)
            p_p = (r_p/d_t)*d_h if d_t > 0 else 0; alc_p = p_p/o_p if o_p>0 else 0
            color_p = "#dc3545" if alc_p < 0.90 else ("#ffc107" if alc_p < 0.95 else "#28a745")
            with (cp1 if i==0 else cp2):
                st.markdown(f'<div style="border: 1px solid #e0e0e0; padding: 20px; border-radius: 10px; background-color: white; min-height: 170px;"><p style="font-weight:bold;">Sede {nom} - Paños</p><h1 style="margin: 0; font-size: 42px; color: #333;">{r_p:,.0f} <span style="font-size: 18px; color: #999;">/ Obj: {o_p:,.0f}</span></h1><p style="color: {color_p}; font-weight: bold; font-size: 18px; margin-top: 15px; border-top: 1px solid #eee; padding-top: 10px;">↑ Proyección: {p_p:,.0f} ({alc_p:.1%})</p></div>', unsafe_allow_html=True)
        
        hist_cj = data['CyP JUJUY'][data['CyP JUJUY']['Año'] == año_sel].copy().groupby('Mes').last().reset_index()
        if not hist_cj.empty:
            st.plotly_chart(px.line(hist_cj, x='Mes', y=[find_col(data['CyP JUJUY'], ['PAÑOS', 'PROP']), find_col(data['CyP JUJUY'], ['OBJ', 'PAÑO'])], title="Evolución Paños Jujuy vs Objetivo", markers=True), use_container_width=True)

except Exception as e:
    st.error(f"Error técnico detectado: {e}")
