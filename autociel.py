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

# --- CARGA DESDE GOOGLE SHEETS ---
@st.cache_data(ttl=60)
def cargar_datos(sheet_id):
    hojas = ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA']
    data_dict = {}
    for h in hojas:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={h.replace(' ', '%20')}"
        df = pd.read_csv(url, dtype=str).fillna("0")
        
        # Limpieza profunda de cada celda
        for col in df.columns:
            if col not in ['Fecha', 'Fecha Corte', 'Canal', 'Estado']:
                # Quitamos símbolos, espacios y cambiamos comas por puntos
                df[col] = df[col].astype(str).str.replace('%', '', regex=False)
                df[col] = df[col].str.replace(',', '.', regex=False)
                df[col] = df[col].str.strip()
                # Convertimos a número real
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        data_dict[h] = df
    return data_dict

ID_SHEET = "1yJgaMR0nEmbKohbT_8Vj627Ma4dURwcQTQcQLPqrFwk"

try:
    data = cargar_datos(ID_SHEET)

    for h in data:
        col_f = 'Fecha Corte' if 'Fecha Corte' in data[h].columns else 'Fecha'
        data[h]['Fecha_dt'] = pd.to_datetime(data[h][col_f], dayfirst=True).dt.date

    fechas = sorted(data['CALENDARIO']['Fecha_dt'].unique(), reverse=True)
    f_sel = st.sidebar.selectbox("📅 Seleccionar Fecha", fechas)
    
    meses_es = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 
                7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
    
    # Aseguramos que d_t y d_h sean números
    c_r = data['CALENDARIO'][data['CALENDARIO']['Fecha_dt'] == f_sel].iloc[0]
    d_t = float(c_r['Días Transcurridos'])
    d_h = float(c_r['Días Hábiles Mes'])
    prog_t = float(d_t / d_h) if d_h > 0 else 0.0

    # --- PORTADA ---
    st.markdown(f"""
        <div class="portada-container">
            <div style="letter-spacing: 3px; opacity: 0.8; text-transform: uppercase;">Grupo CENOA</div>
            <div class="titulo-portada">Resumen General de Objetivos de Posventa</div>
            <div class="status-line">
                📍 Autociel | 📅 {meses_es[f_sel.month]} {f_sel.year} | ⏱️ Avance: {d_t:g}/{d_h:g} días ({prog_t:.1%})
            </div>
        </div>
    """, unsafe_allow_html=True)

    f_obj = f_sel.replace(day=1)
    
    # Cargar filas y asegurar conversión a float de toda la fila
    s_r = data['SERVICIOS'][data['SERVICIOS']['Fecha_dt'] == f_sel].iloc[0]
    r_r = data['REPUESTOS'][data['REPUESTOS']['Fecha_dt'] == f_sel].iloc[0]
    t_r = data['TALLER'][data['TALLER']['Fecha_dt'] == f_sel].iloc[0]
    cj_r = data['CyP JUJUY'][data['CyP JUJUY']['Fecha_dt'] == f_sel].iloc[0]
    cs_r = data['CyP SALTA'][data['CyP SALTA']['Fecha_dt'] == f_sel].iloc[0]

    def get_o(df_name, col):
        df = data[df_name]
        f_o = df[df['Fecha_dt'] == f_obj]
        val = f_o[col].iloc[0] if not f_o.empty else df[col].max()
        return float(val)

    tab1, tab2, tab3, tab4 = st.tabs(["🏠 General", "🛠️ Taller y Eficiencia", "📦 Repuestos", "🎨 Chapa y Pintura"])

    with tab1:
        cols = st.columns(4)
        r_mo = float(s_r['MO Cliente']) + float(s_r['MO Garantía']) + float(s_r['MO Tercero'])
        canales_rep = ['Mostrador', 'Taller', 'Interna', 'Garantía', 'CyP', 'Mayorista', 'Seguros']
        r_rep = sum([float(r_r[f'Venta {c}']) for c in canales_rep if f'Venta {c}' in r_r])
        r_cj = float(cj_r['MO Pura']) + float(cj_r['MO Tercero'])
        r_cs = float(cs_r['MO Pura']) + float(cs_r['MO Tercero']) + float(cs_r.get('Fact Repuestos', 0))
        
        metas = [
            ("M.O. Servicios", r_mo, get_o('SERVICIOS', 'Obj MO Total')), 
            ("Venta Repuestos", r_rep, get_o('REPUESTOS', 'Obj Facturación Total')),
            ("Facturación CyP Jujuy", r_cj, get_o('CyP JUJUY', 'Obj Facturación Total CyP Jujuy')), 
            ("Facturación CyP Salta", r_cs, get_o('CyP SALTA', 'Obj Facturación Total CyP Salta'))
        ]

        for i, (tit, real, obj) in enumerate(metas):
            p_pesos = (real / d_t) * d_h if d_t > 0 else 0
            alc = p_pesos / obj if obj > 0 else 0
            color = "#dc3545" if alc < 0.90 else ("#ffc107" if alc < 0.95 else "#28a745")
            with cols[i]:
                st.markdown(f"**{tit}**")
                st.markdown(f"<h1 style='margin:0; color:#00235d; font-size: 32px;'>${real:,.0f}</h1>", unsafe_allow_html=True)
                st.markdown(f"<p style='margin:0; font-size: 14px; color: #444; font-weight: 700;'>OBJ: ${obj:,.0f}</p>", unsafe_allow_html=True)
                st.markdown(f"<div style='margin-top:10px;'><p style='color:{color}; font-size:18px; margin:0;'><b>Proy: {alc:.1%}</b></p></div>", unsafe_allow_html=True)
                st.markdown(f'<div style="width:100%; background:#e0e0e0; height:8px; border-radius:10px; margin-top:5px;"><div style="width:{min(alc*100, 100)}%; background:{color}; height:8px; border-radius:10px;"></div></div>', unsafe_allow_html=True)

    with tab2:
        st.header("Análisis de Horas y Eficiencia")
        e1, e2, e3 = st.columns(3)
        ht_tot = float(t_r['Hs Trabajadas CC']) + float(t_r['Hs Trabajadas CG']) + float(t_r['Hs Trabajadas CI'])
        hf_tot = float(t_r['Hs Facturadas CC']) + float(t_r['Hs Facturadas CG']) + float(t_r['Hs Facturadas CI'])
        ef_gl = hf_tot / ht_tot if ht_tot > 0 else 0
        
        # Forzar productividad como porcentaje (si en el sheet está como 95, lo llevamos a 0.95)
        prod_val = float(t_r.get('Productividad Taller %', 0))
        if prod_val > 2: prod_val = prod_val / 100

        e1.metric("Eficiencia Global", f"{ef_gl:.1%}")
        e2.metric("Ocupación", f"{(ht_tot / float(t_r['Hs Disponibles Real']) if float(t_r['Hs Disponibles Real']) > 0 else 0):.1%}")
        e3.metric("Productividad", f"{prod_val:.1%}")

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            fig_ht = px.pie(values=[float(t_r['Hs Trabajadas CC']), float(t_r['Hs Trabajadas CG']), float(t_r['Hs Trabajadas CI'])], 
                           names=["M.O. Cliente", "Garantía", "Interna"], hole=0.4, title="Horas Trabajadas",
                           color_discrete_sequence=["#00235d", "#00A8E8", "#28a745"])
            fig_ht.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_ht, use_container_width=True)
        with c2:
            fig_hf = px.pie(values=[float(t_r['Hs Facturadas CC']), float(t_r['Hs Facturadas CG']), float(t_r['Hs Facturadas CI'])], 
                           names=["M.O. Cliente", "Garantía", "Interna"], hole=0.4, title="Horas Facturadas",
                           color_discrete_sequence=["#00235d", "#00A8E8", "#28a745"])
            fig_hf.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_hf, use_container_width=True)

    with tab3:
        st.header("Márgenes de Repuestos por Canal")
        detalles = []
        for c in canales_rep:
            if f'Venta {c}' in r_r:
                vb = float(r_r[f'Venta {c}'])
                vn = vb - float(r_r.get(f'Descuento {c}', 0))
                mg_p = vn - float(r_r.get(f'Costo {c}', 0))
                detalles.append({"Canal": c, "Venta Bruta": vb, "Margen $": mg_p, "% Mg": (mg_p/vn if vn>0 else 0)})
        
        df_rep = pd.DataFrame(detalles)
        st.dataframe(df_rep.style.format({"Venta Bruta": "${:,.0f}", "Margen $": "${:,.0f}", "% Mg": "{:.1%}"}), use_container_width=True, hide_index=True)
        st.info(f"VALOR TOTAL DEL STOCK: ${float(r_r.get('Valor Stock', 0)):,.0f}")

    with tab4:
        st.header("Chapa y Pintura")
        cp_j, cp_s = st.columns(2)
        sedes = [('Jujuy', cj_r, cp_j), ('Salta', cs_r, cp_s)]
        for nom, row, col_web in sedes:
            with col_web:
                st.subheader(f"Sede {nom}")
                st.metric("Paños Propios", f"{int(float(row['Paños Propios']))}")
                fig_cyp = px.pie(values=[float(row['MO Pura']), float(row['MO Tercero'])], 
                               names=["M.O. Pura", "Terceros"], hole=0.4,
                               color_discrete_sequence=["#00235d", "#00A8E8"])
                fig_cyp.update_traces(textinfo='percent+label')
                st.plotly_chart(fig_cyp, use_container_width=True)

except Exception as e:
    st.error(f"Error cargando los datos del Sheet: {e}")
