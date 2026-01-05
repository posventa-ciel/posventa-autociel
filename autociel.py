import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Grupo CENOA - Gestión Posventa", layout="wide")

# --- ESTILO CORPORATIVO ---
st.markdown("""<style>
    .main { background-color: #f4f7f9; }
    .portada-container { background: linear-gradient(90deg, #00235d 0%, #004080 100%); color: white; padding: 2rem; border-radius: 15px; text-align: center; margin-bottom: 2rem; }
    .area-box { background-color: white; border: 1px solid #e0e0e0; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); min-height: 250px; margin-bottom: 20px; }
    .stMetric { background-color: white; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; }
    .stTabs [aria-selected="true"] { background-color: #00235d !important; color: white !important; font-weight: bold; }
</style>""", unsafe_allow_html=True)

# --- CARGA Y NORMALIZACIÓN ---
@st.cache_data(ttl=60)
def cargar_datos(sheet_id):
    hojas = ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA']
    data_dict = {}
    for h in hojas:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={h.replace(' ', '%20')}"
        df = pd.read_csv(url, dtype=str).fillna("0")
        
        # 1. Normalizar nombres de columnas
        df.columns = [c.strip().upper().replace(".", "") for c in df.columns]
        
        # 2. Limpieza de datos (SALTANDO COLUMNAS DE FECHA)
        for col in df.columns:
            if "FECHA" not in col and "CANAL" not in col and "ESTADO" not in col:
                df[col] = df[col].astype(str).str.replace(r'[\$%\s]', '', regex=True).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        data_dict[h] = df
    return data_dict

def find_col(df, keywords):
    for col in df.columns:
        if all(k.upper() in col for k in keywords):
            return col
    return df.columns[0]

ID_SHEET = "1yJgaMR0nEmbKohbT_8Vj627Ma4dURwcQTQcQLPqrFwk"

