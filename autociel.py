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

    # --- FILTROS ---
    años = sorted(data['CALENDARIO']['Fecha_dt'].dt.year.unique(), reverse=True)
    año_sel = st.sidebar.selectbox("📅 Seleccionar Año", años)
    meses_nombres = {1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic"}
    meses_disp = sorted(data['CALENDARIO'][data['CALENDARIO']['Fecha_dt'].dt.year == año_sel]['Fecha_dt'].dt.month.unique(), reverse=True)
    mes_sel = st.sidebar.selectbox("📅 Seleccionar Mes", meses_disp, format_func=lambda x: meses_nombres[x])

    def get_mes_data(df):
        res = df[(df['Fecha_dt'].dt.year == año_sel) & (df['Fecha_dt'].dt.month == mes_sel)]
        return res.sort_values('Fecha_dt').iloc[-1] if not res.empty else df.iloc[-1]

    c_r = get_mes_data(data['CALENDARIO'])
    s_r = get_mes_data(data['SERVICIOS'])
    r_r = get_mes_data(data['REPUESTOS'])
    t_r = get_mes_data(data['TALLER'])
    cj_r = get_mes_data(data['CyP JUJUY'])
    cs_r = get_mes_data(data['CyP SALTA'])

    d_t, d_h = float(c_r.get('Días Transcurridos', 1)), float(c_r.get('Días Hábiles Mes', 1))

    st.markdown(f"""<div class="portada-container"><div class="titulo-portada">Resumen General de Objetivos de Posventa</div>
    <div class="status-line">📍 Autociel | 📅 {meses_nombres[mes_sel]} {año_sel} | ⏱️ Avance: {d_t:g}/{d_h:g} días ({(d_t/d_h):.1%})</div></div>""", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🏠 General", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura"])

    with tab1:
        cols = st.columns(4)
        r_mo = s_r['MO Cliente'] + s_r['MO Garantía'] + s_r['MO Tercero']
        canales = ['Mostrador', 'Taller', 'Interna', 'Garantía', 'CyP', 'Mayorista', 'Seguros']
        r_rep = sum([r_r[f'Venta {c}'] for c in canales if f'Venta {c}' in r_r])
        metas = [("Servicios", r_mo, s_r['Obj MO Total']), ("Repuestos", r_rep, r_r['Obj Facturación Total']),
                 ("CyP Jujuy", cj_r['MO Pura']+cj_r['MO Tercero'], cj_r['Obj Facturación Total CyP Jujuy']),
                 ("CyP Salta", cs_r['MO Pura']+cs_r['MO Tercero']+cs_r.get('Fact Repuestos', 0), cs_r['Obj Facturación Total CyP Salta'])]
        for i, (tit, real, obj) in enumerate(metas):
            p = (real/d_t)*d_h; alc = p/obj if obj>0 else 0
            with cols[i]:
                st.markdown(f"**{tit}**")
                st.markdown(f"<h1 style='margin:0; color:#00235d;'>${real:,.0f}</h1>", unsafe_allow_html=True)
                st.markdown(f"<p style='margin:0; font-weight:bold; color:#666;'>Objetivo: ${obj:,.0f}</p>", unsafe_allow_html=True)
                st.markdown(f"<p style='color:{('#28a745' if alc>0.95 else '#dc3545')}; margin:0;'><b>Proy: {alc:.1%}</b></p>", unsafe_allow_html=True)

    with tab2:
        st.header("Ticket Promedio y Performance")
        cpus = s_r['CPUS'] if s_r['CPUS'] > 0 else 1
        tp_hs = (t_r['Hs Facturadas CC'] + t_r['Hs Facturadas CG']) / cpus
        tp_mo = (s_r['MO Cliente'] + s_r['MO Garantía']) / cpus
        m1, m2 = st.columns(2)
        m1.metric("Ticket Promedio M.O. (Hs)", f"{tp_hs:.2f} hs/OT")
        m2.metric("Ticket Promedio M.O. ($)", f"${tp_mo:,.0f}/OT")

        st.markdown("---")
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

        st.markdown("---")
        hist_serv = data['SERVICIOS'][data['SERVICIOS']['Fecha_dt'].dt.year == año_sel].copy()
        st.plotly_chart(px.line(hist_serv, x='Fecha_dt', y='CPUS', title="Histórico CPUS", markers=True), use_container_width=True)

    with tab3:
        st.header("Repuestos - Márgenes y Composición")
        tp_rep = (r_r.get('Venta Taller',0) + r_r.get('Venta Garantía',0) + r_r.get('Venta CyP',0)) / cpus
        st.metric("Ticket Promedio Repuestos ($)", f"${tp_rep:,.0f}/OT")

        detalles = []
        for c in canales:
            if f'Venta {c}' in r_r:
                vb, d, cost = r_r[f'Venta {c}'], r_r.get(f'Descuento {c}', 0), r_r.get(f'Costo {c}', 0)
                vn = vb - d; ut = vn - cost
                detalles.append({"Canal": c, "Bruta": vb, "Desc": d, "Costo": cost, "Margen $": ut, "% Mg": (ut/vn if vn>0 else 0)})
        df_r = pd.DataFrame(detalles)
        st.dataframe(df_r.style.format({"Bruta":"${:,.0f}","Desc":"${:,.0f}","Costo":"${:,.0f}","Margen $":"${:,.0f}","% Mg":"{:.1%}"}), use_container_width=True, hide_index=True)
        
        c_tot1, c_tot2, c_tot3 = st.columns(3)
        v_bruta_t = df_r['Bruta'].sum(); mg_pesos_t = df_r['Margen $'].sum(); mg_porc_t = mg_pesos_t / (v_bruta_t - df_r['Desc'].sum()) if (v_bruta_t - df_r['Desc'].sum()) > 0 else 0
        c_tot1.metric("Facturación Bruta Total", f"${v_bruta_t:,.0f}"); c_tot2.metric("Margen Total $", f"${mg_pesos_t:,.0f}"); c_tot3.metric("Margen Promedio %", f"{mg_porc_t:.1%}")

        rg1, rg2 = st.columns(2)
        with rg1: st.plotly_chart(px.pie(df_r, values="Bruta", names="Canal", hole=0.4, title="Participación por Canal"), use_container_width=True)
        with rg2:
            v_s = float(r_r.get('Valor Stock', 0)); f = 1 if float(r_r.get('% Stock Vivo', 0)) <= 1 else 100
            df_s = pd.DataFrame({"Estado": ["Vivo", "Obsoleto", "Muerto"], "Valor": [v_s*(r_r.get('% Stock Vivo',0)/f), v_s*(r_r.get('% Stock Obsoleto',0)/f), v_s*(r_r.get('% Stock Muerto',0)/f)]})
            st.plotly_chart(px.pie(df_s, values="Valor", names="Estado", hole=0.4, title="Conformación Stock", color="Estado", color_discrete_map={"Vivo":"#28a745","Obsoleto":"#ffc107","Muerto":"#dc3545"}), use_container_width=True)

    with tab4:
        st.header("Chapa y Pintura - Sedes")
        cp1, cp2 = st.columns(2)
        for i, (nom, row, sh) in enumerate([('Jujuy', cj_r, 'CyP JUJUY'), ('Salta', cs_r, 'CyP SALTA')]):
            r_p, o_p = row['Paños Propios'], row.get('Obj Paños Propios Mensual', 1)
            p_p = (r_p/d_t)*d_h; alc_p = p_p/o_p if o_p>0 else 0
            color_p = "#dc3545" if alc_p < 0.90 else ("#ffc107" if alc_p < 0.95 else "#28a745")
            with (cp1 if i==0 else cp2):
                st.markdown(f'<div style="border: 1px solid #e0e0e0; padding: 20px; border-radius: 10px; background-color: white; min-height: 170px;"><p style="font-weight:bold;">Sede {nom} - Paños</p><h1 style="margin: 0; font-size: 42px; color: #333;">{r_p:,.0f} <span style="font-size: 18px; color: #999;">/ Obj: {o_p:,.0f}</span></h1><p style="color: {color_p}; font-weight: bold; font-size: 18px; margin-top: 15px; border-top: 1px solid #eee; padding-top: 10px;">↑ Proyección: {p_p:,.0f} ({alc_p:.1%})</p></div>', unsafe_allow_html=True)

        st.markdown("---")
        cf1, cf2 = st.columns(2)
        for i, (nom, row) in enumerate([('Jujuy', cj_r), ('Salta', cs_r)]):
            with (cf1 if i == 0 else cf2):
                f_p, f_t, f_r = row['MO Pura'], row['MO Tercero'], (row.get('Fact Repuestos', 0) if nom == 'Salta' else 0)
                st.metric(f"Facturación Total {nom}", f"${(f_p+f_t+f_r):,.0f}")
                st.plotly_chart(px.pie(values=[f_p, f_t, f_r] if f_r>0 else [f_p, f_t], names=["M.O. Pura", "M.O. Terceros", "Repuestos"] if f_r>0 else ["M.O. Pura", "M.O. Terceros"], hole=0.4, color_discrete_sequence=["#00235d", "#00A8E8", "#28a745"]), use_container_width=True)
                m_t = (f_t - row['Costo Tercero']); p_t = (m_t/f_t if f_t > 0 else 0)
                st.markdown(f"<div style='background:#f1f3f6; padding:10px; border-radius:8px; border-left: 5px solid #00235d; margin-top:10px;'>Márgenes Terceros {nom}:<br>Fact: ${f_t:,.0f} | Costo: ${row['Costo Tercero']:,.0f}<br><b>Margen: ${m_t:,.0f} ({p_t:.1%})</b></div>", unsafe_allow_html=True)
                if nom == 'Salta':
                    m_r = (f_r - row['Costo Repuestos']); p_r = (m_r/f_r if f_r > 0 else 0)
                    st.markdown(f"<div style='background:#e8f5e9; padding:10px; border-radius:8px; border-left: 5px solid #28a745; margin-top:5px;'>Márgenes Repuestos Salta:<br>Fact: ${f_r:,.0f} | Costo: ${row['Costo Repuestos']:,.0f}<br><b>Margen: ${m_r:,.0f} ({p_r:.1%})</b></div>", unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error técnico: {e}")
