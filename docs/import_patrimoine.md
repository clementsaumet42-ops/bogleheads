# Import Patrimoine depuis PDF — Guide CGP

## Vue d'ensemble

Le module `src/import_patrimoine/` permet d'extraire automatiquement les données patrimoniales
depuis des relevés PDF (banques, courtiers, assureurs AV) et de les importer dans une mission
active (S16).

Le mode d'extraction est **conservateur** : chaque ligne doit être validée individuellement
par le CGP avant import. Aucun merge silencieux.

---

## Accès

Page Streamlit : **`24_Import_Patrimoine`** dans la barre latérale.

---

## Flux d'utilisation

1. Sélectionner la mission active
2. Téléverser un ou plusieurs relevés PDF
3. Cliquer sur "Lancer extraction"
4. Réviser le tableau ligne par ligne :
   - Vert (confiance ≥ 80) : extraction fiable
   - Orange (50–79) : vérifier avant de cocher
   - Rouge (< 50) : saisie manuelle recommandée
5. Cocher chaque ligne à importer (ou "Valider toutes les lignes vertes")
6. Cliquer "Importer dans la mission"

---

## Émetteurs supportés (S20)

| Émetteur | Template | Type |
|---|---|---|
| Bourse Direct | `bourse_direct.yaml` | Courtier |
| Boursorama | `boursorama.yaml` | Banque/Courtier |
| Fortuneo | `fortuneo.yaml` | Banque/Courtier |
| BNP Paribas | `bnp_paribas.yaml` | Banque |
| Société Générale | `societe_generale.yaml` | Banque |
| Crédit Agricole | `credit_agricole.yaml` | Banque (toutes caisses) |
| CIC / Crédit Mutuel | `cic_cm.yaml` | Banque |
| Generali | `generali.yaml` | Assureur AV |
| Linxea | `linxea.yaml` | Courtier AV |
| AXA | `axa.yaml` | Assureur AV |

---

## Ajouter un template (S21/S22 ou hotfix dogfood)

Les templates sont des fichiers YAML dans `src/import_patrimoine/templates/`.
**Aucun code Python à modifier.** Il suffit de créer un nouveau fichier YAML.

### Structure d'un template

```yaml
emetteur:
  nom: "Nom de l'émetteur"
  type: "courtier"          # "courtier" | "banque" | "assureur"
  signatures:               # Textes recherchés dans le PDF pour détecter l'émetteur
    - "TEXTE EXACT EN MAJUSCULES"
    - "Variante courants"
    - "ORIAS 12 345 678"    # Numéro ORIAS si connu
  enveloppe_par_defaut_si_indetectable: "CTO"   # Enveloppe par défaut

extraction:
  methode: "tableau"        # "tableau" | "regex" | "hybride"
  page_strategie: "auto"    # "auto" | "premiere" | "toutes"

  detection_enveloppe:      # Patterns pour identifier le type de compte
    pea: ["PEA", "Plan d'Épargne en Actions"]
    pea_pme: ["PEA-PME", "PEA PME"]
    cto: ["Compte titres", "CTO"]
    av: ["Assurance vie", "Contrat"]
    per: ["PER", "Plan Épargne Retraite"]

  colonnes_attendues:       # Correspondance entre noms de colonnes et rôles
    - nom: "isin"
      patterns: ["ISIN", "Code ISIN", "Code"]
    - nom: "libelle"
      patterns: ["Libellé", "Désignation", "Valeur"]
    - nom: "quantite"
      patterns: ["Qté", "Quantité", "Nombre de parts"]
    - nom: "valorisation"
      patterns: ["Valorisation", "Montant", "Valeur EUR", "Total"]
    - nom: "cours"
      patterns: ["Cours", "Prix unitaire", "VL"]

  filtres_lignes:
    exclure_si_contient: ["Total", "Sous-total", "TOTAL", "Solde"]
    inclure_si_isin: true   # Ne garder que les lignes contenant un ISIN reconnu

regex_isin: '\b([A-Z]{2}[A-Z0-9]{9}[0-9])\b'
regex_montant_eur: '(\d{1,3}(?:[\s.,]\d{3})*(?:[,.]\d{2})?)\s*€?'

post_traitement:
  normalise_devises: true
  conversion_si_non_eur: false   # S20 : pas de conversion auto, on flag
```

