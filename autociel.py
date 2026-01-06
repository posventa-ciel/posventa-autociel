import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Grupo CENOA - Gestión Posventa", layout="wide")

# --- ESTILO ---
st.markdown("""<style>
    .main { background-color: #f4f7f9; }
    .portada-container { background: linear-gradient(90deg, #00235d 0%, #004080 100%); color: white; padding: 2rem; border-radius: 15px; text-align: center; margin-bottom: 2rem; }
    .area-box { background-color: white; border: 1px solid #e0e0e0; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); min-height: 280px; margin-bottom: 20px; }
    .metric-small { font-size: 0.9rem; color: #666; }
    .stTabs [aria-selected="true"] { background-color: #00235d !important; color: white !important; font-weight: bold; }
</style>""", unsafe_allow_html=True)

# --- FUNCIÓN DE BÚSQUEDA ---
def find_col(df, include_keywords, exclude_keywords=[]):
    """Busca una columna que contenga todas las include_keywords y ninguna exclude_keywords"""
    for col in df.columns:
        # Normalizamos a mayúsculas para comparar
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
            # Limpieza de nombres de columnas
            df.columns = [c.strip().upper().replace(".", "").replace("Í", "I") for c in df.columns]
            
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
            st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/Google_Homepage.svg/1200px-Google_Homepage.svg.png", width=100) # Placeholder logo
            st.header("Filtros")
            # Filtro Año
            años_disp = sorted([int(a) for a in data['CALENDARIO']['Año'].unique() if a > 0], reverse=True)
            año_sel = st.selectbox("📅 Año", años_disp)
            
            # Filtro Mes
            meses_nom = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
            # Filtramos los meses disponibles para el año seleccionado
            df_year = data['CALENDARIO'][data['CALENDARIO']['Año'] == año_sel]
            meses_disp = sorted(df_year['Mes'].unique(), reverse=True)
            mes_sel = st.selectbox("📅 Mes", meses_disp, format_func=lambda x: meses_nom.get(x, "N/A"))

        # --- FILTRADO DE DATAFRAMES ---
        def get_mes_data(df, return_full=False):
            res = df[(df['Año'] == año_sel) & (df['Mes'] == mes_sel)].sort_values('Fecha_dt')
            if return_full: return res
            return res.iloc[-1] if not res.empty else pd.Series(dtype='object')

        c_r = get_mes_data(data['CALENDARIO']) # Última fila calendario
        s_r = get_mes_data(data['SERVICIOS'])
        r_r = get_mes_data(data['REPUESTOS'])
        t_r = get_mes_data(data['TALLER'])
        cj_r = get_mes_data(data['CyP JUJUY'])
        cs_r = get_mes_data(data['CyP SALTA'])

        # --- LÓGICA DE DÍAS Y PROYECCIÓN (SOLUCIÓN PROBLEMA 1) ---
        # 1. Intentamos leer columnas explícitas
        col_dias_trans = find_col(data['CALENDARIO'], ["DIAS", "TRANS"]) or find_col(data['CALENDARIO'], ["DIAS", "AVANCE"])
        col_dias_hab = find_col(data['CALENDARIO'], ["DIAS", "HAB"]) or find_col(data['CALENDARIO'], ["DIAS", "TOTAL"])
        
        d_t = float(c_r.get(col_dias_trans, 0))
        d_h = float(c_r.get(col_dias_hab, 0))

        # 2. Fallback inteligente: Si d_t es 0 o 1 (y estamos a fin de mes, esto es un error), calculamos por fecha
        df_cal_filtrado = get_mes_data(data['CALENDARIO'], return_full=True)
        
        if not df_cal_filtrado.empty:
            fecha_max = df_cal_filtrado['Fecha_dt'].max()
            # Si d_h (días hábiles totales) vino vacío del excel, usamos un estándar aproximado o tratamos de inferirlo
            if d_h <= 1: 
                d_h = 22 # Default días hábiles si falla la lectura
            
            # Si d_t (transcurridos) es incorrecto (ej: 1), lo calculamos:
            # Opción A: Contar registros si cada fila es un día
            d_t_calc = len(df_cal_filtrado)
            # Opción B: Si el mes ya terminó (ej: Diciembre seleccionado y estamos en Enero), d_t debería ser igual a d_h
            hoy = datetime.now()
            if (año_sel < hoy.year) or (año_sel == hoy.year and mes_sel < hoy.month):
                d_t = d_h # Mes cerrado
            elif d_t <= 1 and d_t_calc > 1:
                d_t = d_t_calc # Usamos el conteo de filas si la columna manual falla
        
        # Evitar división por cero
        d_h = max(d_h, 1) 
        d_t = max(d_t, 0) # No puede ser negativo
        
        prog_t = d_t / d_h # % Avance del mes (tiempo)

        # --- KPI PRINCIPAL DE AVANCE ---
        st.markdown(f"""
        <div class="portada-container">
            <h1>Autociel - Tablero Posventa</h1>
            <h3 style="margin:0;">📅 {meses_nom.get(mes_sel)} {año_sel}</h3>
            <div style="margin-top:10px; font-size: 1.2rem;">
                Avance Temporal: <b>{d_t:g}</b> de <b>{d_h:g}</b> días hábiles ({prog_t:.1%})
            </div>
            <div style="background: rgba(255,255,255,0.2); height: 8px; border-radius: 4px; width: 50%; margin: 10px auto;">
                <div style="background: #fff; width: {min(prog_t*100, 100)}%; height: 100%; border-radius: 4px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        tab1, tab2, tab3, tab4 = st.tabs(["🏠 General & Objetivos", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura"])

        with tab1:
            st.markdown("### 🎯 Control de Objetivos")
            st.info("💡 Las tarjetas muestran el **Objetivo Parcial** (lo que deberíamos llevar acumulado al día de hoy según el avance del mes) vs la **Realidad**.")
            
            cols = st.columns(4)
            
            # --- CÁLCULO DE REALES ---
            c_mc = find_col(data['SERVICIOS'], ["MO", "CLI"], exclude_keywords=["OBJ", "HS"])
            c_mg = find_col(data['SERVICIOS'], ["MO", "GAR"], exclude_keywords=["OBJ", "HS"])
            c_mt = find_col(data['SERVICIOS'], ["MO", "TER"], exclude_keywords=["OBJ", "HS"])
            real_mo = s_r.get(c_mc,0) + s_r.get(c_mg,0) + s_r.get(c_mt,0)
            
            canales_totales = ['MOSTRADOR', 'TALLER', 'INTERNA', 'GAR', 'CYP', 'MAYORISTA', 'SEGUROS']
            real_rep = 0
            for c in canales_totales:
                col_v = find_col(data['REPUESTOS'], ["VENTA", c], exclude_keywords=["OBJ"])
                if col_v: real_rep += r_r.get(col_v, 0)
            
            # CyP Jujuy
            cyp_j_mo = cj_r.get(find_col(data['CyP JUJUY'], ["MO", "PUR"]), 0) + cj_r.get(find_col(data['CyP JUJUY'], ["MO", "TER"]), 0)
            # CyP Salta (CORRECCIÓN PROBLEMA 2: Sumar Repuestos)
            cyp_s_mo = cs_r.get(find_col(data['CyP SALTA'], ["MO", "PUR"]), 0) + cs_r.get(find_col(data['CyP SALTA'], ["MO", "TER"]), 0)
            cyp_s_rep = cs_r.get(find_col(data['CyP SALTA'], ["FACT", "REP"]), 0) # Buscamos col que diga FACT y REP
            real_cyp_salta = cyp_s_mo + cyp_s_rep

            metas = [
                ("M.O. Servicios", real_mo, s_r.get(find_col(data['SERVICIOS'], ["OBJ", "MO"]), 1)),
                ("Repuestos", real_rep, r_r.get(find_col(data['REPUESTOS'], ["OBJ", "FACT"]), 1)),
                ("CyP Jujuy", cyp_j_mo, cj_r.get(find_col(data['CyP JUJUY'], ["OBJ", "FACT"]), 1)),
                ("CyP Salta", real_cyp_salta, cs_r.get(find_col(data['CyP SALTA'], ["OBJ", "FACT"]), 1))
            ]
            
            for i, (tit, real, obj_mes) in enumerate(metas):
                # Cálculos corregidos
                obj_parcial = obj_mes * prog_t # Objetivo al día de hoy
                proyeccion_cierre = (real / d_t) * d_h if d_t > 0 else 0
                
                cumplimiento_parcial = real / obj_parcial if obj_parcial > 0 else 0
                cumplimiento_mes = real / obj_mes if obj_mes > 0 else 0
                
                color = "#dc3545" if cumplimiento_parcial < 0.90 else ("#ffc107" if cumplimiento_parcial < 0.98 else "#28a745")
                delta = real - obj_parcial
                icon = "🔻" if delta < 0 else "✅"

                with cols[i]:
                    st.markdown(f"""<div class="area-box">
                        <p style="font-weight:bold; color:#666; margin-bottom:5px;">{tit}</p>
                        <h2 style="margin:0; color:#00235d;">${real:,.0f}</h2>
                        <p class="metric-small">vs Obj. Parcial: <b>${obj_parcial:,.0f}</b> ({icon})</p>
                        <hr style="margin: 10px 0; border-top: 1px solid #eee;">
                        
                        <div style="display:flex; justify-content:space-between; font-size:0.85rem;">
                            <span>Obj. Mes:</span>
                            <b>${obj_mes:,.0f}</b>
                        </div>
                        <div style="display:flex; justify-content:space-between; font-size:0.85rem; color:{color}; font-weight:bold;">
                            <span>Proyección:</span>
                            <span>${proyeccion_cierre:,.0f}</span>
                        </div>
                        
                        <div style="margin-top:15px;">
                            <p style="margin:0; font-size:12px; color:#666;">% Cumplimiento Mes: {cumplimiento_mes:.1%}</p>
                            <div style="width:100%; background:#e0e0e0; height:8px; border-radius:10px; margin-top:2px;">
                                <div style="width:{min(cumplimiento_mes*100, 100)}%; background:{color}; height:8px; border-radius:10px;"></div>
                            </div>
                        </div>
                    </div>""", unsafe_allow_html=True)

        with tab2:
            st.header("Performance y Tickets")
            k1, k2, k3, k4 = st.columns(4)
            c_cpus_real = find_col(data['SERVICIOS'], ["CPUS"], exclude_keywords=["OBJ", "META"])
            c_tus_real = find_col(data['SERVICIOS'], ["OTROS", "CARGOS"], exclude_keywords=["OBJ"])
            
            real_tus = s_r.get(c_cpus_real, 0) + s_r.get(c_tus_real, 0)
            obj_tus = s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'TUS']), 1)
            real_cpus = s_r.get(c_cpus_real, 0)
            obj_cpus = s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'CPUS']), 1)

            # Ticket Promedio
            divisor = real_cpus if real_cpus > 0 else 1
            col_hs_cc = find_col(data['TALLER'], ["FACT", "CC"], exclude_keywords=["$", "PESOS", "OBJ"])
            col_hs_cg = find_col(data['TALLER'], ["FACT", "CG"], exclude_keywords=["$", "PESOS", "OBJ"])
            tp_hs = (t_r.get(col_hs_cc, 0) + t_r.get(col_hs_cg, 0)) / divisor
            tp_mo = real_mo / divisor # Usamos el real_mo calculado en tab1
            
            # Helper para KPIs
            def kpi_card(col, title, val, target):
                target_partial = target * prog_t
                dif = (val / target_partial) - 1 if target_partial > 0 else 0
                col.metric(title, f"{val:,.0f}", f"{dif:.1%} vs Obj.P.", delta_color="normal")

            kpi_card(k1, "TUS Total", real_tus, obj_tus)
            kpi_card(k2, "CPUS Cliente", real_cpus, obj_cpus)
            k3.metric("Ticket Promedio M.O. (Hs)", f"{tp_hs:.2f} hs/CPUS")
            k4.metric("Ticket Promedio M.O. ($)", f"${tp_mo:,.0f}/CPUS")
            
            st.markdown("---")
            # --- LOS 6 INDICADORES DE TALLER ---
            st.subheader("Indicadores de Eficiencia y Productividad")
            
            col_tr_cc = find_col(data['TALLER'], ["TRAB", "CC"], exclude_keywords=["$"])
            col_tr_cg = find_col(data['TALLER'], ["TRAB", "CG"], exclude_keywords=["$"])
            col_tr_ci = find_col(data['TALLER'], ["TRAB", "CI"], exclude_keywords=["$"])
            col_ft_cc = find_col(data['TALLER'], ["FACT", "CC"], exclude_keywords=["$"])
            col_ft_cg = find_col(data['TALLER'], ["FACT", "CG"], exclude_keywords=["$"])
            col_ft_ci = find_col(data['TALLER'], ["FACT", "CI"], exclude_keywords=["$"])

            ht_cc, ht_cg, ht_ci = t_r.get(col_tr_cc, 0), t_r.get(col_tr_cg, 0), t_r.get(col_tr_ci, 0)
            hf_cc, hf_cg, hf_ci = t_r.get(col_ft_cc, 0), t_r.get(col_ft_cg, 0), t_r.get(col_ft_ci, 0)
            
            # Eficiencias
            ef_cc = hf_cc / ht_cc if ht_cc > 0 else 0
            ef_cg = hf_cg / ht_cg if ht_cg > 0 else 0
            ef_gl = (hf_cc + hf_cg + hf_ci) / (ht_cc + ht_cg + ht_ci) if (ht_cc + ht_cg + ht_ci) > 0 else 0
            
            # CORRECCIÓN PROBLEMA 3: Presencia
            hs_disp_reales = t_r.get(find_col(data['TALLER'], ["DISPONIBLES", "REAL"]), 0)
            
            # Cálculo de técnicos (buscamos columna)
            col_tecs = find_col(data['TALLER'], ["TECNICOS"], exclude_keywords=["PROD"])
            cant_tecs = t_r.get(col_tecs, 6) # Default 6 si no encuentra
            if cant_tecs == 0: cant_tecs = 6

            # Horas teóricas basadas en DÍAS TRANSCURRIDOS (d_t) corregidos
            hs_teoricas = cant_tecs * 9 * d_t 
            
            presencia = hs_disp_reales / hs_teoricas if hs_teoricas > 0 else 0
            ocup = (ht_cc + ht_cg + ht_ci) / hs_disp_reales if hs_disp_reales > 0 else 0
            prod = t_r.get(find_col(data['TALLER'], ["PRODUCTIVIDAD", "TALLER"]), 0)
            if prod > 2: prod /= 100

            e1, e2, e3, e4, e5 = st.columns(5)
            e1.metric("Eficiencia CC", f"{ef_cc:.1%}", delta=f"{(ef_cc-1):.1%}")
            e2.metric("Eficiencia Global", f"{ef_gl:.1%}", delta=f"{(ef_gl-0.85):.1%}")
            e3.metric("Grado Presencia", f"{presencia:.1%}", help="Hs Disponibles / (Técnicos * 9hs * Días Transcurridos)")
            e4.metric("Grado Ocupación", f"{ocup:.1%}", delta=f"{(ocup-0.95):.1%}")
            e5.metric("Productividad", f"{prod:.1%}", delta=f"{(prod-0.95):.1%}")

            # Gráficos de Torta de Horas
            g1, g2 = st.columns(2)
            with g1: st.plotly_chart(px.pie(values=[ht_cc, ht_cg, ht_ci], names=["CC", "CG", "CI"], hole=0.4, title="Hs Trabajadas"), use_container_width=True)
            with g2: st.plotly_chart(px.pie(values=[hf_cc, hf_cg, hf_ci], names=["CC", "CG", "CI"], hole=0.4, title="Hs Facturadas"), use_container_width=True)

        with tab3:
            st.header("Gestión de Repuestos")
            r1, r2, r3, r4 = st.columns(4)
            
            detalles = []
            for c in canales_totales:
                v_col = find_col(data['REPUESTOS'], ["VENTA", c], exclude_keywords=["OBJ"])
                if v_col:
                    vb = r_r.get(v_col, 0)
                    d = r_r.get(find_col(data['REPUESTOS'], ["DESC", c]), 0)
                    cost = r_r.get(find_col(data['REPUESTOS'], ["COSTO", c]), 0)
                    vn = vb - d
                    ut = vn - cost
                    detalles.append({"Canal": c, "Venta Neta": vn, "Utilidad $": ut})
            
            df_r_calc = pd.DataFrame(detalles)
            if not df_r_calc.empty:
                vta_total = df_r_calc['Venta Neta'].sum()
                util_total = df_r_calc['Utilidad $'].sum()
                mg_total = util_total / vta_total if vta_total > 0 else 0
                
                # Ticket Repuestos
                v_taller = df_r_calc.loc[df_r_calc['Canal'].isin(['TALLER', 'GAR', 'CYP']), 'Venta Neta'].sum()
                tp_rep = v_taller / divisor
                
                r1.metric("Venta Neta Total", f"${vta_total:,.0f}")
                r2.metric("Utilidad Total", f"${util_total:,.0f}")
                r3.metric("Margen Global", f"{mg_total:.1%}")
                r4.metric("Ticket Repuestos", f"${tp_rep:,.0f}/CPUS")
                
                c1, c2 = st.columns([2,1])
                with c1: st.plotly_chart(px.bar(df_r_calc, x="Canal", y="Venta Neta", text_auto='.2s', title="Venta por Canal"), use_container_width=True)
                with c2: st.plotly_chart(px.pie(df_r_calc, values="Utilidad $", names="Canal", hole=0.4, title="Composición Utilidad"), use_container_width=True)

        with tab4:
            st.header("Chapa y Pintura")
            cf1, cf2 = st.columns(2)
            
            # Función auxiliar para renderizar bloque de CyP
            def render_cyp(col_render, nom, row, sheet_name, is_salta=False):
                with col_render:
                    st.subheader(f"Sede {nom}")
                    f_p = row.get(find_col(data[sheet_name], ['MO', 'PUR']), 0)
                    f_t = row.get(find_col(data[sheet_name], ['MO', 'TER']), 0)
                    
                    # Corrección Salta: Buscar Repuestos
                    f_r = 0
                    if is_salta:
                        f_r = row.get(find_col(data[sheet_name], ['FACT', 'REP']), 0)
                    
                    total_fact = f_p + f_t + f_r
                    st.metric(f"Facturación Total {nom}", f"${total_fact:,.0f}")

                    vals = [f_p, f_t]
                    nams = ["M.O. Pura", "M.O. Terceros"]
                    cols_pie = ["#00235d", "#00A8E8"]
                    
                    if f_r > 0:
                        vals.append(f_r)
                        nams.append("Repuestos")
                        cols_pie.append("#28a745")
                        
                    st.plotly_chart(px.pie(values=vals, names=nams, hole=0.4, color_discrete_sequence=cols_pie), use_container_width=True)

            render_cyp(cf1, 'Jujuy', cj_r, 'CyP JUJUY', is_salta=False)
            render_cyp(cf2, 'Salta', cs_r, 'CyP SALTA', is_salta=True)

except Exception as e:
    st.error(f"⚠️ Error crítico: {e}")
    st.write("Por favor revisa que las hojas de Google Sheets tengan los permisos correctos y los nombres de columna no hayan cambiado drásticamente.")
