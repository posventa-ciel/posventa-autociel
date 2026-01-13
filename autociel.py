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
        padding: 10px 10px 6px 10px;
        border-radius: 8px; 
        box-shadow: 0 1px 2px rgba(0,0,0,0.05); 
        text-align: center; 
        height: 100%; 
        display: flex; 
        flex-direction: column; 
        justify-content: space-between; 
        min-height: 110px; 
    }
    
    .metric-footer {
        border-top: 1px solid #f0f0f0;
        margin-top: 8px;
        padding-top: 6px;
        font-size: 0.7rem;
        display: flex;
        justify-content: space-between;
        color: #666;
    }
    
    div.row-widget.stRadio > div { flex-direction: row; align-items: stretch; }
    div.row-widget.stRadio > div[role="radiogroup"] > label { 
        background-color: #ffffff; 
        border: 1px solid #e0e0e0;
        padding: 8px 16px;
        border-radius: 5px;
        margin-right: 5px;
        font-weight: bold;
        color: #00235d;
    }
    div.row-widget.stRadio > div[role="radiogroup"] > label[data-baseweb="radio"] { 
        background-color: #00235d; 
        color: white;
    }

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

# --- CARGA DE DATOS GOOGLE SHEETS ---
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

# --- FUNCIÓN PARA CÁLCULO DE IRPV (FIDELIZACIÓN) ---
@st.cache_data(ttl=3600)
def calcular_irpv_local(archivo_ventas, archivo_taller):
    try:
        # 1. Cargar Ventas (0km)
        df_v = pd.read_csv(archivo_ventas)
        
        def excel_date(serial):
            if pd.isna(serial) or serial == '': return None
            try: return datetime(1899, 12, 30) + pd.Timedelta(days=float(serial))
            except: return None

        df_v['Fecha_Entrega'] = df_v['Fec.entr'].apply(excel_date)
        df_v['Año_Venta'] = df_v['Fecha_Entrega'].dt.year
        df_v['VIN'] = df_v['Bastidor'].astype(str).str.strip().str.upper()
        df_v = df_v.dropna(subset=['VIN', 'Fecha_Entrega'])

        # 2. Cargar Taller (Servicios)
        df_t = pd.read_csv(archivo_taller)
        df_t['Fecha_Servicio'] = df_t['F.cierre'].apply(excel_date)
        df_t['VIN'] = df_t['Bastidor'].astype(str).str.strip().str.upper()
        df_t['Km'] = pd.to_numeric(df_t['Km'], errors='coerce').fillna(0)
        
        # Filtro: Solo mecánica (Excluir Chapa/Pintura)
        mask_mec = ~df_t['Tipo O.R.'].astype(str).str.contains('CHAPA|PINTURA|SINIESTRO', case=False, na=False)
        df_t = df_t[mask_mec]

        # 3. Clasificar Servicios por KM
        def clasificar_km(k):
            if 5000 <= k <= 15000: return "1er"
            elif 15001 <= k <= 25000: return "2do"
            elif 25001 <= k <= 35000: return "3er"
            return None
        
        df_t['Servicio_Hito'] = df_t['Km'].apply(clasificar_km)
        df_validos = df_t.dropna(subset=['Servicio_Hito'])

        # 4. Cruzar y Calcular
        df_merged = pd.merge(df_v, df_validos[['VIN', 'Servicio_Hito']], on='VIN', how='left')
        
        pivot = df_merged.pivot_table(index=['VIN', 'Año_Venta'], columns='Servicio_Hito', aggfunc='size', fill_value=0).reset_index()
        
        for col in ['1er', '2do', '3er']:
            if col not in pivot.columns: pivot[col] = 0
            else: pivot[col] = pivot[col].apply(lambda x: 1 if x > 0 else 0)

        df_irpv = pivot.groupby('Año_Venta')[['1er', '2do', '3er']].mean()
        return df_irpv

    except Exception as e:
        return None

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

        menu_opts = ["🏠 Objetivos", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura", "📈 Histórico"]
        selected_tab = st.radio("", menu_opts, horizontal=True, label_visibility="collapsed")
        st.markdown("---")

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

        def render_kpi_small(title, val, target=None, target_mensual=None, projection=None, format_str="{:.1%}", label_target="Obj. Parcial"):
            subtext_html = "<div style='height:15px;'></div>"
            footer_html = ""
            
            if target is not None:
                delta = val - target
                color = "#28a745" if delta >= 0 else "#dc3545"
                icon = "▲" if delta >= 0 else "▼"
                subtext_html = f"<div style='margin-top:4px; display:flex; justify-content:center; align-items:center; gap:5px; font-size:0.7rem;'><span style='color:#888;'>{label_target}: {format_str.format(target)}</span><span style='color:{color}; font-weight:bold; background-color:{color}15; padding:1px 4px; border-radius:3px;'>{icon} {format_str.format(abs(delta))}</span></div>"
            
            if target_mensual is not None and projection is not None:
                proy_delta = projection - target_mensual
                color_proy = "#28a745" if proy_delta >= 0 else "#dc3545"
                footer_html = f'''
                <div class="metric-footer">
                    <div>Obj. Mes: <b>{format_str.format(target_mensual)}</b></div>
                    <div style="color:{color_proy}">Proy: <b>{format_str.format(projection)}</b></div>
                </div>
                '''
            
            html = '<div class="metric-card">'
            html += f'<div><p style="color:#666; font-size:0.8rem; margin-bottom:2px;">{title}</p>'
            html += f'<h3 style="color:#00235d; margin:0; font-size:1.3rem;">{format_str.format(val)}</h3>'
            html += subtext_html
            html += '</div>'
            html += footer_html
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
        if selected_tab == "🏠 Objetivos":
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

        elif selected_tab == "🛠️ Servicios y Taller":
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
            with k3: st.markdown(render_kpi_small("Ticket Prom. (Hs)", tp_hs, None, None, None, "{:.2f} hs"), unsafe_allow_html=True)
            with k4: st.markdown(render_kpi_small("Ticket Prom. ($)", tp_mo, tgt_tp_mo, None, None, "${:,.0f}"), unsafe_allow_html=True)

            # --- SECCIÓN: CALIDAD Y REQUERIMIENTOS ---
            st.markdown("---")
            st.markdown("### 🏆 Calidad y Requerimientos de Marca")
            
            def get_calidad_data(keyword_main, brand, is_percent=False, prorate_target=False):
                c_real = find_col(data['SERVICIOS'], [keyword_main, brand], exclude_keywords=["OBJ"])
                c_obj = find_col(data['SERVICIOS'], ["OBJ", keyword_main, brand])
                if not c_obj: c_obj = find_col(data['SERVICIOS'], ["OBJ", keyword_main])
                val_real = s_r.get(c_real, 0)
                
                df_mes = data['SERVICIOS'][(data['SERVICIOS']['Año'] == año_sel) & (data['SERVICIOS']['Mes'] == mes_sel)]
                if not df_mes.empty and c_obj: val_obj_mensual = df_mes[c_obj].max() 
                else: val_obj_mensual = 0
                
                val_proyeccion = val_real / prog_t if prog_t > 0 else 0

                if prorate_target: val_obj_parcial = val_obj_mensual * prog_t
                else:
                    val_obj_parcial = val_obj_mensual
                    val_proyeccion = val_real 
                
                if is_percent:
                    if val_real > 1.0: val_real /= 100
                    if val_obj_parcial > 1.0: val_obj_parcial /= 100
                    if val_obj_mensual > 1.0: val_obj_mensual /= 100
                    if val_proyeccion > 1.0: val_proyeccion /= 100
                    fmt = "{:.1%}"
                else:
                    fmt = "{:,.0f}" if not prorate_target else "{:,.1f}" 
                    
                return val_real, val_obj_parcial, val_obj_mensual, val_proyeccion, fmt

            # DATA
            nps_p_r, nps_p_p, nps_p_m, nps_p_proy, fmt_nps = get_calidad_data("NPS", "PEUGEOT", is_percent=False, prorate_target=False)
            nps_c_r, nps_c_p, nps_c_m, nps_c_proy, _ = get_calidad_data("NPS", "CITROEN", is_percent=False, prorate_target=False)
            vc_p_r, vc_p_p, vc_p_m, vc_p_proy, fmt_vc = get_calidad_data("VIDEO", "PEUGEOT", is_percent=False, prorate_target=True)
            vc_c_r, vc_c_p, vc_c_m, vc_c_proy, _ = get_calidad_data("VIDEO", "CITROEN", is_percent=False, prorate_target=True)
            ff_p_r, ff_p_p, ff_p_m, ff_p_proy, fmt_ff = get_calidad_data("FORFAIT", "PEUGEOT", is_percent=False, prorate_target=True)
            ff_c_r, ff_c_p, ff_c_m, ff_c_proy, _ = get_calidad_data("FORFAIT", "CITROEN", is_percent=False, prorate_target=True)

            c_peugeot, c_citroen = st.columns(2)
            with c_peugeot:
                st.markdown("#### 🦁 Peugeot")
                st.markdown(render_kpi_small("NPS", nps_p_r, nps_p_p, None, None, fmt_nps, label_target="Obj"), unsafe_allow_html=True)
                p_row = st.columns(2)
                with p_row[0]: st.markdown(render_kpi_small("Videocheck", vc_p_r, vc_p_p, vc_p_m, vc_p_proy, fmt_vc), unsafe_allow_html=True)
                with p_row[1]: st.markdown(render_kpi_small("Forfait", ff_p_r, ff_p_p, ff_p_m, ff_p_proy, fmt_ff), unsafe_allow_html=True)

            with c_citroen:
                st.markdown("#### 🔴 Citroën")
                st.markdown(render_kpi_small("NPS", nps_c_r, nps_c_p, None, None, fmt_nps, label_target="Obj"), unsafe_allow_html=True)
                c_row = st.columns(2)
                with c_row[0]: st.markdown(render_kpi_small("Videocheck", vc_c_r, vc_c_p, vc_c_m, vc_c_proy, fmt_vc), unsafe_allow_html=True)
                with c_row[1]: st.markdown(render_kpi_small("Forfait", ff_c_r, ff_c_p, ff_c_m, ff_c_proy, fmt_ff), unsafe_allow_html=True)
            
            # --- NUEVA SECCIÓN DE IRPV ---
            st.markdown("---")
            st.markdown("### 🔄 Fidelización (IRPV)")
            st.markdown("---")
            st.markdown("### 🔄 Fidelización (IRPV)")
            st.caption(f"Cálculo sobre vehículos entregados en el año seleccionado ({año_sel})")

            # --- MODIFICACIÓN: BOTONES DE CARGA ---
            col_load_1, col_load_2 = st.columns(2)
            
            with col_load_1:
                uploaded_ventas = st.file_uploader("📂 Cargar: Historial Entregas 0km", type=["csv", "xls", "xlsx"])
            
            with col_load_2:
                uploaded_taller = st.file_uploader("📂 Cargar: Historial Taller", type=["csv", "xls", "xlsx"])
            
            # Verificar si el usuario cargó ambos archivos
            if uploaded_ventas is not None and uploaded_taller is not None:
                # Pasamos los archivos cargados a la función
                df_irpv = calcular_irpv_local(uploaded_ventas, uploaded_taller)
                
                if df_irpv is not None and año_sel in df_irpv.index:
                    tasas = df_irpv.loc[año_sel]
                    irpv_1 = tasas['1er']
                    irpv_2 = tasas['2do']
                    irpv_3 = tasas['3er']
                    
                    st.success("✅ Datos procesados correctamente")
                    
                    col_i1, col_i2, col_i3 = st.columns(3)
                    with col_i1: st.markdown(render_kpi_small("1er Servicio (10k)", irpv_1, 0.80, None, None, "{:.1%}", "Obj. Ideal"), unsafe_allow_html=True)
                    with col_i2: st.markdown(render_kpi_small("2do Servicio (20k)", irpv_2, 0.60, None, None, "{:.1%}", "Obj. Ideal"), unsafe_allow_html=True)
                    with col_i3: st.markdown(render_kpi_small("3er Servicio (30k)", irpv_3, 0.40, None, None, "{:.1%}", "Obj. Ideal"), unsafe_allow_html=True)
                else:
                    st.info(f"⚠️ Se cargaron los archivos, pero no hay suficientes datos de entregas para el año {año_sel} o hubo un error en la lectura.")
            else:
                st.info("👆 Por favor, carga los dos archivos CSV para visualizar el IRPV.")
