import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Grupo CENOA - Gestión Posventa", layout="wide")

# --- ESTILO CSS MEJORADO ---
st.markdown("""<style>
    .main { background-color: #f4f7f9; }
    .portada-container { background: linear-gradient(90deg, #00235d 0%, #004080 100%); color: white; padding: 2rem; border-radius: 15px; text-align: center; margin-bottom: 2rem; }
    
    /* Tarjetas de KPI Principales */
    .kpi-card { 
        background-color: white; 
        border: 1px solid #e0e0e0; 
        padding: 20px; 
        border-radius: 12px; 
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); 
        margin-bottom: 15px; 
        min-height: 240px; 
    }
    
    /* Tarjetas para indicadores secundarios */
    .metric-card {
        background-color: white;
        border: 1px solid #eee;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        text-align: center;
        height: 100%;
    }

    .stTabs [aria-selected="true"] { background-color: #00235d !important; color: white !important; font-weight: bold; }
    h3 { color: #00235d; font-size: 1.3rem; margin-top: 20px; margin-bottom: 15px; }
</style>""", unsafe_allow_html=True)

# --- FUNCIÓN DE BÚSQUEDA ---
def find_col(df, include_keywords, exclude_keywords=[]):
    for col in df.columns:
        col_upper = col.upper()
        if all(k.upper() in col_upper for k in include_keywords):
            if not any(x.upper() in col_upper for x in exclude_keywords):
                return col
    return ""

# --- CARGA DE DATOS ---
@st.cache_data(ttl=60)
def cargar_datos(sheet_id):
    hojas = ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA']
    data_dict = {}
    for h in hojas:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={h.replace(' ', '%20')}"
        try:
            df = pd.read_csv(url, dtype=str).fillna("0")
            # Limpieza de tildes y mayúsculas
            df.columns = [
                c.strip().upper()
                .replace(".", "")
                .replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U") 
                for c in df.columns
            ]
            for col in df.columns:
                if "FECHA" not in col and "CANAL" not in col and "ESTADO" not in col:
                    df[col] = df[col].astype(str).str.replace(r'[\$%\s]', '', regex=True).str.replace(',', '.')
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            data_dict[h] = df
        except Exception as e:
            st.error(f"Error cargando hoja {h}: {e}")
            return None
    return data_dict

ID_SHEET = "1yJgaMR0nEmbKohbT_8Vj627Ma4dURwcQTQcQLPqrFwk"

