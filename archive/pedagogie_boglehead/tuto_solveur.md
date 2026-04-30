# Tutoriel Solveur Excel — Optimisation Asset Location Boglehead FR

> **Public cible** : CGP/CIF, conseillers patrimoniaux, investisseurs autonomes avancés.
> **Prérequis** : Notions de tableur Excel, concepts de base du portefeuille Boglehead.

---

## 1. Pourquoi un Solveur ? Le problème d'asset location

### 1.1 L'intuition

Vous avez 6 enveloppes fiscales (PEA, PER, PEE, CTO, CTO IS, Contrat Cap IS) et 60 ETF disponibles. La question est :

> **Quel ETF mettre dans quelle enveloppe pour maximiser le capital net après impôts ?**

Ce problème a une solution analytique simple pour 2 enveloppes et 2 classes d'actifs. Avec 6 enveloppes et 60 ETF, on a potentiellement 360 variables de décision — le Solveur devient indispensable.

### 1.2 Les règles intuitives ne suffisent plus

Les règles heuristiques Boglehead ("actions en PEA, obligations en PER") sont une bonne approximation pour les cas simples. Mais elles ne prennent pas en compte :

- La **pondération quantitative** : combien exactement en PEA vs CTO ?
- Les **plafonds de saturation** : que faire quand le PEA est plein ?
- Les **interactions fiscales** : CEHR + CDHR sur les dividendes CTO modifient le calcul
- Le **mark-to-market IS** : l'impact annuel du CTO IS sur la VAN est sous-estimé intuitivement
- La **contrainte d'allocation** : respecter ±5% de la cible tout en optimisant l'enveloppe

---

## 2. Vocabulaire d'optimisation

### 2.1 Programmation Linéaire (LP — Linear Programming)

Un problème LP est de la forme :

```
Maximiser : c^T × x
Sous contraintes : A × x ≤ b
                  x ≥ 0
```

Où `x` est le vecteur des variables de décision (ici, les montants x_ij).

**Propriété clé** : Si la fonction objectif et toutes les contraintes sont linéaires en `x`, la solution optimale se trouve en un sommet du polytope faisable (simplexe).

### 2.2 Programmation Quadratique (QP)

Si l'on ajoute la minimisation de la variance du portefeuille (approche Markowitz) :

```
Minimiser : x^T × Σ × x   (variance)
Maximiser : μ^T × x        (espérance)
```

La fonction objectif devient quadratique. Le Solveur GRG non-linéaire d'Excel peut résoudre de petits QP. Pour les grands problèmes, utiliser OpenSolver avec GLPK.

### 2.3 Programmation Entière (MILP — Mixed Integer Linear Programming)

Si l'on ajoute des variables binaires (décision d'ouvrir ou non une enveloppe) :

```
y_PER ∈ {0, 1}   : 1 si on ouvre/utilise le PER, 0 sinon
x_ij ≤ M × y_j   : On ne peut investir dans l'enveloppe j que si y_j = 1
```

Le MILP nécessite OpenSolver (Solveur intégré Excel ne supporte pas les MILP robustes).

---

## 3. Formulation mathématique du problème d'asset location

### 3.1 Variables de décision

Soit :
- `i ∈ {1, ..., n}` l'ensemble des ETF (n ≈ 60)
- `j ∈ {PEA, PER, PEE, CTO, CTO_IS, Cap_IS}` l'ensemble des enveloppes (6)
- `x_ij ≥ 0` : montant en € de l'ETF i alloué à l'enveloppe j

### 3.2 Fonction objectif

On maximise la Valeur Actuelle Nette après impôts sur l'horizon H :

```
MAX VAN = Σ_i Σ_j VAN_ij(x_ij)
```

Où `VAN_ij(x_ij)` est la VAN nette après impôts de placer x_ij € de l'ETF i dans l'enveloppe j :

```
VAN_ij(x_ij) = x_ij × [(1 + r_i)^H - 1] × (1 - τ_j)
```

Avec :
- `r_i` : rendement annuel attendu de l'ETF i
- `H` : horizon de placement en années
- `τ_j` : taux effectif d'imposition à la sortie de l'enveloppe j

