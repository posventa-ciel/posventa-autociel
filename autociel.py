import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Grupo CENOA - Gestión Posventa", layout="wide")

# --- ESTILO ---
st.markdown("""<style>
    .main { background-color: #f4f7f9; }
    .portada-container { background: linear-gradient(90deg, #00235d 0%, #004080 100%); color: white; padding: 2rem; border-radius: 15px; text-align: center; margin-bottom: 2rem; }
    .area-box { background-color: white; border: 1px solid #e0e0e0; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); min-height: 250px; margin-bottom: 20px; }
    .stMetric { background-color: white; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; }
</style>""", unsafe_allow_html=True)

# --- FUNCIÓN DE BÚSQUEDA DE COLUMNAS ---
def find_col(df, keywords):
    for col in df.columns:
        if all(k.upper() in col for k in keywords):
            return col
    return ""

# --- CARGA DE DATOS ---
@st.cache_data(ttl=60)
def cargar_datos(sheet_id):
    hojas = ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA']
    data_dict = {}
    for h in hojas:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={h.replace(' ', '%20')}"
        df = pd.read_csv(url, dtype=str).fillna("0")
        df.columns = [c.strip().upper().replace(".", "") for c in df.columns]
        
        for col in df.columns:
            if "FECHA" not in col and "CANAL" not in col and "ESTADO" not in col:
                df[col] = df[col].astype(str).str.replace(r'[\$%\s]', '', regex=True).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        data_dict[h] = df
    return data_dict

ID_SHEET = "1yJgaMR0nEmbKohbT_8Vj627Ma4dURwcQTQcQLPqrFwk"