try:
    data = cargar_datos(ID_SHEET)
    
    for h in data:
        col_f = next((c for c in data[h].columns if 'FECHA' in c), data[h].columns[0])
        data[h]['Fecha_dt'] = pd.to_datetime(data[h][col_f], dayfirst=True, errors='coerce')
        data[h]['Mes'] = data[h]['Fecha_dt'].dt.month
        data[h]['Año'] = data[h]['Fecha_dt'].dt.year

    # --- FILTROS ---
    años_disp = sorted([a for a in data['CALENDARIO']['Año'].unique() if pd.notnull(a)], reverse=True)
    año_sel = st.sidebar.selectbox("📅 Seleccionar Año", años_disp)
    
    meses_nom = {1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic"}
    meses_disp = sorted(data['CALENDARIO'][data['CALENDARIO']['Año'] == año_sel]['Mes'].unique(), reverse=True)
    mes_sel = st.sidebar.selectbox("📅 Seleccionar Mes", meses_disp, format_func=lambda x: meses_nom.get(x, "N/A"))

    def get_mes_data(df):
        res = df[(df['Año'] == año_sel) & (df['Mes'] == mes_sel)]
        return res.sort_values('Fecha_dt').iloc[-1] if not res.empty else df.iloc[-1]

    c_r, s_r, r_r, t_r = get_mes_data(data['CALENDARIO']), get_mes_data(data['SERVICIOS']), get_mes_data(data['REPUESTOS']), get_mes_data(data['TALLER'])
    cj_r, cs_r = get_mes_data(data['CyP JUJUY']), get_mes_data(data['CyP SALTA'])

    # Cálculo de días
    d_t = float(c_r[find_col(data['CALENDARIO'], ["DIAS", "TRANS"])])
    d_h = float(c_r[find_col(data['CALENDARIO'], ["DIAS", "HAB"])])
    prog_t = d_t / d_h if d_h > 0 else 0

    st.markdown(f"""<div class="portada-container"><h1>Resumen de Objetivos de Posventa</h1>
    <p>📅 {meses_nom.get(mes_sel)} {año_sel} | Avance: {d_t:g}/{d_h:g} días ({prog_t:.1%})</p></div>""", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🏠 General", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura"])

    with tab1:
        cols = st.columns(4)
        c_mc, c_mg, c_mt = find_col(data['SERVICIOS'], ["MO", "CLI"]), find_col(data['SERVICIOS'], ["MO", "GAR"]), find_col(data['SERVICIOS'], ["MO", "TER"])
        r_mo = s_r[c_mc] + s_r[c_mg] + s_r[c_mt]
        r_rep = sum([r_r[c] for c in r_r.index if "VENTA" in c and "OBJ" not in c])
        
        metas = [
            ("M.O. Servicios", r_mo, s_r.get(find_col(data['SERVICIOS'], ["OBJ", "MO"]), 1)),
            ("Repuestos", r_rep, r_r.get(find_col(data['REPUESTOS'], ["OBJ", "FACT"]), 1)),
            ("CyP Jujuy", cj_r[find_col(data['CyP JUJUY'], ["MO", "PUR"])] + cj_r[find_col(data['CyP JUJUY'], ["MO", "TER"])], cj_r.get(find_col(data['CyP JUJUY'], ["OBJ", "FACT"]), 1)),
            ("CyP Salta", cs_r[find_col(data['CyP SALTA'], ["MO", "PUR"])] + cs_r[find_col(data['CyP SALTA'], ["MO", "TER"])] + cs_r.get('FACTREPUESTOS', 0), cs_r.get(find_col(data['CyP SALTA'], ["OBJ", "FACT"]), 1))
        ]
        
        for i, (tit, real, obj) in enumerate(metas):
            p = (real/d_t)*d_h if d_t > 0 else 0; alc = p/obj if obj > 0 else 0
            color = "#dc3545" if alc < 0.90 else ("#ffc107" if alc < 0.95 else "#28a745")
            with cols[i]:
                st.markdown(f"""<div class="area-box">
                    <p style="font-weight:bold; color:#666; margin-bottom:5px;">{tit}</p>
                    <h2 style="margin:0; color:#00235d;">${real:,.0f}</h2>
                    <p style="margin:0; font-size:13px; color:#999;">Objetivo: ${obj:,.0f}</p>
                    <div style="margin-top:15px;">
                        <p style="color:{color}; margin:0; font-weight:bold;">Proy: {alc:.1%}</p>
                        <p style="color:#666; font-size:13px; margin:0;">Est. al cierre: <b>${p:,.0f}</b></p>
                        <div style="width:100%; background:#e0e0e0; height:8px; border-radius:10px; margin-top:5px;">
                            <div style="width:{min(alc*100, 100)}%; background:{color}; height:8px; border-radius:10px;"></div>
                        </div>
                    </div>
                </div>""", unsafe_allow_html=True)

    with tab2:
        st.header("Performance de Taller")
        k1, k2, k3, k4 = st.columns(4)
        c_cpus = find_col(data['SERVICIOS'], ["CPUS"])
        real_tus = s_r[c_cpus] + s_r.get(find_col(data['SERVICIOS'], ["OTROS", "CARGOS"]), 0)
        k1.metric("TUS Resultado", f"{real_tus:,.0f}")
        k2.metric("TUS Objetivo", f"{s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'TUS']), 0):,.0f}")
        k3.metric("CPUS Resultado", f"{s_r[c_cpus]:,.0f}")
        k4.metric("CPUS Objetivo", f"{s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'CPUS']), 0):,.0f}")
        
        st.markdown("---")
        # Ticket Promedio
        c_div = s_r[c_cpus] if s_r[c_cpus] > 0 else 1
        tp_hs = (t_r.get(find_col(data['TALLER'], ["FACT", "CC"]), 0) + t_r.get(find_col(data['TALLER'], ["FACT", "CG"]), 0)) / c_div
        tp_mo = (s_r[c_mc] + s_r[c_mg]) / c_div
        m1, m2 = st.columns(2)
        m1.metric("Ticket Promedio M.O. (Hs)", f"{tp_hs:.2f} hs/CPUS")
        m2.metric("Ticket Promedio M.O. ($)", f"${tp_mo:,.0f}/CPUS")
        
        # Histórico
        hist_s = data['SERVICIOS'][data['SERVICIOS']['Año'] == año_sel].copy().groupby('Mes').last().reset_index()
        if not hist_s.empty:
            hist_s['TP_PESOS'] = (hist_s[c_mc] + hist_s[c_mg]) / hist_s[c_cpus].replace(0,1)
            st.plotly_chart(px.line(hist_s, x='Mes', y=['CPUS', 'TP_PESOS'], title="Evolución CPUS y Ticket Promedio ($)", markers=True))

    with tab3:
        st.header("Repuestos")
        canales_r = ['MOSTRADOR', 'TALLER', 'INTERNA', 'GARANTIA', 'CYP', 'MAYORISTA', 'SEGUROS']
        detalles = []
        for c in canales_r:
            vb, d, cost = r_r.get(find_col(data['REPUESTOS'], ["VENTA", c]), 0), r_r.get(find_col(data['REPUESTOS'], ["DESC", c]), 0), r_r.get(find_col(data['REPUESTOS'], ["COSTO", c]), 0)
            vn = vb - d; ut = vn - cost
            detalles.append({"Canal": c, "Bruta": vb, "Desc": d, "Costo": cost, "Margen $": ut, "% Mg": (ut/vn if vn>0 else 0)})
        df_r = pd.DataFrame(detalles)
        
        r1, r2, r3 = st.columns(3)
        vbt = df_r['Bruta'].sum(); mgt = df_r['Margen $'].sum(); mgp = mgt / (vbt - df_r['Desc'].sum()) if (vbt - df_r['Desc'].sum())>0 else 0
        r1.metric("Facturación Bruta", f"${vbt:,.0f}")
        r2.metric("Margen Total $", f"${mgt:,.0f}")
        r3.metric("Margen Promedio %", f"{mgp:.1%}")
        st.dataframe(df_r.style.format({"Bruta":"${:,.0f}","Desc":"${:,.0f}","Costo":"${:,.0f}","Margen $":"${:,.0f}","% Mg":"{:.1%}"}), use_container_width=True)
        st.info(f"VALOR TOTAL STOCK: ${float(r_r.get(find_col(data['REPUESTOS'], ['VALOR', 'STOCK']), 0)):,.0f}")
        
        hist_r = data['REPUESTOS'][data['REPUESTOS']['Año'] == año_sel].copy().groupby('Mes').last().reset_index()
        st.plotly_chart(px.bar(hist_r, x='Mes', y=find_col(data['REPUESTOS'],['OBJ','FACT']), title="Histórico de Objetivos de Repuestos"))

    with tab4:
        st.header("Histórico Chapa y Pintura")
        hist_cj = data['CyP JUJUY'][data['CyP JUJUY']['Año'] == año_sel].copy().groupby('Mes').last().reset_index()
        if not hist_cj.empty:
            st.plotly_chart(px.line(hist_cj, x='Mes', y=[find_col(data['CyP JUJUY'], ['PAÑOS', 'PROP']), find_col(data['CyP JUJUY'], ['OBJ', 'PAÑO'])], title="Evolución Paños Jujuy vs Objetivo", markers=True))

except Exception as e:
    st.error(f"Error técnico detectado: {e}")
