import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Grupo CENOA - Gestión Posventa", layout="wide")

# --- ESTILOS CSS (DISEÑO COMPLETO) ---
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
    
    .cyp-detail { background-color: #f8f9fa; padding: 8px; border-radius: 6px; font-size: 0.8rem; margin-top: 5px; border-left: 3px solid #00235d; line-height: 1.3; }
    .cyp-header { font-weight: bold; color: #00235d; font-size: 0.85rem; margin-bottom: 2px; display: block; }
</style>""", unsafe_allow_html=True)

# --- FUNCIONES AUXILIARES ---

def find_col(df, include_keywords, exclude_keywords=[]):
    if df is None: return ""
    for col in df.columns:
        col_upper = str(col).upper()
        if all(k.upper() in col_upper for k in include_keywords):
            if not any(x.upper() in col_upper for x in exclude_keywords):
                return col
    return ""

@st.cache_data(ttl=60)
def cargar_datos(sheet_id):
    hojas = ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA']
    data_dict = {}
    try:
        for h in hojas:
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={h.replace(' ', '%20')}"
            df = pd.read_csv(url, dtype=str).fillna("0")
            df.columns = [
                c.strip().upper()
                .replace(".", "").replace("Á", "A").replace("É", "E")
                .replace("Í", "I").replace("Ó", "O").replace("Ú", "U").replace("Ñ", "N") 
                for c in df.columns
            ]
            for col in df.columns:
                if "FECHA" not in col and "CANAL" not in col and "ESTADO" not in col:
                    df[col] = df[col].astype(str).str.replace(r'[\$%\s]', '', regex=True).str.replace(',', '.')
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            
            # Fechas
            col_f = find_col(df, ["FECHA"]) or (df.columns[0] if not df.empty else None)
            if col_f:
                df['Fecha_dt'] = pd.to_datetime(df[col_f], dayfirst=True, errors='coerce')
                df['Mes'] = df['Fecha_dt'].dt.month
                df['Año'] = df['Fecha_dt'].dt.year
            
            data_dict[h] = df
        return data_dict
    except Exception as e:
        st.error(f"Error Google Sheets: {e}")
        return None

# --- FUNCIONES DE LECTURA E IRPV (NUEVA LÓGICA) ---

def leer_csv_inteligente(uploaded_file):
    try:
        uploaded_file.seek(0)
        preview = pd.read_csv(uploaded_file, header=None, nrows=20, sep=None, engine='python', encoding='utf-8', on_bad_lines='skip')
        idx_header = -1
        keywords = ['BASTIDOR', 'VIN', 'CHASIS', 'MATRICULA']
        for i, row in preview.iterrows():
            row_txt = " ".join([str(x).upper() for x in row.values])
            if any(kw in row_txt for kw in keywords):
                idx_header = i
                break
        if idx_header == -1: idx_header = 0
        
        uploaded_file.seek(0)
        try:
            df = pd.read_csv(uploaded_file, header=idx_header, sep=';', encoding='utf-8', on_bad_lines='skip')
            if len(df.columns) < 2: raise Exception
        except:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, header=idx_header, sep=',', encoding='utf-8', on_bad_lines='skip')
        return df, "OK"
    except Exception as e:
        return None, str(e)

def procesar_irpv(file_v, file_t):
    # 1. Ventas
    df_v, msg_v = leer_csv_inteligente(file_v)
    if df_v is None: return None, f"Ventas: {msg_v}"
    df_v.columns = [str(c).upper().strip() for c in df_v.columns]
    
    col_vin = next((c for c in df_v.columns if 'BASTIDOR' in c or 'VIN' in c), None)
    col_fec = next((c for c in df_v.columns if 'FEC' in c or 'ENTR' in c), None)
    
    if not col_vin or not col_fec: return None, "Ventas: Faltan columnas VIN/Fecha"

    def clean_date(x):
        if pd.isna(x) or str(x).strip() == '': return pd.NaT
        try: return pd.to_datetime(x, dayfirst=True)
        except: return pd.NaT

    df_v['Fecha_Entrega'] = df_v[col_fec].apply(clean_date)
    df_v['Año_Venta'] = df_v['Fecha_Entrega'].dt.year
    df_v['VIN'] = df_v[col_vin].astype(str).str.strip().str.upper()
    df_v = df_v.dropna(subset=['VIN', 'Fecha_Entrega'])

    # 2. Taller
    df_t, msg_t = leer_csv_inteligente(file_t)
    if df_t is None: return None, f"Taller: {msg_t}"
    df_t.columns = [str(c).upper().strip() for c in df_t.columns]
    
    col_vin_t = next((c for c in df_t.columns if 'BASTIDOR' in c or 'VIN' in c), None)
    col_fec_t = next((c for c in df_t.columns if 'CIERRE' in c or 'FEC' in c), None)
    col_km = next((c for c in df_t.columns if 'KM' in c), None)
    col_or = next((c for c in df_t.columns if 'TIPO' in c or 'O.R.' in c), None)
    col_desc = next((c for c in df_t.columns if 'DESCR' in c or 'OPER' in c or 'TRABAJO' in c), None)

    if not col_vin_t or not col_fec_t: return None, "Taller: Faltan columnas VIN/Fecha"

    df_t['Fecha_Servicio'] = df_t[col_fec_t].apply(clean_date)
    df_t['VIN'] = df_t[col_vin_t].astype(str).str.strip().str.upper()
    df_t['Km'] = pd.to_numeric(df_t[col_km], errors='coerce').fillna(0) if col_km else 0
    df_t['Texto'] = df_t[col_desc].astype(str).str.upper() if col_desc else ""

    if col_or:
        mask = ~df_t[col_or].astype(str).str.contains('CHAPA|PINTURA|SINIESTRO', case=False, na=False)
        df_t = df_t[mask]

    # --- CLASIFICACIÓN (La Lógica Mejorada) ---
    def clasif_hibrida(row):
        k = row['Km']
        t = row['Texto']
        # 1er
        if (2500 <= k <= 16500) or any(w in t for w in ["10.000", "10K", "1ER", "PRIMER", "DIEZ MIL"]): return "1er"
        # 2do
        if (16501 <= k <= 27000) or any(w in t for w in ["20.000", "20K", "2DO", "SEGUNDO", "VEINTE MIL"]): return "2do"
        # 3er
        if (27001 <= k <= 38000) or any(w in t for w in ["30.000", "30K", "3ER", "TERCER", "TREINTA MIL"]): return "3er"
        return None
    
    df_t['Hito'] = df_t.apply(clasif_hibrida, axis=1)
    df_validos = df_t.dropna(subset=['Hito'])
    
    pivot_dates = df_validos.pivot_table(index='VIN', columns='Hito', values='Fecha_Servicio', aggfunc='min').reset_index()
    merged = pd.merge(df_v, pivot_dates, on='VIN', how='left')

    # --- LÓGICA SECUENCIAL ---
    hoy = datetime.now()
    def evaluar(row, actual, anterior=None):
        if actual == '1er':
            base = row['Fecha_Entrega']
        else:
            base = row.get(anterior, pd.NaT)
            if pd.isna(base): return np.nan # Cadena rota
        
        if pd.isna(base): return np.nan
        limite = base + timedelta(days=365)
        hecho = row.get(actual, pd.NaT)
        
        if not pd.isna(hecho): return 1.0
        if hoy >= limite: return 0.0
        return np.nan # Aún no vence

    merged['R_1er'] = merged.apply(lambda r: evaluar(r, '1er'), axis=1)
    merged['R_2do'] = merged.apply(lambda r: evaluar(r, '2do', '1er'), axis=1)
    merged['R_3er'] = merged.apply(lambda r: evaluar(r, '3er', '2do'), axis=1)

    res = merged.groupby('Año_Venta')[['R_1er', 'R_2do', 'R_3er']].mean()
    res.columns = ['1er', '2do', '3er']
    return res, "OK"

# --- RENDERIZADORES DE VISUAL ---
def render_kpi_card(title, real, obj_mes, prog_t, is_currency=True, unit="", show_daily=False, d_t=1):
    obj_parcial = obj_mes * prog_t
    proy = (real / d_t) * (d_t/prog_t) if prog_t > 0 else 0 # Estimado simple
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

    html = f"""<div class="kpi-card">
        <div><p>{title}</p><h2>{fmt.format(real)}</h2>{daily_html}</div>
        <div><div class="kpi-subtext">vs Obj. Parcial: <b>{fmt.format(obj_parcial)}</b> <span style="color:{'#28a745' if real >= obj_parcial else '#dc3545'}">({cumpl_parcial_pct:.1%})</span> {icon}</div>
        <hr style="margin:5px 0; border:0; border-top:1px solid #eee;">
        <div style="display:flex; justify-content:space-between; font-size:0.75rem; margin-bottom:2px;"><span>Obj. Mes:</span><b>{fmt.format(obj_mes)}</b></div>
        <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:{color}; font-weight:bold;"><span>Proy:</span><span>{cumpl_proy:.1%}</span></div>
        <div style="margin-top:5px;"><div style="width:100%; background:#e0e0e0; height:5px; border-radius:10px;"><div style="width:{min(cumpl_proy*100, 100)}%; background:{color}; height:5px; border-radius:10px;"></div></div></div></div>
    </div>"""
    return html

def render_kpi_small(title, val, target=None, format_str="{:.1%}"):
    subtext = ""
    if target is not None:
        delta = val - target
        color = "#28a745" if delta >= 0 else "#dc3545"
        icon = "▲" if delta >= 0 else "▼"
        subtext = f"<div style='font-size:0.7rem; color:#888;'>Obj: {format_str.format(target)} <span style='color:{color}'>{icon}</span></div>"
    
    return f"""<div class="metric-card">
        <div><p style="color:#666; font-size:0.8rem; margin-bottom:2px;">{title}</p>
        <h3 style="color:#00235d; margin:0; font-size:1.3rem;">{format_str.format(val)}</h3>{subtext}</div>
    </div>"""

# --- APP PRINCIPAL ---
ID_SHEET = "1yJgaMR0nEmbKohbT_8Vj627Ma4dURwcQTQcQLPqrFwk"

try:
    data = cargar_datos(ID_SHEET)
    
    if data:
        # SideBar
        with st.sidebar:
            if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
            st.header("Filtros")
            anios = sorted([int(a) for a in data['CALENDARIO']['Año'].unique() if a > 0], reverse=True)
            anio_sel = st.selectbox("📅 Año", anios)
            
            meses_nom = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
            df_y = data['CALENDARIO'][data['CALENDARIO']['Año'] == anio_sel]
            mes_sel = st.selectbox("📅 Mes", sorted(df_y['Mes'].unique(), reverse=True), format_func=lambda x: meses_nom.get(x))

        # Helpers Datos
        def get_val(df_name, keys):
            df = data.get(df_name)
            if df is None: return 0
            row = df[(df['Año'] == anio_sel) & (df['Mes'] == mes_sel)]
            if row.empty: return 0
            col = find_col(df, keys, exclude_keywords=["OBJ"])
            return float(row[col].iloc[0]) if col else 0

        def get_obj(df_name, keys):
            df = data.get(df_name)
            if df is None: return 1
            row = df[(df['Año'] == anio_sel) & (df['Mes'] == mes_sel)]
            if row.empty: return 1
            col = find_col(df, ["OBJ"] + keys)
            return float(row[col].iloc[0]) if col else 1

        dias_hab = get_obj('CALENDARIO', ["HAB"])
        dias_trans = get_val('CALENDARIO', ["TRANS"])
        prog_t = min(dias_trans / dias_hab if dias_hab > 0 else 0, 1.0)
        
        # Portada
        st.markdown(f'''<div class="portada-container"><div class="portada-left"><h1>Autociel - Tablero Posventa</h1><h3>📅 {meses_nom.get(mes_sel)} {anio_sel}</h3></div>
        <div class="portada-right"><div>Avance: <b>{dias_trans:g}</b>/{dias_hab:g} días ({prog_t:.1%})</div><div style="background:rgba(255,255,255,0.3);height:6px;border-radius:4px;"><div style="background:#fff;width:{prog_t*100}%;height:100%;border-radius:4px;"></div></div></div></div>''', unsafe_allow_html=True)
        
        tabs = st.tabs(["🏠 Objetivos", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura", "📈 Histórico"])

        # TAB 1: OBJETIVOS
        with tabs[0]:
            c1, c2, c3, c4 = st.columns(4)
            real_mo = sum([get_val('SERVICIOS', ["MO", k]) for k in ["CLI", "GAR", "INT", "TER"]])
            obj_mo = get_obj('SERVICIOS', ["MO"])
            canales_rep = ['MOSTRADOR', 'TALLER', 'INTERNA', 'GAR', 'CYP', 'MAYORISTA', 'SEGUROS']
            real_rep = sum([get_val('REPUESTOS', ["VENTA", k]) for k in canales_rep])
            obj_rep = get_obj('REPUESTOS', ["FACT"])
            real_cj = get_val('CyP JUJUY', ["MO", "PUR"]) + get_val('CyP JUJUY', ["MO", "TER"]) + get_val('CyP JUJUY', ["FACT", "REP"])
            obj_cj = get_obj('CyP JUJUY', ["FACT"])
            real_cs = get_val('CyP SALTA', ["MO", "PUR"]) + get_val('CyP SALTA', ["MO", "TER"]) + get_val('CyP SALTA', ["FACT", "REP"])
            obj_cs = get_obj('CyP SALTA', ["FACT"])

            with c1: st.markdown(render_kpi_card("M.O. Servicios", real_mo, obj_mo, prog_t, d_t=dias_trans), unsafe_allow_html=True)
            with c2: st.markdown(render_kpi_card("Repuestos", real_rep, obj_rep, prog_t, d_t=dias_trans), unsafe_allow_html=True)
            with c3: st.markdown(render_kpi_card("CyP Jujuy", real_cj, obj_cj, prog_t, d_t=dias_trans), unsafe_allow_html=True)
            with c4: st.markdown(render_kpi_card("CyP Salta", real_cs, obj_cs, prog_t, d_t=dias_trans), unsafe_allow_html=True)

        # TAB 2: SERVICIOS
        with tabs[1]:
            # Parte Operativa
            c_main, c_br = st.columns([1, 2])
            with c_main: st.markdown(render_kpi_card("Facturación M.O.", real_mo, obj_mo, prog_t, d_t=dias_trans), unsafe_allow_html=True)
            with c_br:
                df_mo = pd.DataFrame({"Cargo": ["Cliente", "Garantía", "Interno", "Terceros"], 
                                      "Facturación": [get_val('SERVICIOS', ["MO", k]) for k in ["CLI", "GAR", "INT", "TER"]]})
                st.plotly_chart(px.bar(df_mo, x="Facturación", y="Cargo", orientation='h', text_auto='.2s', color="Cargo").update_layout(height=160, margin=dict(l=0,r=0,t=10,b=0)), use_container_width=True)
            
            k1, k2, k3, k4 = st.columns(4)
            cpus = get_val('SERVICIOS', ["CPUS"])
            obj_cpus = get_obj('SERVICIOS', ["CPUS"])
            tus = cpus + get_val('SERVICIOS', ["OTROS", "CARGOS"])
            
            with k1: st.markdown(render_kpi_small("CPUS", cpus, obj_cpus), unsafe_allow_html=True)
            with k2: st.markdown(render_kpi_small("TUS", tus, get_obj('SERVICIOS', ['TUS'])), unsafe_allow_html=True)
            
            # Calidad
            st.markdown("---")
            st.markdown("### 🏆 Calidad")
            nps_p = get_val('SERVICIOS', ["NPS", "PEUGEOT"])
            nps_c = get_val('SERVICIOS', ["NPS", "CITROEN"])
            q1, q2 = st.columns(2)
            with q1: st.markdown(render_kpi_small("NPS Peugeot", nps_p/100 if nps_p>1 else nps_p, 0.65), unsafe_allow_html=True)
            with q2: st.markdown(render_kpi_small("NPS Citroën", nps_c/100 if nps_c>1 else nps_c, 0.65), unsafe_allow_html=True)

            # Taller y Eficiencia
            st.markdown("---")
            st.markdown("### ⚙️ Taller y Eficiencia")
            hf_cc = get_val('TALLER', ["FACT", "CC"])
            ht_cc = get_val('TALLER', ["TRAB", "CC"])
            efi_cc = hf_cc / ht_cc if ht_cc > 0 else 0
            
            t1, t2 = st.columns(2)
            with t1: st.markdown(render_kpi_small("Eficiencia CC", efi_cc, 1.0), unsafe_allow_html=True)
            with t2:
                 prod = get_val('TALLER', ["PRODUCTIVIDAD"])
                 st.markdown(render_kpi_small("Productividad", prod/100 if prod>2 else prod, 0.95), unsafe_allow_html=True)

            # IRPV
            st.markdown("---")
            st.markdown("### 🔄 Fidelización (IRPV)")
            st.info("Sube CSV UTF-8. El análisis filtra autos nuevos (<1 año) para no ensuciar el dato.")
            up_v = st.file_uploader("Entregas 0km", type=["csv"], key="v")
            up_t = st.file_uploader("Historial Taller", type=["csv"], key="t")
            
            if up_v and up_t:
                df_irpv, msg = procesar_irpv(up_v, up_t)
                if df_irpv is not None:
                    anios_disp = sorted(df_irpv.index, reverse=True)
                    sel_anio = st.selectbox("📅 Año Cohorte:", anios_disp)
                    vals = df_irpv.loc[sel_anio]
                    i1, i2, i3 = st.columns(3)
                    with i1: st.metric("1er Service", f"{vals['1er']:.1%}", "Obj: 80%")
                    with i2: st.metric("2do Service", f"{vals['2do']:.1%}", "Obj: 60%")
                    with i3: st.metric("3er Service", f"{vals['3er']:.1%}", "Obj: 40%")
                    with st.expander("Ver Tabla"): st.dataframe(df_irpv.style.format("{:.1%}", na_rep="-"))
                else: st.error(msg)

        # TAB 3: REPUESTOS
        with tabs[2]:
            st.subheader("Gestión de Stock y Margen")
            c_input, c_kpi = st.columns([1, 2])
            with c_input: primas = st.number_input("💰 Primas/Rappels ($)", value=0.0, step=10000.0)
            
            items = []
            for c in canales_rep:
                vb = get_val('REPUESTOS', ["VENTA", c])
                cos = get_val('REPUESTOS', ["COSTO", c])
                items.append({"Canal": c, "Venta": vb, "Costo": cos, "Margen $": vb-cos, "Mg%": (vb-cos)/vb if vb>0 else 0})
            df_rep = pd.DataFrame(items)
            
            tot_ut = df_rep['Margen $'].sum() + primas
            tot_vt = df_rep['Venta'].sum()
            mg_global = tot_ut / tot_vt if tot_vt > 0 else 0
            
            with c_kpi:
                k1, k2 = st.columns(2)
                k1.metric("Utilidad Total", f"${tot_ut:,.0f}")
                k2.metric("Margen Global", f"{mg_global:.1%}", "Obj: 21%")
            
            st.dataframe(df_rep.style.format({"Venta":"${:,.0f}", "Costo":"${:,.0f}", "Margen $":"${:,.0f}", "Mg%":"{:.1%}"}), use_container_width=True)
            
            # Simulador Mix
            st.markdown("---")
            st.markdown("### 🎯 Simulador de Mix Ideal")
            cols = st.columns(3)
            new_mix = {}
            sum_mix = 0
            for i, row in df_rep.iterrows():
                with cols[i % 3]:
                    val = st.slider(f"% {row['Canal']}", 0, 100, int((row['Venta']/tot_vt)*100) if tot_vt>0 else 0, key=f"mx_{i}")
                    new_mix[row['Canal']] = val/100
                    sum_mix += val
            
            if abs(sum_mix - 100) > 1: st.error(f"El mix suma {sum_mix}%, debe ser 100%")
            else:
                sim_ut = sum([obj_rep * share * (df_rep.loc[df_rep['Canal']==c, 'Mg%'].values[0]) for c, share in new_mix.items()]) + primas
                st.success(f"Con este Mix, tu Utilidad Proyectada sería: **${sim_ut:,.0f}** (vs Actual ${tot_ut:,.0f})")

        # TAB 4: CyP
        with tabs[3]:
            c_ju, c_sa = st.columns(2)
            with c_ju:
                st.markdown("#### Jujuy")
                st.markdown(render_kpi_card("Facturación", real_cj, obj_cj, prog_t, d_t=dias_trans), unsafe_allow_html=True)
                panos = get_val('CyP JUJUY', ["PANOS"])
                st.markdown(render_kpi_small("Paños", panos, get_obj('CyP JUJUY', ["PANOS"]), "{:,.0f}"), unsafe_allow_html=True)
                # Detalle Terceros
                ter_j = get_val('CyP JUJUY', ["MO", "TER"])
                st.markdown(f'<div class="cyp-detail">Fact. Terceros: <b>${ter_j:,.0f}</b></div>', unsafe_allow_html=True)
            
            with c_sa:
                st.markdown("#### Salta")
                st.markdown(render_kpi_card("Facturación", real_cs, obj_cs, prog_t, d_t=dias_trans), unsafe_allow_html=True)
                panos_s = get_val('CyP SALTA', ["PANOS"])
                st.markdown(render_kpi_small("Paños", panos_s, get_obj('CyP SALTA', ["PANOS"]), "{:,.0f}"), unsafe_allow_html=True)
                ter_s = get_val('CyP SALTA', ["MO", "TER"])
                st.markdown(f'<div class="cyp-detail">Fact. Terceros: <b>${ter_s:,.0f}</b></div>', unsafe_allow_html=True)

        # TAB 5: HISTORICO
        with tabs[4]:
            st.subheader("Evolución Anual")
            df_h = data['SERVICIOS'][data['SERVICIOS']['Año'] == año_sel].sort_values('Mes')
            if not df_h.empty:
                col_y = find_col(df_h, ["MO", "CLI"])
                st.plotly_chart(px.bar(df_h, x='Mes', y=col_y, title="Facturación MO Cliente", text_auto='.2s'), use_container_width=True)
            else: st.info("Sin datos.")

    else: st.error("No data.")
except Exception as e: st.error(f"Error: {e}")
