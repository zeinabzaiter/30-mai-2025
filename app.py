import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt

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

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(df_abx[week_col], df_abx["Pourcentage"], label="Pourcentage", linewidth=2, marker='o')
        ax.plot(df_abx[week_col], df_abx["Moyenne_mobile_8s"], linestyle='--', label="Moyenne mobile")
        ax.fill_between(df_abx[week_col], df_abx["IC_inf"], df_abx["IC_sup"], color='gray', alpha=0.2, label="IC 95%")
        outliers = df_abx[df_abx["OUTLIER"] == True]
        ax.scatter(outliers[week_col], outliers["Pourcentage"], color='darkred', label="Outliers", zorder=5)
        ax.set_title(f"Évolution de la résistance à {abx}")
        ax.set_xlabel("Semaine")
        ax.set_ylabel("% Résistance")
        ax.legend()
        ax.grid(True)
        st.pyplot(fig)

    with tab2:
        st.subheader("🧬 Évolution des phénotypes")
        pheno = st.selectbox("Choisir un phénotype", list(phenotypes.keys()))
        df_pheno = pd.read_excel(phenotypes[pheno])
        fig2, ax2 = plt.subplots(figsize=(10, 4))
        ax2.plot(df_pheno["Week"], df_pheno["Pourcentage"], label="Pourcentage", linewidth=2, marker='o')
        ax2.plot(df_pheno["Week"], df_pheno["Moyenne_mobile_8s"], linestyle='--', label="Moyenne mobile")
        ax2.fill_between(df_pheno["Week"], df_pheno["IC_inf"], df_pheno["IC_sup"], color='gray', alpha=0.2, label="IC 95%")
        outliers2 = df_pheno[df_pheno["OUTLIER"] == True]
        ax2.scatter(outliers2["Week"], outliers2["Pourcentage"], color='darkred', label="Outliers", zorder=5)
        ax2.set_title(f"Évolution du phénotype {pheno}")
        ax2.set_xlabel("Semaine")
        ax2.set_ylabel("% Présence")
        ax2.legend()
        ax2.grid(True)
        st.pyplot(fig2)

    with tab3:
        st.subheader("🚨 Alertes croisées par semaine et service")
        alertes = []
        for abx, path in antibiotiques.items():
            df_out = pd.read_excel(path)
            week_col = "Week" if "Week" in df_out.columns else "Semaine"
            if "OUTLIER" not in df_out.columns:
                continue
            weeks = df_out[df_out["OUTLIER"] == True][week_col].unique()
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
