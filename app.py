# app.py

import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
import plotly.express as px
import unicodedata

st.set_page_config(page_title="Surveillance bactérienne", layout="wide")

DATA_FOLDER = "data"
bacteries_file = os.path.join(DATA_FOLDER, "TOUS les bacteries a etudier.xlsx")
export_file = os.path.join(DATA_FOLDER, "Export_StaphAureus_COMPLET.csv")

# --------------------------------------------------
# 1) Lecture des données "globales"
# --------------------------------------------------
bacteries_df = pd.read_excel(bacteries_file)

# Lecture de l'export Staphylococcus aureus
df_export = pd.read_csv(export_file)
df_export.columns = df_export.columns.str.strip()
if 'semaine' in df_export.columns:
    df_export['semaine'] = pd.to_numeric(df_export['semaine'], errors='coerce').astype('Int64')

# --------------------------------------------------
# 2) Dictionnaire des fichiers antibiotiques
# --------------------------------------------------
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

# --------------------------------------------------
# 3) Chemins vers les fichiers de phénotypes
#    (pour VRSA, on lira VRSA_analyse.xlsx directement)
# --------------------------------------------------
phenotypes = {
    "MRSA": os.path.join(DATA_FOLDER, "MRSA_analyse.xlsx"),
    "VRSA": None,
    "Wild": os.path.join(DATA_FOLDER, "Wild_analyse.xlsx"),
    "Other": os.path.join(DATA_FOLDER, "Other_analyse.xlsx")
}

# --------------------------------------------------
# 4) Fonctions utilitaires pour la détection domaine global
#    (uniquement utiles pour MRSA/Wild/Other ou onglet "Répartition globale")
# --------------------------------------------------
def normalize_column_name(col_name: str) -> str:
    """
    Enlève les accents et met en minuscules pour comparer aux noms attendus
    (ex. 'Phénotype' -> 'phenotype', '  Phenotype ' -> 'phenotype').
    """
    nfkd = unicodedata.normalize('NFKD', col_name)
    no_accent = "".join(c for c in nfkd if not unicodedata.combining(c))
    return no_accent.strip().lower()

@st.cache_data
def detect_phenotype_column(df: pd.DataFrame) -> str | None:
    """
    Parcourt toutes les colonnes de df et retourne le nom exact
    de la colonne qui correspond à 'phenotype' (après normalisation),
    ou None si aucune colonne n'est trouvée.
    """
    for col in df.columns:
        if normalize_column_name(col) == "phenotype":
            return col
    return None

# --------------------------------------------------
# 5) Onglet "Vue globale"
# --------------------------------------------------
def page_vue_globale():
    st.title("📋 Bactéries à surveiller")
    st.dataframe(bacteries_df, use_container_width=True)

# --------------------------------------------------
# 6) Onglet "Répartition globale"
# --------------------------------------------------
def page_repartition_globale():
    st.title("🥧 Répartition globale (camemberts)")

    # Filtrer par plage de semaines
    if 'semaine' not in df_export.columns:
        st.error("Le fichier Export_StaphAureus_COMPLET.csv doit contenir une colonne 'semaine' (entier).")
        return

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

    # 6.a) Camembert des résultats antibiotiques
    st.subheader("🦠 Camembert des résultats antibiotiques")
    abx_to_plot = [
        col for col in filtered_df.columns
        if col not in ["semaine", "uf"] and filtered_df[col].dtype == object
    ]
    selected_abx = st.selectbox("Choisir un antibiotique à visualiser :", abx_to_plot)

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

    # 6.b) Camembert des phénotypes
    st.subheader("🧬 Camembert des phénotypes")
    pheno_col_global = detect_phenotype_column(filtered_df)
    if pheno_col_global:
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
        st.info("Aucune colonne 'Phenotype' (ou 'phénotype') trouvée dans le CSV d’export.")

# --------------------------------------------------
# 7) Onglet "Staphylococcus aureus" - onglet Antibiotiques
# --------------------------------------------------
def onglet_antibiotiques():
    st.subheader("📈 Évolution hebdomadaire de la résistance")
    abx = st.selectbox("Choisir un antibiotique", sorted(antibiotiques.keys()))
    if not antibiotiques[abx]:
        st.error(f"Fichier pour l’antibiotique {abx} introuvable.")
        return

    df_abx = pd.read_excel(antibiotiques[abx])
    week_col = "Week" if "Week" in df_abx.columns else "Semaine"
    if week_col not in df_abx.columns or "Pourcentage" not in df_abx.columns:
        st.error(f"Le fichier {antibiotiques[abx]} doit contenir les colonnes '{week_col}' et 'Pourcentage'.")
        return

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

