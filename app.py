import streamlit as st
import pandas as pd
import os
import plotly.express as px

st.set_page_config(page_title="Surveillance bactérienne", layout="wide")

# === Données principales ===
DATA_FOLDER = "data"
bacteries_file = os.path.join(DATA_FOLDER, "TOUS les bacteries a etudier.xlsx")
export_file = os.path.join(DATA_FOLDER, "Export_StaphAureus_COMPLET.csv")

# Charger données principales
bacteries_df = pd.read_excel(bacteries_file)
df_export = pd.read_csv(export_file)
df_export.columns = df_export.columns.str.strip()
df_export['semaine'] = pd.to_numeric(df_export['semaine'], errors='coerce')

# === Fichiers OUTLIER antibiotiques ===
antibiotiques = {
    "Vancomycine": os.path.join(DATA_FOLDER, "pctR_Vancomycin_analyse_2024.xlsx"),
    "Teicoplanine": os.path.join(DATA_FOLDER, "pct_R_Teicoplanin_analyse_2024.xlsx"),
    "Gentamycine": os.path.join(DATA_FOLDER, "pct_R_Gentamicin_analyse_2024.xlsx"),
    "Oxacilline": os.path.join(DATA_FOLDER, "pct_R_Oxacillin_analyse_2024.xlsx")
}

# === Fichiers phénotypes ===
phenotypes = {
    "MRSA": os.path.join(DATA_FOLDER, "MRSA_analyse.xlsx"),
    "VRSA": os.path.join(DATA_FOLDER, "VRSA_analyse.xlsx"),
    "Wild": os.path.join(DATA_FOLDER, "Wild_analyse.xlsx"),
    "Other": os.path.join(DATA_FOLDER, "Other_analyse.xlsx")
}

# === Navigation ===
menu = st.sidebar.radio("Navigation", ["Vue globale", "Staphylococcus aureus"])

if menu == "Vue globale":
    st.title("📋 Bactéries à surveiller")
    st.dataframe(bacteries_df, use_container_width=True)

elif menu == "Staphylococcus aureus":
    st.title("🦠 Surveillance : Staphylococcus aureus")
    tab1, tab2, tab3 = st.tabs(["Antibiotiques", "Phénotypes", "Alertes semaine/service"])

    with tab1:
        st.subheader("📈 Évolution hebdomadaire de la résistance")
        abx = st.selectbox("Choisir un antibiotique", list(antibiotiques.keys()))
        df_abx = pd.read_excel(antibiotiques[abx])
        week_col = "Week" if "Week" in df_abx.columns else "Semaine"
        df_abx[week_col] = pd.to_numeric(df_abx[week_col], errors='coerce')
        df_abx = df_abx.dropna(subset=[week_col, "Pourcentage"])
        df_abx["Pourcentage"] = df_abx["Pourcentage"].round(2)

        fig = px.line(df_abx, x=week_col, y="Pourcentage", markers=True, title=f"Évolution de la résistance à {abx}",
                      labels={week_col: "Semaine", "Pourcentage": "% Résistance"},
                      hover_data={"Pourcentage": ':.2f'})
        fig.update_traces(line=dict(width=3), hovertemplate="Semaine %{x}<br>% Résistance: %{y:.2f}%")
        fig.update_layout(yaxis_title="% Résistance", xaxis_title="Semaine")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("🧬 Évolution des phénotypes")
        pheno = st.selectbox("Choisir un phénotype", list(phenotypes.keys()))
        df_pheno = pd.read_excel(phenotypes[pheno])
        df_pheno["Week"] = pd.to_numeric(df_pheno["Week"], errors='coerce')
        df_pheno = df_pheno.dropna(subset=["Week", "Pourcentage"])
        df_pheno["Pourcentage"] = df_pheno["Pourcentage"].round(2)

        fig2 = px.line(df_pheno, x="Week", y="Pourcentage", markers=True, title=f"Évolution du phénotype {pheno}",
                       labels={"Week": "Semaine", "Pourcentage": "% Présence"},
                       hover_data={"Pourcentage": ':.2f'})
        fig2.update_traces(line=dict(width=3), hovertemplate="Semaine %{x}<br>% Présence: %{y:.2f}%")
        fig2.update_layout(yaxis_title="% Présence", xaxis_title="Semaine")
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.subheader("🚨 Alertes croisées par semaine et service")
        alertes = []
        for abx, path in antibiotiques.items():
            df_out = pd.read_excel(path)
            week_col = "Week" if "Week" in df_out.columns else "Semaine"
            if "OUTLIER" not in df_out.columns:
                continue
            df_out[week_col] = pd.to_numeric(df_out[week_col], errors='coerce')
            weeks = df_out[df_out["OUTLIER"] == True][week_col].dropna().unique()
            for w in weeks:
                mask = (df_export['semaine'] == w)
                if abx in df_export.columns:
                    resist = (df_export[abx] == 'R')
                    df_alert = df_export[mask & resist]
                    for srv in df_alert['uf'].unique():
                        nb_r = df_alert[df_alert['uf'] == srv].shape[0]
                        alertes.append({
                            "Semaine": int(w), "Service": srv, "Antibiotique": abx,
                            "Nb_R": nb_r, "Alarme": "Oui"
                        })
        df_final_alertes = pd.DataFrame(alertes)
        st.dataframe(df_final_alertes, use_container_width=True)
        if not df_final_alertes.empty:
            st.download_button("📥 Télécharger les alertes", data=df_final_alertes.to_csv(index=False), file_name="alertes_detectees.csv")
