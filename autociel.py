import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Grupo CENOA - Gestión Posventa", layout="wide")

# --- ESTILO CSS (Compacto) ---
st.markdown("""<style>
    .main { background-color: #f4f7f9; }
    .portada-container { background: linear-gradient(90deg, #00235d 0%, #004080 100%); color: white; padding: 1.5rem; border-radius: 12px; text-align: center; margin-bottom: 1.5rem; }
    
    /* KPI CARD: Más compacto */
    .kpi-card { 
        background-color: white; 
        border: 1px solid #e0e0e0; 
        padding: 15px; 
        border-radius: 10px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); 
        margin-bottom: 10px; 
        min-height: 160px; /* Reducido de 240px */
    }
    
    .kpi-card h2 { font-size: 1.8rem; margin: 5px 0; color: #00235d; }
    .kpi-card p { font-size: 0.85rem; margin: 0; }
    
    .metric-card { background-color: white; border: 1px solid #eee; padding: 12px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); text-align: center; height: 100%; display: flex; flex-direction: column; justify-content: center; min-height: 110px; }
    
    .stTabs [aria-selected="true"] { background-color: #00235d !important; color: white !important; font-weight: bold; }
    h3 { color: #00235d; font-size: 1.2rem; margin-top: 15px; margin-bottom: 10px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
    
    .cyp-detail { background-color: #f8f9fa; padding: 10px; border-radius: 6px; font-size: 0.85rem; margin-top: 8px; border-left: 4px solid #00235d; line-height: 1.4; }
    .cyp-header { font-weight: bold; color: #00235d; font-size: 0.9rem; margin-bottom: 3px; display: block; }
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
            # LIMPIEZA INCLUYENDO Ñ -> N
            df.columns = [
                c.strip().upper()
                .replace(".", "")
                .replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
                .replace("Ñ", "N") 
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
        for h in data:
            col_f = find_col(data[h], ["FECHA"]) or data[h].columns[0]
            data[h]['Fecha_dt'] = pd.to_datetime(data[h][col_f], dayfirst=True, errors='coerce')
            data[h]['Mes'] = data[h]['Fecha_dt'].dt.month
            data[h]['Año'] = data[h]['Fecha_dt'].dt.year

        canales_repuestos = ['MOSTRADOR', 'TALLER', 'INTERNA', 'GAR', 'CYP', 'MAYORISTA', 'SEGUROS']

        with st.sidebar:
            st.header("Filtros")
            años_disp = sorted([int(a) for a in data['CALENDARIO']['Año'].unique() if a > 0], reverse=True)
            año_sel = st.selectbox("📅 Año", años_disp)
            
            meses_nom = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
            df_year = data['CALENDARIO'][data['CALENDARIO']['Año'] == año_sel]
            meses_disp = sorted(df_year['Mes'].unique(), reverse=True)
            mes_sel = st.selectbox("📅 Mes", meses_disp, format_func=lambda x: meses_nom.get(x, "N/A"))

        def get_row(df):
            res = df[(df['Año'] == año_sel) & (df['Mes'] == mes_sel)].sort_values('Fecha_dt')
            return res.iloc[-1] if not res.empty else pd.Series(dtype='object')

        c_r = get_row(data['CALENDARIO'])
        s_r = get_row(data['SERVICIOS'])
        r_r = get_row(data['REPUESTOS'])
        t_r = get_row(data['TALLER'])
        cj_r = get_row(data['CyP JUJUY'])
        cs_r = get_row(data['CyP SALTA'])

        col_trans = find_col(data['CALENDARIO'], ["TRANS"]) 
        col_hab = find_col(data['CALENDARIO'], ["HAB"])
        d_t = float(c_r.get(col_trans, 0))
        d_h = float(c_r.get(col_hab, 22))
        
        hoy = datetime.now()
        if (año_sel < hoy.year) or (año_sel == hoy.year and mes_sel < hoy.month):
             if d_t < d_h: d_t = d_h

        prog_t = d_t / d_h if d_h > 0 else 0
        prog_t = min(prog_t, 1.0)

        # DATA PREPARATION HISTORICO (CON CORRECCIÓN DE COLUMNAS VACÍAS)
        def get_hist_data(sheet_name):
            df = data[sheet_name]
            df = df[df['Año'] == año_sel].sort_values('Mes')
            df = df.groupby('Mes').last().reset_index()
            df['NombreMes'] = df['Mes'].map(meses_nom)
            return df

        h_cal = get_hist_data('CALENDARIO')
        h_ser = get_hist_data('SERVICIOS')
        h_rep = get_hist_data('REPUESTOS')
        h_tal = get_hist_data('TALLER')
        h_cyp_j = get_hist_data('CyP JUJUY')
        h_cyp_s = get_hist_data('CyP SALTA')

        # PORTADA
        st.markdown(f'<div class="portada-container"><h1>Autociel - Tablero Posventa</h1><h3 style="margin:0; color:white;">📅 {meses_nom.get(mes_sel)} {año_sel}</h3><div style="margin-top:10px; font-size: 1.2rem;">Avance: <b>{d_t:g}</b> de <b>{d_h:g}</b> días hábiles ({prog_t:.1%})</div><div style="background: rgba(255,255,255,0.2); height: 8px; border-radius: 4px; width: 50%; margin: 10px auto;"><div style="background: #fff; width: {prog_t*100}%; height: 100%; border-radius: 4px;"></div></div></div>', unsafe_allow_html=True)

        tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏠 Objetivos", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura", "📈 Histórico"])

        # --- HELPERS VISUALES (HTML COMPACTO) ---
        def render_kpi_card(title, real, obj_mes, is_currency=True, unit=""):
            obj_parcial = obj_mes * prog_t
            proy = (real / d_t) * d_h if d_t > 0 else 0
            cumpl_proy = proy / obj_mes if obj_mes > 0 else 0
            fmt = "${:,.0f}" if is_currency else "{:,.0f}"
            if unit: fmt += f" {unit}"
            color = "#dc3545" if cumpl_proy < 0.90 else ("#ffc107" if cumpl_proy < 0.98 else "#28a745")
            icon = "✅" if real >= obj_parcial else "🔻"
            cumpl_parcial_pct = real / obj_parcial if obj_parcial > 0 else 0

            html = '<div class="kpi-card">'
            html += f'<p style="font-weight:bold; color:#666; margin-bottom:5px;">{title}</p>'
            html += f'<h2>{fmt.format(real)}</h2>'
            html += f'<p style="font-size:0.8rem; color:#666; margin-top:2px;">vs Obj. Parcial: <b>{fmt.format(obj_parcial)}</b> <span style="color:{"#28a745" if real >= obj_parcial else "#dc3545"}">({cumpl_parcial_pct:.1%})</span> {icon}</p>'
            html += '<hr style="margin:8px 0; border:0; border-top:1px solid #eee;">'
            html += f'<div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:3px;"><span>Obj. Mes:</span><b>{fmt.format(obj_mes)}</b></div>'
            html += f'<div style="display:flex; justify-content:space-between; font-size:0.8rem; color:{color}; font-weight:bold;"><span>Proyección:</span><span>{fmt.format(proy)} ({cumpl_proy:.1%})</span></div>'
            html += f'<div style="margin-top:8px;"><div style="width:100%; background:#e0e0e0; height:6px; border-radius:10px;"><div style="width:{min(cumpl_proy*100, 100)}%; background:{color}; height:6px; border-radius:10px;"></div></div></div>'
            html += '</div>'
            return html

        def render_kpi_small(title, val, target=None, format_str="{:.1%}"):
            subtext_html = "<div style='height:20px;'></div>"
            if target is not None:
                delta = val - target
                color = "#28a745" if delta >= 0 else "#dc3545"
                icon = "▲" if delta >= 0 else "▼"
                subtext_html = f"<div style='margin-top:6px; display:flex; justify-content:center; align-items:center; gap:6px; font-size:0.75rem;'><span style='color:#888;'>Obj: {format_str.format(target)}</span><span style='color:{color}; font-weight:bold; background-color:{color}15; padding:1px 5px; border-radius:4px;'>{icon} {format_str.format(abs(delta))}</span></div>"
            
            html = '<div class="metric-card">'
            html += f'<p style="color:#666; font-size:0.85rem; margin-bottom:4px;">{title}</p>'
            html += f'<h3 style="color:#00235d; margin:0; font-size:1.4rem;">{format_str.format(val)}</h3>'
            html += subtext_html
            html += '</div>'
            return html

        # --- TAB 1: OBJETIVOS ---
        with tab1:
            st.markdown("### 🎯 Control de Objetivos General")
            cols = st.columns(4)
            c_mo = [find_col(data['SERVICIOS'], ["MO", k], exclude_keywords=["OBJ"]) for k in ["CLI", "GAR", "TER"]]
            real_mo = sum([s_r.get(c, 0) for c in c_mo if c])
            real_rep = sum([r_r.get(find_col(data['REPUESTOS'], ["VENTA", c], exclude_keywords=["OBJ"]), 0) for c in canales_repuestos])
            
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

        with tab2:
            st.markdown("### 🛠️ Performance de Servicios")
            col_main, col_breakdown = st.columns([1, 2])
            real_mo_total = sum([s_r.get(c, 0) for c in c_mo if c])
            obj_mo_total = s_r.get(find_col(data['SERVICIOS'], ["OBJ", "MO"]), 1)
            with col_main: st.markdown(render_kpi_card("Facturación M.O. Total", real_mo_total, obj_mo_total), unsafe_allow_html=True)
            with col_breakdown:
                mo_cli = s_r.get(find_col(data['SERVICIOS'], ["MO", "CLI"], exclude_keywords=["OBJ"]), 0)
                mo_gar = s_r.get(find_col(data['SERVICIOS'], ["MO", "GAR"], exclude_keywords=["OBJ"]), 0)
                mo_int = s_r.get(find_col(data['SERVICIOS'], ["MO", "INT"], exclude_keywords=["OBJ"]), 0)
                mo_ter = s_r.get(find_col(data['SERVICIOS'], ["MO", "TER"], exclude_keywords=["OBJ"]), 0)
                df_mo = pd.DataFrame({"Cargo": ["Cliente", "Garantía", "Interno", "Terceros"], "Facturación": [mo_cli, mo_gar, mo_int, mo_ter]})
                fig_mo = px.bar(df_mo, x="Facturación", y="Cargo", orientation='h', text_auto='.2s', title="Desglose por Cargo", color="Cargo", color_discrete_sequence=["#00235d", "#28a745", "#ffc107", "#17a2b8"])
                fig_mo.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=250)
                st.plotly_chart(fig_mo, use_container_width=True)

            st.markdown("---")
            st.markdown("### ⚙️ Indicadores de Taller")
            ht_cc = t_r.get(find_col(data['TALLER'], ["TRAB", "CC"]), 0)
            ht_cg = t_r.get(find_col(data['TALLER'], ["TRAB", "CG"]), 0)
            ht_ci = t_r.get(find_col(data['TALLER'], ["TRAB", "CI"]), 0)
            hf_cc = t_r.get(find_col(data['TALLER'], ["FACT", "CC"]), 0)
            hf_cg = t_r.get(find_col(data['TALLER'], ["FACT", "CG"]), 0)
            hf_ci = t_r.get(find_col(data['TALLER'], ["FACT", "CI"]), 0)
            ef_cc = hf_cc / ht_cc if ht_cc > 0 else 0
            ef_cg = hf_cg / ht_cg if ht_cg > 0 else 0
            ef_ci = hf_ci / ht_ci if ht_ci > 0 else 0
            ef_gl = (hf_cc+hf_cg+hf_ci) / (ht_cc+ht_cg+ht_ci) if (ht_cc+ht_cg+ht_ci) > 0 else 0
            hs_disp = t_r.get(find_col(data['TALLER'], ["DISPONIBLES", "REAL"]), 0)
            col_tecs = find_col(data['TALLER'], ["TECNICOS"], exclude_keywords=["PROD"])
            cant_tecs = t_r.get(col_tecs, 6)
            if cant_tecs == 0: cant_tecs = 6
            hs_teoricas = cant_tecs * 8 * d_t 
            presencia = hs_disp / hs_teoricas if hs_teoricas > 0 else 0
            ocup = (ht_cc+ht_cg+ht_ci) / hs_disp if hs_disp > 0 else 0
            prod = t_r.get(find_col(data['TALLER'], ["PRODUCTIVIDAD", "TALLER"]), 0)
            if prod > 2: prod /= 100

            e1, e2, e3, e4 = st.columns(4)
            with e1: st.markdown(render_kpi_small("Eficiencia Cargo Cliente", ef_cc, 1.0), unsafe_allow_html=True)
            with e2: st.markdown(render_kpi_small("Eficiencia Garantía", ef_cg, 1.0), unsafe_allow_html=True)
            with e3: st.markdown(render_kpi_small("Eficiencia Interna", ef_ci, 0.20), unsafe_allow_html=True)
            with e4: st.markdown(render_kpi_small("Eficiencia Global", ef_gl, 0.85), unsafe_allow_html=True)

            u1, u2, u3 = st.columns(3)
            with u1: st.markdown(render_kpi_small("Grado de Presencia", presencia, 0.95), unsafe_allow_html=True)
            with u2: st.markdown(render_kpi_small("Grado de Ocupación", ocup, 0.95), unsafe_allow_html=True)
            with u3: st.markdown(render_kpi_small("Productividad", prod, 0.95), unsafe_allow_html=True)

            st.markdown("#### Distribución de Horas")
            g1, g2 = st.columns(2)
            with g1: st.plotly_chart(px.pie(values=[ht_cc, ht_cg, ht_ci], names=["CC", "CG", "CI"], hole=0.4, title="Hs Trabajadas"), use_container_width=True)
            with g2: st.plotly_chart(px.pie(values=[hf_cc, hf_cg, hf_ci], names=["CC", "CG", "CI"], hole=0.4, title="Hs Facturadas"), use_container_width=True)

        with tab3:
            st.markdown("### 📦 Gestión de Repuestos")
            detalles = []
            for c in canales_repuestos:
                v_col = find_col(data['REPUESTOS'], ["VENTA", c], exclude_keywords=["OBJ"])
                if v_col:
                    vb = r_r.get(v_col, 0)
                    d = r_r.get(find_col(data['REPUESTOS'], ["DESC", c]), 0)
                    cost = r_r.get(find_col(data['REPUESTOS'], ["COSTO", c]), 0)
                    vn = vb - d
                    ut = vn - cost
                    detalles.append({"Canal": c, "Venta Bruta": vb, "Desc.": d, "Venta Neta": vn, "Costo": cost, "Utilidad $": ut, "Margen %": (ut/vn if vn>0 else 0)})
            df_r = pd.DataFrame(detalles)
            vta_total_bruta = df_r['Venta Bruta'].sum() if not df_r.empty else 0
            obj_rep_total = r_r.get(find_col(data['REPUESTOS'], ["OBJ", "FACT"]), 1)
            
            c_main, c_kpis = st.columns([1, 3])
            with c_main: st.markdown(render_kpi_card("Facturación Total (Bruta)", vta_total_bruta, obj_rep_total), unsafe_allow_html=True)
            with c_kpis:
                r2, r3, r4 = st.columns(3)
                util_total = df_r['Utilidad $'].sum() if not df_r.empty else 0
                vta_total_neta = df_r['Venta Neta'].sum() if not df_r.empty else 0
                mg_total = util_total / vta_total_neta if vta_total_neta > 0 else 0
                real_cpus = s_r.get(find_col(data['SERVICIOS'], ["CPUS"], exclude_keywords=["OBJ"]), 0)
                div = real_cpus if real_cpus > 0 else 1
                v_taller_neta = df_r.loc[df_r['Canal'].isin(['TALLER', 'GAR', 'CYP']), 'Venta Neta'].sum() if not df_r.empty else 0
                tp_rep = v_taller_neta / div
                with r2: st.markdown(render_kpi_small("Utilidad Total", util_total, None, "${:,.0f}"), unsafe_allow_html=True)
                with r3: st.markdown(render_kpi_small("Margen Global", mg_total, None, "{:.1%}"), unsafe_allow_html=True)
                with r4: st.markdown(render_kpi_small("Ticket Promedio", tp_rep, None, "${:,.0f}"), unsafe_allow_html=True)

            st.markdown("#### 📋 Detalle por Canal")
            if not df_r.empty:
                t_vb = df_r['Venta Bruta'].sum()
                t_desc = df_r['Desc.'].sum()
                t_vn = df_r['Venta Neta'].sum()
                t_cost = df_r['Costo'].sum()
                t_ut = df_r['Utilidad $'].sum()
                t_mg = t_ut / t_vn if t_vn != 0 else 0
                df_show = pd.concat([df_r, pd.DataFrame([{"Canal": "TOTAL", "Venta Bruta": t_vb, "Desc.": t_desc, "Venta Neta": t_vn, "Costo": t_cost, "Utilidad $": t_ut, "Margen %": t_mg}])], ignore_index=True)
                st.dataframe(df_show.style.format({"Venta Bruta": "${:,.0f}", "Desc.": "${:,.0f}", "Venta Neta": "${:,.0f}", "Costo": "${:,.0f}", "Utilidad $": "${:,.0f}", "Margen %": "{:.1%}"}), use_container_width=True, hide_index=True)
            
            c1, c2 = st.columns(2)
            with c1: 
                if not df_r.empty: st.plotly_chart(px.pie(df_r, values="Venta Bruta", names="Canal", hole=0.4, title="Participación (Venta Bruta)"), use_container_width=True)
            with c2:
                val_stock = float(r_r.get(find_col(data['REPUESTOS'], ["VALOR", "STOCK"]), 0))
                p_vivo = float(r_r.get(find_col(data['REPUESTOS'], ["VIVO"]), 0))
                p_obs = float(r_r.get(find_col(data['REPUESTOS'], ["OBSOLETO"]), 0))
                p_muerto = float(r_r.get(find_col(data['REPUESTOS'], ["MUERTO"]), 0))
                f = 1 if p_vivo <= 1 else 100
                df_s = pd.DataFrame({"Estado": ["Vivo", "Obsoleto", "Muerto"], "Valor": [val_stock*(p_vivo/f), val_stock*(p_obs/f), val_stock*(p_muerto/f)]})
                st.plotly_chart(px.pie(df_s, values="Valor", names="Estado", hole=0.4, title="Composición de Stock", color="Estado", color_discrete_map={"Vivo": "#28a745", "Obsoleto": "#ffc107", "Muerto": "#dc3545"}), use_container_width=True)
                st.markdown(f"<div style='text-align:center; background:#f8f9fa; padding:10px; border-radius:8px; border:1px solid #eee;'>💰 <b>Valor Total Stock:</b> ${val_stock:,.0f}</div>", unsafe_allow_html=True)

        with tab4:
            st.markdown("### 🎨 Chapa y Pintura")
            # DATOS JUJUY
            j_f_p = cj_r.get(find_col(data['CyP JUJUY'], ['MO', 'PUR']), 0)
            j_f_t = cj_r.get(find_col(data['CyP JUJUY'], ['MO', 'TER']), 0)
            j_total_fact = j_f_p + j_f_t
            j_obj_fact = cj_r.get(find_col(data['CyP JUJUY'], ["OBJ", "FACT"]), 1)
            j_col_panos = find_col(data['CyP JUJUY'], ['PANOS'], exclude_keywords=['TER', 'OBJ', 'PRE'])
            j_panos_prop = cj_r.get(j_col_panos, 0)
            j_obj_panos = cj_r.get(find_col(data['CyP JUJUY'], ['OBJ', 'PANOS']), 1)
            j_cant_tec = cj_r.get(find_col(data['CyP JUJUY'], ['TECNICO'], exclude_keywords=['PRODUCTIVIDAD']), 1)
            j_ratio = j_panos_prop / j_cant_tec if j_cant_tec > 0 else 0
            j_panos_ter = cj_r.get(find_col(data['CyP JUJUY'], ['PANOS', 'TER']), 0)
            j_c_ter = cj_r.get(find_col(data['CyP JUJUY'], ['COSTO', 'TER']), 0)
            j_m_ter = j_f_t - j_c_ter
            j_mg_ter_pct = j_m_ter/j_f_t if j_f_t > 0 else 0
            
            # DATOS SALTA
            s_f_p = cs_r.get(find_col(data['CyP SALTA'], ['MO', 'PUR']), 0)
            s_f_t = cs_r.get(find_col(data['CyP SALTA'], ['MO', 'TER']), 0)
            s_f_r = cs_r.get(find_col(data['CyP SALTA'], ['FACT', 'REP']), 0)
            s_total_fact = s_f_p + s_f_t + s_f_r
            s_obj_fact = cs_r.get(find_col(data['CyP SALTA'], ["OBJ", "FACT"]), 1)
            s_panos_prop = cs_r.get(find_col(data['CyP SALTA'], ['PANOS'], exclude_keywords=['TER', 'OBJ', 'PRE']), 0)
            s_obj_panos = cs_r.get(find_col(data['CyP SALTA'], ['OBJ', 'PANOS']), 1)
            s_cant_tec = cs_r.get(find_col(data['CyP SALTA'], ['TECNICO'], exclude_keywords=['PRODUCTIVIDAD']), 1)
            s_ratio = s_panos_prop / s_cant_tec if s_cant_tec > 0 else 0
            s_panos_ter = cs_r.get(find_col(data['CyP SALTA'], ['PANOS', 'TER']), 0)
            s_c_ter = cs_r.get(find_col(data['CyP SALTA'], ['COSTO', 'TER']), 0)
            s_m_ter = s_f_t - s_c_ter
            s_mg_ter_pct = s_m_ter/s_f_t if s_f_t > 0 else 0
            s_c_rep = cs_r.get(find_col(data['CyP SALTA'], ['COSTO', 'REP']), 0)
            s_m_rep = s_f_r - s_c_rep
            s_mg_rep_pct = s_m_rep/s_f_r if s_f_r > 0 else 0

            c_jujuy, c_salta = st.columns(2)
            with c_jujuy:
                st.subheader("Sede Jujuy")
                st.markdown(render_kpi_card("Facturación Total Jujuy", j_total_fact, j_obj_fact), unsafe_allow_html=True)
                st.markdown(render_kpi_card("Paños Propios", j_panos_prop, j_obj_panos, is_currency=False, unit="u"), unsafe_allow_html=True)
                st.markdown(render_kpi_small("Promedio Paños por Técnico", j_ratio, None, "{:.1f}"), unsafe_allow_html=True)
                html_ter_j = f'<div class="cyp-detail"><span class="cyp-header">👨‍🔧 Gestión Terceros</span>Cantidad Paños: <b>{j_panos_ter:,.0f}</b><br>Facturación: ${j_f_t:,.0f}<br>Costo: ${j_c_ter:,.0f}<br>Margen: <b>${j_m_ter:,.0f}</b> ({j_mg_ter_pct:.1%})</div>'
                st.markdown(html_ter_j, unsafe_allow_html=True)
            with c_salta:
                st.subheader("Sede Salta")
                st.markdown(render_kpi_card("Facturación Total Salta", s_total_fact, s_obj_fact), unsafe_allow_html=True)
                st.markdown(render_kpi_card("Paños Propios", s_panos_prop, s_obj_panos, is_currency=False, unit="u"), unsafe_allow_html=True)
                st.markdown(render_kpi_small("Promedio Paños por Técnico", s_ratio, None, "{:.1f}"), unsafe_allow_html=True)
                html_ter_s = f'<div class="cyp-detail"><span class="cyp-header">👨‍🔧 Gestión Terceros</span>Cantidad Paños: <b>{s_panos_ter:,.0f}</b><br>Facturación: ${s_f_t:,.0f}<br>Costo: ${s_c_ter:,.0f}<br>Margen: <b>${s_m_ter:,.0f}</b> ({s_mg_ter_pct:.1%})</div>'
                st.markdown(html_ter_s, unsafe_allow_html=True)
                if s_f_r > 0: st.markdown(f'<div class="cyp-detail" style="border-left-color: #28a745;"><span class="cyp-header" style="color:#28a745">📦 Repuestos Taller</span>Facturación: ${s_f_r:,.0f}<br>Costo: ${s_c_rep:,.0f}<br>Margen: <b>${s_m_rep:,.0f}</b> ({s_mg_rep_pct:.1%})</div>', unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("#### Composición Facturación")
            g_jujuy, g_salta = st.columns(2)
            with g_jujuy: st.plotly_chart(px.pie(values=[j_f_p, j_f_t], names=["MO Pura", "Terceros"], hole=0.4, color_discrete_sequence=["#00235d", "#00A8E8"]), use_container_width=True)
            with g_salta: 
                vals_s, nams_s = [s_f_p, s_f_t], ["MO Pura", "Terceros"]
                if s_f_r > 0: vals_s.append(s_f_r); nams_s.append("Repuestos")
                st.plotly_chart(px.pie(values=vals_s, names=nams_s, hole=0.4, color_discrete_sequence=["#00235d", "#00A8E8", "#28a745"]), use_container_width=True)

        with tab5:
            st.markdown(f"### 📈 Evolución Anual {año_sel}")
            
            st.markdown("#### 🛠️ Servicios: Capacidad y Eficiencia")
            h_tal['Hs Disponibles'] = h_tal[find_col(h_tal, ["DISPONIBLES", "REAL"])]
            
            # FIX: Filtrar columnas vacías para evitar error "[''] not in index"
            cols_hs_fact = [find_col(h_tal, ["FACT", k]) for k in ["CC", "CG", "CI"]]
            cols_hs_fact = [c for c in cols_hs_fact if c] # Filter empty
            if cols_hs_fact:
                h_tal['Hs Vendidas'] = h_tal[cols_hs_fact].sum(axis=1)
            else:
                h_tal['Hs Vendidas'] = 0

            df_hs = pd.merge(h_tal[['Mes', 'NombreMes', 'Hs Disponibles', 'Hs Vendidas']], h_ser[['Mes']], on='Mes')
            
            fig_hs = go.Figure()
            fig_hs.add_trace(go.Bar(x=df_hs['NombreMes'], y=df_hs['Hs Vendidas'], name='Hs Vendidas', marker_color='#00235d'))
            fig_hs.add_trace(go.Scatter(x=df_hs['NombreMes'], y=df_hs['Hs Disponibles'], name='Hs Disponibles', mode='lines+markers', line=dict(color='#ffc107', width=3)))
            fig_hs.update_layout(title="Hs Vendidas vs Capacidad", height=350)
            st.plotly_chart(fig_hs, use_container_width=True)

            col_prod = find_col(h_tal, ["PRODUCTIVIDAD", "TALLER"])
            if col_prod:
                h_tal['Productividad'] = h_tal[col_prod].apply(lambda x: x/100 if x > 2 else x)
            else:
                h_tal['Productividad'] = 0
            
            cols_trab = [find_col(h_tal, ["TRAB", k]) for k in ["CC", "CG", "CI"]]
            cols_trab = [c for c in cols_trab if c]
            if cols_trab:
                h_tal['Hs Trabajadas'] = h_tal[cols_trab].sum(axis=1)
                h_tal['Eficiencia Global'] = h_tal.apply(lambda row: row['Hs Vendidas'] / row['Hs Trabajadas'] if row['Hs Trabajadas'] > 0 else 0, axis=1)
            else:
                h_tal['Eficiencia Global'] = 0
            
            fig_efi = go.Figure()
            fig_efi.add_trace(go.Scatter(x=h_tal['NombreMes'], y=h_tal['Eficiencia Global'], name='Efic. Global', mode='lines+markers', line=dict(color='#28a745')))
            fig_efi.add_trace(go.Scatter(x=h_tal['NombreMes'], y=h_tal['Productividad'], name='Productividad', mode='lines+markers', line=dict(color='#17a2b8', dash='dot')))
            fig_efi.update_layout(title="Evolución Eficiencia y Productividad", yaxis_tickformat='.0%', height=300)
            st.plotly_chart(fig_efi, use_container_width=True)

            c_h1, c_h2 = st.columns(2)
            col_cpus = find_col(h_ser, ["CPUS"], exclude_keywords=["OBJ"])
            if col_cpus:
                fig_cpus = px.bar(h_ser, x="NombreMes", y=col_cpus, title="Entradas de Taller (CPUS)", color_discrete_sequence=['#00235d'])
                c_h1.plotly_chart(fig_cpus, use_container_width=True)
                
                h_ser_tal = pd.merge(h_ser, h_tal, on="Mes")
                h_ser_tal['Ticket Hs'] = h_ser_tal.apply(lambda row: row['Hs Vendidas'] / row[col_cpus] if row[col_cpus] > 0 else 0, axis=1)
                fig_tick = px.bar(h_ser_tal, x="NombreMes_x", y="Ticket Hs", title="Ticket Promedio (Horas)", color_discrete_sequence=['#6c757d'])
                c_h2.plotly_chart(fig_tick, use_container_width=True)

            st.markdown("---")
            st.markdown("#### 📦 Repuestos: Salud de Stock y Canales")
            col_vivo = find_col(h_rep, ["VIVO"])
            col_obs = find_col(h_rep, ["OBSOLETO"])
            col_muerto = find_col(h_rep, ["MUERTO"])
            
            fig_stk = go.Figure()
            if col_vivo: fig_stk.add_trace(go.Bar(x=h_rep['NombreMes'], y=h_rep[col_vivo], name='Vivo', marker_color='#28a745'))
            if col_obs: fig_stk.add_trace(go.Bar(x=h_rep['NombreMes'], y=h_rep[col_obs], name='Obsoleto', marker_color='#ffc107'))
            if col_muerto: fig_stk.add_trace(go.Bar(x=h_rep['NombreMes'], y=h_rep[col_muerto], name='Muerto', marker_color='#dc3545'))
            fig_stk.update_layout(barmode='stack', title="Composición de Stock (Evolución)", height=350)
            st.plotly_chart(fig_stk, use_container_width=True)

            col_vta_most = find_col(h_rep, ["VENTA", "MOSTRADOR"])
            col_vta_tall = find_col(h_rep, ["VENTA", "TALLER"])
            
            fig_mix = go.Figure()
            if col_vta_most: fig_mix.add_trace(go.Bar(x=h_rep['NombreMes'], y=h_rep[col_vta_most], name='Mostrador', marker_color='#17a2b8'))
            if col_vta_tall: fig_mix.add_trace(go.Bar(x=h_rep['NombreMes'], y=h_rep[col_vta_tall], name='Taller', marker_color='#00235d'))
            fig_mix.update_layout(barmode='group', title="Venta Mostrador vs Taller ($)", height=350)
            st.plotly_chart(fig_mix, use_container_width=True)

            st.markdown("---")
            st.markdown("#### 🎨 Chapa y Pintura: Producción Física")
            h_cyp = pd.merge(h_cyp_j, h_cyp_s, on="Mes", suffixes=('_J', '_S'))
            h_cyp['NombreMes'] = h_cyp['NombreMes_J']
            
            col_pp_j = find_col(h_cyp_j, ['PANOS'], exclude_keywords=['TER', 'OBJ', 'PRE'])
            col_pp_s = find_col(h_cyp_s, ['PANOS'], exclude_keywords=['TER', 'OBJ', 'PRE'])
            val_pp_j = h_cyp[f'{col_pp_j}_J'] if col_pp_j else 0
            val_pp_s = h_cyp[f'{col_pp_s}_S'] if col_pp_s else 0
            h_cyp['Paños Propios Total'] = val_pp_j + val_pp_s
            
            col_pt_j = find_col(h_cyp_j, ['PANOS', 'TER'])
            col_pt_s = find_col(h_cyp_s, ['PANOS', 'TER'])
            val_pt_j = h_cyp[f'{col_pt_j}_J'] if col_pt_j else 0
            val_pt_s = h_cyp[f'{col_pt_s}_S'] if col_pt_s else 0
            h_cyp['Paños Terceros Total'] = val_pt_j + val_pt_s
            
            fig_panos = go.Figure()
            fig_panos.add_trace(go.Bar(x=h_cyp['NombreMes'], y=h_cyp['Paños Propios Total'], name='Propios', marker_color='#00235d'))
            fig_panos.add_trace(go.Bar(x=h_cyp['NombreMes'], y=h_cyp['Paños Terceros Total'], name='Terceros', marker_color='#17a2b8'))
            fig_panos.update_layout(barmode='stack', title="Producción Total de Paños (Jujuy + Salta)", height=350)
            st.plotly_chart(fig_panos, use_container_width=True)
            
            col_tec_j = find_col(h_cyp_j, ['TECNICO'], exclude_keywords=['PRODUCTIVIDAD']) or find_col(h_cyp_j, ['PRODUCTIVOS'])
            col_tec_s = find_col(h_cyp_s, ['TECNICO'], exclude_keywords=['PRODUCTIVIDAD']) or find_col(h_cyp_s, ['PRODUCTIVOS'])
            val_tec_j = h_cyp[f'{col_tec_j}_J'] if col_tec_j else 0
            val_tec_s = h_cyp[f'{col_tec_s}_S'] if col_tec_s else 0
            
            h_cyp['Tecnicos Total'] = val_tec_j + val_tec_s
            h_cyp['Prod Promedio'] = h_cyp.apply(lambda row: row['Paños Propios Total'] / row['Tecnicos Total'] if row['Tecnicos Total'] > 0 else 0, axis=1)
            
            fig_prod_cyp = px.line(h_cyp, x="NombreMes", y="Prod Promedio", title="Paños por Técnico (Promedio Grupo)", markers=True)
            fig_prod_cyp.update_traces(line_color='#28a745', line_width=3)
            st.plotly_chart(fig_prod_cyp, use_container_width=True)

    else:
        st.warning("No se pudieron cargar los datos.")
except Exception as e:
    st.error(f"Error global: {e}")
