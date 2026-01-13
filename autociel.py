import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# --- FUNCIÓN PARA CÁLCULO DE IRPV (FIDELIZACIÓN) ---
@st.cache_data(ttl=3600)
def calcular_irpv_local(archivo_ventas, archivo_taller):
    try:
        # 1. Cargar Ventas (0km)
        # Ajusta el nombre del archivo si es necesario
        df_v = pd.read_csv(archivo_ventas)
        
        # Función auxiliar para fechas Excel
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
        # Obtenemos lista única de VINs vendidos y sus hitos cumplidos
        df_merged = pd.merge(df_v, df_validos[['VIN', 'Servicio_Hito']], on='VIN', how='left')
        
        # Tabla dinámica: VIN vs Hito (1 si lo hizo, 0 si no)
        pivot = df_merged.pivot_table(index=['VIN', 'Año_Venta'], columns='Servicio_Hito', aggfunc='size', fill_value=0).reset_index()
        
        # Asegurar columnas
        for col in ['1er', '2do', '3er']:
            if col not in pivot.columns: pivot[col] = 0
            else: pivot[col] = pivot[col].apply(lambda x: 1 if x > 0 else 0)

        # Agrupar por Año de Venta (Cohorte)
        df_irpv = pivot.groupby('Año_Venta')[['1er', '2do', '3er']].mean()
        return df_irpv

    except Exception as e:
        return None
        
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
            
            st.markdown("---")
            st.markdown("### ⚙️ Taller")
            # --- TALLER LOGIC ---
            col_tecs = find_col(data['TALLER'], ["TECNICOS"], exclude_keywords=["PROD"])
            if not col_tecs: col_tecs = find_col(data['TALLER'], ["DOTACION"])
            cant_tecs = t_r.get(col_tecs, 6) 
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

        elif selected_tab == "📦 Repuestos":
            st.markdown("### 📦 Repuestos")
            
            # --- 1. INPUT DE PRIMAS / BONOS ---
            col_primas, col_vacia = st.columns([1, 3])
            with col_primas:
                primas_input = st.number_input("💰 Ingresar Primas/Rappels Estimados ($)", min_value=0.0, step=10000.0, format="%.0f", help="Este valor se sumará a la utilidad para calcular el margen real final.")

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
            
            # TOTALES
            vta_total_bruta = df_r['Venta Bruta'].sum() if not df_r.empty else 0
            vta_total_neta = df_r['Venta Neta'].sum() if not df_r.empty else 0
            util_total_operativa = df_r['Utilidad $'].sum() if not df_r.empty else 0
            
            # --- AJUSTE CON PRIMAS ---
            util_total_final = util_total_operativa + primas_input
            mg_total_final = util_total_final / vta_total_neta if vta_total_neta > 0 else 0
            
            obj_rep_total = r_r.get(find_col(data['REPUESTOS'], ["OBJ", "FACT"]), 1)
            costo_total_mes_actual = df_r['Costo'].sum() if not df_r.empty else 0
            val_stock = float(r_r.get(find_col(data['REPUESTOS'], ["VALOR", "STOCK"]), 0))
            
            c_main, c_kpis = st.columns([1, 3])
            with c_main: st.markdown(render_kpi_card("Fact. Bruta", vta_total_bruta, obj_rep_total), unsafe_allow_html=True)
            with c_kpis:
                r2, r3, r4 = st.columns(3)
                meses_stock = val_stock / costo_total_mes_actual if costo_total_mes_actual > 0 else 0
                with r2: st.markdown(render_kpi_small("Utilidad Total (+Primas)", util_total_final, None, None, None, "${:,.0f}"), unsafe_allow_html=True)
                with r3: st.markdown(render_kpi_small("Margen Global Real", mg_total_final, 0.21, None, None, "{:.1%}"), unsafe_allow_html=True)
                with r4: st.markdown(render_kpi_small("Meses Stock", meses_stock, 4.0, None, None, "{:.1f}"), unsafe_allow_html=True)

            if not df_r.empty:
                t_vb = df_r['Venta Bruta'].sum()
                t_desc = df_r['Desc.'].sum()
                t_vn = df_r['Venta Neta'].sum()
                t_cost = df_r['Costo'].sum()
                t_ut = df_r['Utilidad $'].sum()
                t_mg = t_ut / t_vn if t_vn != 0 else 0
                df_show = pd.concat([df_r, pd.DataFrame([{"Canal": "TOTAL OPERATIVO", "Venta Bruta": t_vb, "Desc.": t_desc, "Venta Neta": t_vn, "Costo": t_cost, "Utilidad $": t_ut, "Margen %": t_mg}])], ignore_index=True)
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
            
            st.markdown("---")
            
            # --- 2. CALCULADORA DE MIX IDEAL ---
            st.markdown("### 🎯 Calculadora de Mix y Estrategia Ideal")
            st.info("Define tu participación ideal por canal y el margen al que aspiras vender. El sistema te mostrará qué tan rentable es esa estrategia globalmente.")
            
            col_mix_input, col_mix_res = st.columns([3, 2])
            
            # Valores por defecto
            default_mix = {}
            default_margin = {}
            if vta_total_neta > 0:
                for idx, row in df_r.iterrows():
                    default_mix[row['Canal']] = (row['Venta Neta'] / vta_total_neta) * 100
                    default_margin[row['Canal']] = row['Margen %'] * 100
            
            mix_ideal = {}
            margin_ideal = {}
            sum_mix = 0
            
            with col_mix_input:
                for c in canales_repuestos:
                    val_def_mix = float(default_mix.get(c, 0.0))
                    val_def_marg = float(default_margin.get(c, 25.0))
                    
                    c1_s, c2_s = st.columns([2, 1])
                    with c1_s:
                        val_mix = st.slider(f"% Mix {c}", 0.0, 100.0, val_def_mix, 0.5, key=f"mix_{c}")
                    with c2_s:
                        val_marg = st.number_input(f"% Margen {c}", 0.0, 100.0, val_def_marg, 0.5, key=f"marg_{c}")
                    
                    mix_ideal[c] = val_mix / 100
                    margin_ideal[c] = val_marg / 100
                    sum_mix += val_mix
                
            with col_mix_res:
                st.markdown(f"#### Objetivo Mensual: ${obj_rep_total:,.0f}")
                
                # Indicador de Suma
                delta_sum = sum_mix - 100.0
                color_sum = "off"
                if abs(delta_sum) < 0.1: color_sum = "normal" # Verde por defecto en metric
                else: color_sum = "inverse" # Rojo por defecto en error
                
                st.metric("Suma del Mix Total", f"{sum_mix:.1f}%", f"{delta_sum:.1f}%", delta_color=color_sum)
                if abs(delta_sum) > 0.1:
                    st.error(f"⚠️ El mix debe sumar 100% (Actual: {sum_mix:.1f}%)")
                
                # Calculo de Estrategia
                ideal_data = []
                total_profit_ideal = 0
                for c, share in mix_ideal.items():
                    target_vta = obj_rep_total * share
                    target_marg = margin_ideal.get(c, 0)
                    profit = target_vta * target_marg
                    total_profit_ideal += profit
                    ideal_data.append({"Canal": c, "Mix": share, "Venta Obj": target_vta, "Mg Ideal": target_marg, "Utilidad": profit})
                
                global_margin_ideal = total_profit_ideal / obj_rep_total if obj_rep_total > 0 else 0
                
                st.markdown("#### Resultado Estratégico:")
                st.info(f"Con esta estrategia, tu **Margen Global Promedio** sería del **{global_margin_ideal:.1%}**")
                
                df_ideal = pd.DataFrame(ideal_data)
                st.dataframe(df_ideal.style.format({"Mix": "{:.1%}", "Venta Obj": "${:,.0f}", "Mg Ideal": "{:.1%}", "Utilidad": "${:,.0f}"}), hide_index=True)


            # --- 3. SIMULADOR DE MARGEN (CON PRIMAS) ---
            st.markdown("---")
            st.markdown("### 🎛️ Simulador What-If (Efecto Mix + Primas)")

            sim_data = []
            if not df_r.empty:
                for index, row in df_r.iterrows():
                    sim_data.append({"Canal": row['Canal'], "VentaBase": row['Venta Neta'], "MargenBase": row['Margen %']})
            else:
                for c in canales_repuestos: sim_data.append({"Canal": c, "VentaBase": 1000000, "MargenBase": 0.25})

            col_sim_inputs, col_sim_kpis = st.columns([1, 1])
            proyecciones = []
            
            with col_sim_inputs:
                st.markdown("#### 🔧 Ajuste de Proyecciones")
                with st.expander("Desplegar Controles por Canal", expanded=True):
                    for item in sim_data:
                        c_name = item['Canal']
                        base_v = float(item['VentaBase'])
                        base_m = float(item['MargenBase'])
                        cols_ctrl = st.columns([2, 2])
                        with cols_ctrl[0]:
                            new_v = st.number_input(f"Venta {c_name} ($)", value=base_v, min_value=0.0, step=100000.0, format="%.0f", key=f"sim_v_{c_name}")
                        with cols_ctrl[1]:
                            new_m = st.number_input(f"Margen {c_name} (%)", value=base_m * 100, min_value=0.0, max_value=100.0, step=0.5, format="%.1f", key=f"sim_m_{c_name}") / 100
                        proyecciones.append({"Canal": c_name, "Venta Proy": new_v, "Margen % Proy": new_m, "Utilidad Proy": new_v * new_m})

            df_sim = pd.DataFrame(proyecciones)
            total_v_sim = df_sim['Venta Proy'].sum()
            total_u_sim = df_sim['Utilidad Proy'].sum() + primas_input
            margen_global_sim = total_u_sim / total_v_sim if total_v_sim > 0 else 0
            
            with col_sim_kpis:
                st.markdown("#### 🎯 Resultado Simulado (Inc. Primas)")
                fig_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number+delta", value = margen_global_sim * 100,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': "Margen Global Real", 'font': {'size': 20}},
                    delta = {'reference': 21.0, 'increasing': {'color': "green"}, 'decreasing': {'color': "red"}},
                    gauge = {'axis': {'range': [0, 40], 'tickwidth': 1}, 'bar': {'color': "#00235d"}, 'bgcolor': "white", 'steps': [{'range': [0, 18], 'color': '#dc3545'}, {'range': [18, 21], 'color': '#ffc107'}, {'range': [21, 40], 'color': 'rgba(40, 167, 69, 0.3)'}], 'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 21.0}}
                ))
                fig_gauge.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=20))
                st.plotly_chart(fig_gauge, use_container_width=True)
                
                k1, k2 = st.columns(2)
                with k1: st.metric("Venta Total Proy.", f"${total_v_sim:,.0f}", f"{total_v_sim - vta_total_neta:,.0f} vs Real")
                with k2: st.metric("Utilidad Total Proy.", f"${total_u_sim:,.0f}", f"{total_u_sim - util_total_final:,.0f} vs Real")
                
                st.markdown("##### Contribución de Utilidad ($)")
                st.plotly_chart(px.bar(df_sim, x='Utilidad Proy', y='Canal', orientation='h', text_auto='.2s', color='Margen % Proy', color_continuous_scale='RdYlGn', range_color=[0.10, 0.40]).update_layout(height=250, margin=dict(l=0,r=0,t=0,b=0)), use_container_width=True)

        elif selected_tab == "🎨 Chapa y Pintura":
            st.markdown("### 🎨 Chapa y Pintura")
            
            c_mo_j = find_col(data['CyP JUJUY'], ['MO'], exclude_keywords=['TER', 'OBJ', 'PRE'])
            c_mo_t_j = find_col(data['CyP JUJUY'], ['MO', 'TERCERO'], exclude_keywords=['OBJ'])
            if not c_mo_t_j: c_mo_t_j = find_col(data['CyP JUJUY'], ['MO', 'TER'], exclude_keywords=['OBJ'])
            j_f_p = cj_r.get(c_mo_j, 0)
            j_f_t = cj_r.get(c_mo_t_j, 0)
            j_total_fact = j_f_p + j_f_t
            j_obj_fact = cj_r.get(find_col(data['CyP JUJUY'], ["OBJ", "FACT"]), 1)
            c_panos_j = find_col(data['CyP JUJUY'], ['PANOS'], exclude_keywords=['TER', 'OBJ', 'PRE'])
            if not c_panos_j: c_panos_j = find_col(data['CyP JUJUY'], ['PAÑOS'], exclude_keywords=['TER', 'OBJ', 'PRE'])
            j_panos_prop = cj_r.get(c_panos_j, 0)
            j_obj_panos = cj_r.get(find_col(data['CyP JUJUY'], ['OBJ', 'PANOS']), 1)
            c_tec_j = find_col(data['CyP JUJUY'], ['TECNICO'], exclude_keywords=['PRODUCTIVIDAD'])
            if not c_tec_j: c_tec_j = find_col(data['CyP JUJUY'], ['DOTACION'])
            j_cant_tec = cj_r.get(c_tec_j, 1)
            j_ratio = j_panos_prop / j_cant_tec if j_cant_tec > 0 else 0
            j_panos_ter = cj_r.get(find_col(data['CyP JUJUY'], ['PANOS', 'TER']), 0)
            j_c_ter = cj_r.get(find_col(data['CyP JUJUY'], ['COSTO', 'TER']), 0)
            j_m_ter = j_f_t - j_c_ter
            j_mg_ter_pct = j_m_ter/j_f_t if j_f_t > 0 else 0
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
                st.markdown(render_kpi_small("Paños/Técnico", j_ratio, None, None, None, "{:.1f}"), unsafe_allow_html=True)
                html_ter_j = f'<div class="cyp-detail"><span class="cyp-header">👨‍🔧 Gestión Terceros</span>Cant: <b>{j_panos_ter:,.0f}</b> | Fact: ${j_f_t:,.0f}<br>Mg: <b>${j_m_ter:,.0f}</b> ({j_mg_ter_pct:.1%})</div>'
                st.markdown(html_ter_j, unsafe_allow_html=True)
            with c_salta:
                st.subheader("Sede Salta")
                st.markdown(render_kpi_card("Fact. Total Salta", s_total_fact, s_obj_fact), unsafe_allow_html=True)
                st.markdown(render_kpi_card("Paños Propios", s_panos_prop, s_obj_panos, is_currency=False, unit="u"), unsafe_allow_html=True)
                st.markdown(render_kpi_small("Paños/Técnico", s_ratio, None, None, None, "{:.1f}"), unsafe_allow_html=True)
                html_ter_s = f'<div class="cyp-detail"><span class="cyp-header">👨‍🔧 Gestión Terceros</span>Cant: <b>{s_panos_ter:,.0f}</b> | Fact: ${s_f_t:,.0f}<br>Mg: <b>${s_m_ter:,.0f}</b> ({s_mg_ter_pct:.1%})</div>'
                st.markdown(html_ter_s, unsafe_allow_html=True)
                if s_f_r > 0: st.markdown(f'<div class="cyp-detail" style="border-left-color: #28a745;"><span class="cyp-header" style="color:#28a745">📦 Repuestos</span>Fact: ${s_f_r:,.0f} | Mg: <b>${s_m_rep:,.0f}</b> ({s_mg_rep_pct:.1%})</div>', unsafe_allow_html=True)

            g_jujuy, g_salta = st.columns(2)
            with g_jujuy: st.plotly_chart(px.pie(values=[j_f_p, j_f_t], names=["MO Pura", "Terceros"], hole=0.4, title="Facturación Jujuy", color_discrete_sequence=["#00235d", "#00A8E8"]), use_container_width=True)
            with g_salta: 
                vals_s, nams_s = [s_f_p, s_f_t], ["MO Pura", "Terceros"]
                if s_f_r > 0: vals_s.append(s_f_r); nams_s.append("Repuestos")
                st.plotly_chart(px.pie(values=vals_s, names=nams_s, hole=0.4, title="Facturación Salta", color_discrete_sequence=["#00235d", "#00A8E8", "#28a745"]), use_container_width=True)

        elif selected_tab == "📈 Histórico":
            st.markdown(f"### 📈 Evolución Anual {año_sel}")
            st.markdown("#### 🛠️ Servicios")
            
            col_hab_hist = find_col(h_cal, ["HAB"])
            col_tecs_hist = find_col(h_tal, ["TECNICOS"], exclude_keywords=["PROD", "EFIC"])
            if not col_tecs_hist: col_tecs_hist = find_col(h_tal, ["MECANICOS"], exclude_keywords=["PROD"])
            col_disp_hist = find_col(h_tal, ["DISPONIBLES", "REAL"])
            if not col_disp_hist: col_disp_hist = find_col(h_tal, ["DISP", "REAL"])
            if not col_disp_hist: col_disp_hist = find_col(h_tal, ["DISPONIBLE"]) 
            
            if col_hab_hist and col_disp_hist:
                df_capacidad = pd.merge(h_tal, h_cal[['Mes', col_hab_hist]], on='Mes', suffixes=('', '_cal'))
                if col_tecs_hist: cant_tecnicos_series = df_capacidad[col_tecs_hist].astype(float)
                else: cant_tecnicos_series = 6
                
                df_capacidad['Hs Ideales'] = cant_tecnicos_series * 8 * df_capacidad[col_hab_hist].astype(float)
                df_capacidad['Hs Reales'] = df_capacidad[col_disp_hist].astype(float)
                cols_trab_h = [c for c in [find_col(h_tal, ["TRAB", k]) for k in ["CC", "CG", "CI"]] if c]
                df_capacidad['Hs Ocupadas'] = df_capacidad[cols_trab_h].sum(axis=1) if cols_trab_h else 0
                
                fig_cap = go.Figure()
                fig_cap.add_trace(go.Scatter(x=df_capacidad['NombreMes'], y=df_capacidad['Hs Ideales'], name='Ideal (Teórico)', line=dict(color='gray', dash='dash')))
                fig_cap.add_trace(go.Bar(x=df_capacidad['NombreMes'], y=df_capacidad['Hs Reales'], name='Presencia Real', marker_color='#00235d'))
                fig_cap.add_trace(go.Bar(x=df_capacidad['NombreMes'], y=df_capacidad['Hs Ocupadas'], name='Hs Ocupadas', marker_color='#28a745'))
                st.plotly_chart(fig_cap.update_layout(title="Análisis de Capacidad: Ideal vs Real vs Ocupación", barmode='group', height=350), use_container_width=True)
            
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
            st.plotly_chart(fig_efi.update_layout(title="Eficiencia y Productividad", yaxis_tickformat='.0%', height=300), use_container_width=True)

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
            st.plotly_chart(fig_stk.update_layout(barmode='stack', title="Salud de Stock", height=300), use_container_width=True)

            fig_mix = go.Figure()
            for c in canales_repuestos:
                col_vta = find_col(h_rep, ["VENTA", c], exclude_keywords=["OBJ"])
                if col_vta: fig_mix.add_trace(go.Bar(x=h_rep['NombreMes'], y=h_rep[col_vta], name=c))
            st.plotly_chart(fig_mix.update_layout(barmode='stack', title="Venta Total por Canal (Apilado)", height=300), use_container_width=True)
            
            h_rep['CostoTotalMes'] = 0
            for c in canales_repuestos:
                 col_costo = find_col(h_rep, ["COSTO", c], exclude_keywords=["OBJ"])
                 if col_costo: h_rep['CostoTotalMes'] += h_rep[col_costo]
            
            h_rep['CostoPromedio3M'] = h_rep['CostoTotalMes'].rolling(window=3, min_periods=1).mean()
            col_val_stock = find_col(h_rep, ["VALOR", "STOCK"])
            
            if col_val_stock:
                h_rep['MesesStock'] = h_rep.apply(lambda row: row[col_val_stock] / row['CostoPromedio3M'] if row['CostoPromedio3M'] > 0 else 0, axis=1)
                st.plotly_chart(go.Figure(go.Scatter(x=h_rep['NombreMes'], y=h_rep['MesesStock'], name='Meses Stock', mode='lines+markers', line=dict(color='#6610f2', width=3))).update_layout(title="Evolución Meses de Stock (Stock / Costo Prom. 3 meses)", height=300), use_container_width=True)
            
            c_hist_j, c_hist_s = st.columns(2)
            col_pp_j = find_col(h_cyp_j, ['PANOS'], exclude_keywords=['TER', 'OBJ', 'PRE']) or find_col(h_cyp_j, ['PAÑOS'], exclude_keywords=['TER', 'OBJ'])
            col_pt_j = find_col(h_cyp_j, ['PANOS', 'TER']) or find_col(h_cyp_j, ['PAÑOS', 'TER'])
            h_cyp_j['Paños Propios'] = h_cyp_j[col_pp_j] if col_pp_j else 0
            h_cyp_j['Paños Terceros'] = h_cyp_j[col_pt_j] if col_pt_j else 0
            col_pp_s = find_col(h_cyp_s, ['PANOS'], exclude_keywords=['TER', 'OBJ']) or find_col(h_cyp_s, ['PAÑOS'], exclude_keywords=['TER', 'OBJ'])
            col_pt_s = find_col(h_cyp_s, ['PANOS', 'TER']) or find_col(h_cyp_s, ['PAÑOS', 'TER'])
            h_cyp_s['Paños Propios'] = h_cyp_s[col_pp_s] if col_pp_s else 0
            h_cyp_s['Paños Terceros'] = h_cyp_s[col_pt_s] if col_pt_s else 0
            
            with c_hist_j:
                fig_pj = go.Figure()
                fig_pj.add_trace(go.Bar(x=h_cyp_j['NombreMes'], y=h_cyp_j['Paños Propios'], name='Propios', marker_color='#00235d'))
                fig_pj.add_trace(go.Bar(x=h_cyp_j['NombreMes'], y=h_cyp_j['Paños Terceros'], name='Terceros', marker_color='#17a2b8'))
                st.plotly_chart(fig_pj.update_layout(barmode='stack', title="Evolución Jujuy (Paños)", height=300), use_container_width=True)
            with c_hist_s:
                fig_ps = go.Figure()
                fig_ps.add_trace(go.Bar(x=h_cyp_s['NombreMes'], y=h_cyp_s['Paños Propios'], name='Propios', marker_color='#00235d'))
                fig_ps.add_trace(go.Bar(x=h_cyp_s['NombreMes'], y=h_cyp_s['Paños Terceros'], name='Terceros', marker_color='#17a2b8'))
                st.plotly_chart(fig_ps.update_layout(barmode='stack', title="Evolución Salta (Paños)", height=300), use_container_width=True)

    else:
        st.warning("No se pudieron cargar los datos.")
except Exception as e:
    st.error(f"Error global: {e}")