**Taux effectifs τ_j (simplifiés) :**
| Enveloppe j | τ_j (après 5 ans) |
|---|---|
| PEA (≥5 ans) | 18,6% (PS seulement) |
| PER | ~18,6% (PS sur gains, TMI retraite sur capital) |
| PEE | 18,6% (PS seulement) |
| CTO perso | 31,4% (PFU) |
| CTO IS | 15-25% (IS) + impact MTM |
| Contrat Cap IS | 15-25% (IS) sur base forfaitaire |

### 3.3 Contraintes

**C1 — Eligibilité des ETF par enveloppe :**
```
x_ij = 0  si ETF i non éligible à l'enveloppe j
```
Exemples :
- `x_IWDA_PEA = 0` (iShares MSCI World physique → non éligible PEA)
- `x_CW8_Cap_IS = 0` (ETF swap PEA → non disponible en assurance-vie IS)

**C2 — Plafonds de versement :**
```
Σ_i x_i,PEA ≤ 150 000 - encours_PEA_actuel
```

**C3 — Allocation cible (tolérance ±5%) :**
```
(α_k - δ) × P ≤ Σ_{i ∈ classe_k} Σ_j x_ij ≤ (α_k + δ) × P
```
Où α_k est l'allocation cible de la classe k, δ = 0.05 (tolérance), P = patrimoine total.

**C4 — Budget total :**
```
Σ_i Σ_j x_ij = P   (tout le patrimoine est alloué)
```

**C5 — Non-négativité :**
```
x_ij ≥ 0   ∀ i, j
```

**C6 — Plafond par ETF (optionnel) :**
```
Σ_j x_ij ≤ concentration_max × P   (ex: max 30% dans un seul ETF)
```

### 3.4 Forme matricielle compacte

En notant x le vecteur de toutes les variables `x_ij` (dimensions n×6 aplaties) :

```
MAX  c^T × x
s.c. A_elig × x = 0    (eligibilité)
     A_plaf × x ≤ b    (plafonds)
     A_alloc × x ≤ u   (allocation max)
     A_alloc × x ≥ l   (allocation min)
     1^T × x = P       (budget)
     x ≥ 0
```

Ce problème LP a une solution optimale unique (ou un ensemble convexe de solutions) trouvable en temps polynomial par l'algorithme du simplexe.

---

## 4. Exemple complet — Profil 3 (Dirigeant PME avec Holding IS)

### 4.1 Données du profil

- **Patrimoine financier total** : 3 000 000 €
- **Enveloppes** :
  - PEA : 150 000 € (saturé — plafond atteint)
  - PER : 80 000 €
  - CTO perso : 400 000 €
  - CTO IS (Holding) : 500 000 €
  - Contrat Cap IS (Holding) : 1 200 000 €
- **Allocation cible** : 55% actions, 20% obligations, 10% immo, 8% or, 7% liquidités
- **TMI** : 45% + CEHR 4% + CDHR applicable
- **Horizon** : 15 ans
- **Rendement supposé** : 6%/an

### 4.2 Structure du tableau de décision dans Excel

Créer un tableau avec :

| Colonne | Contenu |
|---|---|
| A | Nom de l'ETF |
| B | Classe d'actifs |
| C-H | x_ij pour chaque enveloppe (PEA, PER, CTO, CTO_IS, Cap_IS, PEE) |
| I | Total alloué = SOMME(C:H) |
| J | Allocation cible (€) |
| K | Écart allocation = I - J |

### 4.3 Construction de la fonction objectif

En cellule M1 (cellule objectif du Solveur) :

```excel
=SUMPRODUCT(C2:C61*VAN_PEA) + SUMPRODUCT(D2:D61*VAN_PER) + 
 SUMPRODUCT(E2:E61*VAN_CTO) + SUMPRODUCT(F2:F61*VAN_IS) +
 SUMPRODUCT(G2:G61*VAN_CapIS) + SUMPRODUCT(H2:H61*VAN_PEE)
```

Où VAN_PEA pour l'ETF i = `((1 + r_i)^H - 1) × (1 - 0.186)` (PS seulement après 5 ans).

### 4.4 Résultat attendu du Solveur

Pour le Profil 3, la solution optimale typique est :

