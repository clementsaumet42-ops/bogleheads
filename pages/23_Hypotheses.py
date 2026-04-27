"""Page 23 — Hypothèses & Sources : consultation (lecture seule) — Sprint S17."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.ui.theme import injecter_css

st.set_page_config(page_title="Hypothèses & Sources", page_icon="🏛️", layout="wide")
injecter_css()

st.title("Hypothèses & Sources")
st.caption(
    "Registre central des hypothèses utilisées dans le tool. "
    "Lecture seule — modification via config/hypotheses.yaml."
)

# ─── Chargement ───────────────────────────────────────────────────────────────

try:
    from src.hypotheses.catalogue import lister_hypotheses_par_categorie
    from src.hypotheses.source import Hypothese

    categories = lister_hypotheses_par_categorie()
    toutes: list[Hypothese] = [h for hyps in categories.values() for h in hyps]
except Exception as exc:
    st.error(f"Impossible de charger les hypothèses : {exc}")
    st.stop()

# ─── Filtres ──────────────────────────────────────────────────────────────────

col_f1, col_f2, col_f3 = st.columns([3, 2, 2])

with col_f1:
    filtre_texte = st.text_input("Recherche (clé, description, source…)", "")

with col_f2:
    cats_dispo = sorted(categories.keys())
    filtre_cat = st.selectbox(
        "Catégorie",
        ["Toutes"] + cats_dispo,
        index=0,
    )

with col_f3:
    confidences = sorted({h.confiance for h in toutes})
    filtre_conf = st.selectbox("Confiance", ["Toutes"] + confidences, index=0)

# ─── Application des filtres ─────────────────────────────────────────────────

filtrees = toutes

if filtre_cat != "Toutes":
    filtrees = [h for h in filtrees if h.categorie == filtre_cat]

if filtre_conf != "Toutes":
    filtrees = [h for h in filtrees if h.confiance == filtre_conf]

if filtre_texte:
    q = filtre_texte.lower()
    filtrees = [
        h
        for h in filtrees
        if q in h.cle.lower()
        or q in h.description.lower()
        or any(q in s.organisme.lower() or q in s.nom.lower() for s in h.sources)
    ]

st.caption(f"{len(filtrees)} hypothèse(s) affichée(s) sur {len(toutes)}")

# ─── Tableau principal ────────────────────────────────────────────────────────

if not filtrees:
    st.info("Aucune hypothèse ne correspond aux filtres.")
else:
    lignes = []
    for h in sorted(filtrees, key=lambda x: (x.categorie, x.cle)):
        source_principale = h.sources[0] if h.sources else None
        lignes.append(
            {
                "Clé": h.cle,
                "Valeur": h.valeur,
                "Unité": h.unite,
                "Catégorie": h.categorie,
                "Description": h.description.strip().replace("\n", " ")[:120],
                "Source principale": source_principale.organisme if source_principale else "—",
                "Année source": source_principale.date_publication.year
                if source_principale
                else "—",
                "URL": source_principale.url if source_principale else None,
                "Version": h.version,
                "Confiance": h.confiance,
                "Validité début": h.date_validite_debut.isoformat(),
                "Validité fin": h.date_validite_fin.isoformat() if h.date_validite_fin else "—",
            }
        )
    df = pd.DataFrame(lignes)

    # Affichage colonnes principales dans le tableau
    cols_display = [
        "Clé",
        "Valeur",
        "Unité",
        "Catégorie",
        "Description",
        "Source principale",
        "Confiance",
        "Version",
    ]
    st.dataframe(df[cols_display], use_container_width=True, hide_index=True)

    # ─── Détail par hypothèse ────────────────────────────────────────────────

    st.subheader("Détail")
    cle_choisie = st.selectbox(
        "Sélectionner une hypothèse pour voir le détail",
        options=[h.cle for h in sorted(filtrees, key=lambda x: x.cle)],
        index=0,
    )
    h_detail = next((h for h in filtrees if h.cle == cle_choisie), None)
    if h_detail:
        c1, c2, c3 = st.columns(3)
        c1.metric("Valeur", f"{h_detail.valeur} {h_detail.unite}")
        c2.metric("Confiance", h_detail.confiance)
        c3.metric("Version", h_detail.version)
        st.markdown(f"**Description :** {h_detail.description.strip()}")
        if h_detail.commentaire_methodologique:
            st.info(f"{h_detail.commentaire_methodologique.strip()}")
        if h_detail.sources:
            st.markdown("**Sources :**")
            for i, s in enumerate(h_detail.sources, 1):
                with st.expander(f"Source {i} — {s.nom}"):
                    st.markdown(f"- **Organisme :** {s.organisme}")
                    st.markdown(f"- **Type :** {s.type_source}")
                    st.markdown(
                        f"- **Publiée le :** {s.date_publication} — "
                        f"**Consultée le :** {s.date_consultation}"
                    )
                    if s.url:
                        st.markdown(f"- **URL :** [{s.url}]({s.url})")
                    if s.extrait:
                        st.markdown(f'- **Extrait :** *"{s.extrait.strip()}"*')

    # ─── Export CSV ──────────────────────────────────────────────────────────

    st.divider()
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Exporter CSV",
        data=csv,
        file_name="hypotheses_boglehead_fr.csv",
        mime="text/csv",
    )

# ─── Info bas de page ─────────────────────────────────────────────────────────

st.divider()
st.caption(
    "Source : config/hypotheses.yaml — "
    "Pour modifier les hypothèses, éditer ce fichier YAML et redémarrer l'app. "
    "Toute modification doit être versionnée et documentée."
)
