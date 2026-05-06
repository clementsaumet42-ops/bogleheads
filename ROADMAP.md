# Roadmap Sextant — plan post-renommage

> Document de référence figé. À redonner tel quel à un nouvel assistant
> (Claude Opus, Copilot, autre) si la conversation actuelle est perdue.
> Dernière mise à jour : 2026-05-06.

---

## Contexte produit (rappel non négociable)

**Sextant** est un atelier de mission patrimoniale **Bogleheads** pour
**experts-comptables inscrits CIF**. Voir `README.md` pour le positionnement
complet (gravé dans le marbre).

Trois frictions à résoudre :
1. Fiscalité d'enveloppe (PEA, AV, CTO, PEE/PER, holding IS, cap IS)
2. Coût caché du rebalancement (privilégier les flux entrants vs arbitrages taxables)
3. Conformité CIF (DER, LM, RAA MIF II, signature eIDAS, journal)

L'IS n'est **qu'une brique** parmi d'autres. Le cœur produit, c'est piloter
un patrimoine indiciel diversifié en limitant la friction fiscale et en
optimisant frais + fiscalité + allocation.

---

## État au moment où ce plan est écrit

- ✅ PR de renommage "HoldIS Advisor" → **Sextant** ouverte/mergée
- ✅ `README.md` réécrit
- ✅ `pages/00_Mission_CGP.py` → `pages/00_Mission_EC.py`
- ✅ Cas dogfood `dogfood/cas_rousseau/` prêt (5 relevés MD + grille 18 pièges + fixture YAML)
- 🚧 `src/mission/` encore au stade squelette
- 🚧 Vocabulaire "CGP" résiduel à purger dans `src/`, `pages/`, `dogfood/`
- 🚧 Personne n'a encore tourné le dogfood de bout en bout

---

## Plan en 3 blocs

### Bloc A — Mesurer (avant de coder quoi que ce soit)

> Tu ne peux pas rendre efficace ce que tu n'as pas mesuré.

**Livrables :**

1. **Santé des tests post-pivot chiffrée**
   - Lancer `pytest` et noter exactement passed / skipped / failed
   - Mettre à jour la ligne du `CHANGELOG.md` qui dit encore "X passed, Y skipped"
   - Lister les tests qui restent rouges et la raison

2. **Dogfood Rousseau-Marchand de bout en bout** (responsabilité humaine, pas IA)
   - Convertir les 5 `.md` en PDF (voir section "Comment générer les PDF" plus bas)
   - Lancer `streamlit run app.py`
   - Suivre les 6 étapes du `dogfood/cas_rousseau/README.md`
   - Remplir **5 fichiers** dans `dogfood/cas_rousseau/` :
     - `grille_scoring.md` (existe déjà — 18 pièges Détecté/Partiel/Manqué)
     - `ruptures_parcours.md` (à créer — chaque sortie d'app forcée)
     - `ressaisies.md` (à créer — chaque champ retapé)
     - `calculs_non_verifiables.md` (à créer — chaque chiffre opaque)
     - `livrables_a_retoucher.md` (à créer — ce que tu n'enverrais pas en l'état)

3. **Synthèse écrite**
   - Top 5 des ruptures les plus douloureuses
   - Top 3 des calculs les moins défendables
   - Cette synthèse devient la liste de courses priorisée des Blocs B et C

⏱ **~1 jour** humain (dogfood) + ~2h IA (synthèse).

**Sans le Bloc A, le reste est de l'architecture en chambre.**

---

### Bloc B — Propre & Logique

#### B.1 — Finir `src/mission/`

**Le squelette est marqué 🚧 dans le README. Tant qu'il flotte, tout flotte.**

- Lifecycle complet : créer → étapes → snapshot → archive ZIP
- Persistance robuste (rétro-compatibilité S16 préservée — les missions
  existantes doivent rester chargeables sans erreur)
- Une seule source de vérité pour l'état mission (pas de duplication entre
  `EtatMission` et `session_state`)
- Test d'intégration : un cycle de vie complet de mission de bout en bout

**Pré-requis :** deep research sur le squelette actuel pour proposer un plan
d'implémentation précis avant de lancer l'agent codeur.

#### B.2 — Purge vocabulaire "CGP" → "EC-CIF"

Dette laissée par la PR de renommage Sextant.

- Commentaires, docstrings, libellés UI dans `src/`
- Variables et fonctions qui contiennent `cgp` → `ec` ou neutre
- `dogfood/cas_rousseau/` : "tool CGP" → "Sextant"
- Critère de succès : `grep -ri "cgp\|CGP" src/ pages/ dogfood/` → 0 occurrence
  (hors `archive/` qui reste figé)

⏱ **~30 min** d'agent codeur, peut tourner en parallèle du Bloc A.

#### B.3 — Refactor `src/pdf_builder.py` (conditionnel)

98 KB dans un seul fichier = dette future si on l'ignore.

- Découper en `src/livrables/pdf/` : un module par section (page de garde,
  diagnostic, allocation, plan, annexes)
- Aucune régression visuelle (les tests `test_pdf_visual_regression.py`
  doivent passer à l'identique)

**Ne se fait que si le Bloc A remonte que c'est une douleur réelle.**

⏱ **~3-5 jours** d'agent codeur en plusieurs PR séquentielles (B.1, puis B.2,
puis B.3 conditionnel).

---

### Bloc C — Efficace : rebalancement par les flux

> La promesse n°2 du README. C'est ce qui différencie Sextant de n'importe
> quel optimiseur d'allocation.

C'est le **seul bloc où on ajoute du métier**. Là se joue la valeur produit :
*"un bon rebalancement se fait d'abord par les flux entrants"*.

