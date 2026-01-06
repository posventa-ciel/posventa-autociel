import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Grupo CENOA - Gestión Posventa", layout="wide")

# --- ESTILO CSS ---
st.markdown("""<style>
    .main { background-color: #f4f7f9; }
    .portada-container { background: linear-gradient(90deg, #00235d 0%, #004080 100%); color: white; padding: 2rem; border-radius: 15px; text-align: center; margin-bottom: 2rem; }
    .kpi-card { background-color: white; border: 1px solid #e0e0e0; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 20px; min-height: 200px; }
    .stTabs [aria-selected="true"] { background-color: #00235d !important; color: white !important; font-weight: bold; }
    .metric-container { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #eee; text-align: center; }
</style>""", unsafe_allow_html=True)

# --- FUNCIÓN DE BÚSQUEDA ---
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
            
            # --- LIMPIEZA DE COLUMNAS (CRÍTICO PARA LEER "DÍAS") ---
            # Eliminamos tildes explícitamente: Á->A, Í->I, etc.
            df.columns = [
                c.strip().upper()
                .replace(".", "")
                .replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U") 
                for c in df.columns
            ]
            
            # Limpieza numérica
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
        # Procesamiento fechas
        for h in data:
            col_f = find_col(data[h], ["FECHA"]) or data[h].columns[0]
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

        # --- OBTENCIÓN DE DATOS (Última fila del mes) ---
        def get_row(df):
            res = df[(df['Año'] == año_sel) & (df['Mes'] == mes_sel)].sort_values('Fecha_dt')
            return res.iloc[-1] if not res.empty else pd.Series(dtype='object')

        c_r = get_row(data['CALENDARIO'])
        s_r = get_row(data['SERVICIOS'])
        r_r = get_row(data['REPUESTOS'])
        t_r = get_row(data['TALLER'])
        cj_r = get_row(data['CyP JUJUY'])
        cs_r = get_row(data['CyP SALTA'])

        # --- LÓGICA DE DÍAS (CORREGIDA) ---
        # Gracias a la limpieza de tildes, ahora buscará "DIAS TRANS" y encontrará "Días Transcurridos"
        col_trans = find_col(data['CALENDARIO'], ["TRANS"]) 
        col_hab = find_col(data['CALENDARIO'], ["HAB"])
        
        d_t = float(c_r.get(col_trans, 0))
        d_h = float(c_r.get(col_hab, 0))

        # Fallback solo si es 0
        if d_h == 0: d_h = 22 

        # Corrección lógica mes pasado (Si estamos en Enero y seleccionas Dic, fuerza cierre)
        hoy = datetime.now()
        if (año_sel < hoy.year) or (año_sel == hoy.year and mes_sel < hoy.month):
             if d_t < d_h: d_t = d_h # Asumimos mes cerrado si es fecha pasada

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

        tab1, tab2, tab3, tab4 = st.tabs(["🏠 Objetivos", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura"])

        # --- TAB 1: OBJETIVOS (VISUALES YA OK) ---
        with tab1:
            st.markdown("### 🎯 Control de Objetivos")
            cols = st.columns(4)
            
            # Datos Reales
            c_mo = [find_col(data['SERVICIOS'], ["MO", k], exclude_keywords=["OBJ"]) for k in ["CLI", "GAR", "TER"]]
            real_mo = sum([s_r.get(c, 0) for c in c_mo if c])
            
            canales = ['MOSTRADOR', 'TALLER', 'INTERNA', 'GAR', 'CYP', 'MAYORISTA', 'SEGUROS']
            real_rep = sum([r_r.get(find_col(data['REPUESTOS'], ["VENTA", c], exclude_keywords=["OBJ"]), 0) for c in canales])
            
            def get_cyp_total(row, df_nom):
                mo = row.get(find_col(data[df_nom], ["MO", "PUR"]), 0) + row.get(find_col(data[df_nom], ["MO", "TER"]), 0)
                rep = row.get(find_col(data[df_nom], ["FACT", "REP"]), 0) 
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
                
                html_card = f"""<div class="kpi-card"><p style="font-weight:bold; color:#666; margin-bottom:5px;">{tit}</p><h2 style="margin:0; color:#00235d;">${real:,.0f}</h2><p style="font-size:0.9rem; color:#666; margin-top:5px;">vs Obj. Parcial: <b>${obj_parcial:,.0f}</b> {icon}</p><hr style="margin:10px 0; border:0; border-top:1px solid #eee;"><div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:5px;"><span>Obj. Mes:</span><b>${obj_mes:,.0f}</b></div><div style="display:flex; justify-content:space-between; font-size:0.85rem; color:{color}; font-weight:bold;"><span>Proyección:</span><span>${proy:,.0f}</span></div><div style="margin-top:10px;"><div style="width:100%; background:#e0e0e0; height:6px; border-radius:10px;"><div style="width:{min(cumpl*100, 100)}%; background:{color}; height:6px; border-radius:10px;"></div></div></div></div>"""
                with cols[i]: st.markdown(html_card, unsafe_allow_html=True)

        # --- TAB 2: SERVICIOS Y TALLER (RESTAURADA COMPLETA) ---
        with tab2:
            st.header("Performance y Tickets")
            k1, k2, k3, k4 = st.columns(4)
            c_cpus = find_col(data['SERVICIOS'], ["CPUS"], exclude_keywords=["OBJ"])
            c_tus = find_col(data['SERVICIOS'], ["OTROS", "CARGOS"], exclude_keywords=["OBJ"])
            
            real_cpus = s_r.get(c_cpus, 0)
            real_tus = real_cpus + s_r.get(c_tus, 0)
            obj_tus = s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'TUS']), 1)
            obj_cpus = s_r.get(find_col(data['SERVICIOS'], ['OBJ', 'CPUS']), 1)
            
            div = real_cpus if real_cpus > 0 else 1
            fact_taller = t_r.get(find_col(data['TALLER'], ["FACT", "CC"]), 0) + t_r.get(find_col(data['TALLER'], ["FACT", "CG"]), 0)
            tp_hs = fact_taller / div
            tp_mo = real_mo / div

            k1.metric("TUS Total", f"{real_tus:,.0f}", f"{(real_tus/(obj_tus*prog_t)-1):.1%} vs Obj.P" if obj_tus > 0 else None)
            k2.metric("CPUS Cliente", f"{real_cpus:,.0f}", f"{(real_cpus/(obj_cpus*prog_t)-1):.1%} vs Obj.P" if obj_cpus > 0 else None)
            k3.metric("Ticket Promedio (Hs)", f"{tp_hs:.2f} hs")
            k4.metric("Ticket Promedio ($)", f"${tp_mo:,.0f}")
            
            st.markdown("---")
            st.subheader("Indicadores de Taller")
            
            # Recuperación de datos detallados de Taller
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

            # Presencia y Ocupación
            hs_disp = t_r.get(find_col(data['TALLER'], ["DISPONIBLES", "REAL"]), 0)
            
            col_tecs = find_col(data['TALLER'], ["TECNICOS"], exclude_keywords=["PROD"])
            cant_tecs = t_r.get(col_tecs, 6)
            if cant_tecs == 0: cant_tecs = 6
            
            # CÁLCULO ACORDADO: Hs Teóricas = Técnicos * 9hs * Días Transcurridos (d_t del Excel)
            hs_teoricas = cant_tecs * 9 * d_t 
            
            presencia = hs_disp / hs_teoricas if hs_teoricas > 0 else 0
            ocup = (ht_cc + ht_cg + ht_ci) / hs_disp if hs_disp > 0 else 0
            prod = t_r.get(find_col(data['TALLER'], ["PRODUCTIVIDAD", "TALLER"]), 0)
            if prod > 2: prod /= 100

            # KPIs Fila 1
            e1, e2, e3 = st.columns(3)
            e1.metric("Eficiencia CC", f"{ef_cc:.1%}", delta=f"{(ef_cc-1):.1%}")
            e2.metric("Eficiencia CG", f"{ef_cg:.1%}", delta=f"{(ef_cg-1):.1%}")
            e3.metric("Eficiencia Global", f"{ef_gl:.1%}", delta=f"{(ef_gl-0.85):.1%}")
            
            # KPIs Fila 2
            e4, e5, e6 = st.columns(3)
            e4.metric("Grado Presencia", f"{presencia:.1%}", help="Hs Disponibles Reales / (Técnicos * 9 * Días Transcurridos)")
            e5.metric("Grado Ocupación", f"{ocup:.1%}", delta=f"{(ocup-0.95):.1%}")
            e6.metric("Productividad", f"{prod:.1%}", delta=f"{(prod-0.95):.1%}")

            # Gráficos de Torta (Restaurados)
            g1, g2 = st.columns(2)
            with g1: st.plotly_chart(px.pie(values=[ht_cc, ht_cg, ht_ci], names=["CC", "CG", "CI"], hole=0.4, title="Hs Trabajadas"), use_container_width=True)
            with g2: st.plotly_chart(px.pie(values=[hf_cc, hf_cg, hf_ci], names=["CC", "CG", "CI"], hole=0.4, title="Hs Facturadas"), use_container_width=True)

        # --- TAB 3: REPUESTOS (RESTAURADA COMPLETA) ---
        with tab3:
            st.header("Análisis de Repuestos")
            r1, r2, r3, r4 = st.columns(4)
            
            detalles = []
            for c in canales:
                v_col = find_col(data['REPUESTOS'], ["VENTA", c], exclude_keywords=["OBJ"])
                if v_col:
                    vb = r_r.get(v_col, 0)
                    d = r_r.get(find_col(data['REPUESTOS'], ["DESC", c]), 0)
                    cost = r_r.get(find_col(data['REPUESTOS'], ["COSTO", c]), 0)
                    vn = vb - d
                    ut = vn - cost
                    detalles.append({"Canal": c, "Venta Neta": vn, "Utilidad $": ut, "Margen %": (ut/vn if vn>0 else 0)})
            
            df_r = pd.DataFrame(detalles)
            
            if not df_r.empty:
                vta_total = df_r['Venta Neta'].sum()
                util_total = df_r['Utilidad $'].sum()
                mg_total = util_total / vta_total if vta_total > 0 else 0
                
                v_taller = df_r.loc[df_r['Canal'].isin(['TALLER', 'GAR', 'CYP']), 'Venta Neta'].sum()
                tp_rep = v_taller / div # Usamos el divisor CPUS
                
                r1.metric("Venta Neta Total", f"${vta_total:,.0f}")
                r2.metric("Utilidad Total", f"${util_total:,.0f}")
                r3.metric("Margen Global", f"{mg_total:.1%}")
                r4.metric("Ticket Repuestos", f"${tp_rep:,.0f}")
                
                st.dataframe(df_r.style.format({"Venta Neta":"${:,.0f}", "Utilidad $":"${:,.0f}", "Margen %":"{:.1%}"}), use_container_width=True)
                
                c1, c2 = st.columns([2,1])
                with c1: st.plotly_chart(px.bar(df_r, x="Canal", y="Venta Neta", text_auto='.2s', title="Venta por Canal"), use_container_width=True)
                
                # Gráfico de Stock (Restaurado)
                with c2:
                    val_stock = float(r_r.get(find_col(data['REPUESTOS'], ["VALOR", "STOCK"]), 0))
                    p_vivo = float(r_r.get(find_col(data['REPUESTOS'], ["VIVO"]), 0))
                    p_obs = float(r_r.get(find_col(data['REPUESTOS'], ["OBSOLETO"]), 0))
                    p_muerto = float(r_r.get(find_col(data['REPUESTOS'], ["MUERTO"]), 0))
                    
                    # Normalización por si viene en decimal (0.5) o entero (50)
                    f = 1 if p_vivo <= 1 else 100
                    df_s = pd.DataFrame({"Estado": ["Vivo", "Obsoleto", "Muerto"], "Valor": [val_stock*(p_vivo/f), val_stock*(p_obs/f), val_stock*(p_muerto/f)]})
                    st.plotly_chart(px.pie(df_s, values="Valor", names="Estado", hole=0.4, title="Stock", color_discrete_sequence=["#28a745", "#ffc107", "#dc3545"]), use_container_width=True)

        # --- TAB 4: CHAPA Y PINTURA (RESTAURADA COMPLETA) ---
        with tab4:
            st.header("Chapa y Pintura")
            cf1, cf2 = st.columns(2)
            
            def render_cyp_full(col_render, nom, row, sheet_name, is_salta=False):
                with col_render:
                    st.subheader(f"Sede {nom}")
                    f_p = row.get(find_col(data[sheet_name], ['MO', 'PUR']), 0)
                    f_t = row.get(find_col(data[sheet_name], ['MO', 'TER']), 0)
                    f_r = row.get(find_col(data[sheet_name], ['FACT', 'REP']), 0) if is_salta else 0
                    
                    st.metric(f"Facturación Total {nom}", f"${(f_p+f_t+f_r):,.0f}")

                    # Gráfico
                    vals = [f_p, f_t]
                    nams = ["M.O. Pura", "M.O. Terceros"]
                    cols_pie = ["#00235d", "#00A8E8"]
                    if f_r > 0:
                        vals.append(f_r); nams.append("Repuestos"); cols_pie.append("#28a745")
                        
                    st.plotly_chart(px.pie(values=vals, names=nams, hole=0.4, color_discrete_sequence=cols_pie), use_container_width=True)
                    
                    # Margen Terceros
                    c_ter = row.get(find_col(data[sheet_name], ['COSTO', 'TER']), 0)
                    m_ter = f_t - c_ter
                    st.info(f"💡 **Terceros:** Fact: ${f_t:,.0f} | Costo: ${c_ter:,.0f} | Mg: ${m_ter:,.0f}")
                    
                    # Paños por Técnico
                    panos = row.get(find_col(data[sheet_name], ['PAÑOS', 'PROP']), 0)
                    col_tecnicos = find_col(data[sheet_name], ['TECNICO'], exclude_keywords=['PRODUCTIVIDAD']) or find_col(data[sheet_name], ['PRODUCTIVOS'])
                    cant_tec = row.get(col_tecnicos, 1) if col_tecnicos else 1
                    ratio = panos / cant_tec if cant_tec > 0 else 0
                    st.metric("Paños por Técnico", f"{ratio:.1f}")

            render_cyp_full(cf1, 'Jujuy', cj_r, 'CyP JUJUY', is_salta=False)
            render_cyp_full(cf2, 'Salta', cs_r, 'CyP SALTA', is_salta=True)

    else:
        st.warning("No se pudieron cargar los datos.")

except Exception as e:
    st.error(f"Error global: {e}")
