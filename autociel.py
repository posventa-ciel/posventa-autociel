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

# --- LIMPIEZA DE DATOS ---
def limpiar_columna_numerica(df, cols_to_skip):
    for col in df.columns:
        if col not in cols_to_skip:
            # Quitamos símbolos que rompen el formato (%) y convertimos comas a puntos
            df[col] = df[col].astype(str).str.replace('%', '', regex=False).str.replace('$', '', regex=False).str.replace(',', '.', regex=False).str.strip()
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    return df

@st.cache_data(ttl=0) # <--- FUERZA A LEER SIEMPRE DATOS NUEVOS
def cargar_datos_sheets(sheet_id):
    hojas = ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA']
    data_dict = {}
    skip = ['Fecha', 'Fecha Corte', 'Canal', 'Estado']
    for h in hojas:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={h.replace(' ', '%20')}"
        df = pd.read_csv(url, dtype=str).fillna("0")
        df = limpiar_columna_numerica(df, skip)
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

    # --- DATOS CALENDARIO ---
    c_r = data['CALENDARIO'][data['CALENDARIO']['Fecha_dt'] == f_sel].iloc[0]
    d_t, d_h = float(c_r['Días Transcurridos']), float(c_r['Días Hábiles Mes'])
    prog_t = d_t / d_h if d_h > 0 else 0.0

    meses_es = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}

    # --- PORTADA ---
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

    def get_o(sh, col):
        df = data[sh]
        res = df[df['Fecha_dt'] == f_obj]
        return float(res[col].iloc[0]) if not res.empty else float(df[col].max())

    t1, t2, t3, t4 = st.tabs(["🏠 General", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura"])

    with t1:
        cols = st.columns(4)
        r_mo = s_r['MO Cliente'] + s_r['MO Garantía'] + s_r['MO Tercero']
        r_rep = sum([r_r[f'Venta {c}'] for c in ['Mostrador','Taller','Interna','Garantía','CyP','Mayorista','Seguros'] if f'Venta {c}' in r_r])
        metas = [("Servicios", r_mo, get_o('SERVICIOS','Obj MO Total')), ("Repuestos", r_rep, get_o('REPUESTOS','Obj Facturación Total')),
                 ("CyP Jujuy", cj_r['MO Pura']+cj_r['MO Tercero'], get_o('CyP JUJUY','Obj Facturación Total CyP Jujuy')),
                 ("CyP Salta", cs_r['MO Pura']+cs_r['MO Tercero'], get_o('CyP SALTA','Obj Facturación Total CyP Salta'))]
        for i, (tit, real, obj) in enumerate(metas):
            p = (real / d_t) * d_h if d_t > 0 else 0
            alc = p / obj if obj > 0 else 0
            color = "#dc3545" if alc < 0.90 else ("#ffc107" if alc < 0.95 else "#28a745")
            with cols[i]:
                st.markdown(f"**{tit}**")
                st.markdown(f"<h2 style='color:#00235d;'>${real:,.0f}</h2>", unsafe_allow_html=True)
                st.markdown(f"<p style='color:{color}; font-weight:bold;'>Proy: {alc:.1%}</p>", unsafe_allow_html=True)
                st.markdown(f'<div style="width:100%; background:#e0e0e0; height:8px; border-radius:10px;"><div style="width:{min(alc*100, 100)}%; background:{color}; height:8px; border-radius:10px;"></div></div>', unsafe_allow_html=True)

    with t2:
        st.header("Flujo de Unidades y Performance")
        k1, k2 = st.columns(2)
        real_tus = s_r['CPUS'] + s_r['Otros Cargos']
        k1.metric("TUS Total", f"{real_tus:,.0f}", f"{(real_tus/d_t*d_h):,.0f} Proy.")
        k2.metric("CPUS", f"{s_r['CPUS']:,.0f}", f"{(s_r['CPUS']/d_t*d_h):,.0f} Proy.")
        st.markdown("---")
        g1, g2 = st.columns(2)
        with g1: st.plotly_chart(px.pie(values=[t_r['Hs Trabajadas CC'], t_r['Hs Trabajadas CG'], t_r['Hs Trabajadas CI']], names=["CC","CG","CI"], hole=0.4, title="Hs Trabajadas"))
        with g2: st.plotly_chart(px.pie(values=[t_r['Hs Facturadas CC'], t_r['Hs Facturadas CG'], t_r['Hs Facturadas CI']], names=["CC","CG","CI"], hole=0.4, title="Hs Facturadas"))
        e1, e2, e3 = st.columns(3)
        ht = t_r['Hs Trabajadas CC'] + t_r['Hs Trabajadas CG'] + t_r['Hs Trabajadas CI']
        hf = t_r['Hs Facturadas CC'] + t_r['Hs Facturadas CG'] + t_r['Hs Facturadas CI']
        e1.metric("Eficiencia Global", f"{(hf/ht if ht>0 else 0):.1%}")
        e2.metric("Ocupación", f"{(ht/t_r['Hs Disponibles Real'] if t_r['Hs Disponibles Real']>0 else 0):.1%}")
        e3.metric("Productividad", f"{(t_r.get('Productividad Taller %', 0)/100 if t_r.get('Productividad Taller %', 0)>1 else t_r.get('Productividad Taller %', 0)):.1%}")

    with t3:
        st.header("Márgenes de Repuestos")
        detalles = []
        for c in ['Mostrador','Taller','Interna','Garantía','CyP','Mayorista','Seguros']:
            if f'Venta {c}' in r_r:
                vn = r_r[f'Venta {c}'] - r_r.get(f'Descuento {c}', 0)
                detalles.append({"Canal": c, "Venta Neta": vn, "Margen %": ((vn - r_r.get(f'Costo {c}', 0))/vn if vn>0 else 0)})
        st.dataframe(pd.DataFrame(detalles).style.format({"Venta Neta": "${:,.0f}", "Margen %": "{:.1%}"}), use_container_width=True)

    with t4:
        st.header("Chapa y Pintura")
        c1, c2 = st.columns(2)
        for i, (nom, row) in enumerate([('Jujuy', cj_r), ('Salta', cs_r)]):
            with (c1 if i==0 else c2):
                st.subheader(nom)
                st.metric("Paños Propios", f"{row['Paños Propios']:,.0f}")
                st.plotly_chart(px.pie(values=[row['MO Pura'], row['MO Tercero']], names=["Propia", "Terceros"], hole=0.4, title=f"Origen MO {nom}"))

except Exception as e:
    st.error(f"Error cargando los datos: {e}")
