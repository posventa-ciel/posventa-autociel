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
    return (real / dias_t) * dias_h if dias_t > 0 else 0

# --- NUEVA FUNCIÓN DE CARGA AUTOMÁTICA ---
@st.cache_data(ttl=600)
def cargar_datos_desde_sheets(sheet_id):
    hojas = ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA']
    data_dict = {}
    for h in hojas:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={h.replace(' ', '%20')}"
        # Cargamos como texto para limpiar formatos de números
        df = pd.read_csv(url, dtype=str).fillna("0")
        # Convertimos comas en puntos para que Python entienda los decimales
        df = df.apply(lambda x: x.str.replace(',', '.') if x.dtype == "object" else x)
        # Convertimos a números lo que corresponda
        for col in df.columns:
            if col not in ['Fecha', 'Fecha Corte', 'Canal', 'Estado']:
                df[col] = pd.to_numeric(df[col], errors='ignore')
        data_dict[h] = df
    return data_dict

# Tu ID de Google Sheets
ID_SHEET = "1yJgaMR0nEmbKohbT_8Vj627Ma4dURwcQTQcQLPqrFwk"

try:
    # Carga automática de datos
    data = cargar_datos_desde_sheets(ID_SHEET)

    # Procesamiento de fechas (Formato Latino)
    for h in data:
        col_f = 'Fecha Corte' if 'Fecha Corte' in data[h].columns else 'Fecha'
        data[h]['Fecha_dt'] = pd.to_datetime(data[h][col_f], dayfirst=True).dt.date

    fechas = sorted(data['CALENDARIO']['Fecha_dt'].unique(), reverse=True)
    f_sel = st.sidebar.selectbox("📅 Seleccionar Fecha", fechas)
    
    meses_es = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 
                7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
    
    # Extraer fila de calendario
    c_r = data['CALENDARIO'][data['CALENDARIO']['Fecha_dt'] == f_sel].iloc[0]
    d_t, d_h = float(c_r['Días Transcurridos']), float(c_r['Días Hábiles Mes'])
    prog_t = d_t / d_h if d_h > 0 else 0

    # --- PORTADA ---
    st.markdown(f"""
        <div class="portada-container">
            <div style="letter-spacing: 3px; opacity: 0.8; text-transform: uppercase;">Grupo CENOA</div>
            <div class="titulo-portada">Resumen General de Objetivos de Posventa</div>
            <div class="status-line">
                📍 Autociel | 📅 {meses_es[f_sel.month]} {f_sel.year} | ⏱️ Avance: {d_t}/{d_h} días ({prog_t:.1%})
            </div>
        </div>
    """, unsafe_allow_html=True)

    f_obj = f_sel.replace(day=1)
    s_r = data['SERVICIOS'][data['SERVICIOS']['Fecha_dt'] == f_sel].iloc[0]
    r_r = data['REPUESTOS'][data['REPUESTOS']['Fecha_dt'] == f_sel].iloc[0]
    t_r = data['TALLER'][data['TALLER']['Fecha_dt'] == f_sel].iloc[0]
    cj_r = data['CyP JUJUY'][data['CyP JUJUY']['Fecha_dt'] == f_sel].iloc[0]
    cs_r = data['CyP SALTA'][data['CyP SALTA']['Fecha_dt'] == f_sel].iloc[0]

    def get_o(df_name, col):
        df = data[df_name]
        f_o = df[df['Fecha_dt'] == f_obj]
        return float(f_o[col].iloc[0]) if not f_o.empty else float(df[col].max())

    tab1, tab2, tab3, tab4 = st.tabs(["🏠 General", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura"])

    with tab1:
        cols = st.columns(4)
        r_mo = s_r['MO Cliente'] + s_r['MO Garantía'] + s_r['MO Tercero']
        canales_rep = ['Mostrador', 'Taller', 'Interna', 'Garantía', 'CyP', 'Mayorista', 'Seguros']
        r_rep = sum([float(r_r[f'Venta {c}']) for c in canales_rep if f'Venta {c}' in r_r])
        r_cj = cj_r['MO Pura'] + cj_r['MO Tercero']
        r_cs = cs_r['MO Pura'] + cs_r['MO Tercero'] + cs_r.get('Fact Repuestos', 0)
        
        metas = [
            ("Servicios", r_mo, get_o('SERVICIOS', 'Obj MO Total')), 
            ("Repuestos", r_rep, get_o('REPUESTOS', 'Obj Facturación Total')),
            ("CyP Jujuy", r_cj, get_o('CyP JUJUY', 'Obj Facturación Total CyP Jujuy')), 
            ("CyP Salta", r_cs, get_o('CyP SALTA', 'Obj Facturación Total CyP Salta'))
        ]

        for i, (tit, real, obj) in enumerate(metas):
            p_pesos = calcular_proyeccion(real, d_t, d_h)
            alc = p_pesos / obj if obj > 0 else 0
            color = "#dc3545" if alc < 0.90 else ("#ffc107" if alc < 0.95 else "#28a745")
            with cols[i]:
                st.markdown(f"**{tit}**")
                st.markdown(f"<h1 style='margin:0; color:#00235d; font-size: 32px;'>${real:,.0f}</h1>", unsafe_allow_html=True)
                st.markdown(f"<p style='margin:0; font-size: 18px; color: #444; font-weight: 700;'>OBJETIVO: ${obj:,.0f}</p>", unsafe_allow_html=True)
                st.markdown(f"""<div style='margin-top:10px;'><p style='color:{color}; font-size:18px; margin:0;'><b>Proy: {alc:.1%}</b></p><p style='color:#666; font-size:14px; margin:0;'>Est. al cierre: <b>${p_pesos:,.0f}</b></p></div>""", unsafe_allow_html=True)
                st.markdown(f"""<div style="width:100%; background:#e0e0e0; height:8px; border-radius:10px; margin-top:5px;"><div style="width:{min(alc*100, 100)}%; background:{color}; height:8px; border-radius:10px;"></div></div>""", unsafe_allow_html=True)

    with tab2:
        st.header("Flujo de Unidades y Performance")
        c_u1, c_u2 = st.columns(2)
        real_tus = s_r['CPUS'] + s_r['Otros Cargos']
        ind_taller = [("Total Unidades Servicio (TUS)", real_tus, get_o('SERVICIOS', 'Obj TUS')), 
                      ("Cargos Clientes (CPUS)", s_r['CPUS'], get_o('SERVICIOS', 'Obj CPUS'))]
        for i, (tit, real, obj) in enumerate(ind_taller):
            p_cant = calcular_proyeccion(real, d_t, d_h)
            alc = p_cant / obj if obj > 0 else 0
            color_kpi = "#dc3545" if alc < 0.90 else ("#ffc107" if alc < 0.95 else "#28a745")
            with (c_u1 if i == 0 else c_u2):
                st.markdown(f"""<div style="border: 1px solid #e0e0e0; padding: 20px; border-radius: 10px; background-color: white; min-height: 180px;">
                                <p style="font-size: 14px; color: #666; margin-bottom: 2px; font-weight: bold;">{tit}</p>
                                <h1 style="margin: 0; font-size: 42px; color: #333;">{real:,.0f} <span style="font-size: 18px; color: #999;">/ Obj: {obj:,.0f}</span></h1>
                                <p style="color: {color_kpi}; font-weight: bold; font-size: 18px; margin-top: 15px; border-top: 1px solid #eee; padding-top: 10px;">↑ Proyección: {p_cant:,.0f} unidades ({alc:.1%})</p></div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.header("Composición de Horas y Eficiencia")
        ht_cc, ht_cg, ht_ci = t_r['Hs Trabajadas CC'], t_r['Hs Trabajadas CG'], t_r['Hs Trabajadas CI']
        hf_cc, hf_cg, hf_ci = t_r['Hs Facturadas CC'], t_r['Hs Facturadas CG'], t_r['Hs Facturadas CI']
        c_h1, c_h2 = st.columns(2)
        with c_h1: st.plotly_chart(px.pie(values=[ht_cc, ht_cg, ht_ci], names=["CC", "CG", "CI"], hole=0.4, title="Horas Trabajadas"), use_container_width=True)
        with c_h2: st.plotly_chart(px.pie(values=[hf_cc, hf_cg, hf_ci], names=["CC", "CG", "CI"], hole=0.4, title="Horas Facturadas"), use_container_width=True)

        e1, e2, e3 = st.columns(3)
        ef_gl = (hf_cc+hf_cg+hf_ci)/(ht_cc+ht_cg+ht_ci) if (ht_cc+ht_cg+ht_ci) > 0 else 0
        e1.metric("Eficiencia CC", f"{(hf_cc/ht_cc if ht_cc>0 else 0):.1%}")
        e2.metric("Eficiencia CG", f"{(hf_cg/ht_cg if ht_cg>0 else 0):.1%}")
        e3.metric("Eficiencia GLOBAL", f"{ef_gl:.1%}")

        k1, k2, k3 = st.columns(3)
        h_d_r = t_r['Hs Disponibles Real']
        h_d_i = 8 * 6 * d_t 
        pres = h_d_r / h_d_i if h_d_i > 0 else 0
        ocup = (ht_cc + ht_cg + ht_ci) / h_d_r if h_d_r > 0 else 0
        k1.metric("Grado Presencia", f"{pres:.1%}")
        k2.metric("Grado Ocupación", f"{ocup:.1%}")
        k3.metric("Productividad", f"{t_r.get('Productividad Taller %', 0):.1%}")

    with tab3:
        st.header("Análisis de Ventas y Stock")
        detalles = []
        for c in canales_rep:
            if f'Venta {c}' in r_r:
                vb = r_r[f'Venta {c}']; d = r_r.get(f'Descuento {c}', 0); cost = r_r.get(f'Costo {c}', 0)
                vn = vb - d; ut = vn - cost
                detalles.append({"Canal": c, "Bruta": vb, "Desc": d, "Costo": cost, "Margen $": ut, "% Mg": (ut/vn if vn>0 else 0)})
        df_r = pd.DataFrame(detalles)
        st.dataframe(df_r.style.format({"Bruta": "${:,.0f}", "Desc": "${:,.0f}", "Costo": "${:,.0f}", "Margen $": "${:,.0f}", "% Mg": "{:.1%}"}), use_container_width=True, hide_index=True)

        v_stock_total = float(r_r.get('Valor Stock', 0))
        st.info(f"VALOR TOTAL DEL STOCK: ${v_stock_total:,.0f}")

    with tab4:
        st.header("Productividad y Facturación CyP")
        sedes_config = [('Jujuy', cj_r, 'Obj Paños Propios Mensual', 'CyP JUJUY'), ('Salta', cs_r, 'Obj Paños Propios Mensual', 'CyP SALTA')]
        c_p1, c_p2 = st.columns(2)
        for i, (nom, row, o_col, sh) in enumerate(sedes_config):
            real_p, obj_p = row['Paños Propios'], get_o(sh, o_col)
            proy_p = calcular_proyeccion(real_p, d_t, d_h); alc_p = proy_p / obj_p if obj_p > 0 else 0
            with (c_p1 if i == 0 else c_p2):
                st.markdown(f"""<div style="border: 1px solid #e0e0e0; padding: 20px; border-radius: 10px; background-color: white; min-height: 170px;">
                                <p style="font-weight:bold;">Sede {nom} - Paños</p>
                                <h1 style="margin: 0; font-size: 42px; color: #333;">{real_p:,.0f} <span style="font-size: 18px; color: #999;">/ Obj: {obj_p:,.0f}</span></h1>
                                <p style="font-weight: bold; font-size: 18px; margin-top: 15px; border-top: 1px solid #eee; padding-top: 10px;">↑ Proyección: {proy_p:,.0f} paños ({alc_p:.1%})</p></div>""", unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error cargando los datos: {e}")