**Livrables :**

- Algorithme : prend `(allocation cible, allocation actuelle, flux entrants
  prévus 12 mois)` → produit `(cascade trimestrielle de versements ciblés
  sur les enveloppes sous-pondérées)`
- Déclenche un **arbitrage** (= vente potentiellement taxable) **uniquement** si :
  - l'écart à la cible dépasse un seuil paramétrable, ET
  - en privilégiant d'abord les enveloppes sans friction fiscale
    (PEA avec antériorité, AV > 8 ans, PEE débloqué)
- Chiffrage explicite du **coût fiscal évité** vs rebalancement naïf →
  c'est le ROI défendable que l'EC montre au client en revue annuelle
- Intégration dans `pages/22_Plan_Execution.py`
- Tests : 3 scénarios (faible écart / écart moyen / forte dérive) avec
  golden files

⏱ **~1 semaine** d'agent codeur en 2-3 PR (algo / UI / tests E2E).

---

## Ordre recommandé

```
Maintenant     →  PR Sextant mergée (✅)
     ↓
Cette semaine  →  Bloc A (humain : 1 jour dogfood + synthèse)
                  + Bloc B.2 en parallèle (agent : purge CGP)
     ↓
Ensuite        →  Bloc B.1 (finir src/mission/)
     ↓
Puis           →  Bloc C (rebalancement par flux)
     ↓
Conditionnel   →  Bloc B.3 (refactor pdf_builder, si A remonte la douleur)
```

**Justification de l'ordre :**

- **A en premier** : sans mesure, on code des solutions à des problèmes
  imaginés.
- **B avant C** : il faut un orchestrateur solide avant de greffer une
  nouvelle brique métier dessus.
- **B.3 en dernier** : c'est de la dette pure, pas de la valeur. Ne se fait
  que si A remonte que c'est douloureux.

---

## Comment générer les PDF du cas Rousseau pour dogfood

Les 5 fichiers Markdown se trouvent dans
`dogfood/cas_rousseau/pdf_a_generer/`. Ils doivent être convertis en PDF
manuellement (les PDF générés ne sont **pas** committés — voir `.gitignore`).

**Cible :** créer un dossier local `dogfood/cas_rousseau/pdf_generes/`
(gitignoré) et y déposer les 5 PDF.

**Méthodes possibles, par ordre de simplicité :**

### Méthode 1 — Pandoc en ligne de commande (recommandée)

```bash
# Installation préalable (une fois)
brew install pandoc                      # macOS
brew install --cask basictex             # ou: brew install mactex

# Génération des 5 PDF
mkdir -p dogfood/cas_rousseau/pdf_generes
cd dogfood/cas_rousseau/pdf_a_generer
for f in *.md; do
  pandoc "$f" -o "../pdf_generes/${f%.md}.pdf" \
    --pdf-engine=pdflatex \
    -V geometry:margin=2cm \
    -V mainfont="Helvetica"
done
```

Avantage : reproductible, scriptable, mêmes PDF à chaque exécution.

### Méthode 2 — Typora (ergonomique pour itérer)

1. Ouvrir chaque `.md` dans [Typora](https://typora.io)
2. Fichier → Exporter → PDF
3. Sauvegarder dans `dogfood/cas_rousseau/pdf_generes/`

Avantage : aperçu visuel direct, mise en forme contrôlable.

### Méthode 3 — VS Code + extension "Markdown PDF"

1. Installer l'extension `yzane.markdown-pdf`
2. Ouvrir un `.md`, clic droit → "Markdown PDF: Export (pdf)"
3. Répéter pour les 5 fichiers

Avantage : reste dans l'éditeur de code.

### Méthode 4 — Pages / Word (manuel)

1. Ouvrir le `.md` dans un éditeur de texte, copier
2. Coller dans Pages (macOS) ou Word
3. Fichier → Exporter au format PDF

Avantage : aucune installation. Inconvénient : moins reproductible.

### Méthode 5 — Navigateur (rapide, sans install)

1. Ouvrir le `.md` dans GitHub (rendu Markdown natif)
2. Cmd+P / Ctrl+P → "Enregistrer au format PDF"

Avantage : zéro install. Inconvénient : on garde la chrome GitHub
(barre de nav, footer) si on n'imprime pas la zone seule.

**Vérification après génération :**

```bash
ls -lh dogfood/cas_rousseau/pdf_generes/
# Doit afficher 5 fichiers .pdf, taille > 10 KB chacun
```

Les 5 PDF sont ensuite déposés dans la page Streamlit `24_Import_Patrimoine`.

---

## Contraintes inviolables (tous blocs)

- ❌ **Aucun appel cloud / LLM** — Sextant tourne 100% en local
- ❌ **Aucun emoji dans l'UI** rendue (charte S19)
- ❌ **Aucun merge silencieux** — toute validation reste explicite
- ❌ **Aucune suppression de tests** — au pire `@pytest.mark.skip`
- ✅ **Rétro-compatibilité** des missions existantes à chaque PR
- ✅ **Tests verts** avant chaque merge
- ✅ **`archive/` ne se touche plus** — c'est l'historique git, point.

---

## Pour redémarrer une nouvelle conversation

Donne ce fichier au nouvel assistant avec ce préambule :

> Voici le plan figé du projet Sextant (repo
> `clementsaumet42-ops/bogleheads`). Lis-le entièrement avant toute
> proposition. Le `README.md` du repo est la source de vérité du
> positionnement produit. Ne propose rien qui s'en écarte.
>
> Dis-moi où on en est par rapport à ce plan et propose la prochaine étape.
