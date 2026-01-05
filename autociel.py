Entendido. He tomado el código "limpio" que me pasaste y le he inyectado las funcionalidades que faltaban (Tickets Promedio, Históricos y selector de Año/Mes) sin romper la estructura visual que ya te gustaba.

Además, he incluido la protección contra el error de la fecha (31/12/2025) para que no vuelva a aparecer.

Aquí tienes el código completo y listo para usar:

Python

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

# --- FUNCIÓN DE BÚSQUEDA INTELIGENTE DE COLUMNAS ---
def find_col(df, keywords):
    """Busca una columna que contenga todas las palabras clave (insensible a mayúsculas/espacios)"""
    for col in df.columns:
        if all(k.upper() in col for k in keywords):
            return col
    return "" # Retorna vacío si no encuentra

# --- CARGA Y NORMALIZACIÓN ---
@st.cache_data(ttl=60)
def cargar_datos(sheet_id):
    hojas = ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA']
    data_dict = {}
    for h in hojas:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={h.replace(' ', '%20')}"
        df = pd.read_csv(url, dtype=str).fillna("0")
        
        # 1. Normalizar nombres de columnas (Mayúsculas y sin puntos)
        df.columns = [c.strip().upper().replace(".", "") for c in df.columns]
        
        # 2. Limpieza Numérica (PROTEGIENDO LAS FECHAS)
        for col in df.columns:
            # Si la columna parece ser una fecha o texto descriptivo, LA SALTAMOS
            if "FECHA" not in col and "CANAL" not in col and "ESTADO" not in col:
                df[col] = df[col].astype(str).str.replace(r'[\$%\s]', '', regex=True).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        data_dict[h] = df
    return data_dict

ID_SHEET = "1yJgaMR0nEmbKohbT_8Vj627Ma4dURwcQTQcQLPqrFwk"

