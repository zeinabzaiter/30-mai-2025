import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Surveillance bactérienne", layout="wide")

DATA_FOLDER = "data"
bacteries_file = os.path.join(DATA_FOLDER, "TOUS les bacteries a etudier.xlsx")
export_file = os.path.join(DATA_FOLDER, "Export_StaphAureus_COMPLET.csv")

# 1) Lecture des données globales
bacteries_df = pd.read_excel(bacteries_file)

# Lecture du CSV de StaphAureus (export)
# On strippe les noms de colonne pour éviter les espaces superflus
df_export = pd.read_csv(export_file)
df_export.columns = df_export.columns.str.strip()
# On tente de convertir 'semaine' en int, s’il existe
if 'semaine' in df_export.columns:
    df_export['semaine'] = pd.to_numeric(df_export['semaine'], errors='coerce').astype('Int64')

# 2) Construction du dictionnaire des fichiers antibiotiques
antibiotiques = {}
for file in os.listdir(DATA_FOLDER):
    if file.startswith("pct") and file.endswith(".xlsx"):
        abx_name = (
            file.replace("pctR_", "")
                .replace("pct_R_", "")
                .replace("pct", "")
                .replace(".xlsx", "")
                .capitalize()
        )
        antibiotiques[abx_name] = os.path.join(DATA_FOLDER, file)

# 3) Chemins vers les fichiers de phénotypes (on retire VRSA ici : on ne lira plus Excel pour VRSA)
phenotypes = {
    "MRSA": os.path.join(DATA_FOLDER, "MRSA_analyse.xlsx"),
    "VRSA": None,  # calculé depuis df_export
    "Wild": os.path.join(DATA_FOLDER, "Wild_analyse.xlsx"),
    "Other": os.path.join(DATA_FOLDER, "Other_analyse.xlsx")
}

# -----------------------------------------------------
# Fonction utilitaire : localiser la colonne "Phenotype"
# -----------------------------------------------------
@st.cache_data
def detect_phenotype_column(df: pd.DataFrame) -> str | None:
    """
    Parcourt les colonnes de df, en supprimant les espaces
    et en passant en minuscules, pour trouver celle qui s'appelle 'phenotype'.
    Retourne le nom exact de la colonne si trouvée, sinon None.
    """
    for col in df.columns:
        if col.strip().lower() == "phenotype":
            return col
    return None


# -----------------------------------------------------
# Fonction utilitaire : calculer le nombre de VRSA par semaine
# -----------------------------------------------------
@st.cache_data
def compute_weekly_vrsa_counts(df: pd.DataFrame) -> pd.DataFrame:
    """
    À partir du DataFrame "df_export", identifié la colonne de phénotype,
    filtre tous les isolats où ce phénotype vaut 'VRSA', puis compte le nombre de VRSA par semaine.
    Renvoie un DataFrame à deux colonnes :
       - 'semaine' : int
       - 'nb_vrsa' : nombre de souches VRSA cette semaine-là
    On “remplit” aussi toutes les semaines entre min et max (avec nb_vrsa=0 si nécessaire).
    """
    # 1) Identifier dynamiquement la colonne "Phenotype"
    pheno_col = detect_phenotype_column(df)
    if pheno_col is None:
        # Si pas de colonne 'Phenotype', on renvoie un DataFrame vide
        return pd.DataFrame(columns=['semaine', 'nb_vrsa'])

    # 2) Filtrer les isolats VRSA (en majuscules pour la comparaison)
    df_vrsa = df[df[pheno_col].astype(str).str.strip().str.upper() == "VRSA"].copy()

    # 3) Si la colonne 'semaine' n’existe pas ou contient uniquement NaN, on renvoie vide
    if 'semaine' not in df_vrsa.columns or df_vrsa['semaine'].dropna().empty:
        return pd.DataFrame(columns=['semaine', 'nb_vrsa'])

    # 4) Compter le nombre de VRSA par semaine
    counts = (
        df_vrsa
        .groupby('semaine')
        .size()
        .reset_index(name='nb_vrsa')
        .sort_values('semaine')
    )

    # 5) S’assurer d’avoir toutes les semaines entre la min et la max
    try:
        semaine_min = int(df['semaine'].min())
        semaine_max = int(df['semaine'].max())
    except Exception:
        # si conversion impossible, on renvoie simplement le counts tel quel
        return counts

    all_weeks = pd.DataFrame({'semaine': list(range(semaine_min, semaine_max + 1))})
    counts = all_weeks.merge(counts, on='semaine', how='left').fillna(0)
    counts['nb_vrsa'] = counts['nb_vrsa'].astype(int)
    return counts