try:
    data = cargar_datos(ID_SHEET)
    
    # Procesar fechas
    for h in data:
        col_f = find_col(data[h], ["FECHA"])
        if not col_f: col_f = data[h].columns[0]
        data[h]['Fecha_dt'] = pd.to_datetime(data[h][col_f], dayfirst=True, errors='coerce')
        data[h]['Mes'] = data[h]['Fecha_dt'].dt.month
        data[h]['Año'] = data[h]['Fecha_dt'].dt.year

    # --- FILTROS ---
    if not data['CALENDARIO'].empty:
        años_disp = sorted([int(a) for a in data['CALENDARIO']['Año'].unique() if a > 0], reverse=True)
        año_sel = st.sidebar.selectbox("📅 Año", años_disp if años_disp else [2026])
        
        meses_nom = {1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic"}
        meses_disp = sorted(data['CALENDARIO'][data['CALENDARIO']['Año'] == año_sel]['Mes'].unique(), reverse=True)
        mes_sel = st.sidebar.selectbox("📅 Mes", meses_disp if len(meses_disp)>0 else [1], format_func=lambda x: meses_nom.get(x, "N/A"))
    else:
        st.error("No hay datos en el Calendario.")
        st.stop()

    # Función para obtener fila del mes seleccionado (KPIs)
    def get_kpi_row(df):
        res = df[(df['Año'] == año_sel) & (df['Mes'] == mes_sel)]
        return res.sort_values('Fecha_dt').iloc[-1] if not res.empty else df.iloc[-1]

    # Función para obtener DataFrame histórico del año seleccionado (Gráficos)
    def get_hist_df(df):
        return df[df['Año'] == año_sel].sort_values('Fecha_dt')

    c_r, s_r, r_r, t_r = get_kpi_row(data['CALENDARIO']), get_kpi_row(data['SERVICIOS']), get_kpi_row(data['REPUESTOS']), get_kpi_row(data['TALLER'])
    cj_r, cs_r = get_kpi_row(data['CyP JUJUY']), get_kpi_row(data['CyP SALTA'])

    col_dt, col_dh = find_col(data['CALENDARIO'], ["DIAS", "TRANS"]), find_col(data['CALENDARIO'], ["DIAS", "HAB"])
    d_t, d_h = float(c_r.get(col_dt, 1)), float(c_r.get(col_dh, 1))
    prog_t = d_t / d_h if d_h > 0 else 0

    st.markdown(f"""<div class="portada-container"><h1>Autociel - Posventa</h1>
    <p>📅 {meses_nom.get(mes_sel)} {año_sel} | Avance: {d_t:g}/{d_h:g} días ({prog_t:.1%})</p></div>""", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🏠 General", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura"])

    with tab1:
        cols = st.columns(4)
        # Columnas MO
        c_mc = find_col(data['SERVICIOS'], ["MO", "CLI"])
        c_mg = find_col(data['SERVICIOS'], ["MO", "GAR"])
        c_mt = find_col(data['SERVICIOS'], ["MO", "TER"])
        r_mo = s_r.get(c_mc, 0) + s_r.get(c_mg, 0) + s_r.get(c_mt, 0)
        
        # Columnas Repuestos
        r_rep = sum([r_r.get(c, 0) for c in r_r.index if "VENTA" in c and "OBJ" not in c])

        # Columnas CyP
        cj_v = cj_r.get(find_col(data['CyP JUJUY'], ["MO", "PUR"]), 0) + cj_r.get(find_col(data['CyP JUJUY'], ["MO", "TER"]), 0)
        cs_v = cs_r.get(find_col(data['CyP SALTA'], ["MO", "PUR"]), 0) + cs_r.get(find_col(data['CyP SALTA'], ["MO", "TER"]), 0) + cs_r.get('FACTREPUESTOS', 0)

        metas = [
            ("M.O. Servicios", r_mo, s_r.get(find_col(data['SERVICIOS'], ["OBJ", "MO"]), 1)),
            ("Repuestos", r_rep, r_r.get(find_col(data['REPUESTOS'], ["OBJ", "FACT"]), 1)),
            ("CyP Jujuy", cj_v, cj_r.get(find_col(data['CyP JUJUY'], ["OBJ", "FACT"]), 1)),
            ("CyP Salta", cs_v, cs_r.get(find_col(data['CyP SALTA'], ["OBJ", "FACT"]), 1))
        ]
        
        for i, (tit, real, obj) in enumerate(metas):
            p = (real/d_t)*d_h if d_t > 0 else 0; alc = p/obj if obj > 0 else 0
            color = "#dc3545" if alc < 0.90 else ("#ffc107" if alc < 0.95 else "#28a745")
            with cols[i]:
                st.markdown(f"""<div class="area-box">
                    <p style="font-weight:bold; color:#666;">{tit}</p>
                    <h2 style="color:#00235d;">${real:,.0f}</h2>
                    <p style="font-size:13px; color:#999;">Obj: ${obj:,.0f}</p>
                    <div style="margin-top:10px;">
                        <p style="color:{color}; font-weight:bold; margin:0;">Proy: {alc:.1%}</p>
                        <p style="font-size:12px; color:#666;">Est. al cierre: <b>${p:,.0f}</b></p>
                        <div style="width:100%; background:#e0e0e0; height:8px; border-radius:10px;"><div style="width:{min(alc*100, 100)}%; background:{color}; height:8px; border-radius:10px;"></div></div>
                    </div>
                </div>""", unsafe_allow_html=True)

    with tab2:
        st.header("Performance y Tickets")
        k1, k2, k3, k4 = st.columns(4)
        c_cpus = find_col(data['SERVICIOS'], ["CPUS"])
        real_cpus = s_r.get(c_cpus, 0)
        real_tus = real_cpus + s_r.get(find_col(data['SERVICIOS'], ["OTROS", "CARGOS"]), 0)
        
        # Objetivos
        obj_tus = s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'TUS']), 1)
        obj_cpus = s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'CPUS']), 1)
        
        # Proyecciones
        p_tus = (real_tus/d_t)*d_h if d_t > 0 else 0; alc_tus = p_tus/obj_tus if obj_tus>0 else 0
        p_cpus = (real_cpus/d_t)*d_h if d_t > 0 else 0; alc_cpus = p_cpus/obj_cpus if obj_cpus>0 else 0
        
        # Función KPI simple
        def kpi(col, t, r, o, p, a):
            c = "#dc3545" if a < 0.90 else ("#ffc107" if a < 0.95 else "#28a745")
            col.markdown(f'<div style="border:1px solid #ddd; padding:15px; border-radius:10px; background:white;"><b>{t}</b><h3>{r:,.0f} <span style="font-size:0.6em; color:#888">/ {o:,.0f}</span></h3><p style="color:{c}; margin:0;">↑ Proy: {p:,.0f} ({a:.1%})</p></div>', unsafe_allow_html=True)

        kpi(k1, "TUS Total", real_tus, obj_tus, p_tus, alc_tus)
        kpi(k2, "CPUS", real_cpus, obj_cpus, p_cpus, alc_cpus)
        
        # --- CÁLCULO TICKET PROMEDIO ---
        # Fórmula: (Hs Fact CC + Hs Fact CG) / CPUS
        c_fact_cc = find_col(data['TALLER'], ["FACT", "CC"]) # Hs Facturadas CC
        c_fact_cg = find_col(data['TALLER'], ["FACT", "CG"]) # Hs Facturadas CG
        
        hs_cc = t_r.get(c_fact_cc, 0)
        hs_cg = t_r.get(c_fact_cg, 0)
        div_cpus = real_cpus if real_cpus > 0 else 1
        
        tp_hs = (hs_cc + hs_cg) / div_cpus
        tp_mo = (s_r.get(c_mc, 0) + s_r.get(c_mg, 0)) / div_cpus # MO Cliente + MO Garantía
        
        k3.metric("Ticket Promedio (Hs)", f"{tp_hs:.2f} hs/CPUS")
        k4.metric("Ticket Promedio ($)", f"${tp_mo:,.0f}/CPUS")
        
        st.markdown("---")
        # Históricos Servicios
        hist_s = get_hist_df(data['SERVICIOS'])
        hist_t = get_hist_df(data['TALLER']) # Necesitamos Taller para las hs históricas
        
        # Unimos por fecha/mes si es necesario, o asumimos mismo orden si están alineados.
        # Mejor calculamos y graficamos lo disponible en SERVICIOS
        if not hist_s.empty:
            st.subheader("Evolución Histórica")
            # Gráfico 1: CPUS
            fig1 = px.line(hist_s, x='Mes', y=c_cpus, title="Evolución CPUS", markers=True)
            st.plotly_chart(fig1, use_container_width=True)
            
            # Gráfico 2: Ticket Promedio $ (Aprox histórico)
            hist_s['TP_PESOS'] = (hist_s[c_mc] + hist_s[c_mg]) / hist_s[c_cpus].replace(0, 1)
            fig2 = px.bar(hist_s, x='Mes', y='TP_PESOS', title="Evolución Ticket Promedio ($)", text_auto='.2s')
            st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.header("Repuestos")
        canales = ['MOSTRADOR', 'TALLER', 'INTERNA', 'GARANTIA', 'CYP', 'MAYORISTA', 'SEGUROS']
        detalles = []
        for c in canales:
            v = r_r.get(find_col(data['REPUESTOS'], ["VENTA", c]), 0)
            d = r_r.get(find_col(data['REPUESTOS'], ["DESC", c]), 0)
            k = r_r.get(find_col(data['REPUESTOS'], ["COSTO", c]), 0)
            vn = v - d; ut = vn - k
            detalles.append({"Canal": c, "Bruta": v, "Desc": d, "Costo": k, "Margen $": ut, "% Mg": (ut/vn if vn>0 else 0)})
        df_r = pd.DataFrame(detalles)
        
        # Métricas Repuestos
        c1, c2, c3, c4 = st.columns(4)
        vbt = df_r['Bruta'].sum()
        mgt = df_r['Margen $'].sum()
        c1.metric("Facturación Bruta", f"${vbt:,.0f}")
        c2.metric("Margen Total $", f"${mgt:,.0f}")
        c3.metric("Margen %", f"{(mgt/(vbt-df_r['Desc'].sum()) if vbt>0 else 0):.1%}")
        
        # Ticket Repuestos: (Taller+Gtia+CyP) / CPUS
        v_tall = r_r.get(find_col(data['REPUESTOS'], ["VENTA", "TALLER"]), 0)
        v_gtia = r_r.get(find_col(data['REPUESTOS'], ["VENTA", "GAR"]), 0)
        v_cyp = r_r.get(find_col(data['REPUESTOS'], ["VENTA", "CYP"]), 0)
        tp_rep = (v_tall + v_gtia + v_cyp) / div_cpus
        c4.metric("Ticket Promedio Rep.", f"${tp_rep:,.0f}/CPUS")
        
        st.dataframe(df_r.style.format({"Bruta":"${:,.0f}","Desc":"${:,.0f}","Costo":"${:,.0f}","Margen $":"${:,.0f}","% Mg":"{:.1%}"}), use_container_width=True)
        st.info(f"VALOR TOTAL STOCK: ${float(r_r.get(find_col(data['REPUESTOS'], ['VALOR', 'STOCK']), 0)):,.0f}")
        
        # Gráficos de Repuestos
        g1, g2 = st.columns(2)
        with g1: st.plotly_chart(px.pie(df_r, values="Bruta", names="Canal", hole=0.4, title="Participación por Canal"), use_container_width=True)
        with g2: 
            # Gráfico de Evolución de Facturación (Histórico)
            hist_r = get_hist_df(data['REPUESTOS'])
            col_obj_r = find_col(data['REPUESTOS'], ['OBJ', 'FACT'])
            if not hist_r.empty:
                st.plotly_chart(px.bar(hist_r, x='Mes', y=col_obj_r, title="Histórico Objetivos Repuestos"), use_container_width=True)

    with tab4:
        st.header("Chapa y Pintura")
        # Evolución Paños
        hist_cj = get_hist_df(data['CyP JUJUY'])
        c_pan = find_col(data['CyP JUJUY'], ['PAÑOS', 'PROP'])
        c_obj_p = find_col(data['CyP JUJUY'], ['OBJ', 'PAÑO'])
        
        if not hist_cj.empty:
             st.plotly_chart(px.line(hist_cj, x='Mes', y=[c_pan, c_obj_p], title="Evolución Paños Jujuy vs Objetivo", markers=True), use_container_width=True)
        
        # Cuadros de Sedes (abajo del gráfico como pediste o viceversa, aquí los dejo para completar la vista)
        cp1, cp2 = st.columns(2)
        for i, (nom, row, sh) in enumerate([('Jujuy', cj_r, 'CyP JUJUY'), ('Salta', cs_r, 'CyP SALTA')]):
            r_p = row.get(find_col(data[sh], ['PAÑOS', 'PROP']), 0)
            o_p = row.get(find_col(data[sh], ['OBJ', 'PAÑO']), 1)
            p_p = (r_p/d_t)*d_h if d_t > 0 else 0; alc_p = p_p/o_p if o_p>0 else 0
            color_p = "#dc3545" if alc_p < 0.90 else ("#ffc107" if alc_p < 0.95 else "#28a745")
            with (cp1 if i==0 else cp2):
                 st.markdown(f'<div style="border: 1px solid #e0e0e0; padding: 20px; border-radius: 10px; background-color: white;"><p style="font-weight:bold;">Sede {nom} - Paños</p><h2 style="color:#333;">{r_p:,.0f} <span style="font-size: 14px; color: #999;">/ Obj: {o_p:,.0f}</span></h2><p style="color: {color_p}; font-weight: bold;">↑ Proy: {p_p:,.0f} ({alc_p:.1%})</p></div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error técnico: {e}")
