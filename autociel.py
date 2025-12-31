Ese error de "unexpected indent" ocurre porque hay unos espacios "fantasma" antes del st.markdown. En Python, si una línea está un milímetro más adentro o más afuera de lo que corresponde, el programa se detiene.

He limpiado completamente el código, corregido las sangrías y verificado que todas las variables (como meses_es) estén en el lugar correcto para que no vuelvan a fallar.

Instrucciones para que funcione ahora:
Ve a GitHub y borra absolutamente todo lo que hay en autociel.py.

Pega este código exacto (asegúrate de que la primera línea import streamlit... no tenga ningún espacio antes):

Python

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

# --- FUNCIÓN DE CARGA ---
@st.cache_data(ttl=600)
def cargar_datos_desde_sheets(sheet_id):
    hojas = ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA']
    data_dict = {}
    for h in hojas:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={h.replace(' ', '%20')}"
        data_dict[h] = pd.read_csv(url).fillna(0)
    return data_dict

SHEET_ID = "1yJgaMR0nEmbKohbT_8Vj627Ma4dURwcQTQcQLPqrFwk"

try:
    data = cargar_datos_desde_sheets(SHEET_ID)

    for h in data:
        col_f = 'Fecha Corte' if 'Fecha Corte' in data[h].columns else 'Fecha'
        data[h]['Fecha_dt'] = pd.to_datetime(data[h][col_f]).dt.date

    fechas = sorted(data['CALENDARIO']['Fecha_dt'].unique(), reverse=True)
    f_sel = st.sidebar.selectbox("📅 Seleccionar Fecha", fechas)
    
    meses_es = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 
                7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
    
    c_r = data['CALENDARIO'][data['CALENDARIO']['Fecha_dt'] == f_sel].iloc[0]
    d_t, d_h = int(c_r['Días Transcurridos']), int(c_r['Días Hábiles Mes'])
    prog_t = d_t / d_h if d_h > 0 else 0

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
        return f_o[col].iloc[0] if not f_o.empty else df[col].max()

    tab1, tab2, tab3, tab4 = st.tabs(["🏠 General", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura"])

    with tab1:
        cols = st.columns(4)
        r_mo = s_r['MO Cliente'] + s_r['MO Garantía'] + s_r['MO Tercero']
        r_rep = sum([r_r[f'Venta {c}'] for c in ['Mostrador', 'Taller', 'Interna', 'Garantía', 'CyP', 'Mayorista', 'Seguros'] if f'Venta {c}' in r_r])
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
                st.markdown(f"<div style='margin-top:10px;'><p style='color:{color}; font-size:18px; margin:0;'><b>Proy: {alc:.1%}</b></p></div>", unsafe_allow_html=True)
                st.markdown(f'<div style="width:100%; background:#e0e0e0; height:8px; border-radius:10px;"><div style="width:{min(alc*100, 100)}%; background:{color}; height:8px; border-radius:10px;"></div></div>', unsafe_allow_html=True)

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
                st.markdown(f'<div style="border: 1px solid #e0e0e0; padding: 20px; border-radius: 10px; background-color: white;">'
                            f'<p style="font-size: 14px; color: #666; font-weight: bold;">{tit}</p>'
                            f'<h1 style="margin: 0; font-size: 42px;">{real:,.0f} <span style="font-size: 18px; color: #999;">/ Obj: {obj:,.0f}</span></h1>'
                            f'<p style="color: {color_kpi}; font-weight: bold;">↑ Proy: {p_cant:,.0f} ({alc:.1%})</p></div>', unsafe_allow_html=True)

    with tab3:
        st.header("Análisis de Ventas y Stock")
        canales = ['Mostrador', 'Taller', 'Interna', 'Garantía', 'CyP', 'Mayorista', 'Seguros']
        detalles = []
        for c in canales:
            if f'Venta {c}' in r_r:
                vn = r_r[f'Venta {c}'] - r_r.get(f'Descuento {c}', 0)
                ut = vn - r_r.get(f'Costo {c}', 0)
                detalles.append({"Canal": c, "Bruta": r_r[f'Venta {c}'], "Margen $": ut, "% Mg": (ut/vn if vn>0 else 0)})
        st.dataframe(pd.DataFrame(detalles), use_container_width=True, hide_index=True)

    with tab4:
        st.header("Productividad y Facturación CyP")
        sedes = [('Jujuy', cj_r), ('Salta', cs_r)]
        c1, c2 = st.columns(2)
        for i, (nom, row) in enumerate(sedes):
            with (c1 if i == 0 else c2):
                st.metric(f"Facturación {nom}", f"${(row['MO Pura']+row['MO Tercero']):,.0f}")

except Exception as e:
    st.error(f"Error en los datos de Autociel: {e}")