# --------------------------------------------------
# 8) Onglet "Staphylococcus aureus" - onglet Phénotypes
# --------------------------------------------------
def onglet_phenotypes():
    st.subheader("🧬 Évolution des phénotypes (sur 4 graphiques ou 1)")

    show_all = st.checkbox("Afficher tous les phénotypes dans le même graphique", value=False)

    if show_all:
        # Si vous voulez superposer MRSA, VRSA (nombre), Wild, Other dans un seul graph
        fig_all = go.Figure()
        couleurs = {"MRSA": "blue", "VRSA": "red", "Wild": "green", "Other": "purple"}

        for pheno, path in phenotypes.items():
            if pheno == "VRSA":
                # Lecture du fichier VRSA_analyse.xlsx
                path_vrsa = os.path.join(DATA_FOLDER, "VRSA_analyse.xlsx")
                if not os.path.isfile(path_vrsa):
                    continue
                df_v = pd.read_excel(path_vrsa)
                if "Week" not in df_v.columns or "VRSA" not in df_v.columns:
                    continue
                df_v["Week"] = pd.to_numeric(df_v["Week"], errors="coerce").astype("Int64")
                df_v = df_v.dropna(subset=["Week", "VRSA"])
                df_v["VRSA"] = df_v["VRSA"].astype(int)

                # Tracé de la courbe “nombre VRSA”
                fig_all.add_trace(go.Scatter(
                    x=df_v["Week"],
                    y=df_v["VRSA"],
                    mode="lines+markers",
                    name=f"<b>Nombre VRSA</b>",
                    line=dict(color=couleurs[pheno], width=3),
                    marker=dict(size=8)
                ))
                # Alertes rouges si VRSA > 0
                df_alert = df_v[df_v["VRSA"] > 0]
                fig_all.add_trace(go.Scatter(
                    x=df_alert["Week"],
                    y=df_alert["VRSA"],
                    mode="markers",
                    name=f"<b>🔴 Alerte VRSA</b>",
                    marker=dict(color="darkred", size=12),
                    hovertemplate="VRSA > 0 (Semaine %{x})<extra></extra>"
                ))

            else:
                # Affichage % pour MRSA, Wild, Other
                if not path or not os.path.isfile(path):
                    continue
                df_ph = pd.read_excel(path)
                if "Week" not in df_ph.columns or "Pourcentage" not in df_ph.columns:
                    continue
                df_ph["Week"] = pd.to_numeric(df_ph["Week"], errors="coerce")
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
        # Affichage d'un seul phénotype
        pheno = st.selectbox("Choisir un phénotype", list(phenotypes.keys()))

        if pheno == "VRSA":
            st.write("### Nombre de souches VRSA par semaine")

            path_vrsa = os.path.join(DATA_FOLDER, "VRSA_analyse.xlsx")
            if not os.path.isfile(path_vrsa):
                st.error("Impossible de trouver le fichier `data/VRSA_analyse.xlsx`.")
                return

            df_pheno = pd.read_excel(path_vrsa)
            # Vérifier que les colonnes "Week" et "VRSA" existent
            if "Week" not in df_pheno.columns or "VRSA" not in df_pheno.columns:
                st.error("Le fichier `VRSA_analyse.xlsx` doit contenir au moins les colonnes : 'Week' et 'VRSA'.")
                return

            df_pheno["Week"] = pd.to_numeric(df_pheno["Week"], errors="coerce").astype("Int64")
            df_pheno = df_pheno.dropna(subset=["Week", "VRSA"])
            df_pheno["VRSA"] = df_pheno["VRSA"].astype(int)

            # 1) Tracé du graphique du nombre de VRSA
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

            # 2) Points rouges (alerte) pour VRSA > 0
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

            # 3) Tableau récapitulatif + téléchargement CSV
            st.subheader("Tableau récapitulatif : Nb VRSA par semaine")
            df_table = (
                df_pheno[["Week", "VRSA"]]
                .rename(columns={"Week": "Semaine", "VRSA": "Nb VRSA"})
                .sort_values("Semaine")
                .reset_index(drop=True)
            )
            st.dataframe(df_table, use_container_width=True)

            csv_data = df_table.to_csv(index=False)
            st.download_button(
                label="📥 Télécharger le tableau VRSA (CSV)",
                data=csv_data,
                file_name="decompte_VRSA_par_semaine.csv",
                mime="text/csv"
            )

        else:
            # MRSA / Wild / Other : affichage du pourcentage + moyenne mobile + IC
            path_pheno = phenotypes[pheno]
            if not path_pheno or not os.path.isfile(path_pheno):
                st.error(f"Impossible de trouver le fichier `{path_pheno}`.")
                return

            df_ph = pd.read_excel(path_pheno)
            if "Week" not in df_ph.columns or "Pourcentage" not in df_ph.columns:
                st.error(f"Le fichier `{path_pheno}` doit contenir au moins les colonnes 'Week' et 'Pourcentage'.")
                return

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

# --------------------------------------------------
# 9) Onglet "Staphylococcus aureus" - onglet Alertes
# --------------------------------------------------
def onglet_alertes():
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
        if not os.path.isfile(path):
            continue
        df_out = pd.read_excel(path)
        week_col = "Week" if "Week" in df_out.columns else "Semaine"
        if "OUTLIER" not in df_out.columns or week_col not in df_out.columns:
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

# --------------------------------------------------
# 10) Lancement de l'application
# --------------------------------------------------
def main():
    page = st.sidebar.radio("Navigation", 
                             ["Vue globale", 
                              "Staphylococcus aureus", 
                              "Répartition globale"])
    if page == "Vue globale":
        page_vue_globale()
    elif page == "Répartition globale":
        page_repartition_globale()
    elif page == "Staphylococcus aureus":
        st.title("🥠 Surveillance : Staphylococcus aureus")
        tab1, tab2, tab3 = st.tabs(["Antibiotiques", "Phénotypes", "Alertes semaine/service"])
        with tab1:
            onglet_antibiotiques()
        with tab2:
            onglet_phenotypes()
        with tab3:
            onglet_alertes()

if __name__ == "__main__":
    main()
