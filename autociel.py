import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import os

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Grupo CENOA - Gestión Posventa",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS ---
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
    .metric-footer {
        border-top: 1px solid #f0f0f0;
        margin-top: 8px;
        padding-top: 6px;
        font-size: 0.7rem;
        display: flex;
        justify-content: space-between;
        color: #666;
    }
    
    /* Ajustes Tabs y Radio Buttons */
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

# --- FUNCIONES AUXILIARES DE CARGA Y BÚSQUEDA ---

def find_col(df, include_keywords, exclude_keywords=[]):
    """Busca una columna en un DataFrame que contenga ciertas palabras clave."""
    if df is None: return ""
    for col in df.columns:
        col_upper = str(col).upper()
        if all(k.upper() in col_upper for k in include_keywords):
            if not any(x.upper() in col_upper for x in exclude_keywords):
                return col
    return ""

@st.cache_data(ttl=60)
def cargar_datos_gsheets(sheet_id):
    """Carga los datos desde Google Sheets."""
    hojas = ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA']
    data_dict = {}
    try:
        for h in hojas:
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={h.replace(' ', '%20')}"
            df = pd.read_csv(url, dtype=str).fillna("0")
            
            # Limpieza de cabeceras
            df.columns = [
                c.strip().upper()
                .replace(".", "")
                .replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
                .replace("Ñ", "N") 
                for c in df.columns
            ]
            
            # Limpieza de valores numéricos
            for col in df.columns:
                if "FECHA" not in col and "CANAL" not in col and "ESTADO" not in col:
                    df[col] = df[col].astype(str).str.replace(r'[\$%\s]', '', regex=True).str.replace(',', '.')
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            
            # Procesar fechas principales
            col_f = find_col(df, ["FECHA"]) or (df.columns[0] if not df.empty else None)
            if col_f:
                df['Fecha_dt'] = pd.to_datetime(df[col_f], dayfirst=True, errors='coerce')
                df['Mes'] = df['Fecha_dt'].dt.month
                df['Año'] = df['Fecha_dt'].dt.year
            
            data_dict[h] = df
        return data_dict
    except Exception as e:
        st.error(f"Error conectando con Google Sheets: {e}")
        return None

# --- FUNCIONES PARA IRPV LOCAL (ARCHIVOS CSV) ---

def leer_csv_inteligente(uploaded_file):
    """Lee archivos CSV buscando la cabecera correcta automáticamente."""
    try:
        uploaded_file.seek(0)
        # Pre-lectura para encontrar cabecera
        preview = pd.read_csv(uploaded_file, header=None, nrows=20, sep=None, engine='python', encoding='utf-8', on_bad_lines='skip')
        
        idx_header = -1
        keywords = ['BASTIDOR', 'VIN', 'CHASIS', 'MATRICULA']
        
        for i, row in preview.iterrows():
            row_txt = " ".join([str(x).upper() for x in row.values])
            if any(kw in row_txt for kw in keywords):
                idx_header = i
                break
        
        if idx_header == -1: idx_header = 0
        
        # Lectura completa
        uploaded_file.seek(0)
        try:
            # Intento 1: Separador punto y coma
            df = pd.read_csv(uploaded_file, header=idx_header, sep=';', encoding='utf-8', on_bad_lines='skip')
            if len(df.columns) < 2: raise Exception("Pocas columnas")
        except:
            # Intento 2: Separador coma
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, header=idx_header, sep=',', encoding='utf-8', on_bad_lines='skip')
            
        return df, "OK"
    except Exception as e:
        return None, str(e)

