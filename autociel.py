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

# --- CARGA DESDE GOOGLE SHEETS (SIN CACHÉ PARA FORZAR ACTUALIZACIÓN) ---
def cargar_datos(sheet_id):
    hojas = ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA']
    data_dict = {}
    for h in hojas:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={h.replace(' ', '%20')}"
        # Usamos decimal=',' porque tu Sheet usa comas
        df = pd.read_csv(url, decimal=',').fillna(0)
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
        r_mo = float(s_r['MO Cliente']) + float(s_r['MO Garantía']) + float(s_r['MO Tercero'])
        canales_rep = ['Mostrador', 'Taller', 'Interna', 'Garantía', 'CyP', 'Mayorista', 'Seguros']
        r_rep = sum([float(r_r[f'Venta {c}']) for c in canales_rep if f'Venta {c}' in r_r])
        r_cj = float(cj_r['MO Pura']) + float(cj_r['MO Tercero'])
        r_cs = float(cs_r['MO Pura']) + float(cs_r['MO Tercero']) + float(cs_r.get('Fact Repuestos', 0))
        
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
                st.markdown(f"<div style='margin-top:10px;'><p style='color:{color}; font-size:18px; margin:0;'><b>Proy: {alc:.1%}</b></p></div>", unsafe_allow_html=True)
                st.markdown(f'<div style="width:100%; background:#e0e0e0; height:8px; border-radius:10px;"><div style="width:{min(alc*100, 100)}%; background:{color}; height:8px; border-radius:10px;"></div></div>', unsafe_allow_html=True)

    with tab2:
        st.header("Flujo de Unidades y Performance")
        c_u1, c_u2 = st.columns(2)
        real_tus = float(s_r['CPUS']) + float(s_r['Otros Cargos'])
        ind_taller = [("Total Unidades Servicio (TUS)", real_tus, get_o('SERVICIOS', 'Obj TUS')), 
                      ("Cargos Clientes (CPUS)", float(s_r['CPUS']), get_o('SERVICIOS', 'Obj CPUS'))]
        for i, (tit, real, obj) in enumerate(ind_taller):
            p_cant = calcular_proyeccion(real, d_t, d_h)
            alc = p_cant / obj if obj > 0 else 0
            color_kpi = "#dc3545" if alc < 0.90 else ("#ffc107" if alc < 0.95 else "#28a745")
            with (c_u1 if i == 0 else c_u2):
                st.markdown(f"""<div style="border: 1px solid #e0e0e0; padding: 20px; border-radius: 10px; background-color: white; min-height: 180px;">
                                <p style="font-size: 14px; color: #666; margin-bottom: 2px; font-weight: bold;">{tit}</p>
                                <h1 style="margin: 0; font-size: 42px; color: #333;">{real:,.0f} <span style="font-size: 18px; color: #999;">/ Obj: {obj:,.0f}</span></h1>
                                <p style="color: {color_kpi}; font-weight: bold; font-size: 18px; margin-top: 15px; border-top: 1px solid #eee; padding-top: 10px;">↑ Proyección: {p_cant:,.0f} ({alc:.1%})</p></div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.header("Composición de Horas")
        ht_cc, ht_cg, ht_ci = float(t_r['Hs Trabajadas CC']), float(t_r['Hs Trabajadas CG']), float(t_r['Hs Trabajadas CI'])
        hf_cc, hf_cg, hf_ci = float(t_r['Hs Facturadas CC']), float(t_r['Hs Facturadas CG']), float(t_r['Hs Facturadas CI'])
        c_h1, c_h2 = st.columns(2)
        with c_h1: st.plotly_chart(px.pie(values=[ht_cc, ht_cg, ht_ci], names=["CC", "CG", "CI"], hole=0.4, title="Horas Trabajadas"), use_container_width=True)
        with c_h2: st.plotly_chart(px.pie(values=[hf_cc, hf_cg, hf_ci], names=["CC", "CG", "CI"], hole=0.4, title="Horas Facturadas"), use_container_width=True)

    with tab3:
        st.header("Márgenes por Canal (Repuestos)")
        detalles = []
        for c in canales_rep:
            if f'Venta {c}' in r_r:
                vb = float(r_r[f'Venta {c}'])
                vn = vb - float(r_r.get(f'Descuento {c}', 0))
                detalles.append({"Canal": c, "Venta Bruta": vb, "Margen $": vn - float(r_r.get(f'Costo {c}', 0)), "% Mg": ((vn - float(r_r.get(f'Costo {c}', 0)))/vn if vn>0 else 0)})
        st.dataframe(pd.DataFrame(detalles).style.format({"Venta Bruta": "${:,.0f}", "Margen $": "${:,.0f}", "% Mg": "{:.1%}"}), use_container_width=True, hide_index=True)

    with tab4:
        st.header("Chapa y Pintura")
        sedes = [('Jujuy', cj_r, 'CyP JUJUY'), ('Salta', cs_r, 'CyP SALTA')]
        cyp1, cyp2 = st.columns(2)
        for i, (nom, row, sh) in enumerate(sedes):
            with (cyp1 if i == 0 else cyp2):
                st.markdown(f"""<div style="border: 1px solid #e0e0e0; padding: 20px; border-radius: 10px; background-color: white;">
                                <h3>Sede {nom}</h3>
                                <p>Paños Propios: <b>{row['Paños Propios']}</b></p>
                                <p>Facturación MO: <b>${(float(row['MO Pura'])+float(row['MO Tercero'])):,.0f}</b></p></div>""", unsafe_allow_html=True)
                st.plotly_chart(px.pie(values=[float(row['MO Pura']), float(row['MO Tercero'])], names=["MO Pura", "Terceros"], hole=0.4, title=f"Composición {nom}"), use_container_width=True)

except Exception as e:
    st.error(f"Error técnico: {e}")
