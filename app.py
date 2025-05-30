import streamlit as st
import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Surveillance bactérienne", layout="wide")

# === Données ===
DATA_FOLDER = "data"
bacteries_file = os.path.join(DATA_FOLDER, "TOUS les bacteries a etudier.xlsx")
export_file = os.path.join(DATA_FOLDER, "Export_StaphAureus_COMPLET.csv")

bacteries_df = pd.read_excel(bacteries_file)
df_export = pd.read_csv(export_file)
df_export.columns = df_export.columns.str.strip()
df_export['semaine'] = pd.to_numeric(df_export['semaine'], errors='coerce')

# Antibiotiques détectés automatiquement
antibiotiques = {}
for file in os.listdir(DATA_FOLDER):
    if file.startswith("pct") and file.endswith(".xlsx"):
        abx_name = file.replace("pctR_", "").replace("pct_R_", "").replace("pct", "").replace(".xlsx", "").capitalize()
        antibiotiques[abx_name] = os.path.join(DATA_FOLDER, file)

# Phénotypes
phenotypes = {
    "MRSA": os.path.join(DATA_FOLDER, "MRSA_analyse.xlsx"),
    "VRSA": os.path.join(DATA_FOLDER, "VRSA_analyse.xlsx"),
    "Wild": os.path.join(DATA_FOLDER, "Wild_analyse.xlsx"),
    "Other": os.path.join(DATA_FOLDER, "Other_analyse.xlsx")
}

# Navigation
menu = st.sidebar.radio("Navigation", ["Vue globale", "Staphylococcus aureus"])

if menu == "Vue globale":
    st.title("📋 Bactéries à surveiller")
    st.dataframe(bacteries_df, use_container_width=True)

elif menu == "Staphylococcus aureus":
    st.title("🦠 Surveillance : Staphylococcus aureus")
    tab1, tab2, tab3 = st.tabs(["Antibiotiques", "Phénotypes", "Alertes semaine/service"])

    with tab1:
        st.subheader("📈 Évolution hebdomadaire de la résistance")
        abx = st.selectbox("Choisir un antibiotique", sorted(antibiotiques.keys()))
        df_abx = pd.read_excel(antibiotiques[abx])
        week_col = "Week" if "Week" in df_abx.columns else "Semaine"

        df_abx[week_col] = pd.to_numeric(df_abx[week_col], errors='coerce')
        df_abx = df_abx.dropna(subset=[week_col, "Pourcentage"])
        df_abx["Pourcentage"] = df_abx["Pourcentage"].round(2)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_abx[week_col], y=df_abx["Pourcentage"],
                                 mode="lines+markers", name="% Résistance",
                                 line=dict(width=3), marker=dict(color="blue")))
        if "Moyenne_mobile_8s" in df_abx.columns:
            fig.add_trace(go.Scatter(x=df_abx[week_col], y=df_abx["Moyenne_mobile_8s"],
                                     mode="lines", name="Moyenne mobile",
                                     line=dict(dash="dash", color="orange")))
        if "IC_sup" in df_abx.columns:
            fig.add_trace(go.Scatter(x=df_abx[week_col], y=df_abx["IC_sup"],
                                     mode="lines", name="Seuil IC 95%",
                                     line=dict(dash="dot", color="gray")))
        if "OUTLIER" in df_abx.columns:
            outliers = df_abx[df_abx["OUTLIER"] == True]
            fig.add_trace(go.Scatter(x=outliers[week_col], y=outliers["Pourcentage"],
                                     mode="markers", name="🔴 Alerte (OUTLIER)",
                                     marker=dict(color="red", size=10)))

        fig.update_layout(title=f"Évolution de la résistance à {abx}",
                          xaxis_title="Semaine", yaxis_title="% Résistance",
                          legend_title="Légende", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("""
        #### ℹ️ Définition des alertes :
        - **Seuil IC 95%** : ligne pointillée grise = limite supérieure de confiance
        - **🔴 OUTLIER** : % de résistance dépassant ce seuil → alerte
        - **Moyenne mobile** : tendance glissante sur 8 semaines
        """)

    with tab2:
        st.subheader("🧬 Évolution des phénotypes")
        pheno = st.selectbox("Choisir un phénotype", list(phenotypes.keys()))
        df_pheno = pd.read_excel(phenotypes[pheno])
        df_pheno["Week"] = pd.to_numeric(df_pheno["Week"], errors='coerce')
        df_pheno = df_pheno.dropna(subset=["Week", "Pourcentage"])
        df_pheno["Pourcentage"] = df_pheno["Pourcentage"].round(2)

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df_pheno["Week"], y=df_pheno["Pourcentage"],
                                  mode="lines+markers",
                                  name="% Présence",
                                  line=dict(width=3, color="blue")))

        if "Moyenne_mobile_8s" in df_pheno.columns:
            fig2.add_trace(go.Scatter(x=df_pheno["Week"], y=df_pheno["Moyenne_mobile_8s"],
                                      mode="lines",
                                      name="Moyenne mobile",
                                      line=dict(dash="dash", color="orange")))

        if "IC_sup" in df_pheno.columns:
            fig2.add_trace(go.Scatter(x=df_pheno["Week"], y=df_pheno["IC_sup"],
                                      mode="lines",
                                      name="Seuil IC 95%",
                                      line=dict(dash="dot", color="gray")))

        if "OUTLIER" in df_pheno.columns:
            outliers = df_pheno[df_pheno["OUTLIER"] == True]
            fig2.add_trace(go.Scatter(x=outliers["Week"], y=outliers["Pourcentage"],
                                      mode="markers",
                                      name="🔴 Alerte (OUTLIER)",
                                      marker=dict(color="red", size=10)))

        fig2.update_layout(title=f"Évolution du phénotype {pheno}",
                           xaxis_title="Semaine",
                           yaxis_title="% Présence",
                           legend_title="Légende",
                           hovermode="x unified")
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown("""
        #### ℹ️ Définition des alertes :
        - **Seuil IC 95%** : ligne pointillée grise = limite supérieure de confiance
        - **🔴 OUTLIER** : % de présence dépassant ce seuil → alerte
        - **Moyenne mobile** : tendance glissante sur 8 semaines
        """)

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
