elif selected_tab == "📦 Repuestos":
            st.markdown("### 📦 Gestión Estratégica de Repuestos")
            
            # --- 1. INPUT DE PRIMAS / BONOS ---
            col_primas, col_vacia = st.columns([1, 3])
            with col_primas:
                primas_input = st.number_input("💰 Ingresar Primas/Rappels Estimados ($)", min_value=0.0, step=10000.0, format="%.0f")

            # Cálculo de datos base
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
            
            vta_total_neta = df_r['Venta Neta'].sum() if not df_r.empty else 0
            util_total_operativa = df_r['Utilidad $'].sum() if not df_r.empty else 0
            util_total_final = util_total_operativa + primas_input
            mg_total_final = util_total_final / vta_total_neta if vta_total_neta > 0 else 0
            val_stock = float(r_r.get(find_col(data['REPUESTOS'], ["VALOR", "STOCK"]), 0))
            obj_rep_total = r_r.get(find_col(data['REPUESTOS'], ["OBJ", "FACT"]), 1)

            # --- TARJETAS GERENCIALES CON COLORES AGRESIVOS ---
            c1, c2, c3 = st.columns(3)
            
            # Semáforo de Margen (Rojo si es < 21%)
            color_mg = "#28a745" if mg_total_final >= 0.21 else "#dc3545"
            bg_mg = "#d4edda" if mg_total_final >= 0.21 else "#f8d7da"

            with c1: # VALOR STOCK TOTAL
                st.markdown(f"""
                    <div style="background-color: #f1f4f9; padding: 20px; border-radius: 10px; border-left: 8px solid #00235d;">
                        <p style="color: #666; margin: 0; font-weight: bold;">VALOR STOCK TOTAL</p>
                        <h2 style="color: #00235d; margin: 0;">${val_stock:,.0f}</h2>
                    </div>
                """, unsafe_allow_html=True)

            with c2: # MARGEN REAL (EL SEMÁFORO)
                st.markdown(f"""
                    <div style="background-color: {bg_mg}; padding: 20px; border-radius: 10px; border: 2px solid {color_mg};">
                        <p style="color: #333; margin: 0; font-weight: bold;">MARGEN GLOBAL REAL</p>
                        <h2 style="color: {color_mg}; margin: 0;">{mg_total_final:.1%}</h2>
                        <p style="font-size: 0.8rem; color: #666; margin: 0;">Objetivo Mínimo: 21%</p>
                    </div>
                """, unsafe_allow_html=True)

            with c3: # ASISTENTE PROACTIVO
                if mg_total_final < 0.21:
                    falta = (vta_total_neta * 0.21) - util_total_final
                    st.markdown(f"""
                        <div style="background-color: #fff3cd; padding: 20px; border-radius: 10px; border-left: 8px solid #ffc107;">
                            <p style="color: #856404; margin: 0; font-weight: bold;">ASISTENTE: NECESIDAD</p>
                            <h3 style="color: #856404; margin: 0;">+ ${falta:,.0f}</h3>
                            <p style="font-size: 0.75rem; color: #856404; margin: 0;">Utilidad extra para llegar al 21%</p>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                        <div style="background-color: #d4edda; padding: 20px; border-radius: 10px; border-left: 8px solid #28a745;">
                            <p style="color: #155724; margin: 0; font-weight: bold;">ESTADO ESTRATÉGICO</p>
                            <h3 style="color: #155724; margin: 0;">MÁRGEN ÓPTIMO</h3>
                            <p style="font-size: 0.75rem; color: #155724; margin: 0;">Estrategia de precios saludable</p>
                        </div>
                    """, unsafe_allow_html=True)

            # --- TABLA DE DATOS Y GRÁFICOS ---
            st.markdown("---")
            if not df_r.empty:
                st.dataframe(df_r.style.format({"Venta Bruta": "${:,.0f}", "Desc.": "${:,.0f}", "Venta Neta": "${:,.0f}", "Costo": "${:,.0f}", "Utilidad $": "${:,.0f}", "Margen %": "{:.1%}"}), use_container_width=True, hide_index=True)
            
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.plotly_chart(px.pie(df_r, values="Venta Bruta", names="Canal", hole=0.4, title="Participación de Venta"), use_container_width=True)
            with col_g2:
                # Recuperamos los indicadores de salud de stock (Vivo, Obsoleto, Muerto)
                p_vivo = float(r_r.get(find_col(data['REPUESTOS'], ["VIVO"]), 0))
                p_obs = float(r_r.get(find_col(data['REPUESTOS'], ["OBSOLETO"]), 0))
                p_muerto = float(r_r.get(find_col(data['REPUESTOS'], ["MUERTO"]), 0))
                f = 1 if p_vivo <= 1 else 100
                df_s = pd.DataFrame({"Estado": ["Vivo", "Obsoleto", "Muerto"], "Valor": [val_stock*(p_vivo/f), val_stock*(p_obs/f), val_stock*(p_muerto/f)]})
                st.plotly_chart(px.pie(df_s, values="Valor", names="Estado", hole=0.4, title="Salud del Stock Total", color="Estado", color_discrete_map={"Vivo": "#28a745", "Obsoleto": "#ffc107", "Muerto": "#dc3545"}), use_container_width=True)

            # --- CALCULADORA DE MIX IDEAL (TU CÓDIGO ORIGINAL MEJORADO) ---
            st.markdown("### 🎯 Calculadora de Mix y Estrategia Ideal")
            col_mix_input, col_mix_res = st.columns([3, 2])
            
            default_mix = {}
            default_margin = {}
            if vta_total_neta > 0:
                for idx, row in df_r.iterrows():
                    default_mix[row['Canal']] = (row['Venta Neta'] / vta_total_neta) * 100
                    default_margin[row['Canal']] = row['Margen %'] * 100
            
            mix_ideal = {}; margin_ideal = {}; sum_mix = 0
            with col_mix_input:
                for c in canales_repuestos:
                    val_def_mix = float(default_mix.get(c, 0.0))
                    val_def_marg = float(default_margin.get(c, 25.0))
                    c1_s, c2_s = st.columns([2, 1])
                    with c1_s: val_mix = st.slider(f"% Mix {c}", 0.0, 100.0, val_def_mix, 0.5, key=f"mix_{c}")
                    with c2_s: val_marg = st.number_input(f"% Margen {c}", 0.0, 100.0, val_def_marg, 0.5, key=f"marg_{c}")
                    mix_ideal[c] = val_mix / 100; margin_ideal[c] = val_marg / 100; sum_mix += val_mix
            
            with col_mix_res:
                st.metric("Suma Mix", f"{sum_mix:.1f}%", f"{sum_mix-100:.1f}%", delta_color="inverse" if abs(sum_mix-100)>0.1 else "normal")
                total_profit_ideal = sum([obj_rep_total * mix_ideal[c] * margin_ideal[c] for c in canales_repuestos])
                global_margin_ideal = total_profit_ideal / obj_rep_total if obj_rep_total > 0 else 0
                st.info(f"Con este Mix, tu Margen Global sería: **{global_margin_ideal:.1%}**")