try:
    data = cargar_datos(ID_SHEET)
    
    if data:
        # Fechas
        for h in data:
            col_f = find_col(data[h], ["FECHA"]) or data[h].columns[0]
            data[h]['Fecha_dt'] = pd.to_datetime(data[h][col_f], dayfirst=True, errors='coerce')
            data[h]['Mes'] = data[h]['Fecha_dt'].dt.month
            data[h]['Año'] = data[h]['Fecha_dt'].dt.year

        # Filtros
        with st.sidebar:
            st.header("Filtros")
            años_disp = sorted([int(a) for a in data['CALENDARIO']['Año'].unique() if a > 0], reverse=True)
            año_sel = st.selectbox("📅 Año", años_disp)
            
            meses_nom = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
            df_year = data['CALENDARIO'][data['CALENDARIO']['Año'] == año_sel]
            meses_disp = sorted(df_year['Mes'].unique(), reverse=True)
            mes_sel = st.selectbox("📅 Mes", meses_disp, format_func=lambda x: meses_nom.get(x, "N/A"))

        # Obtener Fila
        def get_row(df):
            res = df[(df['Año'] == año_sel) & (df['Mes'] == mes_sel)].sort_values('Fecha_dt')
            return res.iloc[-1] if not res.empty else pd.Series(dtype='object')

        c_r = get_row(data['CALENDARIO'])
        s_r = get_row(data['SERVICIOS'])
        r_r = get_row(data['REPUESTOS'])
        t_r = get_row(data['TALLER'])
        cj_r = get_row(data['CyP JUJUY'])
        cs_r = get_row(data['CyP SALTA'])

        # Días
        col_trans = find_col(data['CALENDARIO'], ["TRANS"]) 
        col_hab = find_col(data['CALENDARIO'], ["HAB"])
        d_t = float(c_r.get(col_trans, 0))
        d_h = float(c_r.get(col_hab, 22))
        
        # Ajuste mes cerrado
        hoy = datetime.now()
        if (año_sel < hoy.year) or (año_sel == hoy.year and mes_sel < hoy.month):
             if d_t < d_h: d_t = d_h

        prog_t = d_t / d_h if d_h > 0 else 0
        prog_t = min(prog_t, 1.0)

        # PORTADA
        st.markdown(f"""
        <div class="portada-container">
            <h1>Autociel - Tablero Posventa</h1>
            <h3 style="margin:0; color:white;">📅 {meses_nom.get(mes_sel)} {año_sel}</h3>
            <div style="margin-top:10px; font-size: 1.2rem;">
                Avance: <b>{d_t:g}</b> de <b>{d_h:g}</b> días hábiles ({prog_t:.1%})
            </div>
            <div style="background: rgba(255,255,255,0.2); height: 8px; border-radius: 4px; width: 50%; margin: 10px auto;">
                <div style="background: #fff; width: {prog_t*100}%; height: 100%; border-radius: 4px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        tab1, tab2, tab3, tab4 = st.tabs(["🏠 Objetivos", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura"])

        # --- HELPER PARA TARJETAS HTML ---
        def render_kpi_card(title, real, obj_mes, is_currency=True):
            obj_parcial = obj_mes * prog_t
            proy = (real / d_t) * d_h if d_t > 0 else 0
            
            # Porcentajes
            cumpl_parcial = real / obj_parcial if obj_parcial > 0 else 0
            cumpl_proy = proy / obj_mes if obj_mes > 0 else 0
            
            # Formato
            fmt = "${:,.0f}" if is_currency else "{:,.0f}"
            
            color = "#dc3545" if cumpl_proy < 0.90 else ("#ffc107" if cumpl_proy < 0.98 else "#28a745")
            icon = "✅" if real >= obj_parcial else "🔻"
            
            return f"""
            <div class="kpi-card">
                <p style="font-weight:bold; color:#666; margin-bottom:5px;">{title}</p>
                <h2 style="margin:0; color:#00235d;">{fmt.format(real)}</h2>
                <p style="font-size:0.85rem; color:#666; margin-top:5px;">
                    vs Obj. Parcial: <b>{fmt.format(obj_parcial)}</b> <span style="color:{'#28a745' if real >= obj_parcial else '#dc3545'}">({cumpl_parcial:.1%})</span> {icon}
                </p>
                <hr style="margin:10px 0; border:0; border-top:1px solid #eee;">
                <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:5px;">
                    <span>Obj. Mes:</span><b>{fmt.format(obj_mes)}</b>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:0.85rem; color:{color}; font-weight:bold;">
                    <span>Proyección:</span><span>{fmt.format(proy)} ({cumpl_proy:.1%})</span>
                </div>
                <div style="margin-top:10px;">
                    <div style="width:100%; background:#e0e0e0; height:6px; border-radius:10px;">
                        <div style="width:{min(cumpl_proy*100, 100)}%; background:{color}; height:6px; border-radius:10px;"></div>
                    </div>
                </div>
            </div>
            """

        def render_metric_simple(title, val, format_str="{:.1%}", subtext=""):
             return f"""
            <div class="metric-card">
                <p style="color:#666; font-size:0.9rem; margin-bottom:5px;">{title}</p>
                <h3 style="color:#00235d; margin:0;">{format_str.format(val)}</h3>
                <p style="font-size:0.8rem; color:#888; margin-top:5px;">{subtext}</p>
            </div>
            """

        # --- TAB 1: OBJETIVOS GENERALES ---
        with tab1:
            st.markdown("### 🎯 Control de Objetivos")
            cols = st.columns(4)
            
            # Datos
            c_mo = [find_col(data['SERVICIOS'], ["MO", k], exclude_keywords=["OBJ"]) for k in ["CLI", "GAR", "TER"]]
            real_mo = sum([s_r.get(c, 0) for c in c_mo if c])
            canales = ['MOSTRADOR', 'TALLER', 'INTERNA', 'GAR', 'CYP', 'MAYORISTA', 'SEGUROS']
            real_rep = sum([r_r.get(find_col(data['REPUESTOS'], ["VENTA", c], exclude_keywords=["OBJ"]), 0) for c in canales])
            
            def get_cyp_total(row, df_nom):
                mo = row.get(find_col(data[df_nom], ["MO", "PUR"]), 0) + row.get(find_col(data[df_nom], ["MO", "TER"]), 0)
                rep = row.get(find_col(data[df_nom], ["FACT", "REP"]), 0) 
                return mo + rep

            metas = [
                ("M.O. Servicios", real_mo, s_r.get(find_col(data['SERVICIOS'], ["OBJ", "MO"]), 1)),
                ("Repuestos", real_rep, r_r.get(find_col(data['REPUESTOS'], ["OBJ", "FACT"]), 1)),
                ("CyP Jujuy", get_cyp_total(cj_r, 'CyP JUJUY'), cj_r.get(find_col(data['CyP JUJUY'], ["OBJ", "FACT"]), 1)),
                ("CyP Salta", get_cyp_total(cs_r, 'CyP SALTA'), cs_r.get(find_col(data['CyP SALTA'], ["OBJ", "FACT"]), 1))
            ]

            for i, (tit, real, obj) in enumerate(metas):
                with cols[i]: st.markdown(render_kpi_card(tit, real, obj, True), unsafe_allow_html=True)

        # --- TAB 2: SERVICIOS ---
        with tab2:
            st.markdown("### 🛠️ Performance de Servicios")
            
            # 1. OBJETIVOS TUS Y CPUS (Estilo Tarjeta KPI)
            k1, k2, k3, k4 = st.columns(4)
            
            c_cpus = find_col(data['SERVICIOS'], ["CPUS"], exclude_keywords=["OBJ"])
            c_tus = find_col(data['SERVICIOS'], ["OTROS", "CARGOS"], exclude_keywords=["OBJ"])
            
            real_cpus = s_r.get(c_cpus, 0)
            real_tus = real_cpus + s_r.get(c_tus, 0)
            obj_tus = s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'TUS']), 1)
            obj_cpus = s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'CPUS']), 1)
            
            # Tickets
            div = real_cpus if real_cpus > 0 else 1
            fact_taller = t_r.get(find_col(data['TALLER'], ["FACT", "CC"]), 0) + t_r.get(find_col(data['TALLER'], ["FACT", "CG"]), 0)
            tp_hs = fact_taller / div
            tp_mo = real_mo / div

            with k1: st.markdown(render_kpi_card("TUS Total", real_tus, obj_tus, is_currency=False), unsafe_allow_html=True)
            with k2: st.markdown(render_kpi_card("CPUS Cliente", real_cpus, obj_cpus, is_currency=False), unsafe_allow_html=True)
            with k3: st.markdown(render_metric_simple("Ticket Promedio (Hs)", tp_hs, "{:.2f} hs"), unsafe_allow_html=True)
            with k4: st.markdown(render_metric_simple("Ticket Promedio ($)", tp_mo, "${:,.0f}"), unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("### ⚙️ Indicadores de Taller")
            
            # 2. INDICADORES DE TALLER (En Tarjetas)
            ht_cc = t_r.get(find_col(data['TALLER'], ["TRAB", "CC"]), 0)
            ht_cg = t_r.get(find_col(data['TALLER'], ["TRAB", "CG"]), 0)
            ht_ci = t_r.get(find_col(data['TALLER'], ["TRAB", "CI"]), 0)
            hf_cc = t_r.get(find_col(data['TALLER'], ["FACT", "CC"]), 0)
            hf_cg = t_r.get(find_col(data['TALLER'], ["FACT", "CG"]), 0)
            hf_ci = t_r.get(find_col(data['TALLER'], ["FACT", "CI"]), 0)

            ef_cc = hf_cc / ht_cc if ht_cc > 0 else 0
            ef_cg = hf_cg / ht_cg if ht_cg > 0 else 0
            ef_gl = (hf_cc+hf_cg+hf_ci) / (ht_cc+ht_cg+ht_ci) if (ht_cc+ht_cg+ht_ci) > 0 else 0
            
            hs_disp = t_r.get(find_col(data['TALLER'], ["DISPONIBLES", "REAL"]), 0)
            col_tecs = find_col(data['TALLER'], ["TECNICOS"], exclude_keywords=["PROD"])
            cant_tecs = t_r.get(col_tecs, 6)
            if cant_tecs == 0: cant_tecs = 6
            
            # --- CÁLCULO DE PRESENCIA CORREGIDO (8hs) ---
            hs_teoricas = cant_tecs * 8 * d_t 
            
            presencia = hs_disp / hs_teoricas if hs_teoricas > 0 else 0
            ocup = (ht_cc+ht_cg+ht_ci) / hs_disp if hs_disp > 0 else 0
            prod = t_r.get(find_col(data['TALLER'], ["PRODUCTIVIDAD", "TALLER"]), 0)
            if prod > 2: prod /= 100

            e1, e2, e3, e4, e5, e6 = st.columns(6)
            with e1: st.markdown(render_metric_simple("Eficiencia CC", ef_cc), unsafe_allow_html=True)
            with e2: st.markdown(render_metric_simple("Eficiencia CG", ef_cg), unsafe_allow_html=True)
            with e3: st.markdown(render_metric_simple("Efic. Global", ef_gl), unsafe_allow_html=True)
            with e4: st.markdown(render_metric_simple("Presencia", presencia), unsafe_allow_html=True)
            with e5: st.markdown(render_metric_simple("Ocupación", ocup), unsafe_allow_html=True)
            with e6: st.markdown(render_metric_simple("Productividad", prod), unsafe_allow_html=True)

            # Gráficos de Taller
            g1, g2 = st.columns(2)
            with g1: st.plotly_chart(px.pie(values=[ht_cc, ht_cg, ht_ci], names=["CC", "CG", "CI"], hole=0.4, title="Hs Trabajadas"), use_container_width=True)
            with g2: st.plotly_chart(px.pie(values=[hf_cc, hf_cg, hf_ci], names=["CC", "CG", "CI"], hole=0.4, title="Hs Facturadas"), use_container_width=True)

        # --- TAB 3: REPUESTOS ---
        with tab3:
            st.markdown("### 📦 Gestión de Repuestos")
            
            # Datos
            detalles = []
            for c in canales:
                v_col = find_col(data['REPUESTOS'], ["VENTA", c], exclude_keywords=["OBJ"])
                if v_col:
                    vb = r_r.get(v_col, 0)
                    d = r_r.get(find_col(data['REPUESTOS'], ["DESC", c]), 0)
                    cost = r_r.get(find_col(data['REPUESTOS'], ["COSTO", c]), 0)
                    vn = vb - d
                    ut = vn - cost
                    detalles.append({"Canal": c, "Venta Neta": vn, "Utilidad $": ut})
            df_r = pd.DataFrame(detalles)
            
            vta_total = df_r['Venta Neta'].sum() if not df_r.empty else 0
            obj_rep_total = r_r.get(find_col(data['REPUESTOS'], ["OBJ", "FACT"]), 1)
            
            # 1. Indicador Principal: Objetivo de Facturación (Igual a Tab 1)
            c_main, c_kpis = st.columns([1, 3])
            
            with c_main:
                st.markdown(render_kpi_card("Facturación Repuestos", vta_total, obj_rep_total), unsafe_allow_html=True)
                
            with c_kpis:
                r2, r3, r4 = st.columns(3)
                util_total = df_r['Utilidad $'].sum() if not df_r.empty else 0
                mg_total = util_total / vta_total if vta_total > 0 else 0
                v_taller = df_r.loc[df_r['Canal'].isin(['TALLER', 'GAR', 'CYP']), 'Venta Neta'].sum() if not df_r.empty else 0
                tp_rep = v_taller / div
                
                with r2: st.markdown(render_metric_simple("Utilidad Total", util_total, "${:,.0f}"), unsafe_allow_html=True)
                with r3: st.markdown(render_metric_simple("Margen Global", mg_total, "{:.1%}"), unsafe_allow_html=True)
                with r4: st.markdown(render_metric_simple("Ticket Promedio", tp_rep, "${:,.0f}"), unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            
            # 2. Gráfico Torta Canales
            with c1: 
                if not df_r.empty:
                    st.plotly_chart(px.pie(df_r, values="Venta Neta", names="Canal", hole=0.4, title="Facturación por Canal"), use_container_width=True)
            
            # 3. Gráfico Stock (Rojo Muerto y Total debajo)
            with c2:
                val_stock = float(r_r.get(find_col(data['REPUESTOS'], ["VALOR", "STOCK"]), 0))
                p_vivo = float(r_r.get(find_col(data['REPUESTOS'], ["VIVO"]), 0))
                p_obs = float(r_r.get(find_col(data['REPUESTOS'], ["OBSOLETO"]), 0))
                p_muerto = float(r_r.get(find_col(data['REPUESTOS'], ["MUERTO"]), 0))
                
                f = 1 if p_vivo <= 1 else 100
                df_s = pd.DataFrame({
                    "Estado": ["Vivo", "Obsoleto", "Muerto"], 
                    "Valor": [val_stock*(p_vivo/f), val_stock*(p_obs/f), val_stock*(p_muerto/f)]
                })
                
                # Mapa de color explícito
                color_map = {"Vivo": "#28a745", "Obsoleto": "#ffc107", "Muerto": "#dc3545"}
                
                st.plotly_chart(px.pie(df_s, values="Valor", names="Estado", hole=0.4, title="Composición de Stock", color="Estado", color_discrete_map=color_map), use_container_width=True)
                
                st.markdown(f"<div style='text-align:center; background:#f8f9fa; padding:10px; border-radius:8px; border:1px solid #eee;'>💰 <b>Valor Total Stock:</b> ${val_stock:,.0f}</div>", unsafe_allow_html=True)

        # --- TAB 4: CYP ---
        with tab4:
            st.markdown("### 🎨 Chapa y Pintura")
            cf1, cf2 = st.columns(2)
            def render_cyp(col, nom, row, sh, is_salta):
                with col:
                    st.subheader(f"Sede {nom}")
                    f_p = row.get(find_col(data[sh], ['MO', 'PUR']), 0)
                    f_t = row.get(find_col(data[sh], ['MO', 'TER']), 0)
                    f_r = row.get(find_col(data[sh], ['FACT', 'REP']), 0) if is_salta else 0
                    st.markdown(render_metric_simple(f"Facturación {nom}", f_p+f_t+f_r, "${:,.0f}"), unsafe_allow_html=True)
                    
                    vals = [f_p, f_t]
                    nams = ["MO Pura", "Terceros"]
                    cols_pie = ["#00235d", "#00A8E8"]
                    if f_r > 0:
                        vals.append(f_r); nams.append("Repuestos"); cols_pie.append("#28a745")
                    st.plotly_chart(px.pie(values=vals, names=nams, hole=0.4, color_discrete_sequence=cols_pie), use_container_width=True)

            render_cyp(cf1, 'Jujuy', cj_r, 'CyP JUJUY', False)
            render_cyp(cf2, 'Salta', cs_r, 'CyP SALTA', True)

    else:
        st.warning("No se pudieron cargar los datos.")
except Exception as e:
    st.error(f"Error global: {e}")