| Enveloppe | Classe privilégiée | Justification |
|---|---|---|
| Contrat Cap IS (1,2M€) | **Actions mondiales capitalisantes** | Pas de MTM, capitalisation complète, IS faible |
| PEA (150k€ saturé) | **Actions mondiales PEA** | Exonération IR complète après 5 ans |
| PER (80k€) | **Obligations + Actions non PEA** | Déduction 45% à l'entrée |
| CTO IS (500k€) | **Monétaire + Obligations CT** | MTM peu impactant sur assets à faible TRI |
| CTO perso (400k€) | **Or + Complément actions** | Flexibilité, liquidité |

**Gain fiscal estimé vs naïf CTO** : +20 à +30% de capital net sur 15 ans.

---

## 5. Tutoriel pas-à-pas Excel Solveur

### Étape 1 — Activer le Solveur

**Windows :**
1. `Fichier` → `Options` → `Compléments`
2. En bas : `Gérer : Compléments Excel` → `Atteindre...`
3. Cocher ☑ `Solveur` → `OK`
4. Onglet `Données` → groupe `Analyse` → bouton `Solveur`

**Mac :**
1. `Excel` (menu Apple) → `Préférences` → `Compléments`
2. Cocher ☑ `Solveur` → `OK`
3. Menu `Outils` → `Solveur`

### Étape 2 — Préparer la feuille de calcul

```
Feuille "Optimisation_P3" :
  Colonne A  : Liste des 60 ETF (ISIN + Nom)
  Colonnes B-G : Variables x_ij (initialisées à P/n = 50 000€ chacune)
  Ligne 62   : SOMME de chaque colonne (plafond enveloppe)
  Ligne 63   : Allocation par classe = SOMME.SI sur colonne Classe
  Cellule M1 : Fonction objectif = VAN totale nette après impôts
```

### Étape 3 — Paramétrer le Solveur

Ouvrir le Solveur (Données → Solveur) :

```
Cellule objectif        : $M$1
À maximiser             : ● Valeur maximale
Cellules variables      : $B$2:$G$61  (360 variables x_ij)
```

### Étape 4 — Ajouter les contraintes

Cliquer `Ajouter` pour chaque contrainte :

```
[1] Eligibilité  : $B$2:$G$61 >= 0        (non-négativité)
[2] Budget       : =SOMME($B$2:$G$61) = 3000000
[3] Plafond PEA  : =SOMME($B$2:$B$61) <= 0       (PEA saturé)
[4] Alloc actions min : =SOMME.SI(classe,"Actions",$B$2:$G$61) >= 1500000  (50%)
[5] Alloc actions max : =SOMME.SI(classe,"Actions",$B$2:$G$61) <= 1800000  (60%)
[6] Alloc oblig  : [similaire pour obligations 15%-25%]
[7] Non-CTO_IS ETF growth : [cellules correspondantes = 0 si ETF capitalisant dans CTO IS]
```

### Étape 5 — Choisir la méthode de résolution

- **GRG Nonlinear** : Pour une fonction objectif non-linéaire (avec MTM IS approximé)
- **Simplex LP** : Pour la version linéarisée (taux fixes)
- **Evolutionary** : En dernier recours si les autres échouent

Cocher ☑ `Rendre les variables sans contrainte non négatives`

### Étape 6 — Lancer et interpréter

Cliquer `Résoudre`.

**Si succès** :
- `Le Solveur a trouvé une solution` → Garder la solution
- Vérifier la cohérence : aucun ETF capitalisant en CTO IS, PEA ≤ 150k€

**Si échec** :
- Vérifier l'absence de contradiction entre contraintes
- Relaxer les contraintes d'allocation (±10% au lieu de ±5%)
- Réinitialiser les variables à des valeurs différentes

---

## 6. OpenSolver — Pour les grands problèmes

### 6.1 Pourquoi OpenSolver ?

Le Solveur intégré Excel est limité à **200 variables** et **100 contraintes**. Pour notre problème (360 variables, ~50 contraintes), OpenSolver est nécessaire.

| Critère | Solveur Excel | OpenSolver |
|---|---|---|
| Variables | 200 max | Illimité |
| Contraintes | 100 max | Illimité |
| MILP | Non | Oui (CBC, GLPK) |
| Algorithmes | GRG, Simplex, Evol. | CBC, GLPK, Gurobi, CPLEX |
| Prix | Gratuit (inclus) | Gratuit (CBC/GLPK) |

