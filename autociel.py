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

def calcular_proyeccion(real, dias_t, dias_h):
    return (float(real) / float(dias_t)) * float(dias_h) if float(dias_t) > 0 else 0

@st.cache_data(ttl=60)
def cargar_datos_sheets(sheet_id):
    hojas = ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA']
    data_dict = {}
    for h in hojas:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx:out:csv&sheet={h.replace(' ', '%20')}"
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

    for h in data:
        col_f = 'Fecha Corte' if 'Fecha Corte' in data[h].columns else 'Fecha'
        data[h]['Fecha_dt'] = pd.to_datetime(data[h][col_f], dayfirst=True).dt.date

    fechas = sorted(data['CALENDARIO']['Fecha_dt'].unique(), reverse=True)
    f_sel = st.sidebar.selectbox("📅 Seleccionar Fecha", fechas)
    f_obj = f_sel.replace(day=1)
    
    meses_es = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 
                7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
    
    c_r = data['CALENDARIO'][data['CALENDARIO']['Fecha_dt'] == f_sel].iloc[0]
    d_t, d_h = float(c_r['Días Transcurridos']), float(c_r['Días Hábiles Mes'])
    prog_t = d_t / d_h if d_h > 0 else 0

    st.markdown(f"""<div class="portada-container">
        <div style="letter-spacing: 3px; opacity: 0.8; text-transform: uppercase;">Grupo CENOA</div>
        <div class="titulo-portada">Resumen General de Objetivos de Posventa</div>
        <div class="status-line">📍 Autociel | 📅 {meses_es[f_sel.month]} {f_sel.year} | ⏱️ Avance: {d_t:g}/{d_h:g} días ({prog_t:.1%})</div>
    </div>""", unsafe_allow_html=True)

    s_r = data['SERVICIOS'][data['SERVICIOS']['Fecha_dt'] == f_sel].iloc[0]
    r_r = data['REPUESTOS'][data['REPUESTOS']['Fecha_dt'] == f_sel].iloc[0]
    t_r = data['TALLER'][data['TALLER']['Fecha_dt'] == f_sel].iloc[0]
    cj_r = data['CyP JUJUY'][data['CyP JUJUY']['Fecha_dt'] == f_sel].iloc[0]
    cs_r = data['CyP SALTA'][data['CyP SALTA']['Fecha_dt'] == f_sel].iloc[0]

    def get_o(df_name, col):
        df = data[df_name]; f_o = df[df['Fecha_dt'] == f_obj]
        return float(f_o[col].iloc[0]) if not f_o.empty else float(df[col].max())

    tab1, tab2, tab3, tab4 = st.tabs(["🏠 General", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura"])

    with tab1:
        cols = st.columns(4)
        r_mo = s_r['MO Cliente'] + s_r['MO Garantía'] + s_r['MO Tercero']
        canales = ['Mostrador', 'Taller', 'Interna', 'Garantía', 'CyP', 'Mayorista', 'Seguros']
        r_rep = sum([r_r[f'Venta {c}'] for c in canales if f'Venta {c}' in r_r])
        metas = [("Servicios", r_mo, get_o('SERVICIOS','Obj MO Total')), ("Repuestos", r_rep, get_o('REPUESTOS','Obj Facturación Total')),
                 ("CyP Jujuy", cj_r['MO Pura']+cj_r['MO Tercero'], get_o('CyP JUJUY','Obj Facturación Total CyP Jujuy')),
                 ("CyP Salta", cs_r['MO Pura']+cs_r['MO Tercero']+cs_r.get('Fact Repuestos', 0), get_o('CyP SALTA','Obj Facturación Total CyP Salta'))]
        for i, (tit, real, obj) in enumerate(metas):
            p = calcular_proyeccion(real, d_t, d_h); alc = p/obj if obj>0 else 0
            color = "#dc3545" if alc < 0.90 else ("#ffc107" if alc < 0.95 else "#28a745")
            cols[i].markdown(f"**{tit}**")
            cols[i].markdown(f"<h1 style='margin:0; color:#00235d; font-size: 32px;'>${real:,.0f}</h1>", unsafe_allow_html=True)
            cols[i].markdown(f"<p style='color:{color}; font-weight:bold;'>Proy: {alc:.1%}</p>", unsafe_allow_html=True)
            cols[i].markdown(f'<div style="width:100%; background:#e0e0e0; height:8px; border-radius:10px;"><div style="width:{min(alc*100, 100)}%; background:{color}; height:8px; border-radius:10px;"></div></div>', unsafe_allow_html=True)

    with tab2:
        st.header("Flujo de Unidades y Performance")
        c_u1, c_u2 = st.columns(2)
        real_tus = s_r['CPUS'] + s_r['Otros Cargos']
        for i, (tit, real, obj) in enumerate([("Total Unidades Servicio (TUS)", real_tus, get_o('SERVICIOS','Obj TUS')), ("Cargos Clientes (CPUS)", s_r['CPUS'], get_o('SERVICIOS', 'Obj CPUS'))]):
            p = calcular_proyeccion(real, d_t, d_h); alc = p/obj if obj>0 else 0
            color = "#dc3545" if alc < 0.90 else ("#ffc107" if alc < 0.95 else "#28a745")
            with (c_u1 if i==0 else c_u2):
                st.markdown(f'<div style="border: 1px solid #e0e0e0; padding: 20px; border-radius: 10px; background-color: white;">'
                            f'<p style="font-weight:bold; color:#666;">{tit}</p>'
                            f'<h2>{real:,.0f} <span style="font-size:15px; color:#999;">/ Obj: {obj:,.0f}</span></h2>'
                            f'<p style="color:{color}; font-weight:bold;">↑ Proy: {p:,.0f} ({alc:.1%})</p></div>', unsafe_allow_html=True)
        st.markdown("---")
        st.header("Composición de Horas y Eficiencia")
        ht_cc, ht_cg, ht_ci = t_r['Hs Trabajadas CC'], t_r['Hs Trabajadas CG'], t_r['Hs Trabajadas CI']
        hf_cc, hf_cg, hf_ci = t_r['Hs Facturadas CC'], t_r['Hs Facturadas CG'], t_r['Hs Facturadas CI']
        g1, g2 = st.columns(2)
        with g1: st.plotly_chart(px.pie(values=[ht_cc, ht_cg, ht_ci], names=["CC","CG","CI"], hole=0.4, title="Hs Trabajadas", color_discrete_sequence=["#00235d", "#00A8E8", "#28a745"]), use_container_width=True)
        with g2: st.plotly_chart(px.pie(values=[hf_cc, hf_cg, hf_ci], names=["CC","CG","CI"], hole=0.4, title="Hs Facturadas", color_discrete_sequence=["#00235d", "#00A8E8", "#28a745"]), use_container_width=True)
        
        e1, e2, e3 = st.columns(3)
        ef_cc, ef_cg = (hf_cc/ht_cc if ht_cc>0 else 0), (hf_cg/ht_cg if ht_cg>0 else 0)
        ef_gl = (hf_cc+hf_cg+hf_ci)/(ht_cc+ht_cg+ht_ci) if (ht_cc+ht_cg+ht_ci)>0 else 0
        e1.metric("Eficiencia CC", f"{ef_cc:.1%}", delta=f"{(ef_cc-1):.1%}")
        e2.metric("Eficiencia CG", f"{ef_cg:.1%}", delta=f"{(ef_cg-1):.1%}")
        e3.metric("Eficiencia GLOBAL", f"{ef_gl:.1%}", delta=f"{(ef_gl-0.85):.1%}")
        
        k1, k2, k3 = st.columns(3)
        h_d_r, h_d_i = t_r['Hs Disponibles Real'], (8 * 6 * d_t)
        pres, ocup = (h_d_r/h_d_i if h_d_i>0 else 0), ((ht_cc+ht_cg+ht_ci)/h_d_r if h_d_r>0 else 0)
        prod = t_r.get('Productividad Taller %', 0)
        if prod > 2: prod /= 100
        k1.metric("Grado Presencia", f"{pres:.1%}", delta=f"{(pres-0.9):.1%}")
        k2.metric("Grado Ocupación", f"{ocup:.1%}", delta=f"{(ocup-0.95):.1%}")
        k3.metric("Productividad", f"{prod:.1%}", delta=f"{(prod-0.95):.1%}")

    with tab3:
        st.header("Análisis de Ventas y Stock")
        detalles = []
        for c in canales:
            if f'Venta {c}' in r_r:
                vb, d, cost = r_r[f'Venta {c}'], r_r.get(f'Descuento {c}', 0), r_r.get(f'Costo {c}', 0)
                vn = vb - d; ut = vn - cost
                detalles.append({"Canal": c, "Bruta": vb, "Desc": d, "Costo": cost, "Margen $": ut, "% Mg": (ut/vn if vn>0 else 0)})
        df_r = pd.DataFrame(detalles)
        st.dataframe(df_r.style.format({"Bruta":"${:,.0f}","Desc":"${:,.0f}","Costo":"${:,.0f}","Margen $":"${:,.0f}","% Mg":"{:.1%}"}), use_container_width=True, hide_index=True)
        
        c_tot1, c_tot2, c_tot3 = st.columns(3)
        v_bruta_t = df_r['Bruta'].sum(); v_neta_t = v_bruta_t - df_r['Desc'].sum()
        mg_pesos_t = df_r['Margen $'].sum(); mg_porc_t = (mg_pesos_t / v_neta_t) if v_neta_t > 0 else 0
        c_tot1.metric("Facturación Bruta Total", f"${v_bruta_t:,.0f}")
        c_tot2.metric("Margen Total $", f"${mg_pesos_t:,.0f}")
        c_tot3.metric("Margen Promedio %", f"{mg_porc_t:.1%}")

        st.markdown("---")
        rg1, rg2 = st.columns(2)
        with rg1:
            fig_can = px.pie(df_r, values="Bruta", names="Canal", hole=0.4, title="Participación por Canal")
            fig_can.update_traces(textinfo='percent+label', textposition='inside')
            st.plotly_chart(fig_can, use_container_width=True)
        with rg2:
            v_s = float(r_r.get('Valor Stock', 0)); f = 1 if float(r_r.get('% Stock Vivo', 0)) <= 1 else 100
            df_s = pd.DataFrame({"Estado": ["Vivo", "Obsoleto", "Muerto"], "Valor": [v_s*(r_r.get('% Stock Vivo',0)/f), v_s*(r_r.get('% Stock Obsoleto',0)/f), v_s*(r_r.get('% Stock Muerto',0)/f)]})
            fig_s = px.pie(df_s, values="Valor", names="Estado", hole=0.4, title="Conformación del Stock", color="Estado", color_discrete_map={"Vivo":"#28a745","Obsoleto":"#ffc107","Muerto":"#dc3545"})
            st.plotly_chart(fig_s, use_container_width=True)
            st.info(f"VALOR TOTAL DEL STOCK: ${v_s:,.0f}")

    with tab4:
        st.header("Productividad y Facturación CyP")
        c_p1, c_p2 = st.columns(2)
        for i, (nom, row, sh) in enumerate([('Jujuy', cj_r, 'CyP JUJUY'), ('Salta', cs_r, 'CyP SALTA')]):
            real_p, obj_p = row['Paños Propios'], get_o(sh, 'Obj Paños Propios Mensual')
            proy_p = calcular_proyeccion(real_p, d_t, d_h); alc_p = proy_p / obj_p if obj_p > 0 else 0
            color_p = "#dc3545" if alc_p < 0.90 else ("#ffc107" if alc_p < 0.95 else "#28a745")
            with (c_p1 if i == 0 else c_p2):
                st.markdown(f"""<div style="border: 1px solid #e0e0e0; padding: 20px; border-radius: 10px; background-color: white; min-height: 170px;">
                    <p style="font-weight:bold;">Sede {nom} - Paños</p>
                    <h1 style="margin: 0; font-size: 42px; color: #333;">{real_p:,.0f} <span style="font-size: 18px; color: #999;">/ Obj: {obj_p:,.0f}</span></h1>
                    <p style="color: {color_p}; font-weight: bold; font-size: 18px; margin-top: 15px; border-top: 1px solid #eee; padding-top: 10px;">↑ Proyección: {proy_p:,.0f} paños ({alc_p:.1%})</p></div>""", unsafe_allow_html=True)
        
        st.markdown("---")
        cf1, cf2 = st.columns(2)
        for i, (nom, row) in enumerate([('Jujuy', cj_r), ('Salta', cs_r)]):
            with (cf1 if i == 0 else cf2):
                f_p, f_t, f_r = row['MO Pura'], row['MO Tercero'], (row.get('Fact Repuestos', 0) if nom == 'Salta' else 0)
                st.metric(f"Facturación Total {nom}", f"${(f_p+f_t+f_r):,.0f}")
                st.plotly_chart(px.pie(values=[f_p, f_t, f_r] if f_r>0 else [f_p, f_t], names=["M.O. Pura", "M.O. Terceros", "Repuestos"] if f_r>0 else ["M.O. Pura", "M.O. Terceros"], hole=0.4, color_discrete_sequence=["#00235d", "#00A8E8", "#28a745"]), use_container_width=True)
                # Márgenes Terceros y Repuestos
                m_t, p_t = (f_t - row['Costo Tercero']), ((f_t - row['Costo Tercero'])/f_t if f_t > 0 else 0)
                st.markdown(f"<div style='background:#f1f3f6; padding:10px; border-radius:8px; border-left: 5px solid #00235d;'>Márgenes Terceros {nom}:<br>Fact: ${f_t:,.0f} | Costo: ${row['Costo Tercero']:,.0f}<br><b>Margen: ${m_t:,.0f} ({p_t:.1%})</b></div>", unsafe_allow_html=True)
                if nom == 'Salta':
                    m_r, p_r = (f_r - row['Costo Repuestos']), ((f_r - row['Costo Repuestos'])/f_r if f_r > 0 else 0)
                    st.markdown(f"<div style='background:#e8f5e9; padding:10px; border-radius:8px; border-left: 5px solid #28a745; margin-top:5px;'>Márgenes Repuestos Salta:<br>Fact: ${f_r:,.0f} | Costo: ${row['Costo Repuestos']:,.0f}<br><b>Margen: ${m_r:,.0f} ({p_r:.1%})</b></div>", unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error técnico: {e}")