# -----------------------------------------------------
# Fonction utilitaire : tracer le graphique VRSA
# -----------------------------------------------------
def plot_vrsa_count(df_counts: pd.DataFrame):
    """
    Trace un graphique Plotly :
      - X = semaine
      - Y = nb_vrsa (nombre brut de souches VRSA)
      - ligne + marqueurs bleus
      - marqueur rouge (alerte) si nb_vrsa > 0
    """
    semaines = df_counts['semaine']
    nb_vrsa = df_counts['nb_vrsa']
    df_alert = df_counts[df_counts['nb_vrsa'] > 0]

    fig = go.Figure()

    # 1) Courbe principale du nombre de VRSA (bleu)
    fig.add_trace(go.Scatter(
        x=semaines,
        y=nb_vrsa,
        mode='lines+markers',
        name='Nombre VRSA',
        line=dict(color='blue', width=3),
        marker=dict(color='blue', size=8),
        hovertemplate='Semaine %{x}<br>Nb VRSA %{y}<extra></extra>'
    ))

    # 2) Points d’alerte (rouge) si nb_vrsa > 0
    if not df_alert.empty:
        fig.add_trace(go.Scatter(
            x=df_alert['semaine'],
            y=df_alert['nb_vrsa'],
            mode='markers',
            name='🔴 Alerte VRSA',
            marker=dict(color='red', size=12),
            hovertemplate='⚠ Alerte VRSA !<br>Semaine %{x}<br>Nb VRSA %{y}<extra></extra>'
        ))

    # 3) Mise en page
    fig.update_layout(
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

    st.plotly_chart(fig, use_container_width=True)


# -----------------------------------------------------
# Construction du menu latéral
# -----------------------------------------------------
menu = st.sidebar.radio(
    "Navigation",
    ["Vue globale", "Staphylococcus aureus", "Répartition globale"]
)

if menu == "Vue globale":
    st.title("📋 Bactéries à surveiller")
    st.dataframe(bacteries_df, use_container_width=True)

elif menu == "Répartition globale":
    st.title("🥧 Répartition globale (camemberts)")

    # Filtrage par semaines
    semaine_min = int(df_export["semaine"].min())
    semaine_max = int(df_export["semaine"].max())
    semaine_range = st.slider(
        "Filtrer par plage de semaines :",
        min_value=semaine_min,
        max_value=semaine_max,
        value=(semaine_min, semaine_max),
        step=1
    )

    filtered_df = df_export[
        (df_export["semaine"] >= semaine_range[0]) &
        (df_export["semaine"] <= semaine_range[1])
    ]

    # Camembert résultats antibiotiques
    st.subheader("🦠 Camembert des résultats antibiotiques")
    abx_to_plot = [
        col for col in filtered_df.columns
        if col not in ["semaine", "uf"] and filtered_df[col].dtype == object
    ]
    selected_abx = st.selectbox(
        "Choisir un antibiotique à visualiser :",
        abx_to_plot
    )

    if selected_abx in filtered_df.columns:
        abx_counts = (
            filtered_df[selected_abx]
            .value_counts()
            .reset_index()
        )
        abx_counts.columns = ["Résultat", "Nombre"]
        fig_abx_pie = px.pie(
            abx_counts,
            names="Résultat",
            values="Nombre",
            title=f"Distribution de {selected_abx}"
        )
        st.plotly_chart(fig_abx_pie, use_container_width=True)

    # Camembert des phénotypes
    st.subheader("🧬 Camembert des phénotypes")
    if 'Phenotype' in filtered_df.columns or 'phenotype' in filtered_df.columns:
        # On vérifie la casse/minuscules
        pheno_col_global = ('Phenotype' if 'Phenotype' in filtered_df.columns else 'phenotype')
        pheno_counts = (
            filtered_df[pheno_col_global]
            .value_counts()
            .reset_index()
        )
        pheno_counts.columns = ["Phénotype", "Nombre"]
        fig_pheno_pie = px.pie(
            pheno_counts,
            names="Phénotype",
            values="Nombre",
            title="Distribution des phénotypes"
        )
        st.plotly_chart(fig_pheno_pie, use_container_width=True)
    else:
        st.info("Aucune colonne 'Phenotype' (ou 'phenotype') trouvée dans les données exportées.")

elif menu == "Staphylococcus aureus":
    st.title("🥠 Surveillance : Staphylococcus aureus")
    tab1, tab2, tab3 = st.tabs(
        ["Antibiotiques", "Phénotypes", "Alertes semaine/service"]
    )

    # -------------------------------------------------------------------
    # Onglet 1 : évolution hebdomadaire de la résistance aux antibiotiques
    # -------------------------------------------------------------------
    with tab1:
        st.subheader("📈 Évolution hebdomadaire de la résistance")
        abx = st.selectbox(
            "Choisir un antibiotique",
            sorted(antibiotiques.keys())
        )
        df_abx = pd.read_excel(antibiotiques[abx])
        week_col = "Week" if "Week" in df_abx.columns else "Semaine"
        df_abx[week_col] = pd.to_numeric(df_abx[week_col], errors='coerce')
        df_abx = df_abx.dropna(subset=[week_col, "Pourcentage"])
        df_abx["Pourcentage"] = df_abx["Pourcentage"].round(2)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_abx[week_col],
            y=df_abx["Pourcentage"],
            mode="lines+markers",
            name="% Résistance",
            line=dict(width=3),
            marker=dict(color="blue")
        ))
        if "Moyenne_mobile_8s" in df_abx.columns:
            fig.add_trace(go.Scatter(
                x=df_abx[week_col],
                y=df_abx["Moyenne_mobile_8s"],
                mode="lines",
                name="Moyenne mobile",
                line=dict(dash="dash", color="orange")
            ))
        if "IC_sup" in df_abx.columns:
            fig.add_trace(go.Scatter(
                x=df_abx[week_col],
                y=df_abx["IC_sup"],
                mode="lines",
                name="Seuil IC 95%",
                line=dict(dash="dot", color="gray")
            ))
        if "OUTLIER" in df_abx.columns:
            outliers = df_abx[df_abx["OUTLIER"] == True]
            fig.add_trace(go.Scatter(
                x=outliers[week_col],
                y=outliers["Pourcentage"],
                mode="markers",
                name="🔴 Alerte",
                marker=dict(color="red", size=10)
            ))

        fig.update_layout(
            title=dict(text=f"Évolution de la résistance à {abx}", font=dict(size=24, family="Arial Black")),
            legend=dict(font=dict(size=20, family="Arial Black")),
            xaxis=dict(
                title=dict(text="Semaine", font=dict(size=22, family="Arial Black")),
                tickfont=dict(size=18, family="Arial Black")
            ),
            yaxis=dict(
                title=dict(text="% Résistance", font=dict(size=22, family="Arial Black")),
                tickfont=dict(size=18, family="Arial Black")
            ),
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------
    # Onglet 2 : évolution des phénotypes (dont VRSA count)
    # -----------------------------------------------------
    with tab2:
        st.subheader("🧬 Évolution des phénotypes (sur 4 graphiques ou 1)")

        show_all = st.checkbox(
            "Afficher tous les phénotypes dans le même graphique",
            value=False
        )

        if show_all:
            # Affichage comparé des 4 phénotypes (MRSA, VRSA (nombre), Wild, Other)
            fig_all = go.Figure()
            couleurs = {"MRSA": "blue", "VRSA": "red", "Wild": "green", "Other": "purple"}

            for pheno, path in phenotypes.items():
                if pheno == "VRSA":
                    # ---------------------------
                    # Tracé du “nombre de VRSA”
                    # ---------------------------
                    df_counts_vrsa = compute_weekly_vrsa_counts(df_export)
                    fig_all.add_trace(go.Scatter(
                        x=df_counts_vrsa['semaine'],
                        y=df_counts_vrsa['nb_vrsa'],
                        mode='lines+markers',
                        name=f"<b>Nombre VRSA</b>",
                        line=dict(color=couleurs[pheno], width=3),
                        marker=dict(size=8)
                    ))
                    # Points d’alerte (rouge foncé) sur nb_vrsa > 0
                    df_alerts = df_counts_vrsa[df_counts_vrsa['nb_vrsa'] > 0]
                    fig_all.add_trace(go.Scatter(
                        x=df_alerts['semaine'],
                        y=df_alerts['nb_vrsa'],
                        mode='markers',
                        name=f"<b>🔴 Alerte VRSA</b>",
                        marker=dict(color="darkred", size=12),
                        hovertemplate='ALERTE VRSA !<br>Semaine %{x}<br>Nb VRSA %{y}<extra></extra>'
                    ))

                else:
                    # ---------------------------
                    # Tracé du pourcentage (MRSA, Wild, Other)
                    # ---------------------------
                    df_ph = pd.read_excel(path)
                    df_ph["Week"] = pd.to_numeric(df_ph["Week"], errors='coerce')
                    df_ph = df_ph.dropna(subset=["Week", "Pourcentage"])
                    df_ph["Pourcentage"] = df_ph["Pourcentage"].round(2)

                    fig_all.add_trace(go.Scatter(
                        x=df_ph["Week"],
                        y=df_ph["Pourcentage"],
                        mode="lines+markers",
                        name=f"<b>% {pheno}</b>",
                        line=dict(width=3, color=couleurs[pheno]),
                        marker=dict(size=8)
                    ))

                    if "Moyenne_mobile_8s" in df_ph.columns:
                        fig_all.add_trace(go.Scatter(
                            x=df_ph["Week"],
                            y=df_ph["Moyenne_mobile_8s"],
                            mode="lines",
                            name=f"<b>Moyenne {pheno}</b>",
                            line=dict(dash="dash", color=couleurs[pheno])
                        ))
                    if "IC_sup" in df_ph.columns:
                        fig_all.add_trace(go.Scatter(
                            x=df_ph["Week"],
                            y=df_ph["IC_sup"],
                            mode="lines",
                            name=f"<b>IC sup {pheno}</b>",
                            line=dict(dash="dot", color="lightgray")
                        ))
                    if "OUTLIER" in df_ph.columns:
                        outliers = df_ph[df_ph["OUTLIER"] == True]
                        fig_all.add_trace(go.Scatter(
                            x=outliers["Week"],
                            y=outliers["Pourcentage"],
                            mode="markers",
                            name=f"<b>🔴 Alerte {pheno}</b>",
                            marker=dict(color="black", size=12, symbol="circle-open")
                        ))

            fig_all.update_layout(
                title=dict(text="Évolution comparée des 4 phénotypes", font=dict(size=26, family="Arial Black")),
                legend=dict(font=dict(size=20, family="Arial Black")),
                xaxis=dict(
                    title=dict(text="Semaine", font=dict(size=24, family="Arial Black")),
                    tickfont=dict(size=18, family="Arial Black")
                ),
                yaxis=dict(
                    title=dict(text="Valeur", font=dict(size=24, family="Arial Black")),
                    tickfont=dict(size=18, family="Arial Black")
                ),
                hovermode="x unified"
            )
            st.plotly_chart(fig_all, use_container_width=True)

        else:
            # Affichage d'un seul phénotype choisi
            pheno = st.selectbox("Choisir un phénotype", list(phenotypes.keys()))

            if pheno == "VRSA":
                # -----------------
                # Affichage du nombre brut de VRSA
                # -----------------
                st.write("### Nombre de souches VRSA par semaine")

                # Calcul des décomptes hebdomadaires de VRSA
                df_counts_vrsa = compute_weekly_vrsa_counts(df_export)

                # Si la table est vide, on informe l'utilisateur
                if df_counts_vrsa.empty:
                    st.error("Impossible de trouver la colonne 'Phenotype' dans `Export_StaphAureus_COMPLET.csv`, ou "
                             "la colonne 'semaine' n’est pas correctement renseignée. "
                             "Vérifiez votre fichier d’export.")
                else:
                    # Tracé du graphique VRSA
                    plot_vrsa_count(df_counts_vrsa)

                    # Tableau récapitulatif
                    st.subheader("Tableau récapitulatif : Nb VRSA par semaine")
                    st.dataframe(
                        df_counts_vrsa.rename(columns={'semaine': 'Semaine', 'nb_vrsa': 'Nb VRSA'}),
                        use_container_width=True
                    )
                    csv_data = df_counts_vrsa.to_csv(index=False)
                    st.download_button(
                        label="📥 Télécharger le tableau VRSA (CSV)",
                        data=csv_data,
                        file_name="decompte_VRSA_par_semaine.csv",
                        mime="text/csv"
                    )

            else:
                # ----------------------------
                # Affichage du pourcentage (MRSA, Wild, Other)
                # ----------------------------
                path = phenotypes[pheno]
                df_pheno = pd.read_excel(path)
                df_pheno["Week"] = pd.to_numeric(df_pheno["Week"], errors='coerce')
                df_pheno = df_pheno.dropna(subset=["Week", "Pourcentage"])
                df_pheno["Pourcentage"] = df_pheno["Pourcentage"].round(2)

                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(
                    x=df_pheno["Week"],
                    y=df_pheno["Pourcentage"],
                    mode="lines+markers",
                    name=f"% {pheno}",
                    line=dict(width=3, color="blue")
                ))

                if "Moyenne_mobile_8s" in df_pheno.columns:
                    fig2.add_trace(go.Scatter(
                        x=df_pheno["Week"],
                        y=df_pheno["Moyenne_mobile_8s"],
                        mode="lines",
                        name="Moyenne mobile",
                        line=dict(dash="dash", color="orange")
                    ))
                if "IC_sup" in df_pheno.columns:
                    fig2.add_trace(go.Scatter(
                        x=df_pheno["Week"],
                        y=df_pheno["IC_sup"],
                        mode="lines",
                        name="Seuil IC 95%",
                        line=dict(dash="dot", color="gray")
                    ))

                if "OUTLIER" in df_pheno.columns:
                    outliers = df_pheno[df_pheno["OUTLIER"] == True]
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

    # -------------------------------------------------------
    # Onglet 3 : alertes croisées par semaine et service
    # -------------------------------------------------------
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
