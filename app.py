from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st



st.set_page_config(page_title="Économie africaine", page_icon="🌍", layout="wide")
FICHIER = Path(__file__).parent / "data" / "dataset_economique_afrique_propre.csv"

@st.cache_data
def charger_donnees():
    return pd.read_csv(FICHIER)


df = charger_donnees()

st.title("🌍 Analyse de l'économie africaine")
st.caption("Source : Banque mondiale, World Development Indicators (WDI). 54 pays, 2004-2023")

st.sidebar.header("Filtres")



regions = sorted(df["sous_region"].unique())
regions_choisies = st.sidebar.multiselect("Sous-région", regions, default=regions)

pays_dispo = sorted(df.loc[df["sous_region"].isin(regions_choisies), "pays"].unique())
pays_choisis = st.sidebar.multiselect("Pays (vide = tous)", pays_dispo)

annee_min, annee_max = int(df["annee"].min()), int(df["annee"].max())
annees = st.sidebar.slider("Période", annee_min, annee_max, (annee_min, annee_max))

INDICATEURS = {
    "PIB par habitant (USD)": "pib_par_habitant_usd",
    "PIB (milliards USD)": "pib_milliards_usd",
    "Croissance du PIB (%)": "croissance_pib_pct",
    "Inflation (%)": "inflation_pct",
    "Espérance de vie (ans)": "esperance_vie",
    "Accès à l'électricité (%)": "acces_electricite_pct",
    "Utilisateurs d'internet (%)": "utilisateurs_internet_pct",
}
indicateur_label = st.sidebar.selectbox("Indicateur", list(INDICATEURS))
indicateur = INDICATEURS[indicateur_label]


masque = df["sous_region"].isin(regions_choisies) & df["annee"].between(*annees)
if pays_choisis:
    masque &= df["pays"].isin(pays_choisis)
dff = df[masque]

if dff.empty:
    st.warning("Aucune donnée pour ces filtres.")
    st.stop()

# Test temporaire : à supprimer quand les sections suivantes seront en place
st.write(f"{len(dff)} lignes sélectionnées | indicateur : {indicateur_label}")
st.dataframe(dff.head())

# ---------- Section 1 : vue d'ensemble ----------
st.header("Vue d'ensemble")

an_debut, an_fin = annees
fin = dff[dff["annee"] == an_fin]
debut = dff[dff["annee"] == an_debut]


def formater(x):
    """Affiche un nombre avec un espace pour les milliers, ou 'n.d.' s'il est manquant."""
    return "n.d." if pd.isna(x) else f"{x:,.1f}".replace(",", " ")


med_fin = fin[indicateur].median()
med_debut = debut[indicateur].median()

# Variation entre le début et la fin de la période
delta = None
if an_debut != an_fin and pd.notna(med_fin) and pd.notna(med_debut):
    if indicateur.endswith("_pct"):
        delta = f"{med_fin - med_debut:+.1f} pts depuis {an_debut}"
    elif med_debut != 0:
        delta = f"{(med_fin / med_debut - 1) * 100:+.1f} % depuis {an_debut}"
delta_color = "inverse" if indicateur == "inflation_pct" else "normal"

# Pays au maximum et au minimum (en ignorant les valeurs manquantes)
valides = fin.dropna(subset=[indicateur])
if valides.empty:
    pays_haut = pays_bas = "n.d."
    val_haut = val_bas = float("nan")
else:
    ligne_haut = valides.loc[valides[indicateur].idxmax()]
    ligne_bas = valides.loc[valides[indicateur].idxmin()]
    pays_haut, val_haut = ligne_haut["pays"], ligne_haut[indicateur]
    pays_bas, val_bas = ligne_bas["pays"], ligne_bas[indicateur]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Pays sélectionnés", dff["pays"].nunique())
col2.metric(f"Médiane en {an_fin}", formater(med_fin), delta, delta_color=delta_color)
col3.metric(f"Maximum en {an_fin} ({pays_haut})", formater(val_haut))
col4.metric(f"Minimum en {an_fin} ({pays_bas})", formater(val_bas))

st.caption(
    f"{indicateur_label} : médiane calculée sur {fin[indicateur].notna().sum()} pays "
    f"ayant une donnée en {an_fin}. Médiane plutôt que moyenne, car quelques valeurs "
    f"extrêmes fausseraient la moyenne."
)


# ---------- Section 2 : analyse temporelle ----------
st.header("Analyse temporelle")

col_graphe = indicateur
note = ""

if pays_choisis:
   
    if f"{indicateur}_ecrete" in dff.columns:
        col_graphe = f"{indicateur}_ecrete"
        note = " Valeurs extrêmes écrêtées (5e-95e percentile) pour garder le graphique lisible."
    donnees_graph = dff
    couleur = "pays"
    titre = f"{indicateur_label} par pays"
else:
 
    donnees_graph = (
        dff.groupby(["sous_region", "annee"])[indicateur].median().reset_index()
    )
    couleur = "sous_region"
    titre = f"{indicateur_label} : médiane par sous-région"

fig = px.line(
    donnees_graph,
    x="annee",
    y=col_graphe,
    color=couleur,
    markers=True,
    title=titre,
    labels={col_graphe: indicateur_label, "annee": "Année"},
)
fig.update_layout(hovermode="x unified", legend_title_text="")
st.plotly_chart(fig, width="stretch")

st.caption(
    "Ce graphique montre l'évolution de l'indicateur au fil des années. "
    "Sans pays sélectionné, chaque courbe est la médiane d'une sous-région ; "
    "avec des pays sélectionnés, chaque courbe est un pays." + note
)
# ---------- Section 3 : comparaison géographique ----------
st.header("Comparaison géographique")

carte = fin.dropna(subset=[indicateur])