try:
    data = cargar_datos(ID_SHEET)
    
    # Procesamiento de Fechas
    for h in data:
        # Busca la columna fecha (usando 'FECHA' como clave)
        col_f = find_col(data[h], ["FECHA"])
        if not col_f: col_f = data[h].columns[0] # Fallback
        
        data[h]['Fecha_dt'] = pd.to_datetime(data[h][col_f], dayfirst=True, errors='coerce')
        data[h]['Mes'] = data[h]['Fecha_dt'].dt.month
        data[h]['Año'] = data[h]['Fecha_dt'].dt.year

    # --- FILTROS DE AÑO Y MES ---
    # Obtenemos años disponibles de la hoja calendario
    años_disp = sorted([int(a) for a in data['CALENDARIO']['Año'].unique() if a > 0], reverse=True)
    año_sel = st.sidebar.selectbox("📅 Seleccionar Año", años_disp)
    
    meses_nom = {1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic"}
    # Filtramos meses disponibles para ese año
    meses_disp = sorted(data['CALENDARIO'][data['CALENDARIO']['Año'] == año_sel]['Mes'].unique(), reverse=True)
    mes_sel = st.sidebar.selectbox("📅 Seleccionar Mes", meses_disp, format_func=lambda x: meses_nom.get(x, "N/A"))

    # Función para obtener el último dato del mes seleccionado
    def get_mes_data(df):
        res = df[(df['Año'] == año_sel) & (df['Mes'] == mes_sel)]
        return res.sort_values('Fecha_dt').iloc[-1] if not res.empty else df.iloc[-1] # Si no hay datos, evita crash

    c_r, s_r, r_r, t_r = get_mes_data(data['CALENDARIO']), get_mes_data(data['SERVICIOS']), get_mes_data(data['REPUESTOS']), get_mes_data(data['TALLER'])
    cj_r, cs_r = get_mes_data(data['CyP JUJUY']), get_mes_data(data['CyP SALTA'])

    # Cálculo de días
    col_dt = find_col(data['CALENDARIO'], ["DIAS", "TRANS"])
    col_dh = find_col(data['CALENDARIO'], ["DIAS", "HAB"])
    d_t = float(c_r.get(col_dt, 1))
    d_h = float(c_r.get(col_dh, 1))
    prog_t = d_t / d_h if d_h > 0 else 0

    st.markdown(f"""<div class="portada-container"><h1>Autociel - Posventa</h1>
    <p>📅 {meses_nom.get(mes_sel)} {año_sel} | Avance: {d_t:g}/{d_h:g} días ({prog_t:.1%})</p></div>""", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🏠 General", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura"])

    with tab1:
        cols = st.columns(4)
        # Columnas dinámicas para MO
        c_mc, c_mg, c_mt = find_col(data['SERVICIOS'], ["MO", "CLI"]), find_col(data['SERVICIOS'], ["MO", "GAR"]), find_col(data['SERVICIOS'], ["MO", "TER"])
        r_mo = s_r[c_mc] + s_r[c_mg] + s_r[c_mt]
        
        # Repuestos Total (Sumando canales de venta)
        r_rep = sum([r_r[c] for c in r_r.index if "VENTA" in c and "OBJ" not in c])
        
        metas = [
            ("M.O. Servicios", r_mo, s_r.get(find_col(data['SERVICIOS'], ["OBJ", "MO"]), 1)),
            ("Repuestos", r_rep, r_r.get(find_col(data['REPUESTOS'], ["OBJ", "FACT"]), 1)),
            ("CyP Jujuy", cj_r.get(find_col(data['CyP JUJUY'], ["MO", "PUR"]), 0) + cj_r.get(find_col(data['CyP JUJUY'], ["MO", "TER"]), 0), cj_r.get(find_col(data['CyP JUJUY'], ["OBJ", "FACT"]), 1)),
            ("CyP Salta", cs_r.get(find_col(data['CyP SALTA'], ["MO", "PUR"]), 0) + cs_r.get(find_col(data['CyP SALTA'], ["MO", "TER"]), 0) + cs_r.get('FACTREPUESTOS', 0), cs_r.get(find_col(data['CyP SALTA'], ["OBJ", "FACT"]), 1))
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
        st.header("Performance y Tickets")
        k1, k2, k3, k4 = st.columns(4)
        c_cpus = find_col(data['SERVICIOS'], ["CPUS"])
        real_tus = s_r.get(c_cpus, 0) + s_r.get(find_col(data['SERVICIOS'], ["OTROS", "CARGOS"]), 0)
        
        # Proyecciones para TUS y CPUS
        obj_tus = s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'TUS']), 1)
        p_tus = (real_tus/d_t)*d_h if d_t > 0 else 0
        alc_tus = p_tus/obj_tus if obj_tus > 0 else 0
        
        real_cpus = s_r.get(c_cpus, 0)
        obj_cpus = s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'CPUS']), 1)
        p_cpus = (real_cpus/d_t)*d_h if d_t > 0 else 0
        alc_cpus = p_cpus/obj_cpus if obj_cpus > 0 else 0

        # Función auxiliar para mostrar KPI con proyección
        def kpi_card(col, title, real, obj, proy, alc):
            color = "#dc3545" if alc < 0.90 else ("#ffc107" if alc < 0.95 else "#28a745")
            with col:
                st.markdown(f'<div style="border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; background-color: white;">'
                            f'<p style="font-weight:bold; color:#666; font-size:13px;">{title}</p>'
                            f'<h3>{real:,.0f} <span style="font-size:14px; color:#999;">/ {obj:,.0f}</span></h3>'
                            f'<p style="color:{color}; font-weight:bold; margin:0; font-size:14px;">↑ Proy: {proy:,.0f} ({alc:.1%})</p></div>', unsafe_allow_html=True)

        kpi_card(k1, "TUS Total", real_tus, obj_tus, p_tus, alc_tus)
        kpi_card(k2, "CPUS (Cargos Cliente)", real_cpus, obj_cpus, p_cpus, alc_cpus)
        
        # Tickets Promedio
        c_div = real_cpus if real_cpus > 0 else 1
        tp_hs = (t_r.get(find_col(data['TALLER'], ["FACT", "CC"]), 0) + t_r.get(find_col(data['TALLER'], ["FACT", "CG"]), 0)) / c_div
        tp_mo = (s_r.get(c_mc, 0) + s_r.get(c_mg, 0)) / c_div
        
        k3.metric("Ticket Promedio M.O. (Hs)", f"{tp_hs:.2f} hs/CPUS")
        k4.metric("Ticket Promedio M.O. ($)", f"${tp_mo:,.0f}/CPUS")
        
        st.markdown("---")
        # Históricos Servicios (Gráficos)
        hist_s = data['SERVICIOS'][data['SERVICIOS']['Año'] == año_sel].copy().groupby('Mes').last().reset_index()
        if not hist_s.empty:
            # Calculamos Ticket Promedio Histórico
            col_mc_h = find_col(data['SERVICIOS'], ["MO", "CLI"])
            col_mg_h = find_col(data['SERVICIOS'], ["MO", "GAR"])
            col_cpus_h = find_col(data['SERVICIOS'], ["CPUS"])
            hist_s['TP_PESOS'] = (hist_s[col_mc_h] + hist_s[col_mg_h]) / hist_s[col_cpus_h].replace(0,1)
            
            hg1, hg2 = st.columns(2)
            with hg1: st.plotly_chart(px.line(hist_s, x='Mes', y=col_cpus_h, title="Evolución CPUS", markers=True), use_container_width=True)
            with hg2: st.plotly_chart(px.bar(hist_s, x='Mes', y='TP_PESOS', title="Evolución Ticket Promedio ($)", text_auto='.2s'), use_container_width=True)

    with tab3:
        st.header("Repuestos")
        canales_r = ['MOSTRADOR', 'TALLER', 'INTERNA', 'GARANTIA', 'CYP', 'MAYORISTA', 'SEGUROS']
        detalles = []
        for c in canales_r:
            v_col = find_col(data['REPUESTOS'], ["VENTA", c])
            d_col = find_col(data['REPUESTOS'], ["DESC", c])
            c_col = find_col(data['REPUESTOS'], ["COSTO", c])
            vb = r_r.get(v_col, 0)
            d = r_r.get(d_col, 0)
            cost = r_r.get(c_col, 0)
            vn = vb - d; ut = vn - cost
            detalles.append({"Canal": c, "Bruta": vb, "Desc": d, "Costo": cost, "Margen $": ut, "% Mg": (ut/vn if vn>0 else 0)})
        df_r = pd.DataFrame(detalles)
        
        # Métricas Repuestos
        r1, r2, r3, r4 = st.columns(4)
        vbt = df_r['Bruta'].sum()
        mgt = df_r['Margen $'].sum()
        mgp = mgt / (vbt - df_r['Desc'].sum()) if (vbt - df_r['Desc'].sum())>0 else 0
        
        # Ticket Promedio Repuestos: (Taller + Garantia + CyP) / CPUS
        venta_taller = r_r.get(find_col(data['REPUESTOS'], ["VENTA", "TALLER"]), 0)
        venta_gtia = r_r.get(find_col(data['REPUESTOS'], ["VENTA", "GAR"]), 0)
        venta_cyp = r_r.get(find_col(data['REPUESTOS'], ["VENTA", "CYP"]), 0)
        tp_rep = (venta_taller + venta_gtia + venta_cyp) / c_div # c_div es CPUS
        
        r1.metric("Facturación Bruta", f"${vbt:,.0f}")
        r2.metric("Margen Total $", f"${mgt:,.0f}")
        r3.metric("Margen %", f"{mgp:.1%}")
        r4.metric("Ticket Promedio Rep.", f"${tp_rep:,.0f}/CPUS")
        
        st.dataframe(df_r.style.format({"Bruta":"${:,.0f}","Desc":"${:,.0f}","Costo":"${:,.0f}","Margen $":"${:,.0f}","% Mg":"{:.1%}"}), use_container_width=True)
        st.info(f"VALOR TOTAL STOCK: ${float(r_r.get(find_col(data['REPUESTOS'], ['VALOR', 'STOCK']), 0)):,.0f}")
        
        # Histórico Repuestos
        st.markdown("---")
        hist_r = data['REPUESTOS'][data['REPUESTOS']['Año'] == año_sel].copy().groupby('Mes').last().reset_index()
        # Calculamos venta total histórica para comparar con objetivo
        cols_venta = [c for c in hist_r.columns if "VENTA" in c and "OBJ" not in c]
        hist_r['Venta Total'] = hist_r[cols_venta].sum(axis=1)
        st.plotly_chart(px.bar(hist_r, x='Mes', y=['Venta Total', find_col(data['REPUESTOS'],['OBJ','FACT'])], barmode='group', title="Evolución Facturación vs Objetivo"), use_container_width=True)

    with tab4:
        st.header("Chapa y Pintura")
        # Cuadros de Sedes (Mismo código visual que te gustaba)
        cp1, cp2 = st.columns(2)
        for i, (nom, row, sh) in enumerate([('Jujuy', cj_r, 'CyP JUJUY'), ('Salta', cs_r, 'CyP SALTA')]):
            r_p = row.get(find_col(data[sh], ['PAÑOS', 'PROP']), 0)
            o_p = row.get(find_col(data[sh], ['OBJ', 'PAÑO']), 1)
            p_p = (r_p/d_t)*d_h if d_t > 0 else 0; alc_p = p_p/o_p if o_p>0 else 0
            color_p = "#dc3545" if alc_p < 0.90 else ("#ffc107" if alc_p < 0.95 else "#28a745")
            with (cp1 if i==0 else cp2):
                st.markdown(f'<div style="border: 1px solid #e0e0e0; padding: 20px; border-radius: 10px; background-color: white; min-height: 170px;"><p style="font-weight:bold;">Sede {nom} - Paños</p><h1 style="margin: 0; font-size: 42px; color: #333;">{r_p:,.0f} <span style="font-size: 18px; color: #999;">/ Obj: {o_p:,.0f}</span></h1><p style="color: {color_p}; font-weight: bold; font-size: 18px; margin-top: 15px; border-top: 1px solid #eee; padding-top: 10px;">↑ Proyección: {p_p:,.0f} ({alc_p:.1%})</p></div>', unsafe_allow_html=True)
        
        st.markdown("---")
        # Histórico Paños
        hist_cj = data['CyP JUJUY'][data['CyP JUJUY']['Año'] == año_sel].copy().groupby('Mes').last().reset_index()
        col_panos = find_col(data['CyP JUJUY'], ['PAÑOS', 'PROP'])
        col_obj_p = find_col(data['CyP JUJUY'], ['OBJ', 'PAÑO'])
        if not hist_cj.empty:
            st.plotly_chart(px.line(hist_cj, x='Mes', y=[col_panos, col_obj_p], title="Evolución Paños Jujuy vs Objetivo", markers=True), use_container_width=True)

except Exception as e:
    st.error(f"⚠️ Error detectado: {e}")
