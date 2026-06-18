# Cas de test dogfood — Famille Rousseau-Marchand

> Données 100 % fictives — usage interne dogfood uniquement.  
> Ce dossier ne contient aucun client réel, aucune adresse réelle, aucun IBAN réel.

---

## Présentation du cas

Le cas Rousseau-Marchand est un dossier patrimonial fictif complexe conçu pour tester Sextant de bout en bout. Il met en scène un couple avec des revenus hétérogènes (cadre salarié + TNS), un patrimoine financier diversifié de 1,3 M€ (PEA, CTO, AV, PER, épargne salariale, actifs alternatifs), un patrimoine immobilier net de 2,1 M€ soumis à l'IFI, et cinq enveloppes financières importables via la page S20. Le cas inclut 18 pièges fiscaux, réglementaires et d'allocation délibérément insérés pour évaluer la qualité de détection du tool.

---

## Comment utiliser ce cas

**Prérequis :** l'application Streamlit est lancée localement (`streamlit run app.py`).

**Étape 1 — Créer la mission**  
Depuis la page `00_Mission_EC`, créer une nouvelle mission intitulée "Rousseau-Marchand 2026". Saisir le profil du foyer en s'appuyant sur la fixture `tests/fixtures/cas_rousseau.yaml`.

**Étape 2 — Générer les PDF de test**  
Ouvrir chacun des 5 fichiers Markdown du dossier `dogfood/cas_rousseau/pdf_a_generer/` dans un éditeur (Word, Pages, Typora). Exporter au format PDF. Sauvegarder les 5 PDF dans un dossier local temporaire (non commité — voir `.gitignore`).

**Étape 3 — Importer les relevés via la page S20**  
Depuis la page `24_Import_Patrimoine`, déposer successivement les 5 PDF générés. Vérifier pour chacun :
- la détection automatique de l'émetteur (signature YAML correspondante)
- les lignes extraites et leur score de confiance
- les alertes déclenchées (H2O, concentration PEE, titres UK)

**Étape 4 — Parcourir le fil conducteur S16**  
Depuis la page `00_Mission_EC`, suivre les étapes : Profil → Profilage MIF II → Allocation cible → Asset location → Plan d'exécution → Conformité CIF. Vérifier à chaque étape que les données importées en S20 sont bien reprises.

**Étape 5 — Générer tous les livrables**  
Depuis la page Mission, utiliser le bouton "Tout générer" (S18) pour produire le ZIP complet : rapport PDF, DER, lettre de mission, Excel.

**Étape 6 — Scorer via la grille**  
Ouvrir `dogfood/cas_rousseau/grille_scoring.md`. Pour chacun des 18 pièges, cocher `Détecté`, `Partiellement` ou `Manqué` selon le comportement observé. Consigner les observations dans le champ "Notes".

---

## Contenu de ce dossier

| Fichier / Dossier | Description |
|---|---|
| `pdf_a_generer/01_releve_bourse_direct_pea_antoine.md` | PEA Antoine — Bourse Direct — 110 000 € |
| `pdf_a_generer/02_releve_boursorama_cto_joint.md` | CTO joint — Boursorama — 165 000 € |
| `pdf_a_generer/03_releve_generali_espace_lux_av_antoine.md` | AV Generali Espace Lux — 380 000 € |
| `pdf_a_generer/04_releve_linxea_spirit_2_av_camille.md` | AV Linxea Spirit 2 — Camille — 290 000 € |
| `pdf_a_generer/05_releve_amundi_pee_percol_antoine.md` | Épargne salariale Amundi — 180 000 € |
| `grille_scoring.md` | 18 pièges scorables avec critères de détection |
| `../../tests/fixtures/cas_rousseau.yaml` | Fixture YAML complète pour tests de régression |

---

## Avertissement

Ce dossier contient exclusivement des données fictives inventées à des fins de test interne. Tout ressemblance avec une situation patrimoniale réelle est fortuite. Les ISIN utilisés sont ceux d'instruments financiers réels cotés, mais les quantités, valorisations et données personnelles sont intégralement inventées.

Les PDF générés par l'EC à partir des fichiers Markdown ne doivent pas être committés dans le dépôt (voir `.gitignore` : `dogfood/cas_rousseau/pdf_generes/`).