def procesar_irpv(file_v, file_t):
    """Procesa los archivos de Ventas y Taller para calcular fidelización."""
    
    # 1. CARGAR VENTAS
    df_v, msg_v = leer_csv_inteligente(file_v)
    if df_v is None: return None, f"Error en archivo de Ventas: {msg_v}"
    df_v.columns = [str(c).upper().strip() for c in df_v.columns]
    
    col_vin = next((c for c in df_v.columns if 'BASTIDOR' in c or 'VIN' in c or 'CHASIS' in c), None)
    col_fec = next((c for c in df_v.columns if 'FEC' in c or 'ENTR' in c), None)
    
    if not col_vin or not col_fec: return None, f"Ventas: No se encuentran columnas VIN/FECHA. Cols: {list(df_v.columns)}"

    def clean_date(x):
        if pd.isna(x) or str(x).strip() == '': return pd.NaT
        try: return pd.to_datetime(x, dayfirst=True)
        except: return pd.NaT

    df_v['Fecha_Entrega'] = df_v[col_fec].apply(clean_date)
    df_v['Año_Venta'] = df_v['Fecha_Entrega'].dt.year
    df_v['VIN'] = df_v[col_vin].astype(str).str.strip().str.upper()
    df_v = df_v.dropna(subset=['VIN', 'Fecha_Entrega'])

    # 2. CARGAR TALLER
    df_t, msg_t = leer_csv_inteligente(file_t)
    if df_t is None: return None, f"Error en archivo de Taller: {msg_t}"
    df_t.columns = [str(c).upper().strip() for c in df_t.columns]
    
    col_vin_t = next((c for c in df_t.columns if 'BASTIDOR' in c or 'VIN' in c), None)
    col_fec_t = next((c for c in df_t.columns if 'CIERRE' in c or 'FEC' in c), None)
    col_km = next((c for c in df_t.columns if 'KM' in c), None)
    col_or = next((c for c in df_t.columns if 'TIPO' in c or 'O.R.' in c), None)
    col_desc = next((c for c in df_t.columns if 'DESCR' in c or 'OPER' in c or 'TRABAJO' in c), None)

    if not col_vin_t or not col_fec_t: return None, f"Taller: No se encuentran columnas VIN/FECHA. Cols: {list(df_t.columns)}"

    df_t['Fecha_Servicio'] = df_t[col_fec_t].apply(clean_date)
    df_t['VIN'] = df_t[col_vin_t].astype(str).str.strip().str.upper()
    df_t['Km'] = pd.to_numeric(df_t[col_km], errors='coerce').fillna(0) if col_km else 0
    df_t['Texto'] = df_t[col_desc].astype(str).str.upper() if col_desc else ""

    if col_or:
        # Excluir Chapa y Pintura
        mask = ~df_t[col_or].astype(str).str.contains('CHAPA|PINTURA|SINIESTRO', case=False, na=False)
        df_t = df_t[mask]

    # --- CLASIFICACIÓN HÍBRIDA (KM + TEXTO) ---
    def clasif_hibrida(row):
        k = row['Km']
        t = row['Texto']
        
        # 1er Service (10k)
        if (2500 <= k <= 16500) or any(w in t for w in ["10.000", "10K", "1ER", "PRIMER", "DIEZ MIL"]): return "1er"
        # 2do Service (20k)
        if (16501 <= k <= 27000) or any(w in t for w in ["20.000", "20K", "2DO", "SEGUNDO", "VEINTE MIL"]): return "2do"
        # 3er Service (30k)
        if (27001 <= k <= 38000) or any(w in t for w in ["30.000", "30K", "3ER", "TERCER", "TREINTA MIL"]): return "3er"
        
        return None
    
    df_t['Hito'] = df_t.apply(clasif_hibrida, axis=1)
    df_validos = df_t.dropna(subset=['Hito'])

    # Obtener fechas de cada hito
    pivot_dates = df_validos.pivot_table(index='VIN', columns='Hito', values='Fecha_Servicio', aggfunc='min').reset_index()
    
    merged = pd.merge(df_v, pivot_dates, on='VIN', how='left')

    # --- LÓGICA DE TIEMPO Y CADENA ---
    hoy = datetime.now()

    def evaluar_retencion(row, hito_actual, hito_anterior=None):
        # Determinar fecha base
        if hito_actual == '1er':
            f_base = row['Fecha_Entrega']
        else:
            f_anterior = row.get(hito_anterior, pd.NaT)
            # Si no hizo el anterior, cadena rota -> No cuenta en denominador
            if pd.isna(f_anterior): return np.nan
            f_base = f_anterior

        if pd.isna(f_base): return np.nan

        f_limite = f_base + timedelta(days=365)
        f_actual = row.get(hito_actual, pd.NaT)
        
        if not pd.isna(f_actual): return 1.0 # Hecho
        if hoy >= f_limite: return 0.0 # Vencido (Fuga)
        return np.nan # Aún en plazo (No cuenta)

    merged['R_1er'] = merged.apply(lambda r: evaluar_retencion(r, '1er'), axis=1)
    merged['R_2do'] = merged.apply(lambda r: evaluar_retencion(r, '2do', '1er'), axis=1)
    merged['R_3er'] = merged.apply(lambda r: evaluar_retencion(r, '3er', '2do'), axis=1)

    res = merged.groupby('Año_Venta')[['R_1er', 'R_2do', 'R_3er']].mean()
    res.columns = ['1er', '2do', '3er'] # Renombrar para visualización
    return res, "OK"

