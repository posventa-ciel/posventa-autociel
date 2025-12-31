import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Grupo CENOA - Gestión Posventa", layout="wide")

# --- ESTILO CORPORATIVO ---
st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    .portada-container {
        background: linear-gradient(90deg, #00235d 0%, #004080 100%);
        color: white; padding: 2rem; border-radius: 15px;
        margin-bottom: 2rem; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .titulo-portada { font-size: 2.2rem; font-weight: 800; margin: 10px 0; border:none !important; }
    .status-line { background: rgba(255,255,255,0.1); padding: 5px 15px; border-radius: 50px; display: inline-block; font-size: 0.9rem; }
    .stMetric { background-color: white; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; }
    .stTabs [aria-selected="true"] { background-color: #00235d !important; color: white !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

def calcular_proyeccion(real, dias_t, dias_h):
    return (real / dias_t) * dias_h if dias_t > 0 else 0

archivo = st.sidebar.file_uploader("📂 Cargar Archivo Madre Autociel", type="xlsx")

if archivo:
    try:
        hojas = ['CALENDARIO', 'SERVICIOS', 'REPUESTOS', 'TALLER', 'CyP JUJUY', 'CyP SALTA']
        data = {h: pd.read_excel(archivo, sheet_name=h).fillna(0) for h in hojas}

        for h in hojas:
            col_f = 'Fecha Corte' if 'Fecha Corte' in data[h].columns else 'Fecha'
            data[h]['Fecha_dt'] = pd.to_datetime(data[h][col_f]).dt.date

        fechas = sorted(data['CALENDARIO']['Fecha_dt'].unique(), reverse=True)
        f_sel = st.sidebar.selectbox("📅 Seleccionar Fecha", fechas)
        
        meses_es = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 
                    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
        
        c_r = data['CALENDARIO'][data['CALENDARIO']['Fecha_dt'] == f_sel].iloc[0]
        d_t, d_h = int(c_r['Días Transcurridos']), int(c_r['Días Hábiles Mes'])
        prog_t = d_t / d_h if d_h > 0 else 0

        # --- PORTADA ---
        st.markdown(f"""
            <div class="portada-container">
                <div style="letter-spacing: 3px; opacity: 0.8; text-transform: uppercase;">Grupo CENOA</div>
                <div class="titulo-portada">Resumen General de Objetivos de Posventa</div>
                <div class="status-line">
                    📍 Autociel | 📅 {meses_es[f_sel.month]} {f_sel.year} | ⏱️ Avance: {d_t}/{d_h} días ({prog_t:.1%})
                </div>
            </div>
        """, unsafe_allow_html=True)

        f_obj = f_sel.replace(day=1)
        s_r = data['SERVICIOS'][data['SERVICIOS']['Fecha_dt'] == f_sel].iloc[0]
        r_r = data['REPUESTOS'][data['REPUESTOS']['Fecha_dt'] == f_sel].iloc[0]
        t_r = data['TALLER'][data['TALLER']['Fecha_dt'] == f_sel].iloc[0]
        cj_r = data['CyP JUJUY'][data['CyP JUJUY']['Fecha_dt'] == f_sel].iloc[0]
        cs_r = data['CyP SALTA'][data['CyP SALTA']['Fecha_dt'] == f_sel].iloc[0]

        def get_o(df_name, col):
            df = data[df_name]
            f_o = df[df['Fecha_dt'] == f_obj]
            return f_o[col].iloc[0] if not f_o.empty else df[col].max()

        tab1, tab2, tab3, tab4 = st.tabs(["🏠 General", "🛠️ Servicios y Taller", "📦 Repuestos", "🎨 Chapa y Pintura"])

        with tab1:
            cols = st.columns(4)
            # Cálculos de Real
            r_mo = s_r['MO Cliente'] + s_r['MO Garantía'] + s_r['MO Tercero']
            r_rep = sum([r_r[f'Venta {c}'] for c in ['Mostrador', 'Taller', 'Interna', 'Garantía', 'CyP', 'Mayorista', 'Seguros'] if f'Venta {c}' in r_r])
            r_cj = cj_r['MO Pura'] + cj_r['MO Tercero']
            r_cs = cs_r['MO Pura'] + cs_r['MO Tercero'] + cs_r.get('Fact Repuestos', 0)
            
            # Definición de Metas
            metas = [
                ("Servicios", r_mo, get_o('SERVICIOS', 'Obj MO Total')), 
                ("Repuestos", r_rep, get_o('REPUESTOS', 'Obj Facturación Total')),
                ("CyP Jujuy", r_cj, get_o('CyP JUJUY', 'Obj Facturación Total CyP Jujuy')), 
                ("CyP Salta", r_cs, get_o('CyP SALTA', 'Obj Facturación Total CyP Salta'))
            ]

            for i, (tit, real, obj) in enumerate(metas):
                # Calculamos proyección en $ y el alcance porcentual
                p_pesos = calcular_proyeccion(real, d_t, d_h)
                alc = p_pesos / obj if obj > 0 else 0
                
                # Color del semáforo
                color = "#dc3545" if alc < 0.90 else ("#ffc107" if alc < 0.95 else "#28a745")
                
                with cols[i]:
                    st.markdown(f"**{tit}**")
                    st.markdown(f"<h1 style='margin:0; color:#00235d; font-size: 32px;'>${real:,.0f}</h1>", unsafe_allow_html=True)
                    st.markdown(f"<p style='margin:0; font-size: 18px; color: #444; font-weight: 700;'>OBJETIVO: ${obj:,.0f}</p>", unsafe_allow_html=True)
                    
                    # Proyección porcentual y en pesos
                    st.markdown(f"""
                        <div style='margin-top:10px;'>
                            <p style='color:{color}; font-size:18px; margin:0;'><b>Proy: {alc:.1%}</b></p>
                            <p style='color:#666; font-size:14px; margin:0;'>Est. al cierre: <b>${p_pesos:,.0f}</b></p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Barra de progreso
                    st.markdown(f"""
                        <div style="width:100%; background:#e0e0e0; height:8px; border-radius:10px; margin-top:5px;">
                            <div style="width:{min(alc*100, 100)}%; background:{color}; height:8px; border-radius:10px;"></div>
                        </div>
                    """, unsafe_allow_html=True)

        with tab2:
            st.header("Flujo de Unidades y Performance")
            c_u1, c_u2 = st.columns(2)
            real_tus = s_r['CPUS'] + s_r['Otros Cargos']
            ind_taller = [("Total Unidades Servicio (TUS)", real_tus, get_o('SERVICIOS', 'Obj TUS')), 
                         ("Cargos Clientes (CPUS)", s_r['CPUS'], get_o('SERVICIOS', 'Obj CPUS'))]
            for i, (tit, real, obj) in enumerate(ind_taller):
                p_cant = calcular_proyeccion(real, d_t, d_h)
                alc = p_cant / obj if obj > 0 else 0
                color_kpi = "#dc3545" if alc < 0.90 else ("#ffc107" if alc < 0.95 else "#28a745")
                with (c_u1 if i == 0 else c_u2):
                    st.markdown(f"""
                        <div style="border: 1px solid #e0e0e0; padding: 20px; border-radius: 10px; background-color: white; min-height: 180px;">
                            <p style="font-size: 14px; color: #666; margin-bottom: 2px; font-weight: bold;">{tit}</p>
                            <h1 style="margin: 0; font-size: 42px; color: #333;">{real:,.0f} <span style="font-size: 18px; color: #999;">/ Obj: {obj:,.0f}</span></h1>
                            <p style="color: {color_kpi}; font-weight: bold; font-size: 18px; margin-top: 15px; border-top: 1px solid #eee; padding-top: 10px;">
                                ↑ Proyección: {p_cant:,.0f} unidades ({alc:.1%})
                            </p>
                        </div>
                    """, unsafe_allow_html=True)

            st.markdown("---")
            st.header("Composición de Horas y Eficiencia")
            ht_cc, ht_cg, ht_ci = t_r['Hs Trabajadas CC'], t_r['Hs Trabajadas CG'], t_r['Hs Trabajadas CI']
            hf_cc, hf_cg, hf_ci = t_r['Hs Facturadas CC'], t_r['Hs Facturadas CG'], t_r['Hs Facturadas CI']
            c_h1, c_h2 = st.columns(2)
            with c_h1:
                st.plotly_chart(px.pie(values=[ht_cc, ht_cg, ht_ci], names=["CC", "CG", "CI"], hole=0.4, title="Horas Trabajadas"), use_container_width=True)
            with c_h2:
                st.plotly_chart(px.pie(values=[hf_cc, hf_cg, hf_ci], names=["CC", "CG", "CI"], hole=0.4, title="Horas Facturadas"), use_container_width=True)

            e1, e2, e3 = st.columns(3)
            ef_cc = hf_cc / ht_cc if ht_cc > 0 else 0
            ef_cg = hf_cg / ht_cg if ht_cg > 0 else 0
            ef_gl = (hf_cc+hf_cg+hf_ci)/(ht_cc+ht_cg+ht_ci) if (ht_cc+ht_cg+ht_ci) > 0 else 0
            e1.metric("Eficiencia CC", f"{ef_cc:.1%}", delta=f"{(ef_cc-1):.1%}")
            e2.metric("Eficiencia CG", f"{ef_cg:.1%}", delta=f"{(ef_cg-1):.1%}")
            e3.metric("Eficiencia GLOBAL", f"{ef_gl:.1%}", delta=f"{(ef_gl-0.85):.1%}")
            
            k1, k2, k3 = st.columns(3)
            h_d_r = t_r['Hs Disponibles Real']
            h_d_i = 8 * 6 * d_t 
            pres = h_d_r / h_d_i if h_d_i > 0 else 0
            ocup = (ht_cc + ht_cg + ht_ci) / h_d_r if h_d_r > 0 else 0
            prod = t_r.get('Productividad Taller %', 0)
            k1.metric("Grado Presencia", f"{pres:.1%}", delta=f"{(pres-0.9):.1%}")
            k2.metric("Grado Ocupación", f"{ocup:.1%}", delta=f"{(ocup-0.95):.1%}")
            k3.metric("Productividad", f"{prod:.1%}", delta=f"{(prod-0.95):.1%}")

        with tab3:
            st.header("Análisis de Ventas y Stock")
            
            # 1. Preparación de datos de Ventas
            canales = ['Mostrador', 'Taller', 'Interna', 'Garantía', 'CyP', 'Mayorista', 'Seguros']
            detalles = []
            for c in canales:
                if f'Venta {c}' in r_r:
                    vb = r_r[f'Venta {c}']
                    d = r_r.get(f'Descuento {c}', 0)
                    cost = r_r.get(f'Costo {c}', 0)
                    vn = vb - d
                    ut = vn - cost
                    detalles.append({
                        "Canal": c, 
                        "Bruta": vb, 
                        "Desc": d, 
                        "Costo": cost, 
                        "Margen $": ut, 
                        "% Mg": (ut/vn if vn>0 else 0)
                    })
            
            df_r = pd.DataFrame(detalles)
            
            st.subheader("Márgenes por Canal")
            st.dataframe(
                df_r.style.format({
                    "Bruta": "${:,.0f}", 
                    "Desc": "${:,.0f}", 
                    "Costo": "${:,.0f}", 
                    "Margen $": "${:,.0f}", 
                    "% Mg": "{:.1%}"
                }), 
                use_container_width=True,
                hide_index=True 
            )

            # --- MÉTRICAS DE TOTALES ---
            st.markdown("### Resumen de Rentabilidad Total")
            c_tot1, c_tot2, c_tot3 = st.columns(3)
            
            total_facturacion_bruta = df_r['Bruta'].sum()
            total_margen_pesos = df_r['Margen $'].sum()
            total_descuentos = df_r['Desc'].sum()
            v_neta_total = total_facturacion_bruta - total_descuentos
            margen_porc_total = (total_margen_pesos / v_neta_total) if v_neta_total > 0 else 0

            with c_tot1:
                st.metric("Facturación Bruta Total", f"${total_facturacion_bruta:,.0f}")
            with c_tot2:
                st.metric("Margen Total $", f"${total_margen_pesos:,.0f}")
            with c_tot3:
                st.metric("Margen Promedio %", f"{margen_porc_total:.1%}")

            st.markdown("---")
            
            # 2. GRÁFICOS: Composición de Ventas y Stock
            g1, g2 = st.columns(2)
            
            with g1:
                st.subheader("Participación por Canal")
                fig_canales = px.pie(df_r, values="Bruta", names="Canal", hole=0.4, 
                                   color_discrete_sequence=px.colors.qualitative.Prism)
                # Etiquetas adentro con nombre y porcentaje
                fig_canales.update_traces(textinfo='percent+label', textposition='inside')
                st.plotly_chart(fig_canales, use_container_width=True)

            with g2:
                st.subheader("Conformación del Stock")
                v_stock_total = float(r_r.get('Valor Stock', 0))
                p_v = float(r_r.get('% Stock Vivo', 0))
                p_o = float(r_r.get('% Stock Obsoleto', 0))
                p_m = float(r_r.get('% Stock Muerto', 0))
                
                factor = 1 if p_v <= 1 else 100 
                
                df_stock = pd.DataFrame({
                    "Estado": ["Stock Vivo", "Stock Obsoleto", "Stock Muerto"],
                    "Valor ($)": [v_stock_total*(p_v/factor), v_stock_total*(p_o/factor), v_stock_total*(p_m/factor)]
                })
                
                fig_s = px.pie(df_stock, values="Valor ($)", names="Estado", hole=0.4,
                               color="Estado",
                               color_discrete_map={
                                   "Stock Vivo": "#28a745", 
                                   "Stock Obsoleto": "#ffc107", 
                                   "Stock Muerto": "#dc3545"
                               })
                # CORRECCIÓN: Ahora también con etiquetas adentro
                fig_s.update_traces(textinfo='percent+label', textposition='inside')
                st.plotly_chart(fig_s, use_container_width=True)
                st.info(f"VALOR TOTAL DEL STOCK: ${v_stock_total:,.0f}")

        with tab4:
            st.header("Productividad y Facturación CyP")
            sedes_config = [('Jujuy', cj_r, 'Obj Paños Propios Mensual', 'CyP JUJUY'), ('Salta', cs_r, 'Obj Paños Propios Mensual', 'CyP SALTA')]
            c_p1, c_p2 = st.columns(2)
            for i, (nom, row, o_col, sh) in enumerate(sedes_config):
                real_p, obj_p = row['Paños Propios'], get_o(sh, o_col)
                proy_p = calcular_proyeccion(real_p, d_t, d_h); alc_p = proy_p / obj_p if obj_p > 0 else 0
                c_c = "#dc3545" if alc_p < 0.90 else ("#ffc107" if alc_p < 0.95 else "#28a745")
                with (c_p1 if i == 0 else c_p2):
                    st.markdown(f"""<div style="border: 1px solid #e0e0e0; padding: 20px; border-radius: 10px; background-color: white; min-height: 170px;">
                        <p style="font-weight:bold;">Sede {nom} - Paños</p>
                        <h1 style="margin: 0; font-size: 42px; color: #333;">{real_p:,.0f} <span style="font-size: 18px; color: #999;">/ Obj: {obj_p:,.0f}</span></h1>
                        <p style="color: {c_c}; font-weight: bold; font-size: 18px; margin-top: 15px; border-top: 1px solid #eee; padding-top: 10px;">
                                ↑ Proyección: {proy_p:,.0f} paños ({alc_p:.1%})
                        </p></div>""", unsafe_allow_html=True)
            
            st.markdown("---")
            cf1, cf2 = st.columns(2)
            for i, (nom, row, o_col, sh) in enumerate(sedes_config):
                with (cf1 if i == 0 else cf2):
                    f_pur, f_ter = row.get('MO Pura', 0), row.get('MO Tercero', 0)
                    f_rep_cyp = row.get('Fact Repuestos', 0) if nom == 'Salta' else 0
                    st.metric(f"Facturación Total {nom}", f"${(f_pur+f_ter+f_rep_cyp):,.0f}")
                    
                    labels_cyp = ["M.O. Pura", "M.O. Terceros"]
                    values_cyp = [f_pur, f_ter]
                    if nom == 'Salta': labels_cyp.append("Repuestos"); values_cyp.append(f_rep_cyp)
                    st.plotly_chart(px.pie(values=values_cyp, names=labels_cyp, hole=0.4, color_discrete_sequence=["#00235d", "#00A8E8", "#28a745"]), use_container_width=True)

                    f_t, c_t = row.get('MO Tercero', 0), row.get('Costo Tercero', 0)
                    m_t, p_t = (f_t - c_t), ((f_t - c_t)/f_t if f_t > 0 else 0)
                    st.markdown(f"""<div style='background:#f1f3f6; padding:10px; border-radius:8px; border-left: 5px solid #00235d;'>
                        <p style='margin:0; font-size:13px;'>Márgenes Terceros {nom}:</p>
                        <p style='margin:0; font-size:14px;'>Fact: ${f_t:,.0f} | Costo: ${c_t:,.0f}</p>
                        <p style='margin:0; font-size:16px; color:#00235d;'><b>Margen: ${m_t:,.0f} ({p_t:.1%})</b></p></div>""", unsafe_allow_html=True)
                    
                    if nom == 'Salta':
                        fr, cr = row.get('Fact Repuestos', 0), row.get('Costo Repuestos', 0)
                        mr, pr = (fr - cr), ((fr - cr)/fr if fr > 0 else 0)
                        st.markdown(f"""<div style='background:#e8f5e9; padding:10px; border-radius:8px; border-left: 5px solid #28a745; margin-top:5px;'>
                            <p style='margin:0; font-size:13px;'>Márgenes Repuestos {nom}:</p>
                            <p style='margin:0; font-size:14px;'>Fact: ${fr:,.0f} | Costo: ${cr:,.0f}</p>
                            <p style='margin:0; font-size:16px; color:#2e7d32;'><b>Margen: ${mr:,.0f} ({pr:.1%})</b></p></div>""", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error en los datos: {e}")
else:
    st.info("Sube el archivo Excel de Autociel para comenzar.")
