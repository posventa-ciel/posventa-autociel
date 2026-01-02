import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Grupo CENOA - Gestión Posventa", layout="wide")

# --- ESTILO ---
st.markdown("""<style>
    .main { background-color: #f4f7f9; }
    .portada-container { background: linear-gradient(90deg, #00235d 0%, #004080 100%); color: white; padding: 2rem; border-radius: 15px; text-align: center; margin-bottom: 2rem; }
    .stMetric { background-color: white; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; }
    .stTabs [aria-selected="true"] { background-color: #00235d !important; color: white !important; font-weight: bold; }
</style>""", unsafe_allow_html=True)

# --- CARGA DE DATOS ---
@st.cache_data(ttl=600)
def cargar_datos(sheet_id):
    hojas = ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA']
    data_dict = {}
    for h in hojas:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={h.replace(' ', '%20')}"
        df = pd.read_csv(url, dtype=str).fillna("0")
        # Limpieza de comas argentinas a puntos internacionales
        df = df.apply(lambda x: x.str.replace(',', '.') if x.dtype == "object" else x)
        for col in df.columns:
            if col not in ['Fecha', 'Fecha Corte', 'Canal', 'Estado']:
                df[col] = pd.to_numeric(df[col], errors='ignore')
        data_dict[h] = df
    return data_dict

def calcular_proyeccion(real, d_t, d_h):
    return (real / d_t) * d_h if d_t > 0 else 0

ID_SHEET = "1yJgaMR0nEmbKohbT_8Vj627Ma4dURwcQTQcQLPqrFwk"

try:
    df_all = cargar_datos(ID_SHEET)
    for h in df_all:
        col = 'Fecha Corte' if 'Fecha Corte' in df_all[h].columns else 'Fecha'
        df_all[h]['Fecha_dt'] = pd.to_datetime(df_all[h][col], dayfirst=True).dt.date

    fechas = sorted(df_all['CALENDARIO']['Fecha_dt'].unique(), reverse=True)
    f_sel = st.sidebar.selectbox("📅 Seleccionar Fecha", fechas)
    f_obj = f_sel.replace(day=1)

    # Variables Calendario
    c_r = df_all['CALENDARIO'][df_all['CALENDARIO']['Fecha_dt'] == f_sel].iloc[0]
    d_t, d_h = float(c_r['Días Transcurridos']), float(c_r['Días Hábiles Mes'])
    meses = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}

    # PORTADA
    st.markdown(f"""<div class="portada-container">
        <h1>Autociel - Tablero Posventa 2026</h1>
        <p>📍 {meses[f_sel.month]} | Avance: {d_t}/{d_h} días ({(d_t/d_h):.1%})</p>
    </div>""", unsafe_allow_html=True)

    # Extraer filas de datos
    s_r = df_all['SERVICIOS'][df_all['SERVICIOS']['Fecha_dt'] == f_sel].iloc[0]
    r_r = df_all['REPUESTOS'][df_all['REPUESTOS']['Fecha_dt'] == f_sel].iloc[0]
    t_r = df_all['TALLER'][df_all['TALLER']['Fecha_dt'] == f_sel].iloc[0]
    cj_r = df_all['CyP JUJUY'][df_all['CyP JUJUY']['Fecha_dt'] == f_sel].iloc[0]
    cs_r = df_all['CyP SALTA'][df_all['CyP SALTA']['Fecha_dt'] == f_sel].iloc[0]

    def get_o(sh, col):
        df = df_all[sh]
        res = df[df['Fecha_dt'] == f_obj]
        return float(res[col].iloc[0]) if not res.empty else 1.0

    t1, t2, t3, t4 = st.tabs(["🏠 General", "🛠️ Taller", "📦 Repuestos", "🎨 Chapa y Pintura"])

    with t1:
        cols = st.columns(4)
        metas = [
            ("Servicios ($)", s_r['MO Cliente']+s_r['MO Garantía']+s_r['MO Tercero'], get_o('SERVICIOS','Obj MO Total')),
            ("Repuestos ($)", sum([r_r[f'Venta {c}'] for c in ['Mostrador','Taller','Interna','Garantía','CyP','Mayorista','Seguros'] if f'Venta {c}' in r_r]), get_o('REPUESTOS','Obj Facturación Total')),
            ("CyP Jujuy ($)", cj_r['MO Pura']+cj_r['MO Tercero'], get_o('CyP JUJUY','Obj Facturación Total CyP Jujuy')),
            ("CyP Salta ($)", cs_r['MO Pura']+cs_r['MO Tercero'], get_o('CyP SALTA','Obj Facturación Total CyP Salta'))
        ]
        for i, (tit, real, obj) in enumerate(metas):
            proy = calcular_proyeccion(real, d_t, d_h)
            alc = proy / obj if obj > 0 else 0
            color = "#dc3545" if alc < 0.90 else ("#ffc107" if alc < 0.95 else "#28a745")
            cols[i].markdown(f"**{tit}**")
            cols[i].markdown(f"<h2 style='color:#00235d;'>${real:,.0f}</h2>", unsafe_allow_html=True)
            cols[i].markdown(f"<p style='color:{color}; font-weight:bold;'>Proy: {alc:.1%}</p>", unsafe_allow_html=True)

    with t2:
        st.subheader("Eficiencia y Productividad")
        e1, e2, e3 = st.columns(3)
        ef_gl = (t_r['Hs Facturadas CC']+t_r['Hs Facturadas CG']+t_r['Hs Facturadas CI']) / (t_r['Hs Trabajadas CC']+t_r['Hs Trabajadas CG']+t_r['Hs Trabajadas CI']) if (t_r['Hs Trabajadas CC']) > 0 else 0
        e1.metric("Eficiencia Global", f"{ef_gl:.1%}")
        e2.metric("Ocupación", f"{(t_r['Hs Trabajadas CC']/t_r['Hs Disponibles Real'] if t_r['Hs Disponibles Real']>0 else 0):.1%}")
        e3.metric("Productividad", f"{t_r.get('Productividad Taller %', 0):.1%}")
        st.plotly_chart(px.pie(values=[t_r['Hs Trabajadas CC'], t_r['Hs Trabajadas CG'], t_r['Hs Trabajadas CI']], names=["Cliente", "Garantía", "Interna"], title="Distribución de Horas Trabajadas"))

    with t3:
        st.subheader("Márgenes de Repuestos")
        canales = ['Mostrador', 'Taller', 'Interna', 'Garantía', 'CyP', 'Mayorista', 'Seguros']
        detalles = []
        for c in canales:
            if f'Venta {c}' in r_r:
                vn = r_r[f'Venta {c}'] - r_r.get(f'Descuento {c}', 0)
                detalles.append({"Canal": c, "Venta Neta": vn, "Margen %": ((vn - r_r.get(f'Costo {c}', 0))/vn if vn>0 else 0)})
        st.table(pd.DataFrame(detalles))

    with t4:
        st.subheader("Paños Chapa y Pintura")
        cyp1, cyp2 = st.columns(2)
        for i, (nom, row, sh) in enumerate([('Jujuy', cj_r, 'CyP JUJUY'), ('Salta', cs_r, 'CyP SALTA')]):
            with (cyp1 if i==0 else cyp2):
                st.write(f"**Sede {nom}**")
                st.metric("Paños Propios", f"{row['Paños Propios']}", delta=f"{row['Paños Propios'] - get_o(sh, 'Obj Paños Propios Mensual'):.0f} vs Obj")

except Exception as e:
    st.error(f"Error técnico: {e}")