# --- MAIN APP ---

ID_SHEET = "1yJgaMR0nEmbKohbT_8Vj627Ma4dURwcQTQcQLPqrFwk"

try:
    data = cargar_datos_gsheets(ID_SHEET)
    
    if data:
        # --- SIDEBAR: FILTROS ---
        with st.sidebar:
            if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
            st.header("Filtros")
            
            # Selector Año
            anios_disp = sorted([int(a) for a in data['CALENDARIO']['Año'].unique() if a > 0], reverse=True)
            año_sel = st.selectbox("📅 Año", anios_disp)
            
            # Selector Mes
            meses_nom = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
            df_year = data['CALENDARIO'][data['CALENDARIO']['Año'] == año_sel]
            meses_disp = sorted(df_year['Mes'].unique(), reverse=True)
            mes_sel = st.selectbox("📅 Mes", meses_disp, format_func=lambda x: meses_nom.get(x, "N/A"))

        # --- PREPARACIÓN DE DATOS DEL MES ---
        def get_val(df_name, keys):
            df = data.get(df_name)
            if df is None: return 0
            row = df[(df['Año'] == año_sel) & (df['Mes'] == mes_sel)]
            if row.empty: return 0
            col = find_col(df, keys, exclude_keywords=["OBJ"])
            return float(row[col].iloc[0]) if col else 0

        def get_obj(df_name, keys):
            df = data.get(df_name)
            if df is None: return 1
            row = df[(df['Año'] == año_sel) & (df['Mes'] == mes_sel)]
            if row.empty: return 1
            col = find_col(df, ["OBJ"] + keys)
            return float(row[col].iloc[0]) if col else 1

        # Cálculo de Avance
        dias_hab = get_obj('CALENDARIO', ["HAB"])
        dias_trans = get_val('CALENDARIO', ["TRANS"])
        prog_t = min(dias_trans / dias_hab if dias_hab > 0 else 0, 1.0)

        # --- PORTADA ---
        st.markdown(f'''
        <div class="portada-container">
            <div class="portada-left">
                <h1>Autociel - Tablero Posventa</h1>
                <h3>📅 {meses_nom.get(mes_sel)} {año_sel}</h3>
            </div>
            <div class="portada-right">
                <div>Avance: <b>{dias_trans:g}</b>/{dias_hab:g} días ({prog_t:.1%})</div>
                <div style="background: rgba(255,255,255,0.3); height: 6px; border-radius: 4px; width: 100%;">
                    <div style="background: #fff; width: {prog_t*100}%; height: 100%; border-radius: 4px;"></div>
                </div>
            </div>
        </div>
        ''', unsafe_allow_html=True)

        # --- PESTAÑAS PRINCIPALES ---
        tabs = st.tabs(["🏠 Objetivos", "🛠️ Servicios y Fidelización", "📦 Repuestos", "🎨 Chapa y Pintura", "📈 Histórico"])

        # --- TAB 1: OBJETIVOS ---
        with tabs[0]:
            c1, c2, c3, c4 = st.columns(4)
            
            # MO Servicios Total
            real_mo = sum([get_val('SERVICIOS', ["MO", k]) for k in ["CLI", "GAR", "INT", "TER"]])
            obj_mo = get_obj('SERVICIOS', ["MO"])
            
            # Repuestos Total
            canales_rep = ['MOSTRADOR', 'TALLER', 'INTERNA', 'GAR', 'CYP', 'MAYORISTA', 'SEGUROS']
            real_rep = sum([get_val('REPUESTOS', ["VENTA", k]) for k in canales_rep])
            obj_rep = get_obj('REPUESTOS', ["FACT"])
            
            # CyP Total Jujuy
            real_cj = get_val('CyP JUJUY', ["MO", "PUR"]) + get_val('CyP JUJUY', ["MO", "TER"]) + get_val('CyP JUJUY', ["FACT", "REP"])
            obj_cj = get_obj('CyP JUJUY', ["FACT"])
            
            # CyP Total Salta
            real_cs = get_val('CyP SALTA', ["MO", "PUR"]) + get_val('CyP SALTA', ["MO", "TER"]) + get_val('CyP SALTA', ["FACT", "REP"])
            obj_cs = get_obj('CyP SALTA', ["FACT"])

            # Render Cards
            def kpi_card(title, real, target):
                delta = real - target
                color = "green" if delta >= 0 else "red"
                st.markdown(f"""
                <div class="kpi-card">
                    <p>{title}</p>
                    <h2>${real:,.0f}</h2>
                    <div class="kpi-subtext">Obj: ${target:,.0f} <span style="color:{color}">({real/target if target>0 else 0:.1%})</span></div>
                </div>
                """, unsafe_allow_html=True)
            
            with c1: kpi_card("M.O. Servicios", real_mo, obj_mo)
            with c2: kpi_card("Repuestos", real_rep, obj_rep)
            with c3: kpi_card("CyP Jujuy", real_cj, obj_cj)
            with c4: kpi_card("CyP Salta", real_cs, obj_cs)

        # --- TAB 2: SERVICIOS Y IRPV ---
        with tabs[1]:
            col_metrics, col_irpv = st.columns([1, 1])
            
            with col_metrics:
                st.subheader("Indicadores Operativos")
                cpus = get_val('SERVICIOS', ["CPUS"])
                obj_cpus = get_obj('SERVICIOS', ["CPUS"])
                tus = cpus + get_val('SERVICIOS', ["OTROS", "CARGOS"])
                
                m1, m2 = st.columns(2)
                m1.metric("CPUS (Entradas)", f"{cpus:.0f}", f"Obj: {obj_cpus:.0f}")
                m2.metric("TUS Total", f"{tus:.0f}", f"Obj: {get_obj('SERVICIOS', ['TUS']):.0f}")
                
                # Calidad
                st.markdown("##### Calidad (NPS)")
                nps_p = get_val('SERVICIOS', ["NPS", "PEUGEOT"])
                nps_c = get_val('SERVICIOS', ["NPS", "CITROEN"])
                q1, q2 = st.columns(2)
                q1.metric("NPS Peugeot", f"{nps_p:.1f}%")
                q2.metric("NPS Citroën", f"{nps_c:.1f}%")

            with col_irpv:
                st.subheader("🔄 Fidelización (IRPV)")
                st.info("Sube archivos CSV (UTF-8) para analizar la retención.")
                
                up_v = st.file_uploader("📂 Entregas 0km (.csv)", type=["csv"], key="up_v")
                up_t = st.file_uploader("📂 Historial Taller (.csv)", type=["csv"], key="up_t")
                
                if up_v and up_t:
                    with st.spinner("Procesando datos y calculando maduración..."):
                        df_irpv, msg = procesar_irpv(up_v, up_t)
                    
                    if df_irpv is not None:
                        st.success("✅ Datos Procesados")
                        anios_disp = sorted(df_irpv.index.tolist(), reverse=True)
                        
                        st.markdown("---")
                        col_sel, _ = st.columns([2, 1])
                        with col_sel:
                            anio_cohorte = st.selectbox("📅 Analizar Cohorte (Año Venta):", anios_disp)
                        
                        vals = df_irpv.loc[anio_cohorte]
                        
                        k1, k2, k3 = st.columns(3)
                        
                        def card_irpv(label, val, target):
                            st.metric(label, f"{val:.1%}" if not pd.isna(val) else "Pendiente", f"Obj: {target}")

                        with k1: card_irpv("1er Service", vals['1er'], "80%")
                        with k2: card_irpv("2do Service", vals['2do'], "60%")
                        with k3: card_irpv("3er Service", vals['3er'], "40%")
                        
                        st.caption(f"Nota: Los porcentajes reflejan la retención de clientes de {anio_cohorte} que ya cumplieron el plazo para volver.")
                        
                        with st.expander("Ver Tabla Detallada por Año"):
                            st.dataframe(df_irpv.style.format("{:.1%}", na_rep="-"), use_container_width=True)
                    else:
                        st.error(f"❌ Error: {msg}")

        # --- TAB 3: REPUESTOS ---
        with tabs[2]:
            st.subheader("Gestión de Stock y Margen")
            
            col_inputs, col_kpis = st.columns([1, 2])
            with col_inputs:
                primas = st.number_input("💰 Primas/Rappels Estimados ($)", value=0.0, step=10000.0)
            
            items = []
            for c in canales_rep:
                vb = get_val('REPUESTOS', ["VENTA", c])
                cos = get_val('REPUESTOS', ["COSTO", c])
                items.append({"Canal": c, "Venta": vb, "Costo": cos, "Margen $": vb-cos})
            
            df_rep = pd.DataFrame(items)
            total_ut = df_rep['Margen $'].sum() + primas
            total_vt = df_rep['Venta'].sum()
            mg_pct = total_ut / total_vt if total_vt > 0 else 0
            
            with col_kpis:
                r1, r2 = st.columns(2)
                r1.metric("Utilidad Total (+Primas)", f"${total_ut:,.0f}")
                r2.metric("Margen Global Real", f"{mg_pct:.1%}", "Obj: 21%")
            
            st.dataframe(df_rep.style.format({"Venta":"${:,.0f}", "Costo":"${:,.0f}", "Margen $":"${:,.0f}"}), use_container_width=True)
            
            # Stock Status
            st.subheader("Salud de Stock")
            val_stock = get_val('REPUESTOS', ["VALOR", "STOCK"])
            p_vivo = get_val('REPUESTOS', ["VIVO"])
            p_obs = get_val('REPUESTOS', ["OBSOLETO"])
            p_muerto = get_val('REPUESTOS', ["MUERTO"])
            
            # Normalizar si viene en % o decimal
            f = 1 if p_vivo <= 1 else 100
            df_stock = pd.DataFrame({
                "Estado": ["Vivo", "Obsoleto", "Muerto"],
                "Valor": [val_stock*(p_vivo/f), val_stock*(p_obs/f), val_stock*(p_muerto/f)]
            })
            
            fig_stock = px.pie(df_stock, values='Valor', names='Estado', hole=0.4, color='Estado',
                               color_discrete_map={"Vivo":"#28a745", "Obsoleto":"#ffc107", "Muerto":"#dc3545"})
            st.plotly_chart(fig_stock, use_container_width=True)

        # --- TAB 4: CyP ---
        with tabs[3]:
            st.subheader("Gestión Chapa y Pintura")
            
            cj, cs = st.columns(2)
            with cj:
                st.markdown("#### 🌵 Sede Jujuy")
                st.metric("Facturación Total", f"${real_cj:,.0f}", f"Obj: ${obj_cj:,.0f}")
                panos_j = get_val('CyP JUJUY', ["PANOS"])
                st.metric("Paños Propios", f"{panos_j:.0f}")
                
            with cs:
                st.markdown("#### ⛰️ Sede Salta")
                st.metric("Facturación Total", f"${real_cs:,.0f}", f"Obj: ${obj_cs:,.0f}")
                panos_s = get_val('CyP SALTA', ["PANOS"])
                st.metric("Paños Propios", f"{panos_s:.0f}")

        # --- TAB 5: HISTÓRICO ---
        with tabs[4]:
            st.subheader(f"Evolución Anual - {año_sel}")
            
            df_hist = data['SERVICIOS'][data['SERVICIOS']['Año'] == año_sel].copy()
            if not df_hist.empty:
                # Ordenar por mes
                df_hist = df_hist.sort_values('Mes')
                col_mo_cli = find_col(df_hist, ["MO", "CLI"])
                
                fig_hist = px.bar(df_hist, x='Mes', y=col_mo_cli, title="Evolución Facturación MO Cliente",
                                  labels={'Mes': 'Mes', col_mo_cli: 'Facturación ($)'})
                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.info("No hay datos históricos para este año.")

    else:
        st.warning("No se pudieron cargar los datos de Google Sheets.")

except Exception as e:
    st.error(f"Error Global en la aplicación: {e}")