### Conseils de calibration

1. **Signatures** : utilisez le texte tel qu'il apparaît dans le header PDF (majuscules souvent).
   Ajoutez plusieurs variantes (acronyme, nom complet, ORIAS).
2. **Colonnes** : si les colonnes de votre relevé ont des noms différents, ajoutez-les à `patterns`.
3. **Filtres** : excluez les lignes "Total", "TOTAL PORTEFEUILLE", etc., pour éviter les doublons.
4. **Test rapide** : `pytest tests/test_detecteur_emetteur.py -v` après ajout du template.

### Tester un template

```python
# Script de test rapide (à lancer en dehors des tests pytest)
from src.import_patrimoine.parseur_template import charger_template, appliquer_template

tpl = charger_template("mon_emetteur.yaml")
# Créer un tableau synthétique représentant les données extraites
tableaux_bruts = [[
    ["ISIN", "Libellé", "Quantité", "Valorisation"],
    ["FR0010315770", "Lyxor CAC 40", "100", "5 000,00"],
    ["LU0908501842", "Amundi MSCI World", "50", "12 500,00"],
]]
lignes = appliquer_template(tpl, "", tableaux_bruts, "test.pdf", via_ocr=False)
for l in lignes:
    print(l.nom_actif, l.valorisation_eur, l.confiance)
```

---

## Score de confiance

| Critère | Points |
|---|---|
| Template matché | +40 |
| ISIN extrait et valide (format ISO 6166) | +25 |
| Valorisation parsée sans ambiguïté | +20 |
| Enveloppe identifiée | +10 |
| Texte natif (pas d'OCR) | +5 |
| **Total maximum** | **100** |

- Score ≥ 80 → **Vert** (extraction fiable)
- Score 50–79 → **Orange** (à vérifier)
- Score < 50 → **Rouge** (incertain, saisie manuelle recommandée)

---

## OCR (PDF scannés)

Si le PDF contient moins de 100 caractères de texte natif, le module détecte un probable scan
et tente l'OCR via Tesseract (langue `fra`).

**Prérequis système** :
```bash
# Ubuntu / Debian
sudo apt-get install tesseract-ocr tesseract-ocr-fra poppler-utils

# macOS (Homebrew)
brew install tesseract tesseract-lang
```

**Dépendances Python** :
```bash
pip install "bogleheads-fr[pdf]"
# ou
pip install pdfplumber pytesseract pdf2image
```

Si Tesseract est absent au runtime, le module affiche un message clair et ne plante pas.
La revue manuelle est alors requise.

---

## Audit et traçabilité

Chaque import génère une entrée dans `data/missions/{mission_id}/audit.json` :
```json
[
  {
    "timestamp": "2026-04-27T14:00:00+00:00",
    "import": {
      "pdf_nom": "releve_bourse_direct.pdf",
      "pdf_hash": "sha256...",
      "emetteur_detecte": "Bourse Direct",
      "template_utilise": "bourse_direct",
      "lignes_validees": [...],
      "lignes_rejetees": [...]
    }
  }
]
```

Ce journal est **append-only** : chaque import est ajouté à la fin, jamais écrasé.

---

## Privacy

- Les PDF déposés sont traités en mémoire (fichier temporaire dans `output/` supprimé après extraction)
- Aucun PDF n'est jamais commité dans le dépôt (`.gitignore`)
- Les données extraites sont persistées uniquement dans `data/missions/{id}/` (gitignored)

---

## Roadmap S21/S22

- Élargissement des émetteurs (ING, Hello Bank, Trade Republic, Suravenir, Cardif…)
- Calibration fine des templates par retour dogfood
- Support des relevés multi-pages avec en-tête récurrent
- Conversion automatique des devises étrangères (option)
