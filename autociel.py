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

    st.markdown(f"""
        <div class="portada-container">
            <div style="letter-spacing: 3px; opacity: 0.8; text-transform: uppercase;">Grupo CENOA</div>
            <div class="titulo-portada">Resumen General de Objetivos de Posventa</div>
            <div class="status-line">📍 Autociel | 📅 {meses_es[f_sel.month]} {f_sel.year} | ⏱️ Avance: {d_t:g}/{d_h:g} días ({prog_t:.1%})</div>
        </div>
    """, unsafe_allow_html=True)

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
        st.header("Eficiencia de Taller")
        g1, g2 = st.columns(2)
        with g1: st.plotly_chart(px.pie(values=[t_r['Hs Trabajadas CC'], t_r['Hs Trabajadas CG'], t_r['Hs Trabajadas CI']], names=["CC","CG","CI"], hole=0.4, title="Hs Trabajadas", color_discrete_sequence=["#00235d", "#00A8E8", "#28a745"]), use_container_width=True)
        with g2: st.plotly_chart(px.pie(values=[t_r['Hs Facturadas CC'], t_r['Hs Facturadas CG'], t_r['Hs Facturadas CI']], names=["CC","CG","CI"], hole=0.4, title="Hs Facturadas", color_discrete_sequence=["#00235d", "#00A8E8", "#28a745"]), use_container_width=True)
        e1, e2, e3 = st.columns(3)
        ht = t_r['Hs Trabajadas CC']+t_r['Hs Trabajadas CG']+t_r['Hs Trabajadas CI']
        hf = t_r['Hs Facturadas CC']+t_r['Hs Facturadas CG']+t_r['Hs Facturadas CI']
        e1.metric("Eficiencia Global", f"{(hf/ht if ht>0 else 0):.1%}")
        e2.metric("Ocupación", f"{(ht/t_r['Hs Disponibles Real'] if t_r['Hs Disponibles Real']>0 else 0):.1%}")
        e3.metric("Productividad", f"{(t_r.get('Productividad Taller %', 0)/100 if t_r.get('Productividad Taller %',0)>1 else t_r.get('Productividad Taller %',0)):.1%}")

    with tab3:
        st.header("Análisis de Repuestos")
        detalles = []
        for c in canales:
            if f'Venta {c}' in r_r:
                vb, d, cost = r_r[f'Venta {c}'], r_r.get(f'Descuento {c}', 0), r_r.get(f'Costo {c}', 0)
                vn = vb - d; ut = vn - cost
                detalles.append({"Canal": c, "Bruta": vb, "Desc": d, "Costo": cost, "Margen $": ut, "% Mg": (ut/vn if vn>0 else 0)})
        df_r = pd.DataFrame(detalles)
        st.dataframe(df_r.style.format({"Bruta":"${:,.0f}","Desc":"${:,.0f}","Costo":"${:,.0f}","Margen $":"${:,.0f}","% Mg":"{:.1%}"}), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        rg1, rg2 = st.columns(2)
        with rg1:
            st.subheader("Participación por Canal")
            fig_can = px.pie(df_r, values="Bruta", names="Canal", hole=0.4, color_discrete_sequence=px.colors.qualitative.Prism)
            fig_can.update_traces(textinfo='percent+label', textposition='inside')
            st.plotly_chart(fig_can, use_container_width=True)
        with rg2:
            st.subheader("Conformación del Stock")
            v_s = float(r_r.get('Valor Stock', 0))
            p_v, p_o, p_m = float(r_r.get('% Stock Vivo', 0)), float(r_r.get('% Stock Obsoleto', 0)), float(r_r.get('% Stock Muerto', 0))
            f = 1 if p_v <= 1 else 100
            df_s = pd.DataFrame({"Estado": ["Vivo", "Obsoleto", "Muerto"], "Valor": [v_s*(p_v/f), v_s*(p_o/f), v_s*(p_m/f)]})
            fig_s = px.pie(df_s, values="Valor", names="Estado", hole=0.4, color="Estado", color_discrete_map={"Vivo":"#28a745","Obsoleto":"#ffc107","Muerto":"#dc3545"})
            fig_s.update_traces(textinfo='percent+label', textposition='inside')
            st.plotly_chart(fig_s, use_container_width=True)
            st.info(f"VALOR TOTAL DEL STOCK: ${v_s:,.0f}")

    with tab4:
        st.header("Chapa y Pintura")
        cyp_j, cyp_s = st.columns(2)
        for i, (nom, row, sh) in enumerate([('Jujuy', cj_r, 'CyP JUJUY'), ('Salta', cs_r, 'CyP SALTA')]):
            with (cyp_j if i==0 else cyp_s):
                st.subheader(f"Sede {nom}")
                st.metric("Paños Propios", f"{row['Paños Propios']:,.0f}")
                st.plotly_chart(px.pie(values=[row['MO Pura'], row['MO Tercero']], names=["MO Pura", "Terceros"], hole=0.4, title=f"Facturación {nom}", color_discrete_sequence=["#00235d", "#00A8E8"]), use_container_width=True)

except Exception as e:
    st.error(f"Error técnico: {e}")