### 6.2 Installation

1. Télécharger sur **https://opensolver.org** → Release
2. Extraire l'archive → dossier `OpenSolver`
3. Copier dans :
   - Windows : `C:\Users\[user]\AppData\Roaming\Microsoft\Excel\XLSTART\`
   - Mac : `~/Library/Group Containers/UBF8T346G9.Office/User Content/Startup/Excel/`
4. Redémarrer Excel → onglet `OpenSolver` apparaît

### 6.3 Utilisation

L'interface est similaire au Solveur standard :
1. Définir la cellule objectif (même cellule)
2. Ajouter les contraintes (même syntaxe)
3. Choisir le solveur : **CBC** pour LP/MILP, **CPLEX** si disponible
4. `Solve` → résout sans limite de taille

---

## 7. Troubleshooting

### Problème : "Aucune solution réalisable"

**Cause probable** : Les contraintes se contredisent.

**Diagnostic** :
1. Retirer toutes les contraintes sauf Budget + Non-négativité
2. Ajouter les contraintes une par une
3. Identifier celle qui rend le problème infaisable

**Solution** :
- Vérifier que `Σ plafonds_j ≥ Patrimoine_total`
- Relaxer les contraintes d'allocation (±10% au lieu de ±5%)
- Vérifier que l'allocation cible est réalisable avec les enveloppes disponibles

### Problème : "Solution sous-optimale / convergence lente"

**Cause probable** : Optimum local avec GRG Non-linéaire.

**Solution** :
- Cocher ☑ `Utiliser la mise à l'échelle automatique`
- Cocher ☑ `Ignorer la contrainte d'entiers` (si applicable)
- Utiliser l'option `Recherche aléatoire` avec 100 essais
- Passer à OpenSolver avec CBC (global pour LP)

### Problème : "Les ETF IS reçoivent peu d'allocation"

**Comportement attendu** : Le Solveur "fuit" le CTO IS à cause du mark-to-market.

**Vérification** : Calculer manuellement la VAN IS avec MTM pour confirmer que c'est bien inférieur au Contrat Cap IS. Si oui, la solution est correcte.

### Problème : "Le PEA n'est pas saturé dans la solution"

**Cause** : La contrainte d'allocation empêche de tout mettre en PEA.

**Solution** : Ajouter une contrainte `x_i,PEA = plafond_PEA_restant` pour forcer la saturation du PEA avant d'optimiser le reste.

---

## 8. Conseils pour le CGP

### 8.1 Sensibilité aux hypothèses

La solution du Solveur dépend fortement des hypothèses de rendement. Toujours :
1. Tester avec rendement pessimiste (3%), central (6%), optimiste (9%)
2. Présenter au client une fourchette de résultats, pas un chiffre unique
3. Refaire l'optimisation annuellement (ou après une variation de marché > 20%)

### 8.2 Validation manuelle obligatoire

Le Solveur est un outil de calcul, pas un oracle. Vérifier :
- La solution respecte les règles fiscales (éligibilité, plafonds)
- Elle est cohérente avec les objectifs du client (liquidité, horizon)
- Elle prend en compte les contraintes non modélisées (succession, divorce, déménagement)

### 8.3 Documentation de la recommandation

Conserver systématiquement :
- Le fichier Excel avec la solution du Solveur
- Les hypothèses utilisées (rendement, TMI retraite, TME contrat cap IS)
- La date de l'optimisation
- La signature du client sur la recommandation personnalisée

---

## 9. Références et ressources

- **Opensolver.org** : Documentation OpenSolver
- **William Bernstein** — *The Four Pillars of Investing* : Fondements Boglehead
- **Larry Swedroe** — *The Only Guide to Alternative Investments You'll Ever Need* : Règles de rebalancement
- **AMF** — *Guide de l'investisseur* : Réglementation française
- **CGI (Code Général des Impôts)** : art. 163 quinquies D (PEA), 209-0 A (MTM IS), 238 septies E (Contrat Cap IS)
- **Boglehead Wiki** : https://www.bogleheads.org/wiki/Asset_location
