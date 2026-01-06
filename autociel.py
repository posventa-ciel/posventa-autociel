import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Grupo CENOA - Gestión Posventa", layout="wide")

# --- ESTILO (Simplificado para evitar errores de renderizado) ---
st.markdown("""<style>
    .main { background-color: #f4f7f9; }
    .portada-container { background: linear-gradient(90deg, #00235d 0%, #004080 100%); color: white; padding: 2rem; border-radius: 15px; text-align: center; margin-bottom: 2rem; }
    .stTabs [aria-selected="true"] { background-color: #00235d !important; color: white !important; font-weight: bold; }
</style>""", unsafe_allow_html=True)

# --- FUNCIÓN DE BÚSQUEDA ---
def find_col(df, include_keywords, exclude_keywords=[]):
    """Busca columna normalizando mayúsculas"""
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
            # --- LIMPIEZA ROBUSTA DE NOMBRES DE COLUMNA (SOLUCIÓN ERROR FECHAS) ---
            # Eliminamos tildes explícitamente para que "Días" coincida con "DIAS"
            df.columns = [
                c.strip().upper()
                .replace(".", "")
                .replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U") 
                for c in df.columns
            ]
            
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
        # Procesamiento de Fechas global
        for h in data:
            col_f = find_col(data[h], ["FECHA"])
            if not col_f and not data[h].empty: col_f = data[h].columns[0]
            
            data[h]['Fecha_dt'] = pd.to_datetime(data[h][col_f], dayfirst=True, errors='coerce')
            data[h]['Mes'] = data[h]['Fecha_dt'].dt.month
            data[h]['Año'] = data[h]['Fecha_dt'].dt.year

        # --- FILTROS ---
        with st.sidebar:
            st.header("Filtros")
            años_disp = sorted([int(a) for a in data['CALENDARIO']['Año'].unique() if a > 0], reverse=True)
            año_sel = st.selectbox("📅 Año", años_disp)
            
            meses_nom = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
            df_year = data['CALENDARIO'][data['CALENDARIO']['Año'] == año_sel]
            meses_disp = sorted(df_year['Mes'].unique(), reverse=True)
            mes_sel = st.selectbox("📅 Mes", meses_disp, format_func=lambda x: meses_nom.get(x, "N/A"))

        # --- OBTENCIÓN DE FILA DEL MES ---
        def get_mes_data(df):
            # Filtramos por año y mes
            res = df[(df['Año'] == año_sel) & (df['Mes'] == mes_sel)].sort_values('Fecha_dt')
            # Devolvemos la última fila (la más actual del mes)
            return res.iloc[-1] if not res.empty else pd.Series(dtype='object')

        c_r = get_mes_data(data['CALENDARIO'])
        s_r = get_mes_data(data['SERVICIOS'])
        r_r = get_mes_data(data['REPUESTOS'])
        t_r = get_mes_data(data['TALLER'])
        cj_r = get_mes_data(data['CyP JUJUY'])
        cs_r = get_mes_data(data['CyP SALTA'])

        # --- CORRECCIÓN LÓGICA DE DÍAS ---
        # Buscamos columnas limpias (sin tildes gracias a la función de carga)
        col_dias_trans = find_col(data['CALENDARIO'], ["DIAS", "TRANS"])
        col_dias_hab = find_col(data['CALENDARIO'], ["DIAS", "HAB"]) # Ahora encontrará "DIAS HABILES MES"
        
        # Leemos los valores. Si no existen, devuelve 0.
        d_t = float(c_r.get(col_dias_trans, 0))
        d_h = float(c_r.get(col_dias_hab, 0))

        # Validación básica para evitar división por cero, pero RESPETANDO lo que diga el excel
        if d_h == 0: d_h = 1 
        
        prog_t = d_t / d_h # Porcentaje de avance
        prog_t = min(prog_t, 1.0) # Topeamos al 100%

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
            st.markdown("### 🎯 Tablero de Control")
            cols = st.columns(4)
            
            # --- CÁLCULOS REALES ---
            c_mc = find_col(data['SERVICIOS'], ["MO", "CLI"], exclude_keywords=["OBJ", "HS"])
            c_mg = find_col(data['SERVICIOS'], ["MO", "GAR"], exclude_keywords=["OBJ", "HS"])
            c_mt = find_col(data['SERVICIOS'], ["MO", "TER"], exclude_keywords=["OBJ", "HS"])
            real_mo = s_r.get(c_mc,0) + s_r.get(c_mg,0) + s_r.get(c_mt,0)
            
            canales_totales = ['MOSTRADOR', 'TALLER', 'INTERNA', 'GAR', 'CYP', 'MAYORISTA', 'SEGUROS']
            real_rep = 0
            for c in canales_totales:
                col_v = find_col(data['REPUESTOS'], ["VENTA", c], exclude_keywords=["OBJ"])
                if col_v: real_rep += r_r.get(col_v, 0)
            
            cyp_j_mo = cj_r.get(find_col(data['CyP JUJUY'], ["MO", "PUR"]), 0) + cj_r.get(find_col(data['CyP JUJUY'], ["MO", "TER"]), 0)
            
            # Suma de Salta (MO + Repuestos)
            cyp_s_mo = cs_r.get(find_col(data['CyP SALTA'], ["MO", "PUR"]), 0) + cs_r.get(find_col(data['CyP SALTA'], ["MO", "TER"]), 0)
            cyp_s_rep = cs_r.get(find_col(data['CyP SALTA'], ["FACT", "REP"]), 0)
            real_cyp_salta = cyp_s_mo + cyp_s_rep

            metas = [
                ("M.O. Servicios", real_mo, s_r.get(find_col(data['SERVICIOS'], ["OBJ", "MO"]), 1)),
                ("Repuestos", real_rep, r_r.get(find_col(data['REPUESTOS'], ["OBJ", "FACT"]), 1)),
                ("CyP Jujuy", cyp_j_mo, cj_r.get(find_col(data['CyP JUJUY'], ["OBJ", "FACT"]), 1)),
                ("CyP Salta", real_cyp_salta, cs_r.get(find_col(data['CyP SALTA'], ["OBJ", "FACT"]), 1))
            ]
            
            for i, (tit, real, obj_mes) in enumerate(metas):
                obj_parcial = obj_mes * prog_t
                proyeccion = (real / d_t) * d_h if d_t > 0 else 0
                cumplimiento = real / obj_mes if obj_mes > 0 else 0
                
                # Definición de colores
                color_bar = "#dc3545" if cumplimiento < 0.90 else ("#ffc107" if cumplimiento < 0.98 else "#28a745")
                icon = "✅" if real >= obj_parcial else "🔻"
                
                # HTML SIMPLIFICADO Y SEGURO
                card_html = f"""
                <div style="background-color: white; border: 1px solid #e0e0e0; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 20px;">
                    <p style="font-weight:bold; color:#666; margin-bottom:5px;">{tit}</p>
                    <h2 style="margin:0; color:#00235d;">${real:,.0f}</h2>
                    <p style="font-size: 0.9rem; color: #666; margin-top:5px;">vs Obj. Parcial: <b>${obj_parcial:,.0f}</b> {icon}</p>
                    <hr style="margin: 10px 0; border: 0; border-top: 1px solid #eee;">
                    
                    <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 5px;">
                        <span>Obj. Mes:</span>
                        <b>${obj_mes:,.0f}</b>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: {color_bar}; font-weight: bold;">
                        <span>Proyección:</span>
                        <span>${proyeccion:,.0f}</span>
                    </div>
                    
                    <div style="margin-top:10px;">
                        <div style="width:100%; background:#e0e0e0; height:6px; border-radius:10px;">
                            <div style="width:{min(cumplimiento*100, 100)}%; background:{color_bar}; height:6px; border-radius:10px;"></div>
                        </div>
                    </div>
                </div>
                """
                with cols[i]:
                    st.markdown(card_html, unsafe_allow_html=True)

        with tab2:
            st.header("KPIs Taller")
            k1, k2, k3, k4 = st.columns(4)
            c_cpus_real = find_col(data['SERVICIOS'], ["CPUS"], exclude_keywords=["OBJ", "META"])
            c_tus_real = find_col(data['SERVICIOS'], ["OTROS", "CARGOS"], exclude_keywords=["OBJ"])
            
            real_cpus = s_r.get(c_cpus_real, 0)
            real_tus = real_cpus + s_r.get(c_tus_real, 0)
            obj_tus = s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'TUS']), 1)
            obj_cpus = s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'CPUS']), 1)

            # Ticket Promedio
            divisor = real_cpus if real_cpus > 0 else 1
            col_hs_cc = find_col(data['TALLER'], ["FACT", "CC"], exclude_keywords=["$", "PESOS", "OBJ"])
            col_hs_cg = find_col(data['TALLER'], ["FACT", "CG"], exclude_keywords=["$", "PESOS", "OBJ"])
            tp_hs = (t_r.get(col_hs_cc, 0) + t_r.get(col_hs_cg, 0)) / divisor
            tp_mo = real_mo / divisor
            
            k1.metric("TUS Total", f"{real_tus:,.0f}", f"{(real_tus/(obj_tus*prog_t)-1):.1%} vs Obj.P" if obj_tus > 0 else "0%")
            k2.metric("CPUS Cliente", f"{real_cpus:,.0f}", f"{(real_cpus/(obj_cpus*prog_t)-1):.1%} vs Obj.P" if obj_cpus > 0 else "0%")
            k3.metric("Ticket Prom. M.O. (Hs)", f"{tp_hs:.2f} hs")
            k4.metric("Ticket Prom. M.O. ($)", f"${tp_mo:,.0f}")
            
            st.divider()
            st.subheader("Eficiencia y Presencia")
            
            col_tr_cc = find_col(data['TALLER'], ["TRAB", "CC"], exclude_keywords=["$"])
            col_tr_cg = find_col(data['TALLER'], ["TRAB", "CG"], exclude_keywords=["$"])
            col_tr_ci = find_col(data['TALLER'], ["TRAB", "CI"], exclude_keywords=["$"])
            col_ft_cc = find_col(data['TALLER'], ["FACT", "CC"], exclude_keywords=["$"])
            col_ft_cg = find_col(data['TALLER'], ["FACT", "CG"], exclude_keywords=["$"])
            col_ft_ci = find_col(data['TALLER'], ["FACT", "CI"], exclude_keywords=["$"])

            ht_cc, ht_cg, ht_ci = t_r.get(col_tr_cc, 0), t_r.get(col_tr_cg, 0), t_r.get(col_tr_ci, 0)
            hf_cc, hf_cg, hf_ci = t_r.get(col_ft_cc, 0), t_r.get(col_ft_cg, 0), t_r.get(col_ft_ci, 0)
            
            ef_cc = hf_cc / ht_cc if ht_cc > 0 else 0
            ef_gl = (hf_cc + hf_cg + hf_ci) / (ht_cc + ht_cg + ht_ci) if (ht_cc + ht_cg + ht_ci) > 0 else 0
            
            # --- CORRECCIÓN PRESENCIA ---
            hs_disp_reales = t_r.get(find_col(data['TALLER'], ["DISPONIBLES", "REAL"]), 0)
            col_tecs = find_col(data['TALLER'], ["TECNICOS"], exclude_keywords=["PROD"])
            cant_tecs = t_r.get(col_tecs, 6)
            if cant_tecs == 0: cant_tecs = 6

            # Usamos d_t (Días Transcurridos del Excel)
            hs_teoricas = cant_tecs * 9 * d_t 
            
            presencia = hs_disp_reales / hs_teoricas if hs_teoricas > 0 else 0
            ocup = (ht_cc + ht_cg + ht_ci) / hs_disp_reales if hs_disp_reales > 0 else 0
            prod = t_r.get(find_col(data['TALLER'], ["PRODUCTIVIDAD", "TALLER"]), 0)
            if prod > 2: prod /= 100

            e1, e2, e3, e4, e5 = st.columns(5)
            e1.metric("Eficiencia CC", f"{ef_cc:.1%}")
            e2.metric("Eficiencia Global", f"{ef_gl:.1%}")
            e3.metric("Grado Presencia", f"{presencia:.1%}")
            e4.metric("Grado Ocupación", f"{ocup:.1%}")
            e5.metric("Productividad", f"{prod:.1%}")
            
            g1, g2 = st.columns(2)
            with g1: st.plotly_chart(px.pie(values=[ht_cc, ht_cg, ht_ci], names=["CC", "CG", "CI"], hole=0.4, title="Hs Trabajadas"), use_container_width=True)
            with g2: st.plotly_chart(px.pie(values=[hf_cc, hf_cg, hf_ci], names=["CC", "CG", "CI"], hole=0.4, title="Hs Facturadas"), use_container_width=True)

        with tab3:
            st.header("Repuestos")
            r1, r2, r3, r4 = st.columns(4)
            detalles = []
            for c in canales_totales:
                v_col = find_col(data['REPUESTOS'], ["VENTA", c], exclude_keywords=["OBJ"])
                if v_col:
                    vb = r_r.get(v_col, 0)
                    d = r_r.get(find_col(data['REPUESTOS'], ["DESC", c]), 0)
                    cost = r_r.get(find_col(data['REPUESTOS'], ["COSTO", c]), 0)
                    vn = vb - d; ut = vn - cost
                    detalles.append({"Canal": c, "Venta Neta": vn, "Utilidad $": ut})
            
            df_r_calc = pd.DataFrame(detalles)
            if not df_r_calc.empty:
                vta_total = df_r_calc['Venta Neta'].sum()
                util_total = df_r_calc['Utilidad $'].sum()
                mg_total = util_total / vta_total if vta_total > 0 else 0
                v_taller = df_r_calc.loc[df_r_calc['Canal'].isin(['TALLER', 'GAR', 'CYP']), 'Venta Neta'].sum()
                tp_rep = v_taller / divisor
                
                r1.metric("Venta Neta", f"${vta_total:,.0f}")
                r2.metric("Utilidad", f"${util_total:,.0f}")
                r3.metric("Margen %", f"{mg_total:.1%}")
                r4.metric("Ticket Rep", f"${tp_rep:,.0f}")
                
                st.plotly_chart(px.bar(df_r_calc, x="Canal", y="Venta Neta", title="Venta Neta por Canal"), use_container_width=True)

        with tab4:
            st.header("Chapa y Pintura")
            cf1, cf2 = st.columns(2)
            def render_cyp(col_render, nom, row, sheet_name, is_salta=False):
                with col_render:
                    st.subheader(f"Sede {nom}")
                    f_p = row.get(find_col(data[sheet_name], ['MO', 'PUR']), 0)
                    f_t = row.get(find_col(data[sheet_name], ['MO', 'TER']), 0)
                    f_r = row.get(find_col(data[sheet_name], ['FACT', 'REP']), 0) if is_salta else 0
                    
                    st.metric(f"Total Facturado {nom}", f"${(f_p+f_t+f_r):,.0f}")
                    
                    vals = [f_p, f_t]
                    nams = ["MO Pura", "Terceros"]
                    if f_r > 0:
                        vals.append(f_r); nams.append("Repuestos")
                    
                    st.plotly_chart(px.pie(values=vals, names=nams, hole=0.4), use_container_width=True)

            render_cyp(cf1, 'Jujuy', cj_r, 'CyP JUJUY', is_salta=False)
            render_cyp(cf2, 'Salta', cs_r, 'CyP SALTA', is_salta=True)

except Exception as e:
    st.error(f"⚠️ Error: {e}")
