import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

st.set_page_config(page_title="Grupo CENOA - Gestión Posventa", layout="wide")

# --- ESTILO CSS ---
st.markdown("""<style>
    .block-container { padding-top: 1rem; padding-bottom: 2rem; }
    .main { background-color: #f4f7f9; }
    
    .portada-container { 
        background: linear-gradient(90deg, #00235d 0%, #004080 100%); 
        color: white; 
        padding: 1rem 1.5rem; 
        border-radius: 10px; 
        margin-bottom: 1rem; 
        display: flex; 
        justify-content: space-between; 
        align-items: center;
        flex-wrap: wrap;
        gap: 15px;
    }
    
    .portada-left h1 { font-size: 1.4rem; margin: 0; line-height: 1.2; }
    .portada-left h3 { font-size: 1rem; margin: 0; color: #cbd5e1; font-weight: normal; }
    .portada-right { text-align: right; min-width: 200px; }
    .portada-right div { font-size: 0.9rem; margin-bottom: 5px; }
    
    .kpi-card { 
        background-color: white; 
        border: 1px solid #e0e0e0; 
        padding: 12px 15px; 
        border-radius: 8px; 
        box-shadow: 0 1px 3px rgba(0,0,0,0.05); 
        margin-bottom: 8px; 
        min-height: 145px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    
    .kpi-card p { font-size: 0.85rem; margin: 0; color: #666; font-weight: 600; }
    .kpi-card h2 { font-size: 1.8rem; margin: 4px 0; color: #00235d; } 
    .kpi-subtext { font-size: 0.75rem; color: #888; }
    
    .metric-card { 
        background-color: white; 
        border: 1px solid #eee; 
        padding: 10px; 
        border-radius: 8px; 
        box-shadow: 0 1px 2px rgba(0,0,0,0.05); 
        text-align: center; 
        height: 100%; 
        display: flex; 
        flex-direction: column; 
        justify-content: center; 
        min-height: 90px; 
    }
    
    .stTabs [aria-selected="true"] { background-color: #00235d !important; color: white !important; font-weight: bold; }
    h3 { color: #00235d; font-size: 1.1rem; margin-top: 10px; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 4px; }
    
    .cyp-detail { background-color: #f8f9fa; padding: 8px; border-radius: 6px; font-size: 0.8rem; margin-top: 5px; border-left: 3px solid #00235d; line-height: 1.3; }
    .cyp-header { font-weight: bold; color: #00235d; font-size: 0.85rem; margin-bottom: 2px; display: block; }
</style>""", unsafe_allow_html=True)