if carte.empty:
    st.info(f"Aucune donnée disponible en {an_fin} pour cet indicateur.")
else:
    gauche, droite = st.columns([3, 2])

    with gauche:
        bas, haut = carte[indicateur].quantile([0.05, 0.95])
        fig_carte = px.choropleth(
            carte,
            locations="iso3",
            color=indicateur,
            hover_name="pays",
            scope="africa",
            color_continuous_scale="Viridis",
            range_color=(bas, haut),
            labels={indicateur: indicateur_label},
            title=f"{indicateur_label} en {an_fin}",
        )
        fig_carte.update_geos(showcountries=True)
        fig_carte.update_layout(margin=dict(l=0, r=0, t=40, b=0), height=500)
        st.plotly_chart(fig_carte, width="stretch")

    with droite:
        par_region = (
            carte.groupby("sous_region")[indicateur].median().sort_values().reset_index()
        )
        fig_barres = px.bar(
            par_region,
            x=indicateur,
            y="sous_region",
            orientation="h",
            text_auto=".1f",
            labels={indicateur: indicateur_label, "sous_region": ""},
            title=f"Médiane par sous-région en {an_fin}",
        )
        fig_barres.update_layout(height=500)
        st.plotly_chart(fig_barres, width="stretch")

    st.caption(
        f"Carte : {indicateur_label} par pays en {an_fin}. Les pays en gris n'ont pas de donnée. "
        "L'échelle de couleurs va du 5e au 95e percentile, pour qu'un pays extrême n'écrase pas "
        "les autres. Les petites îles (Seychelles, Maurice, Comores, Cap-Vert) sont trop petites "
        "pour apparaître : survole la carte ou regarde le tableau de la section 1. "
        "Barres : médiane de chaque sous-région."
    )
    
    # ---------- Section 4 : corrélations ----------
st.header("Corrélations")

colonnes_corr = list(INDICATEURS.values())
etiquettes = {col: libelle for libelle, col in INDICATEURS.items()}

# --- Heatmap ---
if dff["pays"].nunique() < 5:
    st.info("Sélectionne au moins 5 pays (ou aucun) pour afficher la matrice de corrélations.")
else:
    corr = dff[colonnes_corr].corr(method="spearman").rename(
        index=etiquettes, columns=etiquettes
    )
    fig_corr = px.imshow(
        corr,
        text_auto=".2f",
        zmin=-1,
        zmax=1,
        color_continuous_scale="RdBu_r",
        aspect="auto",
        title="Matrice de corrélations (Spearman)",
    )
    st.plotly_chart(fig_corr, width="stretch")

    st.caption(
        "Chaque case donne le lien entre deux indicateurs : +1 = ils évoluent ensemble, "
        "-1 = ils évoluent en sens inverse, 0 = aucun lien. Corrélation de Spearman (sur les "
        "rangs), peu sensible aux valeurs extrêmes. Calculée sur toutes les années de la période "
        "et tous les pays filtrés : le temps fait progresser plusieurs indicateurs en même temps, "
        "ce qui peut gonfler certains liens. Corrélation n'est pas causalité."
    )

# --- Nuage de points interactif ---
st.subheader("Explorer deux indicateurs")

libelles = list(INDICATEURS)
c1, c2, c3 = st.columns(3)
x_label = c1.selectbox("Axe X", libelles, index=libelles.index("Accès à l'électricité (%)"), key="axe_x")
y_label = c2.selectbox("Axe Y", libelles, index=libelles.index("Espérance de vie (ans)"), key="axe_y")
log_x = c3.checkbox("Échelle logarithmique en X", value=False)

x_col, y_col = INDICATEURS[x_label], INDICATEURS[y_label]

donnees_sc = fin.dropna(subset=[x_col, y_col, "population"])
if log_x:
    donnees_sc = donnees_sc[donnees_sc[x_col] > 0]

if len(donnees_sc) < 3:
    st.info(f"Pas assez de pays avec des données en {an_fin} pour ces deux indicateurs.")
else:
    fig_sc = px.scatter(
        donnees_sc,
        x=x_col,
        y=y_col,
        color="sous_region",
        size="population",
        size_max=40,
        hover_name="pays",
        log_x=log_x,
        labels={x_col: x_label, y_col: y_label, "sous_region": "Sous-région"},
        title=f"{y_label} selon {x_label}, en {an_fin}",
    )
    st.plotly_chart(fig_sc, width="stretch")

    st.caption(
        f"Chaque bulle est un pays en {an_fin} (année unique, donc pas d'effet du temps). "
        "La taille de la bulle représente la population, la couleur la sous-région. "
        "L'échelle logarithmique aide quand quelques pays ont des valeurs très élevées."
    )
   # ---------- Section 5 : distribution ----------
st.header("Distribution")

donnees_dist = fin.dropna(subset=[indicateur])

if len(donnees_dist) < 3:
    st.info(f"Pas assez de pays avec des données en {an_fin} pour cet indicateur.")
else:
    fig_dist = px.histogram(
        donnees_dist,
        x=indicateur,
        color="sous_region",
        nbins=12,
        labels={indicateur: indicateur_label, "sous_region": "Sous-région"},
        title=f"Nombre de pays par tranche de valeur en {an_fin}",
    )
    fig_dist.update_layout(yaxis_title="Nombre de pays", bargap=0.1)
    st.plotly_chart(fig_dist, width="stretch")

    st.caption(
        f"Chaque barre compte les pays dont la valeur de l'indicateur en {an_fin} tombe dans une "
        "tranche. Les couleurs séparent les sous-régions : on voit si les valeurs sont concentrées "
        "sur quelques tranches ou étalées, et quelles sous-régions occupent chaque tranche."
    )