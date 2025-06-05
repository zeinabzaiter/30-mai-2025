    # … (tout le code précédent, inchangé) …

    elif menu == "Staphylococcus aureus":
        st.title("🥠 Surveillance : Staphylococcus aureus")
        tab1, tab2, tab3 = st.tabs(
            ["Antibiotiques", "Phénotypes", "Alertes semaine/service"]
        )

        # ------------------------------------------------------------
        # Onglet 1 : antibiotiques (inchangé)
        # ------------------------------------------------------------
        with tab1:
            # … votre code existant pour l’affichage des antibiotiques …

        # ------------------------------------------------------------
        # Onglet 2 : phénotypes (dont VRSA utilisant déjà la colonne VRSA)
        # ------------------------------------------------------------
        with tab2:
            st.subheader("🧬 Évolution des phénotypes (sur 4 graphiques ou 1)")

            show_all = st.checkbox(
                "Afficher tous les phénotypes dans le même graphique",
                value=False
            )

            if show_all:
                # … votre code pour afficher tous les phénotypes ensemble (non modifié) …
                pass

            else:
                pheno = st.selectbox("Choisir un phénotype", list(phenotypes.keys()))

                # ----------------------------------------------------------------
                # Parti VRSA : on lit la colonne "VRSA" (qui est déjà un entier)
                # ----------------------------------------------------------------
                if pheno == "VRSA":
                    st.write("### Nombre de souches VRSA par semaine")

                    # 1) Charger le fichier VRSA_analyse.xlsx
                    path_vrsa = os.path.join(DATA_FOLDER, "VRSA_analyse.xlsx")
                    try:
                        df_pheno = pd.read_excel(path_vrsa)
                    except FileNotFoundError:
                        st.error(f"Impossible de trouver le fichier `{path_vrsa}`.")
                        st.stop()

                    # 2) Vérifier l’existence des colonnes attendues : Week + VRSA
                    if "Week" not in df_pheno.columns or "VRSA" not in df_pheno.columns:
                        st.error("Le fichier VRSA_analyse.xlsx doit contenir au moins les colonnes : 'Week' et 'VRSA'.")
                        st.stop()

                    # 3) Convertir Week en entier, filtrer les valeurs non valides
                    df_pheno["Week"] = pd.to_numeric(df_pheno["Week"], errors="coerce").astype("Int64")
                    df_pheno = df_pheno.dropna(subset=["Week", "VRSA"])
                    df_pheno["VRSA"] = df_pheno["VRSA"].astype(int)

                    # 4) Tracer le graphique “Nombre de VRSA”
                    fig_vrsa = go.Figure()
                    fig_vrsa.add_trace(go.Scatter(
                        x=df_pheno["Week"],
                        y=df_pheno["VRSA"],
                        mode="lines+markers",
                        name="Nombre VRSA",
                        line=dict(color="blue", width=3),
                        marker=dict(color="blue", size=8),
                        hovertemplate="Semaine %{x}<br>Nombre VRSA %{y}<extra></extra>"
                    ))

                    # 5) Points rouges pour l’alerte si VRSA > 0
                    df_alert_vrsa = df_pheno[df_pheno["VRSA"] > 0]
                    if not df_alert_vrsa.empty:
                        fig_vrsa.add_trace(go.Scatter(
                            x=df_alert_vrsa["Week"],
                            y=df_alert_vrsa["VRSA"],
                            mode="markers",
                            name="🔴 Alerte VRSA",
                            marker=dict(color="red", size=12),
                            hovertemplate="⚠ Alerte VRSA !<br>Semaine %{x}<br>Nombre VRSA %{y}<extra></extra>"
                        ))

                    # 6) Mise en page
                    fig_vrsa.update_layout(
                        title=dict(
                            text="Évolution hebdomadaire du nombre de souches VRSA",
                            font=dict(size=26, family="Arial Black")
                        ),
                        legend=dict(
                            font=dict(size=18, family="Arial Black"),
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        ),
                        xaxis=dict(
                            title=dict(text="Semaine", font=dict(size=22, family="Arial Black")),
                            tickfont=dict(size=18, family="Arial Black"),
                            dtick=1
                        ),
                        yaxis=dict(
                            title=dict(text="Nombre de VRSA", font=dict(size=22, family="Arial Black")),
                            tickfont=dict(size=18, family="Arial Black"),
                            rangemode="tozero"
                        ),
                        hovermode="x unified",
                        margin=dict(l=60, r=40, t=100, b=60),
                        height=600
                    )
                    st.plotly_chart(fig_vrsa, use_container_width=True)

                    # 7) Afficher le tableau récapitulatif
                    st.subheader("Tableau récapitulatif : Nb VRSA par semaine")
                    df_table = df_pheno[["Week", "VRSA"]].rename(
                        columns={"Week": "Semaine", "VRSA": "Nb VRSA"}
                    ).sort_values("Semaine").reset_index(drop=True)
                    st.dataframe(df_table, use_container_width=True)

                    # 8) Bouton de téléchargement CSV
                    csv_data = df_table.to_csv(index=False)
                    st.download_button(
                        label="📥 Télécharger le tableau VRSA (CSV)",
                        data=csv_data,
                        file_name="decompte_VRSA_par_semaine.csv",
                        mime="text/csv"
                    )

                # ----------------------------------------------------------------
                # Cas MRSA / Wild / Other : on conserve le % + moyenne mobile + IC
                # ----------------------------------------------------------------
                else:
                    path_pheno = phenotypes[pheno]
                    df_ph = pd.read_excel(path_pheno)
                    df_ph["Week"] = pd.to_numeric(df_ph["Week"], errors="coerce")
                    df_ph = df_ph.dropna(subset=["Week", "Pourcentage"])
                    df_ph["Pourcentage"] = df_ph["Pourcentage"].round(2)

                    fig2 = go.Figure()
                    fig2.add_trace(go.Scatter(
                        x=df_ph["Week"],
                        y=df_ph["Pourcentage"],
                        mode="lines+markers",
                        name=f"% {pheno}",
                        line=dict(width=3, color="blue")
                    ))

                    if "Moyenne_mobile_8s" in df_ph.columns:
                        fig2.add_trace(go.Scatter(
                            x=df_ph["Week"],
                            y=df_ph["Moyenne_mobile_8s"],
                            mode="lines",
                            name="Moyenne mobile",
                            line=dict(dash="dash", color="orange")
                        ))
                    if "IC_sup" in df_ph.columns:
                        fig2.add_trace(go.Scatter(
                            x=df_ph["Week"],
                            y=df_ph["IC_sup"],
                            mode="lines",
                            name="Seuil IC 95 %",
                            line=dict(dash="dot", color="gray")
                        ))
                    if "OUTLIER" in df_ph.columns:
                        outliers = df_ph[df_ph["OUTLIER"] == True]
                        fig2.add_trace(go.Scatter(
                            x=outliers["Week"],
                            y=outliers["Pourcentage"],
                            mode="markers",
                            name="🔴 Alerte",
                            marker=dict(color="red", size=10)
                        ))

                    fig2.update_layout(
                        title=dict(text=f"Évolution du phénotype {pheno}", font=dict(size=24, family="Arial Black")),
                        legend=dict(font=dict(size=20, family="Arial Black")),
                        xaxis=dict(
                            title=dict(text="Semaine", font=dict(size=22, family="Arial Black")),
                            tickfont=dict(size=18, family="Arial Black")
                        ),
                        yaxis=dict(
                            title=dict(text=f"% {pheno}", font=dict(size=22, family="Arial Black")),
                            tickfont=dict(size=18, family="Arial Black")
                        ),
                        hovermode="x unified"
                    )
                    st.plotly_chart(fig2, use_container_width=True)

        # ---------------------------------------------------
        # Onglet 3 : alertes croisées par semaine et service
        # ---------------------------------------------------
        with tab3:
            st.subheader("🚨 Alertes croisées par semaine et service")
            alertes = []
            correspondance = {
                "Gentamicin_analyse_2024": "Gentamycine",
                "Vancomycin_analyse_2024": "Téicoplanine",
                "Teicoplanin_analyse_2024": "Téicoplanine",
                "Linezolid_analyse": "Linezolide",
                "Daptomycin_analyse": "Daptomycine",
                "Clindamycin_analyse": "Clindamycine",
                "Oxacillin_analyse_2024": "Oxacilline",
                "Sxt_analyse": "Cotrimoxazole",
                "Dalbavancin_analyse": "Dalbavancine"
            }

            for abx, path in antibiotiques.items():
                df_out = pd.read_excel(path)
                week_col = "Week" if "Week" in df_out.columns else "Semaine"
                if "OUTLIER" not in df_out.columns:
                    continue
                df_out[week_col] = pd.to_numeric(df_out[week_col], errors='coerce')
                weeks = df_out[df_out["OUTLIER"] == True][week_col].dropna().unique()

                col_export = correspondance.get(abx, abx)
                for w in weeks:
                    if col_export not in df_export.columns:
                        continue
                    mask = (df_export['semaine'] == w)
                    resist = (df_export[col_export] == 'R')
                    df_alert = df_export[mask & resist]
                    for srv in df_alert['uf'].unique():
                        nb_r = df_alert[df_alert['uf'] == srv].shape[0]
                        alertes.append({
                            "Semaine": int(w),
                            "Service": srv,
                            "Antibiotique": col_export,
                            "Nb_R": nb_r,
                            "Alarme": f"Semaine {int(w)} : Alerte pour {col_export} dans le service {srv}"
                        })

            df_final_alertes = pd.DataFrame(alertes)
            st.dataframe(df_final_alertes, use_container_width=True)

            if not df_final_alertes.empty:
                st.download_button(
                    "📅 Télécharger les alertes",
                    data=df_final_alertes.to_csv(index=False),
                    file_name="alertes_detectees.csv"
                )