# --- FUNCIÓN DE BÚSQUEDA ---
def find_col(df, include_keywords, exclude_keywords=[]):
    if df is None: return ""
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
            if os.path.exists("logo.png"):
                st.image("logo.png", use_container_width=True)
                
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

        # DATA HISTORICO
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

        # --- PORTADA ---
        st.markdown(f'''
        <div class="portada-container">
            <div class="portada-left">
                <h1>Autociel - Tablero Posventa</h1>
                <h3>📅 {meses_nom.get(mes_sel)} {año_sel}</h3>
            </div>
            <div class="portada-right">
                <div>Avance: <b>{d_t:g}</b>/{d_h:g} días ({prog_t:.1%})</div>
                <div style="background: rgba(255,255,255,0.3); height: 6px; border-radius: 4px; width: 100%;">
                    <div style="background: #fff; width: {prog_t*100}%; height: 100%; border-radius: 4px;"></div>
                </div>
            </div>
        </div>
        ''', unsafe_allow_html=True)

        tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏠 Objetivos", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura", "📈 Histórico"])

        # --- HELPERS VISUALES ---
        def render_kpi_card(title, real, obj_mes, is_currency=True, unit="", show_daily=False):
            obj_parcial = obj_mes * prog_t
            proy = (real / d_t) * d_h if d_t > 0 else 0
            cumpl_proy = proy / obj_mes if obj_mes > 0 else 0
            fmt = "${:,.0f}" if is_currency else "{:,.0f}"
            if unit: fmt += f" {unit}"
            color = "#dc3545" if cumpl_proy < 0.90 else ("#ffc107" if cumpl_proy < 0.98 else "#28a745")
            icon = "✅" if real >= obj_parcial else "🔻"
            cumpl_parcial_pct = real / obj_parcial if obj_parcial > 0 else 0
            
            daily_html = ""
            if show_daily:
                daily_val = real / d_t if d_t > 0 else 0
                fmt_daily = "${:,.0f}" if is_currency else "{:,.1f}"
                daily_html = f'<div style="font-size:0.75rem; color:#00235d; background-color:#eef2f7; padding: 1px 6px; border-radius:4px; display:inline-block; margin-bottom:4px;">Prom: <b>{fmt_daily.format(daily_val)}</b> /día</div>'

            html = '<div class="kpi-card">'
            html += f'<div><p>{title}</p>'
            html += f'<h2>{fmt.format(real)}</h2>'
            html += daily_html 
            html += '</div>'
            html += f'<div><div class="kpi-subtext">vs Obj. Parcial: <b>{fmt.format(obj_parcial)}</b> <span style="color:{"#28a745" if real >= obj_parcial else "#dc3545"}">({cumpl_parcial_pct:.1%})</span> {icon}</div>'
            html += '<hr style="margin:5px 0; border:0; border-top:1px solid #eee;">'
            html += f'<div style="display:flex; justify-content:space-between; font-size:0.75rem; margin-bottom:2px;"><span>Obj. Mes:</span><b>{fmt.format(obj_mes)}</b></div>'
            html += f'<div style="display:flex; justify-content:space-between; font-size:0.75rem; color:{color}; font-weight:bold;"><span>Proyección:</span><span>{fmt.format(proy)} ({cumpl_proy:.1%})</span></div>'
            html += f'<div style="margin-top:5px;"><div style="width:100%; background:#e0e0e0; height:5px; border-radius:10px;"><div style="width:{min(cumpl_proy*100, 100)}%; background:{color}; height:5px; border-radius:10px;"></div></div></div></div>'
            html += '</div>'
            return html

        def render_kpi_small(title, val, target=None, format_str="{:.1%}"):
            subtext_html = "<div style='height:15px;'></div>"
            if target is not None:
                delta = val - target
                color = "#28a745" if delta >= 0 else "#dc3545"
                icon = "▲" if delta >= 0 else "▼"
                subtext_html = f"<div style='margin-top:4px; display:flex; justify-content:center; align-items:center; gap:5px; font-size:0.7rem;'><span style='color:#888;'>Obj: {format_str.format(target)}</span><span style='color:{color}; font-weight:bold; background-color:{color}15; padding:1px 4px; border-radius:3px;'>{icon} {format_str.format(abs(delta))}</span></div>"
            
            html = '<div class="metric-card">'
            html += f'<p style="color:#666; font-size:0.8rem; margin-bottom:2px;">{title}</p>'
            html += f'<h3 style="color:#00235d; margin:0; font-size:1.3rem;">{format_str.format(val)}</h3>'
            html += subtext_html
            html += '</div>'
            return html

        # --- LÓGICA DE COLUMNAS ROBUSTA (SERVICIOS) ---
        c_cli = find_col(data['SERVICIOS'], ["MO", "CLI"], exclude_keywords=["OBJ"])
        c_gar = find_col(data['SERVICIOS'], ["MO", "GAR"], exclude_keywords=["OBJ"])
        c_int = find_col(data['SERVICIOS'], ["MO", "INT"], exclude_keywords=["OBJ"])
        if not c_int: c_int = find_col(data['SERVICIOS'], ["INTERNA"], exclude_keywords=["OBJ", "MO"])
        
        c_ter = find_col(data['SERVICIOS'], ["MO", "TERCERO"], exclude_keywords=["OBJ"])
        if not c_ter: c_ter = find_col(data['SERVICIOS'], ["MO", "TERCEROS"], exclude_keywords=["OBJ"])
        if not c_ter: c_ter = find_col(data['SERVICIOS'], ["MO", "TER"], exclude_keywords=["OBJ"])
        if not c_ter: c_ter = find_col(data['SERVICIOS'], ["TERCERO"], exclude_keywords=["OBJ", "MO", "COSTO"])

        val_cli = s_r.get(c_cli, 0) if c_cli else 0
        val_gar = s_r.get(c_gar, 0) if c_gar else 0
        val_int = s_r.get(c_int, 0) if c_int else 0
        val_ter = s_r.get(c_ter, 0) if c_ter else 0
        
        real_mo_total = val_cli + val_gar + val_int + val_ter
        
        # --- TAB 1: OBJETIVOS ---
        with tab1:
            cols = st.columns(4)
            real_rep = sum([r_r.get(find_col(data['REPUESTOS'], ["VENTA", c], exclude_keywords=["OBJ"]), 0) for c in canales_repuestos])
            
            def get_cyp_total(row, df_nom):
                mo = row.get(find_col(data[df_nom], ["MO", "PUR"]), 0) + row.get(find_col(data[df_nom], ["MO", "TER"]), 0)
                rep = row.get(find_col(data[df_nom], ["FACT", "REP"]), 0) 
                return mo + rep

            metas = [
                ("M.O. Servicios", real_mo_total, s_r.get(find_col(data['SERVICIOS'], ["OBJ", "MO"]), 1)),
                ("Repuestos", real_rep, r_r.get(find_col(data['REPUESTOS'], ["OBJ", "FACT"]), 1)),
                ("CyP Jujuy", get_cyp_total(cj_r, 'CyP JUJUY'), cj_r.get(find_col(data['CyP JUJUY'], ["OBJ", "FACT"]), 1)),
                ("CyP Salta", get_cyp_total(cs_r, 'CyP SALTA'), cs_r.get(find_col(data['CyP SALTA'], ["OBJ", "FACT"]), 1))
            ]
            for i, (tit, real, obj) in enumerate(metas):
                with cols[i]: st.markdown(render_kpi_card(tit, real, obj, True), unsafe_allow_html=True)

        with tab2:
            col_main, col_breakdown = st.columns([1, 2])
            obj_mo_total = s_r.get(find_col(data['SERVICIOS'], ["OBJ", "MO"]), 1)
            
            with col_main: st.markdown(render_kpi_card("Facturación M.O.", real_mo_total, obj_mo_total, show_daily=True), unsafe_allow_html=True)
            
            with col_breakdown:
                df_mo = pd.DataFrame({
                    "Cargo": ["Cliente", "Garantía", "Interno", "Terceros"], 
                    "Facturación": [val_cli, val_gar, val_int, val_ter]
                })
                fig_mo = px.bar(df_mo, x="Facturación", y="Cargo", orientation='h', text_auto='.2s', title="", color="Cargo", color_discrete_sequence=["#00235d", "#28a745", "#ffc107", "#17a2b8"])
                fig_mo.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=160) 
                st.plotly_chart(fig_mo, use_container_width=True)

            k1, k2, k3, k4 = st.columns(4)
            c_cpus = find_col(data['SERVICIOS'], ["CPUS"], exclude_keywords=["OBJ"])
            c_tus_others = find_col(data['SERVICIOS'], ["OTROS", "CARGOS"], exclude_keywords=["OBJ"])
            real_cpus = s_r.get(c_cpus, 0)
            real_tus = real_cpus + s_r.get(c_tus_others, 0)
            obj_cpus = s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'CPUS']), 1)
            obj_tus = s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'TUS']), 1)
            div = real_cpus if real_cpus > 0 else 1
            tp_mo = real_mo_total / div
            hf_cc = t_r.get(find_col(data['TALLER'], ["FACT", "CC"]), 0)
            hf_cg = t_r.get(find_col(data['TALLER'], ["FACT", "CG"]), 0)
            hf_ci = t_r.get(find_col(data['TALLER'], ["FACT", "CI"]), 0)
            tp_hs = (hf_cc+hf_cg+hf_ci) / div
            tgt_tp_mo = obj_mo_total / obj_cpus if obj_cpus > 0 else 0

            with k1: st.markdown(render_kpi_card("TUS Total", real_tus, obj_tus, is_currency=False, show_daily=True), unsafe_allow_html=True)
            with k2: st.markdown(render_kpi_card("CPUS (Entradas)", real_cpus, obj_cpus, is_currency=False, show_daily=True), unsafe_allow_html=True)
            with k3: st.markdown(render_kpi_small("Ticket Prom. (Hs)", tp_hs, None, "{:.2f} hs"), unsafe_allow_html=True)
            with k4: st.markdown(render_kpi_small("Ticket Prom. ($)", tp_mo, tgt_tp_mo, "${:,.0f}"), unsafe_allow_html=True)

            # --- SECCIÓN: CALIDAD Y REQUERIMIENTOS ---
            st.markdown("---")
            st.markdown("### 🏆 Calidad y Requerimientos de Marca")
            
            def get_calidad_data(keyword_main, brand, is_percent=False, prorate_target=False):
                # 1. Buscamos el REAL (ej: NPS + PEUGEOT)
                c_real = find_col(data['SERVICIOS'], [keyword_main, brand], exclude_keywords=["OBJ"])
                
                # 2. Buscamos el OBJETIVO (FALLBACK LOGIC)
                c_obj = find_col(data['SERVICIOS'], ["OBJ", keyword_main, brand])
                if not c_obj: c_obj = find_col(data['SERVICIOS'], ["OBJ", keyword_main])
                
                val_real = s_r.get(c_real, 0)
                val_obj = s_r.get(c_obj, 0)
                
                # --- AJUSTE OBJETIVOS PARCIALES (PRORRATEO) ---
                if prorate_target:
                    # Si es una métrica acumulativa (Volumen), multiplicamos el Obj Mensual x Avance de Días
                    val_obj = val_obj * prog_t
                
                if is_percent:
                    if val_real > 1.0: val_real /= 100
                    if val_obj > 1.0: val_obj /= 100
                    fmt = "{:.1%}"
                else:
                    # Si NO es porcentaje (Cantidad o NPS), usamos formato entero/decimal
                    fmt = "{:,.0f}" if not prorate_target else "{:,.1f}" 
                    # Nota: si prorrateamos, a veces queda decimal (ej: objetivo 5.5 autos), usamos 1 decimal
                    
                return val_real, val_obj, fmt

            # NPS (Sin porcentaje, SIN prorrateo porque es promedio)
            nps_p_r, nps_p_o, fmt_nps = get_calidad_data("NPS", "PEUGEOT", is_percent=False, prorate_target=False)
            nps_c_r, nps_c_o, _ = get_calidad_data("NPS", "CITROEN", is_percent=False, prorate_target=False)
            
            # VIDEOCHECK (Sin porcentaje, cantidad, CON prorrateo)
            vc_p_r, vc_p_o, fmt_vc = get_calidad_data("VIDEO", "PEUGEOT", is_percent=False, prorate_target=True)
            vc_c_r, vc_c_o, _ = get_calidad_data("VIDEO", "CITROEN", is_percent=False, prorate_target=True)
            
            # FORFAIT (Sin porcentaje, cantidad, CON prorrateo)
            ff_p_r, ff_p_o, fmt_ff = get_calidad_data("FORFAIT", "PEUGEOT", is_percent=False, prorate_target=True)
            ff_c_r, ff_c_o, _ = get_calidad_data("FORFAIT", "CITROEN", is_percent=False, prorate_target=True)

            # Layout: 
            q1, q2 = st.columns(2)
            with q1: st.markdown(render_kpi_small("NPS Peugeot", nps_p_r, nps_p_o, fmt_nps), unsafe_allow_html=True)
            with q2: st.markdown(render_kpi_small("NPS Citroën", nps_c_r, nps_c_o, fmt_nps), unsafe_allow_html=True)
            
            p1, p2, p3, p4 = st.columns(4)
            with p1: st.markdown(render_kpi_small("Videocheck Peug.", vc_p_r, vc_p_o, fmt_vc), unsafe_allow_html=True)
            with p2: st.markdown(render_kpi_small("Videocheck Citr.", vc_c_r, vc_c_o, fmt_vc), unsafe_allow_html=True)
            with p3: st.markdown(render_kpi_small("Forfait Peug.", ff_p_r, ff_p_o, fmt_ff), unsafe_allow_html=True)
            with p4: st.markdown(render_kpi_small("Forfait Citr.", ff_c_r, ff_c_o, fmt_ff), unsafe_allow_html=True)
            
            st.markdown("---")

            st.markdown("### ⚙️ Taller")
            # --- TALLER CARD LOGIC ---
            col_tecs = find_col(data['TALLER'], ["TECNICOS"], exclude_keywords=["PROD"])
            if not col_tecs: col_tecs = find_col(data['TALLER'], ["DOTACION"])
            
            cant_tecs = t_r.get(col_tecs, 6) # Si no encuentra, usa 6 por defecto
            if cant_tecs == 0: cant_tecs = 6

            ht_cc = t_r.get(find_col(data['TALLER'], ["TRAB", "CC"]), 0)
            ht_cg = t_r.get(find_col(data['TALLER'], ["TRAB", "CG"]), 0)
            ht_ci = t_r.get(find_col(data['TALLER'], ["TRAB", "CI"]), 0)
            ef_cc = hf_cc / ht_cc if ht_cc > 0 else 0
            ef_cg = hf_cg / ht_cg if ht_cg > 0 else 0
            ef_ci = hf_ci / ht_ci if ht_ci > 0 else 0
            ef_gl = (hf_cc+hf_cg+hf_ci) / (ht_cc+ht_cg+ht_ci) if (ht_cc+ht_cg+ht_ci) > 0 else 0
            
            hs_disp = t_r.get(find_col(data['TALLER'], ["DISPONIBLES", "REAL"]), 0)
            hs_teoricas = cant_tecs * 8 * d_t 
            presencia = hs_disp / hs_teoricas if hs_teoricas > 0 else 0
            ocup = (ht_cc+ht_cg+ht_ci) / hs_disp if hs_disp > 0 else 0
            prod = t_r.get(find_col(data['TALLER'], ["PRODUCTIVIDAD", "TALLER"]), 0)
            if prod > 2: prod /= 100

            e1, e2, e3, e4 = st.columns(4)
            with e1: st.markdown(render_kpi_small("Eficiencia CC", ef_cc, 1.0), unsafe_allow_html=True)
            with e2: st.markdown(render_kpi_small("Eficiencia Gar.", ef_cg, 1.0), unsafe_allow_html=True)
            with e3: st.markdown(render_kpi_small("Eficiencia Int.", ef_ci, 0.20), unsafe_allow_html=True)
            with e4: st.markdown(render_kpi_small("Eficiencia Global", ef_gl, 0.85), unsafe_allow_html=True)

            u1, u2, u3 = st.columns(3)
            with u1: st.markdown(render_kpi_small("Presencia", presencia, 0.95), unsafe_allow_html=True)
            with u2: st.markdown(render_kpi_small("Ocupación", ocup, 0.95), unsafe_allow_html=True)
            with u3: st.markdown(render_kpi_small("Productividad", prod, 0.95), unsafe_allow_html=True)

            g1, g2 = st.columns(2)
            with g1: st.plotly_chart(px.pie(values=[ht_cc, ht_cg, ht_ci], names=["CC", "CG", "CI"], hole=0.4, title="Hs Trabajadas"), use_container_width=True)
            with g2: st.plotly_chart(px.pie(values=[hf_cc, hf_cg, hf_ci], names=["CC", "CG", "CI"], hole=0.4, title="Hs Facturadas"), use_container_width=True)

        with tab3:
            st.markdown("### 📦 Repuestos")
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
            
            costo_total_mes_actual = df_r['Costo'].sum() if not df_r.empty else 0
            val_stock = float(r_r.get(find_col(data['REPUESTOS'], ["VALOR", "STOCK"]), 0))
            
            c_main, c_kpis = st.columns([1, 3])
            with c_main: st.markdown(render_kpi_card("Fact. Bruta", vta_total_bruta, obj_rep_total), unsafe_allow_html=True)
            with c_kpis:
                r2, r3, r4 = st.columns(3)
                util_total = df_r['Utilidad $'].sum() if not df_r.empty else 0
                vta_total_neta = df_r['Venta Neta'].sum() if not df_r.empty else 0
                mg_total = util_total / vta_total_neta if vta_total_neta > 0 else 0
                meses_stock = val_stock / costo_total_mes_actual if costo_total_mes_actual > 0 else 0
                with r2: st.markdown(render_kpi_small("Utilidad Total", util_total, None, "${:,.0f}"), unsafe_allow_html=True)
                with r3: st.markdown(render_kpi_small("Margen Global", mg_total, None, "{:.1%}"), unsafe_allow_html=True)
                with r4: st.markdown(render_kpi_small("Meses Stock", meses_stock, 4.0, "{:.1f}"), unsafe_allow_html=True)

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
                if not df_r.empty: st.plotly_chart(px.pie(df_r, values="Venta Bruta", names="Canal", hole=0.4, title="Participación"), use_container_width=True)
            with c2:
                p_vivo = float(r_r.get(find_col(data['REPUESTOS'], ["VIVO"]), 0))
                p_obs = float(r_r.get(find_col(data['REPUESTOS'], ["OBSOLETO"]), 0))
                p_muerto = float(r_r.get(find_col(data['REPUESTOS'], ["MUERTO"]), 0))
                f = 1 if p_vivo <= 1 else 100
                df_s = pd.DataFrame({"Estado": ["Vivo", "Obsoleto", "Muerto"], "Valor": [val_stock*(p_vivo/f), val_stock*(p_obs/f), val_stock*(p_muerto/f)]})
                st.plotly_chart(px.pie(df_s, values="Valor", names="Estado", hole=0.4, title="Stock", color="Estado", color_discrete_map={"Vivo": "#28a745", "Obsoleto": "#ffc107", "Muerto": "#dc3545"}), use_container_width=True)
                st.markdown(f"<div style='text-align:center; background:#f8f9fa; padding:10px; border-radius:8px; border:1px solid #eee;'>💰 <b>Valor Total Stock:</b> ${val_stock:,.0f}</div>", unsafe_allow_html=True)

        with tab4:
            st.markdown("### 🎨 Chapa y Pintura")
            
            # --- BÚSQUEDA ROBUSTA PARA JUJUY ---
            c_mo_j = find_col(data['CyP JUJUY'], ['MO'], exclude_keywords=['TER', 'OBJ', 'PRE'])
            c_mo_t_j = find_col(data['CyP JUJUY'], ['MO', 'TERCERO'], exclude_keywords=['OBJ'])
            if not c_mo_t_j: c_mo_t_j = find_col(data['CyP JUJUY'], ['MO', 'TER'], exclude_keywords=['OBJ'])
            
            j_f_p = cj_r.get(c_mo_j, 0)
            j_f_t = cj_r.get(c_mo_t_j, 0)
            j_total_fact = j_f_p + j_f_t
            j_obj_fact = cj_r.get(find_col(data['CyP JUJUY'], ["OBJ", "FACT"]), 1)
            
            # Paños
            c_panos_j = find_col(data['CyP JUJUY'], ['PANOS'], exclude_keywords=['TER', 'OBJ', 'PRE'])
            if not c_panos_j: c_panos_j = find_col(data['CyP JUJUY'], ['PAÑOS'], exclude_keywords=['TER', 'OBJ', 'PRE'])
            
            j_panos_prop = cj_r.get(c_panos_j, 0)
            j_obj_panos = cj_r.get(find_col(data['CyP JUJUY'], ['OBJ', 'PANOS']), 1)
            
            # Tecnicos (Solo para KPI card actual)
            c_tec_j = find_col(data['CyP JUJUY'], ['TECNICO'], exclude_keywords=['PRODUCTIVIDAD'])
            if not c_tec_j: c_tec_j = find_col(data['CyP JUJUY'], ['DOTACION'])
            j_cant_tec = cj_r.get(c_tec_j, 1)
            
            j_ratio = j_panos_prop / j_cant_tec if j_cant_tec > 0 else 0
            
            # Terceros Panos y Costos
            j_panos_ter = cj_r.get(find_col(data['CyP JUJUY'], ['PANOS', 'TER']), 0)
            j_c_ter = cj_r.get(find_col(data['CyP JUJUY'], ['COSTO', 'TER']), 0)
            j_m_ter = j_f_t - j_c_ter
            j_mg_ter_pct = j_m_ter/j_f_t if j_f_t > 0 else 0
            
            # --- BÚSQUEDA ROBUSTA PARA SALTA ---
            c_mo_s = find_col(data['CyP SALTA'], ['MO'], exclude_keywords=['TER', 'OBJ', 'PRE'])
            c_mo_t_s = find_col(data['CyP SALTA'], ['MO', 'TERCERO'], exclude_keywords=['OBJ'])
            if not c_mo_t_s: c_mo_t_s = find_col(data['CyP SALTA'], ['MO', 'TER'], exclude_keywords=['OBJ'])
            
            s_f_p = cs_r.get(c_mo_s, 0)
            s_f_t = cs_r.get(c_mo_t_s, 0)
            s_f_r = cs_r.get(find_col(data['CyP SALTA'], ['FACT', 'REP']), 0)
            s_total_fact = s_f_p + s_f_t + s_f_r
            s_obj_fact = cs_r.get(find_col(data['CyP SALTA'], ["OBJ", "FACT"]), 1)
            
            c_panos_s = find_col(data['CyP SALTA'], ['PANOS'], exclude_keywords=['TER', 'OBJ', 'PRE'])
            if not c_panos_s: c_panos_s = find_col(data['CyP SALTA'], ['PAÑOS'], exclude_keywords=['TER', 'OBJ', 'PRE'])
            
            s_panos_prop = cs_r.get(c_panos_s, 0)
            s_obj_panos = cs_r.get(find_col(data['CyP SALTA'], ['OBJ', 'PANOS']), 1)
            
            c_tec_s = find_col(data['CyP SALTA'], ['TECNICO'], exclude_keywords=['PRODUCTIVIDAD'])
            if not c_tec_s: c_tec_s = find_col(data['CyP SALTA'], ['DOTACION'])
            s_cant_tec = cs_r.get(c_tec_s, 1)
            
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
                st.markdown(render_kpi_card("Fact. Total Jujuy", j_total_fact, j_obj_fact), unsafe_allow_html=True)
                st.markdown(render_kpi_card("Paños Propios", j_panos_prop, j_obj_panos, is_currency=False, unit="u"), unsafe_allow_html=True)
                st.markdown(render_kpi_small("Paños/Técnico", j_ratio, None, "{:.1f}"), unsafe_allow_html=True)
                html_ter_j = f'<div class="cyp-detail"><span class="cyp-header">👨‍🔧 Gestión Terceros</span>Cant: <b>{j_panos_ter:,.0f}</b> | Fact: ${j_f_t:,.0f}<br>Mg: <b>${j_m_ter:,.0f}</b> ({j_mg_ter_pct:.1%})</div>'
                st.markdown(html_ter_j, unsafe_allow_html=True)
            with c_salta:
                st.subheader("Sede Salta")
                st.markdown(render_kpi_card("Fact. Total Salta", s_total_fact, s_obj_fact), unsafe_allow_html=True)
                st.markdown(render_kpi_card("Paños Propios", s_panos_prop, s_obj_panos, is_currency=False, unit="u"), unsafe_allow_html=True)
                st.markdown(render_kpi_small("Paños/Técnico", s_ratio, None, "{:.1f}"), unsafe_allow_html=True)
                html_ter_s = f'<div class="cyp-detail"><span class="cyp-header">👨‍🔧 Gestión Terceros</span>Cant: <b>{s_panos_ter:,.0f}</b> | Fact: ${s_f_t:,.0f}<br>Mg: <b>${s_m_ter:,.0f}</b> ({s_mg_ter_pct:.1%})</div>'
                st.markdown(html_ter_s, unsafe_allow_html=True)
                if s_f_r > 0: st.markdown(f'<div class="cyp-detail" style="border-left-color: #28a745;"><span class="cyp-header" style="color:#28a745">📦 Repuestos</span>Fact: ${s_f_r:,.0f} | Mg: <b>${s_m_rep:,.0f}</b> ({s_mg_rep_pct:.1%})</div>', unsafe_allow_html=True)

            g_jujuy, g_salta = st.columns(2)
            with g_jujuy: st.plotly_chart(px.pie(values=[j_f_p, j_f_t], names=["MO Pura", "Terceros"], hole=0.4, title="Facturación Jujuy", color_discrete_sequence=["#00235d", "#00A8E8"]), use_container_width=True)
            with g_salta: 
                vals_s, nams_s = [s_f_p, s_f_t], ["MO Pura", "Terceros"]
                if s_f_r > 0: vals_s.append(s_f_r); nams_s.append("Repuestos")
                st.plotly_chart(px.pie(values=vals_s, names=nams_s, hole=0.4, title="Facturación Salta", color_discrete_sequence=["#00235d", "#00A8E8", "#28a745"]), use_container_width=True)

        with tab5:
            st.markdown(f"### 📈 Evolución Anual {año_sel}")
            st.markdown("#### 🛠️ Servicios")
            
            # --- NUEVO GRÁFICO: IDEAL VS REAL VS OCUPADO ---
            col_hab_hist = find_col(h_cal, ["HAB"])
            
            # INTENTAMOS BUSCAR COLUMNA DE TÉCNICOS, SINO USAMOS 6 FIJO
            col_tecs_hist = find_col(h_tal, ["TECNICOS"], exclude_keywords=["PROD", "EFIC"])
            if not col_tecs_hist: col_tecs_hist = find_col(h_tal, ["MECANICOS"], exclude_keywords=["PROD"])
            
            # BUSQUEDA FLEXIBLE PARA DISPONIBLES (Requerido)
            col_disp_hist = find_col(h_tal, ["DISPONIBLES", "REAL"])
            if not col_disp_hist: col_disp_hist = find_col(h_tal, ["DISP", "REAL"])
            if not col_disp_hist: col_disp_hist = find_col(h_tal, ["DISPONIBLE"]) 
            
            # SOLO NECESITAMOS HAB Y DISP (TECNICOS ES OPCIONAL, DEFAULT 6)
            if col_hab_hist and col_disp_hist:
                df_capacidad = pd.merge(h_tal, h_cal[['Mes', col_hab_hist]], on='Mes', suffixes=('', '_cal'))
                
                # Calculo de Hs Ideales = Tecnicos * 8 * Dias Habiles
                # Si existe columna de tecnicos la usa, sino usa 6
                if col_tecs_hist:
                    cant_tecnicos_series = df_capacidad[col_tecs_hist].astype(float)
                else:
                    cant_tecnicos_series = 6
                
                df_capacidad['Hs Ideales'] = cant_tecnicos_series * 8 * df_capacidad[col_hab_hist].astype(float)
                df_capacidad['Hs Reales'] = df_capacidad[col_disp_hist].astype(float)
                
                # Hs Ocupadas (Trabajadas)
                cols_trab_h = [c for c in [find_col(h_tal, ["TRAB", k]) for k in ["CC", "CG", "CI"]] if c]
                df_capacidad['Hs Ocupadas'] = df_capacidad[cols_trab_h].sum(axis=1) if cols_trab_h else 0
                
                fig_cap = go.Figure()
                fig_cap.add_trace(go.Scatter(x=df_capacidad['NombreMes'], y=df_capacidad['Hs Ideales'], name='Ideal (Teórico)', line=dict(color='gray', dash='dash')))
                fig_cap.add_trace(go.Bar(x=df_capacidad['NombreMes'], y=df_capacidad['Hs Reales'], name='Presencia Real', marker_color='#00235d'))
                fig_cap.add_trace(go.Bar(x=df_capacidad['NombreMes'], y=df_capacidad['Hs Ocupadas'], name='Hs Ocupadas', marker_color='#28a745'))
                
                fig_cap.update_layout(title="Análisis de Capacidad: Ideal vs Real vs Ocupación", barmode='group', height=350)
                st.plotly_chart(fig_cap, use_container_width=True)
            else:
                st.warning(f"⚠️ No se pudo generar el gráfico de Capacidad. Faltan columnas: {'Dias Habiles' if not col_hab_hist else ''} {'Disponibles' if not col_disp_hist else ''}")
            
            # ------------------------------------------------
            
            col_prod = find_col(h_tal, ["PRODUCTIVIDAD", "TALLER"])
            h_tal['Productividad'] = h_tal[col_prod].apply(lambda x: x/100 if x > 2 else x) if col_prod else 0
            cols_trab = [c for c in [find_col(h_tal, ["TRAB", k]) for k in ["CC", "CG", "CI"]] if c]
            h_tal['Hs Trabajadas'] = h_tal[cols_trab].sum(axis=1) if cols_trab else 0
            
            h_tal['Hs Vendidas'] = 0
            cols_hs_fact = [c for c in [find_col(h_tal, ["FACT", k]) for k in ["CC", "CG", "CI"]] if c]
            if cols_hs_fact: h_tal['Hs Vendidas'] = h_tal[cols_hs_fact].sum(axis=1)

            h_tal['Eficiencia Global'] = h_tal.apply(lambda row: row['Hs Vendidas'] / row['Hs Trabajadas'] if row['Hs Trabajadas'] > 0 else 0, axis=1)
            
            fig_efi = go.Figure()
            fig_efi.add_trace(go.Scatter(x=h_tal['NombreMes'], y=h_tal['Eficiencia Global'], name='Efic. Global', mode='lines+markers', line=dict(color='#28a745')))
            fig_efi.add_trace(go.Scatter(x=h_tal['NombreMes'], y=h_tal['Productividad'], name='Productividad', mode='lines+markers', line=dict(color='#17a2b8', dash='dot')))
            fig_efi.update_layout(title="Eficiencia y Productividad", yaxis_tickformat='.0%', height=300)
            st.plotly_chart(fig_efi, use_container_width=True)

            c_h1, c_h2 = st.columns(2)
            col_cpus = find_col(h_ser, ["CPUS"], exclude_keywords=["OBJ"])
            if col_cpus:
                c_h1.plotly_chart(px.bar(h_ser, x="NombreMes", y=col_cpus, title="Entradas (CPUS)", color_discrete_sequence=['#00235d']), use_container_width=True)
                h_ser_tal = pd.merge(h_ser, h_tal, on="Mes")
                h_ser_tal['Ticket Hs'] = h_ser_tal.apply(lambda row: row['Hs Vendidas'] / row[col_cpus] if row[col_cpus] > 0 else 0, axis=1)
                c_h2.plotly_chart(px.bar(h_ser_tal, x="NombreMes_x", y="Ticket Hs", title="Ticket Promedio (Hs)", color_discrete_sequence=['#6c757d']), use_container_width=True)

            st.markdown("---")
            st.markdown("#### 📦 Repuestos")
            col_vivo, col_obs, col_muerto = find_col(h_rep, ["VIVO"]), find_col(h_rep, ["OBSOLETO"]), find_col(h_rep, ["MUERTO"])
            fig_stk = go.Figure()
            if col_vivo: fig_stk.add_trace(go.Bar(x=h_rep['NombreMes'], y=h_rep[col_vivo], name='Vivo', marker_color='#28a745'))
            if col_obs: fig_stk.add_trace(go.Bar(x=h_rep['NombreMes'], y=h_rep[col_obs], name='Obsoleto', marker_color='#ffc107'))
            if col_muerto: fig_stk.add_trace(go.Bar(x=h_rep['NombreMes'], y=h_rep[col_muerto], name='Muerto', marker_color='#dc3545'))
            fig_stk.update_layout(barmode='stack', title="Salud de Stock", height=300)
            st.plotly_chart(fig_stk, use_container_width=True)

            # GRÁFICO APILADO CANALES
            fig_mix = go.Figure()
            for c in canales_repuestos:
                col_vta = find_col(h_rep, ["VENTA", c], exclude_keywords=["OBJ"])
                if col_vta:
                    fig_mix.add_trace(go.Bar(x=h_rep['NombreMes'], y=h_rep[col_vta], name=c))
            
            fig_mix.update_layout(barmode='stack', title="Venta Total por Canal (Apilado)", height=300)
            st.plotly_chart(fig_mix, use_container_width=True)
            
            # GRÁFICO MESES DE STOCK
            h_rep['CostoTotalMes'] = 0
            for c in canales_repuestos:
                 col_costo = find_col(h_rep, ["COSTO", c], exclude_keywords=["OBJ"])
                 if col_costo:
                     h_rep['CostoTotalMes'] += h_rep[col_costo]
            
            h_rep['CostoPromedio3M'] = h_rep['CostoTotalMes'].rolling(window=3, min_periods=1).mean()
            col_val_stock = find_col(h_rep, ["VALOR", "STOCK"])
            
            if col_val_stock:
                h_rep['MesesStock'] = h_rep.apply(lambda row: row[col_val_stock] / row['CostoPromedio3M'] if row['CostoPromedio3M'] > 0 else 0, axis=1)
                
                fig_rot = go.Figure()
                fig_rot.add_trace(go.Scatter(x=h_rep['NombreMes'], y=h_rep['MesesStock'], name='Meses Stock', mode='lines+markers', line=dict(color='#6610f2', width=3)))
                fig_rot.update_layout(title="Evolución Meses de Stock (Stock / Costo Prom. 3 meses)", height=300)
                st.plotly_chart(fig_rot, use_container_width=True)

            st.markdown("---")
            st.markdown("#### 🎨 Chapa y Pintura - Desglose por Sede")
            
            # --- BÚSQUEDA ROBUSTA HISTÓRICO CyP ---
            col_pp_j = find_col(h_cyp_j, ['PANOS'], exclude_keywords=['TER', 'OBJ', 'PRE'])
            if not col_pp_j: col_pp_j = find_col(h_cyp_j, ['PAÑOS'], exclude_keywords=['TER', 'OBJ'])
            
            col_pt_j = find_col(h_cyp_j, ['PANOS', 'TER'])
            if not col_pt_j: col_pt_j = find_col(h_cyp_j, ['PAÑOS', 'TER'])
            
            h_cyp_j['Paños Propios'] = h_cyp_j[col_pp_j] if col_pp_j else 0
            h_cyp_j['Paños Terceros'] = h_cyp_j[col_pt_j] if col_pt_j else 0
            
            col_pp_s = find_col(h_cyp_s, ['PANOS'], exclude_keywords=['TER', 'OBJ'])
            if not col_pp_s: col_pp_s = find_col(h_cyp_s, ['PAÑOS'], exclude_keywords=['TER', 'OBJ'])
            
            col_pt_s = find_col(h_cyp_s, ['PANOS', 'TER'])
            if not col_pt_s: col_pt_s = find_col(h_cyp_s, ['PAÑOS', 'TER'])
            
            h_cyp_s['Paños Propios'] = h_cyp_s[col_pp_s] if col_pp_s else 0
            h_cyp_s['Paños Terceros'] = h_cyp_s[col_pt_s] if col_pt_s else 0
            
            c_hist_j, c_hist_s = st.columns(2)
            
            with c_hist_j:
                fig_pj = go.Figure()
                fig_pj.add_trace(go.Bar(x=h_cyp_j['NombreMes'], y=h_cyp_j['Paños Propios'], name='Propios', marker_color='#00235d'))
                fig_pj.add_trace(go.Bar(x=h_cyp_j['NombreMes'], y=h_cyp_j['Paños Terceros'], name='Terceros', marker_color='#17a2b8'))
                fig_pj.update_layout(barmode='stack', title="Evolución Jujuy (Paños)", height=300)
                st.plotly_chart(fig_pj, use_container_width=True)
                
            with c_hist_s:
                fig_ps = go.Figure()
                fig_ps.add_trace(go.Bar(x=h_cyp_s['NombreMes'], y=h_cyp_s['Paños Propios'], name='Propios', marker_color='#00235d'))
                fig_ps.add_trace(go.Bar(x=h_cyp_s['NombreMes'], y=h_cyp_s['Paños Terceros'], name='Terceros', marker_color='#17a2b8'))
                fig_ps.update_layout(barmode='stack', title="Evolución Salta (Paños)", height=300)
                st.plotly_chart(fig_ps, use_container_width=True)

    else:
        st.warning("No se pudieron cargar los datos.")
except Exception as e:
    st.error(f"Error global: {e}")
