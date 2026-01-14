import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
import os

# Intentar importar xlrd para manejar excels viejos
try:
    import xlrd
except ImportError:
    xlrd = None

st.set_page_config(page_title="Grupo CENOA - Gestión Posventa", layout="wide")

# --- ESTILO CSS ---
st.markdown("""<style>
    .block-container { padding-top: 1rem; padding-bottom: 2rem; }
    .main { background-color: #f4f7f9; }
    .kpi-card { background-color: white; border: 1px solid #e0e0e0; padding: 12px 15px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 8px; min-height: 145px; display: flex; flex-direction: column; justify-content: space-between; }
    .metric-card { background-color: white; border: 1px solid #eee; padding: 10px; border-radius: 8px; text-align: center; min-height: 110px; }
    .cyp-detail { background-color: #f8f9fa; padding: 8px; border-radius: 6px; font-size: 0.8rem; margin-top: 5px; border-left: 3px solid #00235d; }
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

# --- SÚPER CARGADOR DE ARCHIVOS (ESPECIAL QUITER .XLS) ---
def super_cargador(uploaded_file):
    errores = []
    
    # 1. INTENTO FUERTE: Excel Binario (xlrd)
    # Esto es para los archivos que empiezan con ÐÏà¡± (Magic Bytes de Office viejo)
    try:
        uploaded_file.seek(0)
        # Forzamos el motor 'xlrd' que es el único que lee estos binarios
        return pd.read_excel(uploaded_file, engine='xlrd'), "Excel Binario (.xls)"
    except Exception as e:
        errores.append(f"Fallo xlrd: {str(e)}")

    # 2. INTENTO: Excel Moderno (openpyxl)
    try:
        uploaded_file.seek(0)
        return pd.read_excel(uploaded_file, engine='openpyxl'), "Excel Moderno (.xlsx)"
    except Exception as e:
        errores.append(f"Fallo openpyxl: {str(e)}")

    # 3. INTENTO: HTML (A veces Quiter exporta HTML como xls)
    try:
        uploaded_file.seek(0)
        dfs = pd.read_html(uploaded_file, header=0)
        if dfs: return dfs[0], "HTML Web Table"
    except Exception as e:
        errores.append(f"Fallo HTML: {str(e)}")

    # 4. INTENTO: CSV (Separador coma)
    try:
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file, encoding='latin-1'), "CSV Coma"
    except Exception as e:
        errores.append(f"Fallo CSV Coma: {str(e)}")

    # 5. INTENTO: CSV (Separador punto y coma)
    try:
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file, sep=';', encoding='latin-1'), "CSV Punto y Coma"
    except Exception as e:
        errores.append(f"Fallo CSV P.Coma: {str(e)}")

    return None, f"No se pudo leer. Errores: {'; '.join(errores)}"

# --- PROCESAMIENTO IRPV ---
def procesar_irpv(file_v, file_t):
    # Cargar Ventas
    df_v, tipo_v = super_cargador(file_v)
    if df_v is None: 
        if "xlrd" in str(tipo_v) and xlrd is None:
            return None, "Falta instalar librería 'xlrd'. Ejecuta: pip install xlrd"
        return None, f"Error Ventas: {tipo_v}"
    
    # Limpieza Columnas Ventas
    df_v.columns = [str(c).upper().strip() for c in df_v.columns]
    
    # Buscar columnas clave (flexible)
    col_vin = next((c for c in df_v.columns if 'BASTIDOR' in c or 'VIN' in c or 'CHASIS' in c), None)
    col_fec = next((c for c in df_v.columns if 'FEC' in c or 'ENTR' in c), None)
    
    if not col_vin or not col_fec:
        return None, f"Ventas: No se encontraron columnas 'Bastidor' ni 'Fecha'. (Cols detectadas: {list(df_v.columns)})"

    # Procesar Fechas Ventas
    def clean_date(x):
        if pd.isna(x) or x == '': return None
        # Si es número serial de Excel
        if isinstance(x, (int, float)):
            try: return datetime(1899, 12, 30) + pd.Timedelta(days=float(x))
            except: pass
        # Si es texto
        try: return pd.to_datetime(x, dayfirst=True, errors='coerce')
        except: return None

    df_v['Fecha_Entrega'] = df_v[col_fec].apply(clean_date)
    df_v['Año_Venta'] = df_v['Fecha_Entrega'].dt.year
    df_v['VIN'] = df_v[col_vin].astype(str).str.strip().str.upper()
    df_v = df_v.dropna(subset=['VIN', 'Fecha_Entrega'])

    # Cargar Taller
    df_t, tipo_t = super_cargador(file_t)
    if df_t is None: return None, f"Error Taller: {tipo_t}"
    
    # Limpieza Columnas Taller
    df_t.columns = [str(c).upper().strip() for c in df_t.columns]
    
    col_vin_t = next((c for c in df_t.columns if 'BASTIDOR' in c or 'VIN' in c), None)
    col_fec_t = next((c for c in df_t.columns if 'CIERRE' in c or 'FEC' in c), None)
    col_km = next((c for c in df_t.columns if 'KM' in c), None)
    col_or = next((c for c in df_t.columns if 'TIPO' in c or 'O.R.' in c), None)

    if not col_vin_t or not col_fec_t:
        return None, f"Taller: Faltan columnas clave (Bastidor/Cierre). (Cols detectadas: {list(df_t.columns)})"

    df_t['Fecha_Servicio'] = df_t[col_fec_t].apply(clean_date)
    df_t['VIN'] = df_t[col_vin_t].astype(str).str.strip().str.upper()
    
    if col_km:
        df_t['Km'] = df_t[col_km].astype(str).str.replace('.','').str.replace(',','.')
        df_t['Km'] = pd.to_numeric(df_t['Km'], errors='coerce').fillna(0)
    else: df_t['Km'] = 0

    # Filtro Chapa
    if col_or:
        mask = ~df_t[col_or].astype(str).str.contains('CHAPA|PINTURA|SINIESTRO', case=False, na=False)
        df_t = df_t[mask]

    # Clasificar
    def clasif(k):
        if 5000 <= k <= 15000: return "1er"
        elif 15001 <= k <= 25000: return "2do"
        elif 25001 <= k <= 35000: return "3er"
        return None
    
    df_t['Hito'] = df_t['Km'].apply(clasif)
    df_validos = df_t.dropna(subset=['Hito'])

    # Cruzar
    merged = pd.merge(df_v, df_validos[['VIN', 'Hito']], on='VIN', how='left')
    pivot = merged.pivot_table(index=['VIN', 'Año_Venta'], columns='Hito', aggfunc='size', fill_value=0).reset_index()
    
    for c in ['1er', '2do', '3er']:
        if c not in pivot.columns: pivot[c] = 0
        else: pivot[c] = pivot[c].apply(lambda x: 1 if x > 0 else 0)
        
    res = pivot.groupby('Año_Venta')[['1er', '2do', '3er']].mean()
    return res, "OK"

# --- MAIN APP ---
ID_SHEET = "1yJgaMR0nEmbKohbT_8Vj627Ma4dURwcQTQcQLPqrFwk"

try:
    data = cargar_datos(ID_SHEET)
    
    if data:
        # Preprocesamiento Básico
        for h in data:
            col_f = find_col(data[h], ["FECHA"]) or data[h].columns[0]
            data[h]['Fecha_dt'] = pd.to_datetime(data[h][col_f], dayfirst=True, errors='coerce')
            data[h]['Mes'] = data[h]['Fecha_dt'].dt.month
            data[h]['Año'] = data[h]['Fecha_dt'].dt.year

        with st.sidebar:
            if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
            st.header("Filtros")
            anios = sorted([int(x) for x in data['CALENDARIO']['Año'].unique() if x > 0], reverse=True)
            anio_sel = st.selectbox("📅 Año", anios)
            
            meses_nom = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
            df_y = data['CALENDARIO'][data['CALENDARIO']['Año'] == anio_sel]
            mes_sel = st.selectbox("📅 Mes", sorted(df_y['Mes'].unique(), reverse=True), format_func=lambda x: meses_nom.get(x))

        # Helpers de obtención de datos
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

        # Avance temporal
        dias_hab = get_obj(data['CALENDARIO'], ["HAB"])
        dias_trans = get_val(data['CALENDARIO'], ["TRANS"])
        prog_t = min(dias_trans / dias_hab if dias_hab > 0 else 0, 1.0)
        
        # --- UI LAYOUT ---
        st.title(f"Tablero Posventa - {meses_nom.get(mes_sel)} {anio_sel}")
        tabs = st.tabs(["🏠 Objetivos", "🛠️ Servicios", "📦 Repuestos", "🎨 Chapa y Pintura", "📈 Histórico"])

        with tabs[0]: # OBJETIVOS
            c1, c2, c3, c4 = st.columns(4)
            
            # MO Servicios
            real_mo = sum([get_val(data['SERVICIOS'], ["MO", k]) for k in ["CLI", "GAR", "INT", "TER"]])
            obj_mo = get_obj(data['SERVICIOS'], ["MO"])
            c1.metric("M.O. Servicios", f"${real_mo:,.0f}", f"Obj: ${obj_mo:,.0f}")
            
            # Repuestos
            real_rep = sum([get_val(data['REPUESTOS'], ["VENTA", k]) for k in ['MOSTRADOR', 'TALLER', 'INTERNA', 'GAR', 'CYP', 'MAYORISTA', 'SEGUROS']])
            obj_rep = get_obj(data['REPUESTOS'], ["FACT"])
            c2.metric("Repuestos", f"${real_rep:,.0f}", f"Obj: ${obj_rep:,.0f}")
            
            # Cyp Jujuy
            real_cj = get_val(data['CyP JUJUY'], ["MO", "PUR"]) + get_val(data['CyP JUJUY'], ["MO", "TER"]) + get_val(data['CyP JUJUY'], ["FACT", "REP"])
            obj_cj = get_obj(data['CyP JUJUY'], ["FACT"])
            c3.metric("CyP Jujuy", f"${real_cj:,.0f}", f"Obj: ${obj_cj:,.0f}")

            # Cyp Salta
            real_cs = get_val(data['CyP SALTA'], ["MO", "PUR"]) + get_val(data['CyP SALTA'], ["MO", "TER"]) + get_val(data['CyP SALTA'], ["FACT", "REP"])
            obj_cs = get_obj(data['CyP SALTA'], ["FACT"])
            c4.metric("CyP Salta", f"${real_cs:,.0f}", f"Obj: ${obj_cs:,.0f}")

        with tabs[1]: # SERVICIOS
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
                st.caption("Fidelización calculada sobre ventas acumuladas (Cohortes).")
                
                up_v = st.file_uploader("Entregas 0km", key="v")
                up_t = st.file_uploader("Historial Taller", key="t")
                
                if up_v and up_t:
                    df_res, msg = procesar_irpv(up_v, up_t)
                    if df_res is not None:
                        st.success("✅ Procesado Exitosamente")
                        anios_irpv = sorted(df_res.index, reverse=True)
                        sel_anio_irpv = st.selectbox("Año Cohorte:", anios_irpv)
                        
                        vals = df_res.loc[sel_anio_irpv]
                        c_i1, c_i2, c_i3 = st.columns(3)
                        c_i1.metric("1er Service", f"{vals['1er']:.1%}", "Obj: 80%")
                        c_i2.metric("2do Service", f"{vals['2do']:.1%}", "Obj: 60%")
                        c_i3.metric("3er Service", f"{vals['3er']:.1%}", "Obj: 40%")
                        
                        with st.expander("Ver Datos Completos"):
                            st.dataframe(df_res.style.format("{:.1%}"))
                    else:
                        st.error(f"⚠️ Error: {msg}")

        with tabs[2]: # REPUESTOS
            st.subheader("Gestión de Stock y Margen")
            # Primas
            primas = st.number_input("Primas/Rappels ($)", value=0.0, step=1000.0)
            
            # Detalle Canales
            canales = ['MOSTRADOR', 'TALLER', 'INTERNA', 'GAR', 'CYP', 'MAYORISTA', 'SEGUROS']
            items = []
            for c in canales:
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

        with tabs[3]: # CyP
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
        
        with tabs[4]: # HISTORICO
            st.subheader("Evolución Anual")
            df_h = data['SERVICIOS'][data['SERVICIOS']['Año'] == anio_sel]
            fig = px.bar(df_h, x='Mes', y=find_col(data['SERVICIOS'], ["MO", "CLI"]), title="Evolución MO Cliente")
            st.plotly_chart(fig, use_container_width=True)

    else:
        st.error("No se pudieron cargar los datos de Google Sheets.")

except Exception as e:
    st.error(f"Error Crítico: {e}")
