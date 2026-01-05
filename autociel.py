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

# --- FUNCIÓN DE LIMPIEZA DE DATOS ---
def limpiar_valor(v):
    if isinstance(v, str):
        # Quitamos símbolos que rompen la conversión a número
        v = v.replace('%', '').replace('$', '').replace(' ', '').replace(',', '.')
    try:
        return float(v)
    except:
        return 0.0

@st.cache_data(ttl=60)
def cargar_datos(sheet_id):
    hojas = ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA']
    data_dict = {}
    for h in hojas:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={h.replace(' ', '%20')}"
        df = pd.read_csv(url, dtype=str).fillna("0")
        
        # Convertimos todas las columnas numéricas a float real
        for col in df.columns:
            if col not in ['Fecha', 'Fecha Corte', 'Canal', 'Estado']:
                df[col] = df[col].apply(limpiar_valor)
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
    f_obj = f_sel.replace(day=1)

    # --- DATOS CALENDARIO ---
    c_r = data['CALENDARIO'][data['CALENDARIO']['Fecha_dt'] == f_sel].iloc[0]
    d_t = float(c_r['Días Transcurridos'])
    d_h = float(c_r['Días Hábiles Mes'])
    prog_t = d_t / d_h if d_h > 0 else 0.0

    meses_es = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 
                7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}

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

    # Filas de datos
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

    tab1, tab2, tab3, tab4 = st.tabs(["🏠 General", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura"])

    with tab1:
        cols = st.columns(4)
        r_mo = s_r['MO Cliente'] + s_r['MO Garantía'] + s_r['MO Tercero']
        canales_rep = ['Mostrador', 'Taller', 'Interna', 'Garantía', 'CyP', 'Mayorista', 'Seguros']
        r_rep = sum([r_r[f'Venta {c}'] for c in canales_rep if f'Venta {c}' in r_r])
        r_cj = cj_r['MO Pura'] + cj_r['MO Tercero']
        r_cs = cs_r['MO Pura'] + cs_r['MO Tercero'] + cs_r.get('Fact Repuestos', 0)
        
        metas = [("Servicios", r_mo, get_o('SERVICIOS', 'Obj MO Total')), 
                 ("Repuestos", r_rep, get_o('REPUESTOS', 'Obj Facturación Total')),
                 ("CyP Jujuy", r_cj, get_o('CyP JUJUY', 'Obj Facturación Total CyP Jujuy')), 
                 ("CyP Salta", r_cs, get_o('CyP SALTA', 'Obj Facturación Total CyP Salta'))]

        for i, (tit, real, obj) in enumerate(metas):
            p_pesos = (real / d_t) * d_h if d_t > 0 else 0
            alc = p_pesos / obj if obj > 0 else 0
            color = "#dc3545" if alc < 0.90 else ("#ffc107" if alc < 0.95 else "#28a745")
            with cols[i]:
                st.markdown(f"**{tit}**")
                st.markdown(f"<h1 style='margin:0; color:#00235d; font-size: 32px;'>${real:,.0f}</h1>", unsafe_allow_html=True)
                st.markdown(f"<p style='margin:0; font-size: 16px; font-weight:bold;'>OBJ: ${obj:,.0f}</p>", unsafe_allow_html=True)
                st.markdown(f"<p style='color:{color}; margin:0; font-weight:bold;'>Proy: {alc:.1%}</p>", unsafe_allow_html=True)
                st.markdown(f'<div style="width:100%; background:#e0e0e0; height:8px; border-radius:10px;"><div style="width:{min(alc*100, 100)}%; background:{color}; height:8px; border-radius:10px;"></div></div>', unsafe_allow_html=True)

    with tab2:
        st.header("Flujo de Unidades y Performance")
        c_u1, c_u2 = st.columns(2)
        real_tus = s_r['CPUS'] + s_r['Otros Cargos']
        for i, (tit, real, obj) in enumerate([("Total Unidades Servicio (TUS)", real_tus, get_o('SERVICIOS', 'Obj TUS')), 
                                              ("Cargos Clientes (CPUS)", s_r['CPUS'], get_o('SERVICIOS', 'Obj CPUS'))]):
            p_cant = (real / d_t) * d_h if d_t > 0 else 0
            alc = p_cant / obj if obj > 0 else 0
            color_kpi = "#dc3545" if alc < 0.90 else ("#ffc107" if alc < 0.95 else "#28a745")
            with (c_u1 if i == 0 else c_u2):
                st.markdown(f"""<div style="border: 1px solid #e0e0e0; padding: 20px; border-radius: 10px; background-color: white;">
                    <p style="font-weight: bold; color: #666;">{tit}</p>
                    <h2 style="margin:0;">{real:,.0f} <span style="font-size:15px; color:#999;">/ Obj: {obj:,.0f}</span></h2>
                    <p style="color:{color_kpi}; font-weight:bold; margin-top:10px;">↑ Proy: {p_cant:,.0f} ({alc:.1%})</p>
                </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.header("Composición de Horas y Eficiencia")
        g1, g2 = st.columns(2)
        with g1:
            st.plotly_chart(px.pie(values=[t_r['Hs Trabajadas CC'], t_r['Hs Trabajadas CG'], t_r['Hs Trabajadas CI']], 
                                   names=["CC", "CG", "CI"], hole=0.4, title="Hs Trabajadas"), use_container_width=True)
        with g2:
            st.plotly_chart(px.pie(values=[t_r['Hs Facturadas CC'], t_r['Hs Facturadas CG'], t_r['Hs Facturadas CI']], 
                                   names=["CC", "CG", "CI"], hole=0.4, title="Hs Facturadas"), use_container_width=True)
        
        e1, e2, e3 = st.columns(3)
        ht_tot = t_r['Hs Trabajadas CC'] + t_r['Hs Trabajadas CG'] + t_r['Hs Trabajadas CI']
        hf_tot = t_r['Hs Facturadas CC'] + t_r['Hs Facturadas CG'] + t_r['Hs Facturadas CI']
        e1.metric("Eficiencia Global", f"{(hf_tot/ht_tot if ht_tot>0 else 0):.1%}")
        e2.metric("Ocupación", f"{(ht_tot/t_r['Hs Disponibles Real'] if t_r['Hs Disponibles Real']>0 else 0):.1%}")
        e3.metric("Productividad", f"{(t_r.get('Productividad Taller %', 0)/100 if t_r.get('Productividad Taller %', 0)>1 else t_r.get('Productividad Taller %', 0)):.1%}")

    with tab3:
        st.header("Análisis de Ventas y Márgenes de Repuestos")
        detalles = []
        for c in canales_rep:
            if f'Venta {c}' in r_r:
                vn = r_r[f'Venta {c}'] - r_r.get(f'Descuento {c}', 0)
                mg = vn - r_r.get(f'Costo {c}', 0)
                detalles.append({"Canal": c, "Venta Neta": vn, "Margen $": mg, "% Margen": (mg/vn if vn>0 else 0)})
        st.dataframe(pd.DataFrame(detalles).style.format({"Venta Neta": "${:,.0f}", "Margen $": "${:,.0f}", "% Margen": "{:.1%}"}), use_container_width=True)
        st.info(f"VALOR TOTAL DEL STOCK: ${r_r.get('Valor Stock', 0):,.0f}")

    with tab4:
        st.header("Producción y Facturación Chapa y Pintura")
        c1, c2 = st.columns(2)
        for i, (nom, row) in enumerate([('Jujuy', cj_r), ('Salta', cs_r)]):
            with (c1 if i==0 else c2):
                st.subheader(f"Sede {nom}")
                st.metric("Paños Propios", f"{row['Paños Propios']:,.0f}")
                st.plotly_chart(px.pie(values=[row['MO Pura'], row['MO Tercero']], names=["Propia", "Terceros"], hole=0.4, title=f"Origen MO {nom}"), use_container_width=True)
                if nom == 'Salta':
                    st.write(f"Fact. Repuestos: ${row.get('Fact Repuestos', 0):,.0f}")

except Exception as e:
    st.error(f"Error cargando los datos del Sheet: {e}")
