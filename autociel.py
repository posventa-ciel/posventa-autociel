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
    .kpi-card { background-color: white; border: 1px solid #e0e0e0; padding: 12px 15px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 8px; min-height: 145px; display: flex; flex-direction: column; justify-content: space-between; }
    .metric-card { background-color: white; border: 1px solid #eee; padding: 10px; border-radius: 8px; text-align: center; min-height: 110px; }
</style>""", unsafe_allow_html=True)

# --- FUNCIÓN DE BÚSQUEDA ---
def find_col(df, include_keywords, exclude_keywords=[]):
    if df is None: return ""
    for col in df.columns:
        col_upper = str(col).upper()
        if all(k.upper() in col_upper for k in include_keywords):
            if not any(x.upper() in col_upper for x in exclude_keywords):
                return col
    return ""

# --- CARGA DATOS GSHEETS ---
@st.cache_data(ttl=60)
def cargar_datos(sheet_id):
    hojas = ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA']
    data_dict = {}
    for h in hojas:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={h.replace(' ', '%20')}"
        try:
            df = pd.read_csv(url, dtype=str).fillna("0")
            df.columns = [c.strip().upper().replace(".", "").replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U").replace("Ñ", "N") for c in df.columns]
            for col in df.columns:
                if "FECHA" not in col and "CANAL" not in col and "ESTADO" not in col:
                    df[col] = df[col].astype(str).str.replace(r'[\$%\s]', '', regex=True).str.replace(',', '.')
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            data_dict[h] = df
        except Exception as e:
            st.error(f"Error hoja {h}: {e}")
            return None
    return data_dict

# --- LECTURA DE CSV LIMPIOS (Busca la cabecera automáticamente) ---
def leer_csv_inteligente(uploaded_file):
    try:
        # Leemos las primeras 20 lineas para encontrar dónde empieza la tabla
        uploaded_file.seek(0)
        preview = pd.read_csv(uploaded_file, header=None, nrows=20, sep=None, engine='python', encoding='utf-8', on_bad_lines='skip')
        
        # Buscamos palabras clave
        idx_header = -1
        keywords = ['BASTIDOR', 'VIN', 'CHASIS', 'MATRICULA']
        
        for i, row in preview.iterrows():
            row_txt = " ".join([str(x).upper() for x in row.values])
            if any(kw in row_txt for kw in keywords):
                idx_header = i
                break
        
        # Si no encuentra cabecera, asume la fila 0
        if idx_header == -1: idx_header = 0
        
        # Leemos el archivo completo saltando las filas basura
        uploaded_file.seek(0)
        # Probamos separador ; primero (Excel CSV español)
        try:
            df = pd.read_csv(uploaded_file, header=idx_header, sep=';', encoding='utf-8')
            if len(df.columns) < 2: raise Exception("Pocas columnas")
        except:
            # Si falla, probamos coma (CSV estándar)
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, header=idx_header, sep=',', encoding='utf-8')
            
        return df, "OK"
    except Exception as e:
        return None, str(e)

# --- PROCESAMIENTO IRPV (LÓGICA SECUENCIAL + TIEMPO) ---
def procesar_irpv(file_v, file_t):
    from datetime import timedelta
    import numpy as np
    
    # 1. Cargar Ventas
    df_v, msg_v = leer_csv_inteligente(file_v)
    if df_v is None: return None, f"Error Ventas: {msg_v}"
    df_v.columns = [str(c).upper().strip() for c in df_v.columns]
    
    col_vin = next((c for c in df_v.columns if 'BASTIDOR' in c or 'VIN' in c or 'CHASIS' in c), None)
    col_fec = next((c for c in df_v.columns if 'FEC' in c or 'ENTR' in c), None)
    
    if not col_vin or not col_fec: return None, f"Ventas: Faltan columnas clave. Cols: {list(df_v.columns)}"

    def clean_date(x):
        if pd.isna(x) or str(x).strip() == '': return None
        try: return pd.to_datetime(x, dayfirst=True)
        except: return None

    df_v['Fecha_Entrega'] = df_v[col_fec].apply(clean_date)
    df_v['Año_Venta'] = df_v['Fecha_Entrega'].dt.year
    df_v['VIN'] = df_v[col_vin].astype(str).str.strip().str.upper()
    df_v = df_v.dropna(subset=['VIN', 'Fecha_Entrega'])

    # 2. Cargar Taller
    df_t, msg_t = leer_csv_inteligente(file_t)
    if df_t is None: return None, f"Error Taller: {msg_t}"
    df_t.columns = [str(c).upper().strip() for c in df_t.columns]
    
    col_vin_t = next((c for c in df_t.columns if 'BASTIDOR' in c or 'VIN' in c), None)
    col_fec_t = next((c for c in df_t.columns if 'CIERRE' in c or 'FEC' in c), None)
    col_km = next((c for c in df_t.columns if 'KM' in c), None)
    col_or = next((c for c in df_t.columns if 'TIPO' in c or 'O.R.' in c), None)
    col_desc = next((c for c in df_t.columns if 'DESCR' in c or 'OPER' in c or 'TRABAJO' in c), None)

    if not col_vin_t or not col_fec_t: return None, f"Taller: Faltan columnas clave. Cols: {list(df_t.columns)}"

    df_t['Fecha_Servicio'] = df_t[col_fec_t].apply(clean_date)
    df_t['VIN'] = df_t[col_vin_t].astype(str).str.strip().str.upper()
    if col_km: df_t['Km'] = pd.to_numeric(df_t[col_km], errors='coerce').fillna(0)
    else: df_t['Km'] = 0
    
    if col_desc: df_t['Texto'] = df_t[col_desc].astype(str).str.upper()
    else: df_t['Texto'] = ""

    if col_or:
        mask = ~df_t[col_or].astype(str).str.contains('CHAPA|PINTURA|SINIESTRO', case=False, na=False)
        df_t = df_t[mask]

    # --- CLASIFICACIÓN DE HITOS (Híbrida) ---
    def clasif_hibrida(row):
        k = row['Km']
        t = row['Texto']
        
        # 1er Service (10k)
        if (2500 <= k <= 16500) or any(w in t for w in ["10.000", "10000", "10K", "10 KM", "DIEZ MIL", "1ER", "PRIMER"]): return "1er"
        
        # 2do Service (20k)
        if (16501 <= k <= 27000) or any(w in t for w in ["20.000", "20000", "20K", "20 KM", "VEINTE MIL", "2DO", "SEGUNDO"]): return "2do"
        
        # 3er Service (30k)
        if (27001 <= k <= 38000) or any(w in t for w in ["30.000", "30000", "30K", "30 KM", "TREINTA MIL", "3ER", "TERCER"]): return "3er"
        
        return None
    
    df_t['Hito'] = df_t.apply(clasif_hibrida, axis=1)
    df_validos = df_t.dropna(subset=['Hito'])

    # 3. OBTENER FECHAS REALES DE CADA SERVICIO
    # Pivotamos para tener una columna con la FECHA de cada servicio por VIN
    pivot_dates = df_validos.pivot_table(index='VIN', columns='Hito', values='Fecha_Servicio', aggfunc='min').reset_index()
    
    # Unimos con Ventas
    merged = pd.merge(df_v, pivot_dates, on='VIN', how='left')

    # --- LÓGICA DE TIEMPO (LA PARTE CLAVE) ---
    hoy = datetime.now()

    def evaluar_retencion(row, hito_actual, hito_anterior=None):
        # Fecha base para contar los 12 meses
        if hito_actual == '1er':
            f_base = row['Fecha_Entrega']
        else:
            # Para 2do y 3er, dependemos de que haya hecho el anterior
            f_anterior = row.get(hito_anterior, pd.NaT) # Fecha del hito anterior (columna se llama '1er', '2do'...)
            if pd.isna(f_anterior):
                # Si no hizo el anterior, la cadena se rompió. 
                # Retornamos NaN para no contarlo en el denominador (Retención Condicional)
                return np.nan
            f_base = f_anterior

        # Fecha límite (Vencimiento) = Fecha Base + 365 días
        f_limite = f_base + timedelta(days=365)
        
        # Fecha real del servicio actual
        f_actual = row.get(hito_actual, pd.NaT)
        
        # CASO 1: YA LO HIZO
        if not pd.isna(f_actual):
            return 1.0 # Éxito
        
        # CASO 2: NO LO HIZO, PERO YA PASÓ EL AÑO (VENCIDO)
        if hoy >= f_limite:
            return 0.0 # Fracaso (Fuga)
            
        # CASO 3: NO LO HIZO, PERO TODAVÍA TIENE TIEMPO (INMADURO)
        return np.nan # Pendiente (No cuenta en la estadística)

    # Aplicamos la lógica fila por fila
    merged['R_1er'] = merged.apply(lambda r: evaluar_retencion(r, '1er'), axis=1)
    merged['R_2do'] = merged.apply(lambda r: evaluar_retencion(r, '2do', '1er'), axis=1)
    merged['R_3er'] = merged.apply(lambda r: evaluar_retencion(r, '3er', '2do'), axis=1)

    # Agrupamos por Año de Venta
    # El promedio ignora automáticamente los NaN, dándote la tasa real de los que ya cumplieron plazo
    res = merged.groupby('Año_Venta')[['R_1er', 'R_2do', 'R_3er']].mean()
    
    # Renombrar columnas para el gráfico
    res.columns = ['1er', '2do', '3er']
    
    return res, "OK"

# --- MAIN APP ---
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
            if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
            st.header("Filtros")
            anios = sorted([int(x) for x in data['CALENDARIO']['Año'].unique() if x > 0], reverse=True)
            anio_sel = st.selectbox("📅 Año", anios)
            
            meses_nom = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
            df_y = data['CALENDARIO'][data['CALENDARIO']['Año'] == anio_sel]
            mes_sel = st.selectbox("📅 Mes", sorted(df_y['Mes'].unique(), reverse=True), format_func=lambda x: meses_nom.get(x))

        def get_val(df, keys):
            if df is None: return 0
            row = df[(df['Año'] == anio_sel) & (df['Mes'] == mes_sel)]
            if row.empty: return 0
            col = find_col(df, keys, exclude_keywords=["OBJ"])
            return float(row[col].iloc[0]) if col else 0

        def get_obj(df, keys):
            if df is None: return 1
            row = df[(df['Año'] == anio_sel) & (df['Mes'] == mes_sel)]
            if row.empty: return 1
            col = find_col(df, ["OBJ"] + keys)
            return float(row[col].iloc[0]) if col else 1

        dias_hab = get_obj(data['CALENDARIO'], ["HAB"])
        dias_trans = get_val(data['CALENDARIO'], ["TRANS"])
        prog_t = min(dias_trans / dias_hab if dias_hab > 0 else 0, 1.0)
        
        st.title(f"Tablero Posventa - {meses_nom.get(mes_sel)} {anio_sel}")
        tabs = st.tabs(["🏠 Objetivos", "🛠️ Servicios", "📦 Repuestos", "🎨 Chapa y Pintura", "📈 Histórico"])

        with tabs[0]: 
            c1, c2, c3, c4 = st.columns(4)
            real_mo = sum([get_val(data['SERVICIOS'], ["MO", k]) for k in ["CLI", "GAR", "INT", "TER"]])
            obj_mo = get_obj(data['SERVICIOS'], ["MO"])
            c1.metric("M.O. Servicios", f"${real_mo:,.0f}", f"Obj: ${obj_mo:,.0f}")
            
            real_rep = sum([get_val(data['REPUESTOS'], ["VENTA", k]) for k in canales_repuestos])
            obj_rep = get_obj(data['REPUESTOS'], ["FACT"])
            c2.metric("Repuestos", f"${real_rep:,.0f}", f"Obj: ${obj_rep:,.0f}")
            
            real_cj = get_val(data['CyP JUJUY'], ["MO", "PUR"]) + get_val(data['CyP JUJUY'], ["MO", "TER"]) + get_val(data['CyP JUJUY'], ["FACT", "REP"])
            obj_cj = get_obj(data['CyP JUJUY'], ["FACT"])
            c3.metric("CyP Jujuy", f"${real_cj:,.0f}", f"Obj: ${obj_cj:,.0f}")

            real_cs = get_val(data['CyP SALTA'], ["MO", "PUR"]) + get_val(data['CyP SALTA'], ["MO", "TER"]) + get_val(data['CyP SALTA'], ["FACT", "REP"])
            obj_cs = get_obj(data['CyP SALTA'], ["FACT"])
            c4.metric("CyP Salta", f"${real_cs:,.0f}", f"Obj: ${obj_cs:,.0f}")

        with tabs[1]:
            col_kpi, col_irpv = st.columns([1, 1])
            with col_kpi:
                st.subheader("Indicadores del Mes")
                cpus = get_val(data['SERVICIOS'], ["CPUS"])
                obj_cpus = get_obj(data['SERVICIOS'], ["CPUS"])
                st.metric("CPUS (Entradas)", f"{cpus:.0f}", f"Obj: {obj_cpus:.0f}")
                tus = cpus + get_val(data['SERVICIOS'], ["OTROS", "CARGOS"])
                st.metric("TUS Total", f"{tus:.0f}", f"Obj: {get_obj(data['SERVICIOS'], ['TUS']):.0f}")

            with col_irpv:
                st.subheader("🔄 Fidelización (IRPV)")
                st.markdown("ℹ️ **Importante:** Sube archivos guardados en Excel como **'CSV UTF-8 (delimitado por comas)'**.")
                
                up_v = st.file_uploader("Entregas 0km (CSV)", type=["csv"], key="v")
                up_t = st.file_uploader("Historial Taller (CSV)", type=["csv"], key="t")
                
                if up_v and up_t:
                    df_res, msg = procesar_irpv(up_v, up_t)
                    if df_res is not None:
                        st.success("✅ Procesado Exitosamente")
                        anios_irpv = sorted(df_res.index, reverse=True)
                        sel_anio_irpv = st.selectbox("Año Cohorte:", anios_irpv)
                        
                        vals = df_res.loc[sel_anio_irpv]
                        c_i1, c_i2, c_i3 = st.columns(3)
                        c_i1.metric("1er Service (10k)", f"{vals['1er']:.1%}", "Obj: 80%")
                        c_i2.metric("2do Service (20k)", f"{vals['2do']:.1%}", "Obj: 60%")
                        c_i3.metric("3er Service (30k)", f"{vals['3er']:.1%}", "Obj: 40%")
                        
                        with st.expander("Ver Tabla Completa"):
                            st.dataframe(df_res.style.format("{:.1%}"))
                    else:
                        st.error(f"❌ Error: {msg}")

        with tabs[2]:
            st.subheader("Gestión de Stock y Margen")
            primas = st.number_input("Primas/Rappels ($)", value=0.0, step=1000.0)
            items = []
            for c in canales_repuestos:
                vb = get_val(data['REPUESTOS'], ["VENTA", c])
                cos = get_val(data['REPUESTOS'], ["COSTO", c])
                items.append({"Canal": c, "Venta": vb, "Costo": cos, "Margen $": vb-cos})
            
            df_rep = pd.DataFrame(items)
            total_ut = df_rep['Margen $'].sum() + primas
            total_vt = df_rep['Venta'].sum()
            mg_pct = total_ut / total_vt if total_vt > 0 else 0
            
            k1, k2 = st.columns(2)
            k1.metric("Utilidad Total (c/Primas)", f"${total_ut:,.0f}")
            k2.metric("Margen Global %", f"{mg_pct:.1%}")
            st.dataframe(df_rep.style.format({"Venta":"${:,.0f}", "Costo":"${:,.0f}", "Margen $":"${:,.0f}"}), use_container_width=True)

        with tabs[3]:
            st.subheader("Chapa y Pintura")
            c_ju, c_sa = st.columns(2)
            with c_ju:
                st.markdown("#### Jujuy")
                st.metric("Facturación", f"${real_cj:,.0f}", f"Obj: ${obj_cj:,.0f}")
                panos = get_val(data['CyP JUJUY'], ["PANOS"])
                st.metric("Paños", f"{panos:.0f}")
            with c_sa:
                st.markdown("#### Salta")
                st.metric("Facturación", f"${real_cs:,.0f}", f"Obj: ${obj_cs:,.0f}")
                panos_s = get_val(data['CyP SALTA'], ["PANOS"])
                st.metric("Paños", f"{panos_s:.0f}")
        
        with tabs[4]:
            st.subheader("Evolución Anual")
            df_h = data['SERVICIOS'][data['SERVICIOS']['Año'] == anio_sel]
            fig = px.bar(df_h, x='Mes', y=find_col(data['SERVICIOS'], ["MO", "CLI"]), title="Evolución MO Cliente")
            st.plotly_chart(fig, use_container_width=True)

    else: st.error("No se pudieron cargar los datos de Google Sheets.")
except Exception as e: st.error(f"Error Crítico: {e}")
