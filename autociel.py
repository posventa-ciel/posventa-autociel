import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Grupo CENOA - Gestión Posventa", layout="wide")

# --- ESTILO CSS ---
st.markdown("""<style>
    .main { background-color: #f4f7f9; }
    .portada-container { background: linear-gradient(90deg, #00235d 0%, #004080 100%); color: white; padding: 2rem; border-radius: 15px; text-align: center; margin-bottom: 2rem; }
    .kpi-card { background-color: white; border: 1px solid #e0e0e0; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .stTabs [aria-selected="true"] { background-color: #00235d !important; color: white !important; font-weight: bold; }
</style>""", unsafe_allow_html=True)

# --- FUNCIÓN DE BÚSQUEDA DE COLUMNAS ---
def find_col(df, include_keywords, exclude_keywords=[]):
    """Busca columna ignorando mayúsculas/minúsculas"""
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
            
            # Limpieza agresiva de nombres de columnas (Mayúsculas y sin espacios extra)
            df.columns = [c.strip().upper().replace(".", "") for c in df.columns]
            
            # Limpieza de datos numéricos
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
        # --- PROCESAMIENTO FECHAS ---
        for h in data:
            col_f = find_col(data[h], ["FECHA"]) or data[h].columns[0]
            data[h]['Fecha_dt'] = pd.to_datetime(data[h][col_f], dayfirst=True, errors='coerce')
            data[h]['Mes'] = data[h]['Fecha_dt'].dt.month
            data[h]['Año'] = data[h]['Fecha_dt'].dt.year

        # --- BARRA LATERAL (FILTROS) ---
        with st.sidebar:
            st.header("Filtros")
            años_disp = sorted([int(a) for a in data['CALENDARIO']['Año'].unique() if a > 0], reverse=True)
            año_sel = st.selectbox("📅 Año", años_disp)
            
            meses_nom = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
            df_year = data['CALENDARIO'][data['CALENDARIO']['Año'] == año_sel]
            meses_disp = sorted(df_year['Mes'].unique(), reverse=True)
            mes_sel = st.selectbox("📅 Mes", meses_disp, format_func=lambda x: meses_nom.get(x, "N/A"))
            
            # Debug (Opcional: eliminar después)
            if st.checkbox("Ver columnas (Debug)"):
                st.write("Columnas Calendario:", data['CALENDARIO'].columns.tolist())

        # --- OBTENCIÓN DE DATOS DEL MES ---
        def get_row(df):
            res = df[(df['Año'] == año_sel) & (df['Mes'] == mes_sel)].sort_values('Fecha_dt')
            return res.iloc[-1] if not res.empty else pd.Series(dtype='object')

        c_r = get_row(data['CALENDARIO'])
        s_r = get_row(data['SERVICIOS'])
        r_r = get_row(data['REPUESTOS'])
        t_r = get_row(data['TALLER'])
        cj_r = get_row(data['CyP JUJUY'])
        cs_r = get_row(data['CyP SALTA'])

        # --- CORRECCIÓN CRÍTICA DE FECHAS ---
        # No buscamos "DIAS" porque el tilde suele fallar. Buscamos palabras únicas.
        # "TRANS" para Transcurridos, "HAB" para Hábiles.
        col_trans = find_col(data['CALENDARIO'], ["TRANS"]) 
        col_hab = find_col(data['CALENDARIO'], ["HAB"])
        
        d_t = float(c_r.get(col_trans, 0))
        d_h = float(c_r.get(col_hab, 0))

        # Lógica de seguridad: Si viene vacío, calculamos, PERO SIEMPRE priorizamos el Excel
        if d_h == 0: 
            d_h = 22 # Solo si es 0 ponemos default
        
        # Corrección: Si seleccionas un mes pasado (ej: Dic estando en Ene), D_T debe ser igual a D_H
        # Esto corrige el "1 de 20" si el Excel quedó incompleto en días transcurridos
        hoy = datetime.now()
        fecha_corte = pd.to_datetime(c_r.get('Fecha_dt')) if 'Fecha_dt' in c_r else hoy
        
        # Si el mes seleccionado es anterior al actual, asumimos mes completo
        if (año_sel < hoy.year) or (año_sel == hoy.year and mes_sel < hoy.month):
             # Si en el excel dice 20 y 20, usamos eso. Si dice 1 y 20, forzamos 20 y 20.
             if d_t < d_h: d_t = d_h

        prog_t = d_t / d_h if d_h > 0 else 0
        prog_t = min(prog_t, 1.0)

        # --- PORTADA ---
        st.markdown(f"""
        <div class="portada-container">
            <h1>Autociel - Tablero Posventa</h1>
            <h3 style="margin:0;">📅 {meses_nom.get(mes_sel)} {año_sel}</h3>
            <div style="margin-top:10px; font-size: 1.2rem;">
                Avance: <b>{d_t:g}</b> de <b>{d_h:g}</b> días hábiles ({prog_t:.1%})
            </div>
            <div style="background: rgba(255,255,255,0.2); height: 8px; border-radius: 4px; width: 50%; margin: 10px auto;">
                <div style="background: #fff; width: {prog_t*100}%; height: 100%; border-radius: 4px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        tab1, tab2, tab3, tab4 = st.tabs(["🏠 Objetivos", "🛠️ Servicios", "📦 Repuestos", "🎨 Chapa y Pintura"])

        with tab1:
            st.markdown("### 🎯 Control de Objetivos")
            cols = st.columns(4)
            
            # Datos Reales
            c_mo = [find_col(data['SERVICIOS'], ["MO", k], exclude_keywords=["OBJ"]) for k in ["CLI", "GAR", "TER"]]
            real_mo = sum([s_r.get(c, 0) for c in c_mo if c])
            
            canales = ['MOSTRADOR', 'TALLER', 'INTERNA', 'GAR', 'CYP', 'MAYORISTA', 'SEGUROS']
            real_rep = sum([r_r.get(find_col(data['REPUESTOS'], ["VENTA", c], exclude_keywords=["OBJ"]), 0) for c in canales])
            
            # CyP Totales
            def get_cyp_total(row, df_nom):
                mo = row.get(find_col(data[df_nom], ["MO", "PUR"]), 0) + row.get(find_col(data[df_nom], ["MO", "TER"]), 0)
                rep = row.get(find_col(data[df_nom], ["FACT", "REP"]), 0) # Suma repuestos si existe columna
                return mo + rep

            real_jujuy = get_cyp_total(cj_r, 'CyP JUJUY')
            real_salta = get_cyp_total(cs_r, 'CyP SALTA')

            metas = [
                ("M.O. Servicios", real_mo, s_r.get(find_col(data['SERVICIOS'], ["OBJ", "MO"]), 1)),
                ("Repuestos", real_rep, r_r.get(find_col(data['REPUESTOS'], ["OBJ", "FACT"]), 1)),
                ("CyP Jujuy", real_jujuy, cj_r.get(find_col(data['CyP JUJUY'], ["OBJ", "FACT"]), 1)),
                ("CyP Salta", real_salta, cs_r.get(find_col(data['CyP SALTA'], ["OBJ", "FACT"]), 1))
            ]

            for i, (tit, real, obj_mes) in enumerate(metas):
                obj_parcial = obj_mes * prog_t
                proy = (real / d_t) * d_h if d_t > 0 else 0
                cumpl = real / obj_mes if obj_mes > 0 else 0
                
                color = "#dc3545" if cumpl < 0.90 else ("#ffc107" if cumpl < 0.98 else "#28a745")
                icon = "✅" if real >= obj_parcial else "🔻"
                
                # HTML MINIFICADO (Sin espacios ni saltos de línea para evitar error de renderizado)
                html_card = f"""<div class="kpi-card"><p style="font-weight:bold; color:#666; margin-bottom:5px;">{tit}</p><h2 style="margin:0; color:#00235d;">${real:,.0f}</h2><p style="font-size:0.9rem; color:#666; margin-top:5px;">vs Obj. Parcial: <b>${obj_parcial:,.0f}</b> {icon}</p><hr style="margin:10px 0; border:0; border-top:1px solid #eee;"><div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:5px;"><span>Obj. Mes:</span><b>${obj_mes:,.0f}</b></div><div style="display:flex; justify-content:space-between; font-size:0.85rem; color:{color}; font-weight:bold;"><span>Proyección:</span><span>${proy:,.0f}</span></div><div style="margin-top:10px;"><div style="width:100%; background:#e0e0e0; height:6px; border-radius:10px;"><div style="width:{min(cumpl*100, 100)}%; background:{color}; height:6px; border-radius:10px;"></div></div></div></div>"""
                
                with cols[i]:
                    st.markdown(html_card, unsafe_allow_html=True)

        with tab2:
            st.header("KPIs Taller")
            k1, k2, k3, k4 = st.columns(4)
            
            c_cpus = find_col(data['SERVICIOS'], ["CPUS"], exclude_keywords=["OBJ"])
            c_tus = find_col(data['SERVICIOS'], ["OTROS", "CARGOS"], exclude_keywords=["OBJ"])
            
            real_cpus = s_r.get(c_cpus, 0)
            real_tus = real_cpus + s_r.get(c_tus, 0)
            
            # Tickets
            div = real_cpus if real_cpus > 0 else 1
            fact_taller = t_r.get(find_col(data['TALLER'], ["FACT", "CC"]), 0) + t_r.get(find_col(data['TALLER'], ["FACT", "CG"]), 0)
            tp_hs = fact_taller / div
            tp_mo = real_mo / div

            k1.metric("TUS Total", f"{real_tus:,.0f}")
            k2.metric("CPUS Cliente", f"{real_cpus:,.0f}")
            k3.metric("Ticket Hs", f"{tp_hs:.2f}")
            k4.metric("Ticket $", f"${tp_mo:,.0f}")
            
            st.divider()
            
            # Indicadores Taller
            e1, e2, e3, e4, e5 = st.columns(5)
            
            ht = sum([t_r.get(find_col(data['TALLER'], ["TRAB", k]), 0) for k in ["CC", "CG", "CI"]])
            hf = sum([t_r.get(find_col(data['TALLER'], ["FACT", k]), 0) for k in ["CC", "CG", "CI"]])
            
            # Presencia corregida con d_t correcto
            hs_disp = t_r.get(find_col(data['TALLER'], ["DISP", "REAL"]), 0)
            cant_tecs = t_r.get(find_col(data['TALLER'], ["TECNICOS"]), 6)
            if cant_tecs == 0: cant_tecs = 6
            
            hs_teoricas = cant_tecs * 9 * d_t # Aquí usamos el d_t leído correctamente del Excel
            
            ef_gl = hf / ht if ht > 0 else 0
            presencia = hs_disp / hs_teoricas if hs_teoricas > 0 else 0
            ocup = ht / hs_disp if hs_disp > 0 else 0
            prod = t_r.get(find_col(data['TALLER'], ["PROD", "TALLER"]), 0)
            if prod > 2: prod /= 100

            e1.metric("Eficiencia Global", f"{ef_gl:.1%}")
            e2.metric("Presencia", f"{presencia:.1%}")
            e3.metric("Ocupación", f"{ocup:.1%}")
            e4.metric("Productividad", f"{prod:.1%}")
            e5.metric("Hs Facturadas", f"{hf:,.0f}")

            # Gráficos
            g1, g2 = st.columns(2)
            ht_vals = [t_r.get(find_col(data['TALLER'], ["TRAB", k]), 0) for k in ["CC", "CG", "CI"]]
            hf_vals = [t_r.get(find_col(data['TALLER'], ["FACT", k]), 0) for k in ["CC", "CG", "CI"]]
            
            with g1: st.plotly_chart(px.pie(values=ht_vals, names=["CC", "CG", "CI"], title="Hs Trabajadas", hole=0.4), use_container_width=True)
            with g2: st.plotly_chart(px.pie(values=hf_vals, names=["CC", "CG", "CI"], title="Hs Facturadas", hole=0.4), use_container_width=True)

        with tab3:
            st.header("Repuestos")
            df_rep = []
            for c in canales:
                v = r_r.get(find_col(data['REPUESTOS'], ["VENTA", c], exclude_keywords=["OBJ"]), 0)
                util = v - r_r.get(find_col(data['REPUESTOS'], ["COSTO", c]), 0) - r_r.get(find_col(data['REPUESTOS'], ["DESC", c]), 0)
                if v > 0: df_rep.append({"Canal": c, "Venta": v, "Utilidad": util})
            
            if df_rep:
                dfr = pd.DataFrame(df_rep)
                col_r1, col_r2 = st.columns([3, 1])
                with col_r1: st.plotly_chart(px.bar(dfr, x="Canal", y="Venta", title="Venta por Canal"), use_container_width=True)
                with col_r2: 
                    st.metric("Total Venta", f"${dfr['Venta'].sum():,.0f}")
                    st.metric("Total Utilidad", f"${dfr['Utilidad'].sum():,.0f}")

        with tab4:
            st.header("Chapa y Pintura")
            c1, c2 = st.columns(2)
            
            def render_cyp(col, titulo, real, row, df_name):
                with col:
                    st.subheader(titulo)
                    st.metric("Facturación Total", f"${real:,.0f}")
                    mo_p = row.get(find_col(data[df_name], ["MO", "PUR"]), 0)
                    mo_t = row.get(find_col(data[df_name], ["MO", "TER"]), 0)
                    rep = row.get(find_col(data[df_name], ["FACT", "REP"]), 0)
                    
                    data_pie = {"MO Pura": mo_p, "Terceros": mo_t}
                    if rep > 0: data_pie["Repuestos"] = rep
                    
                    st.plotly_chart(px.pie(values=list(data_pie.values()), names=list(data_pie.keys()), hole=0.4), use_container_width=True)

            render_cyp(c1, "Jujuy", real_jujuy, cj_r, 'CyP JUJUY')
            render_cyp(c2, "Salta", real_salta, cs_r, 'CyP SALTA')

    else:
        st.warning("No se pudieron cargar los datos. Revisa la ID del Google Sheet.")

except Exception as e:
    st.error(f"Error global: {e}")
