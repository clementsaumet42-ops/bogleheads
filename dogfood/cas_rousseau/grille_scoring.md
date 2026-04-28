# Grille de scoring — Cas Rousseau-Marchand

> Usage interne dogfood uniquement. Données 100 % fictives.  
> Cocher les cases après chaque session de test du tool.

---

## Mode d'emploi

Pour chaque piège :
- `[x] Détecté` : le tool l'identifie correctement et propose la bonne action
- `[x] Partiellement` : détection partielle ou suggestion incomplète
- `[x] Manqué` : le tool ne détecte pas le piège

Criticité : **Critique** = bloquant MIF II ou fiscal / **Important** = recommandation non optionnelle / **Nice-to-have** = valeur ajoutée complémentaire

---

## Fiscalité (pièges 1 à 7)

---

### Piège 1 — TMI variable Antoine (41 % hors bonus / 45 % avec bonus)

**Description :** Antoine perçoit un salaire brut de 180 000 € + bonus variable entre 30 000 € et 50 000 €. Selon l'année, son RFR oscille entre ~218 400 € (sans bonus) et ~268 400 € (avec bonus max). La TMI peut donc passer de 41 % à 45 %. Tout conseil fiscal basé sur un TMI fixe est inexact.

**Ce que le tool doit détecter / proposer :** Afficher une fourchette de TMI (41-45 %) plutôt qu'un point fixe. Alerter que toute optimisation (PER, AV, donation) doit être simulée sur les deux hypothèses.

**Ou dans l'UI :** Page S04 Profil (champ TMI), section Fiscalité du rapport PDF, alerte audit.

**Criticite :** Critique

- [ ] Détecté
- [ ] Partiellement
- [ ] Manqué

**Notes :**

---

### Piège 2 — 3,5 parts fiscales : étudiante rattachée ou détachée ?

**Description :** Léa (née 2007-02-10, étudiante) est rattachée au foyer fiscal → 3,5 parts. Si elle se détache et demande l'aide au logement, le foyer tombe à 3 parts. La différence d'impôt est significative à TMI 41 %.

**Ce que le tool doit détecter / proposer :** Simuler l'impact du détachement fiscal de Léa. Comparer : économie IR foyer vs allocations/aides auxquelles Léa aurait droit en déclaration séparée.

**Ou dans l'UI :** Page S04 Profil (section enfants), page Fiscalité, alerte audit.

**Criticite :** Important

- [ ] Détecté
- [ ] Partiellement
- [ ] Manqué

**Notes :**

---

### Piège 3 — PER Antoine : plafond cumulé avec report 3 ans non utilisés

**Description :** Antoine n'a pas utilisé son plafond PER les 3 dernières années. Le plafond cumulé reportable peut atteindre 4 × 32 000 € = 128 000 € en théorie. Une déduction exceptionnelle à TMI 45 % (année de bonus) représente un gain fiscal maximal.

**Ce que le tool doit détecter / proposer :** Calculer le plafond disponible incluant les reports N-1, N-2, N-3. Signaler l'opportunité de versement exceptionnel l'année du bonus.

**Ou dans l'UI :** Page S04 Profil (PER), section Fiscalité rapport PDF, recommandation S18.

**Criticite :** Critique

- [ ] Détecté
- [ ] Partiellement
- [ ] Manqué

**Notes :**

---

### Piège 4 — PER Camille TNS : plafond spécifique 10 % bénéfice + 15 % au-dessus du PASS

**Description :** Camille est avocate associée (TNS BNC). Son plafond PER est calculé différemment : 10 % du bénéfice net + 15 % de la fraction du bénéfice entre 1 et 8 PASS. À 140 000 € de bénéfice, ce plafond est supérieur au plafond salarié.

**Ce que le tool doit détecter / proposer :** Appliquer la formule TNS et non le plafond salarié standard. Afficher le calcul détaillé. Signaler si les versements réels sont inférieurs au plafond disponible.

**Ou dans l'UI :** Page S04 Profil (statut TNS), section PER rapport PDF, alerte audit.

**Criticite :** Critique

- [ ] Détecté
- [ ] Partiellement
- [ ] Manqué

**Notes :**

---

### Piège 5 — AV Antoine > 15 ans vs Camille < 8 ans : ordre optimal de rachat

**Description :** En cas de besoin de liquidités, l'AV Generali d'Antoine (> 15 ans) bénéficie de l'abattement de 9 200 € annuel. L'AV Linxea de Camille est à < 8 ans jusqu'au 05/09/2026 (abattement 4 600 €). Après cette date, abattement 9 200 €. L'ordre de rachat impacte la fiscalité effective.

**Ce que le tool doit détecter / proposer :** Comparer le coût fiscal d'un rachat sur l'une ou l'autre AV selon la date du rachat. Recommander l'ordre optimal (Antoine en premier si avant septembre 2026, puis Camille après le 05/09/2026).

**Ou dans l'UI :** Section Assurance-vie rapport PDF, scénario de rachat S17, alerte audit.

**Criticite :** Critique

- [ ] Détecté
- [ ] Partiellement
- [ ] Manqué

**Notes :**

---

### Piège 6 — Versements AV avant 70 ans : anticipation transmission

**Description :** Antoine aura 70 ans en 2043. Tout versement sur une AV avant ses 70 ans bénéficie de l'exonération de 152 500 € par bénéficiaire (art. 990 I CGI). Après 70 ans, seuls 30 500 € sont exonérés pour l'ensemble des bénéficiaires (art. 757 B).

**Ce que le tool doit détecter / proposer :** Alerter si le calendrier de versements risque de dépasser 70 ans. Quantifier l'économie de droits de succession en versant avant/après 70 ans. Vérifier les clauses bénéficiaires de l'AV Generali.

**Ou dans l'UI :** Section Transmission rapport PDF, alerte audit, page S04 (date de naissance).

**Criticite :** Important

- [ ] Détecté
- [ ] Partiellement
- [ ] Manqué

**Notes :**

---

### Piège 7 — IFI : patrimoine immobilier net > 1,3 M€ → assujettissement

**Description :** RP Lyon (1 600 000 € - 30 % abattement = 1 120 000 €) + RS Annecy (520 000 € - crédit 180 000 € = 340 000 €) → IFI net ~ 1 460 000 € > seuil 1 300 000 €. IFI estimé ~3 700 €/an (barème progressif).

**Ce que le tool doit détecter / proposer :** Calculer automatiquement l'assiette IFI nette (après abattement RP 30 % et déduction des crédits immobiliers). Comparer au seuil 1,3 M€. Afficher le montant estimé de l'IFI et les leviers de réduction (dons, SCPI déficit foncier, dette IFI-déductible).

**Ou dans l'UI :** Page S04 Profil (immobilier), section Fiscalité rapport PDF, alerte audit.

**Criticite :** Critique

- [ ] Détecté
- [ ] Partiellement
- [ ] Manqué

**Notes :**

---

## Conformité / MIF II (pièges 8 à 10)

---

### Piège 8 — Profil Camille avocate fiscaliste = client averti ?

**Description :** Camille est avocate fiscaliste associée. Sa profession implique une connaissance approfondie de la fiscalité, mais pas nécessairement des produits financiers complexes au sens MIF II. Le statut "client averti" doit être documenté par un questionnaire spécifique, pas seulement par la profession.

**Ce que le tool doit détecter / proposer :** Signaler que la qualification "client averti" ne peut pas être déduite automatiquement de la profession. Proposer le formulaire de demande de reclassification MIF II et documenter les critères (nombre de transactions, portefeuille > 500 000 €, expérience professionnelle dans le secteur financier).

**Ou dans l'UI :** Page S03 Profilage MIF II, alerte audit, section Conformité DER.

**Criticite :** Critique

- [ ] Détecté
- [ ] Partiellement
- [ ] Manqué

**Notes :**

---

### Piège 9 — H2O Multibonds dans AV Generali : fonds historiquement suspendu

**Description :** Le fonds H2O Multibonds (FR0010923375) a été suspendu de 2020 à 2023 suite à des problèmes de liquidité sur des actifs illiquides (obligations Windhorst). La valorisation au bilan de Generali correspond à une évaluation à dire d'expert. Le risque de recouvrement partiel est réel.

**Ce que le tool doit détecter / proposer :** Identifier le fonds par son ISIN et déclencher une alerte de conformité. Mentionner l'historique de suspension. Recommander de vérifier la valorisation avec l'assureur. Proposer un arbitrage vers un fonds liquide si la situation est toujours en cours de résolution.

**Ou dans l'UI :** Section AV rapport PDF (ligne H2O), alerte audit rouge, page S20 import (flag à l'import).

**Criticite :** Critique

- [ ] Détecté
- [ ] Partiellement
- [ ] Manqué

**Notes :**

---

### Piège 10 — PEE : concentration actionnariat employeur à 60 %

**Description :** Sur le PEE d'Antoine (95 000 €), 57 000 € sont investis en FCPE Actionnariat (actions de l'employeur), soit 60 % du PEE. La règle prudentielle recommande de ne pas dépasser 33 % en titres de l'employeur (cumul risque emploi + risque capital).

**Ce que le tool doit détecter / proposer :** Alerter sur la concentration excessive. Calculer le pourcentage exact. Recommander un arbitrage progressif vers le FCPE Diversifié. Quantifier le risque : si l'employeur fait défaut, Antoine perd à la fois son emploi et 57 000 € d'épargne.

**Ou dans l'UI :** Section Épargne salariale rapport PDF, alerte audit, page S04 (épargne salariale).

**Criticite :** Important

- [ ] Détecté
- [ ] Partiellement
- [ ] Manqué

**Notes :**

---

## Allocation / Cohérence (pièges 11 à 15)

---

### Piège 11 — Liquidités 185 000 € vs horizon 10 ans : excès de cash

**Description :** Les liquidités totales s'élèvent à : CC joint 42 000 + LA Antoine 22 950 + LA Camille 22 950 + LDDS Antoine 12 000 + LDDS Camille 12 000 + Livret LCL 18 000 + CAT BNP 55 000 = 184 900 €, soit ~14 % du patrimoine financier. Avec un horizon retraite de 10 ans, ce niveau de cash est clairement excessif.

**Ce que le tool doit détecter / proposer :** Calculer le ratio liquidités / patrimoine financier total. Comparer à une norme de réserve de sécurité (3-6 mois de dépenses, soit ~45 000-90 000 € pour ce foyer). Identifier l'excédent (environ 95 000-140 000 €) et proposer un redéploiement.

**Ou dans l'UI :** Section Allocation rapport PDF, alerte audit, page S05 Allocation.

**Criticite :** Important

- [ ] Détecté
- [ ] Partiellement
- [ ] Manqué

**Notes :**

---

### Piège 12 — Crypto + crowdfunding 20 000 € : actifs alternatifs (1,2 %)

**Description :** Antoine détient 8 000 € en crypto (BTC + ETH) avec 30 % de PV latente et 12 000 € en crowdfunding immobilier Anaxago (taux 9 %, 3 échéances 2027-2028). Ces 20 000 € représentent 1,2 % du patrimoine financier total.

**Ce que le tool doit détecter / proposer :** Identifier et catégoriser ces actifs comme "alternatifs". Signaler le risque de liquidité du crowdfunding (capital bloqué jusqu'aux échéances). Rappeler la fiscalité des crypto (PFU 30 % ou barème). Vérifier que la part alternatives reste dans les limites du profil risque.

**Ou dans l'UI :** Section Alternatifs rapport PDF, page S04 (actifs divers), alerte audit.

**Criticite :** Nice-to-have

- [ ] Détecté
- [ ] Partiellement
- [ ] Manqué

**Notes :**

---

### Piège 13 — PEA Camille jamais ouvert : opportunité d'antériorité à 1 €

**Description :** Camille n'a pas de PEA. Ouvrir un PEA aujourd'hui à 1 € fait démarrer le compteur des 5 ans (exonération de plus-value). Si elle attend, elle perd de l'antériorité. L'ouverture est gratuite chez Bourse Direct ou Fortuneo.

**Ce que le tool doit détecter / proposer :** Détecter l'absence de PEA pour Camille (statut "non_ouvert_opportunite_anteriorite"). Recommander l'ouverture immédiate d'un PEA à 1 € pour démarrer le délai de 5 ans. Calculer la date à laquelle le PEA serait fiscal en 2031.

**Ou dans l'UI :** Section PEA rapport PDF, recommandation S18, alerte audit.

**Criticite :** Important

- [ ] Détecté
- [ ] Partiellement
- [ ] Manqué

**Notes :**

---

### Piège 14 — Titres UK dans CTO : convention UK-FR et retenue à la source 15 %

**Description :** Shell (GB00BP6MXD84) et BP (GB0007980591) versent des dividendes soumis à une retenue à la source de 15 % au Royaume-Uni (convention fiscale franco-britannique post-Brexit). Cette retenue est imputable sur l'IR français mais génère un travail déclaratif spécifique (formulaire cerfa 2047).

**Ce que le tool doit détecter / proposer :** Identifier les ISIN GB et déclencher une alerte spécifique sur la retenue à la source. Rappeler la procédure de récupération via la déclaration 2047. Proposer éventuellement le déplacement vers des fonds domiciliés en Irlande (Ucits IE) pour éviter ce frottement.

**Ou dans l'UI :** Section CTO rapport PDF (lignes Shell et BP), alerte audit, page S20 import.

**Criticite :** Important

- [ ] Détecté
- [ ] Partiellement
- [ ] Manqué

**Notes :**

---

### Piège 15 — PEA Antoine : plafond versements 150 000 € → 40 000 € restants

**Description :** Antoine a versé 82 000 € dans son PEA (encours 110 000 €, PV 28 000 €). Le plafond légal du PEA est 150 000 €. Il lui reste donc 68 000 € de capacité de versement. Avec un besoin d'investissement identifié et un TMI élevé, optimiser le PEA est prioritaire.

**Ce que le tool doit détecter / proposer :** Calculer automatiquement la capacité résiduelle PEA (150 000 - versements_total). Signaler l'opportunité dans le contexte des objectifs d'Antoine (retraite dans 10 ans, exonération PV à horizon).

**Ou dans l'UI :** Section PEA rapport PDF, page S04 (PEA), recommandation S18.

**Criticite :** Important

- [ ] Détecté
- [ ] Partiellement
- [ ] Manqué

**Notes :**

---

## Projection / Monte-Carlo (pièges 16 à 18)

---

### Piège 16 — 3e résidence à 600 000 € en 2028 : retrait AV Camille > 8 ans + abattement

**Description :** Le projet d'achat d'une 3e résidence (budget 600 000 €, horizon 2028-2030) nécessite un financement partiel. L'AV Linxea de Camille dépassera 8 ans en septembre 2026, bénéficiant alors de l'abattement de 9 200 €. Un rachat partiel en 2028 serait fiscalement optimal.

**Ce que le tool doit détecter / proposer :** Dans le scénario de projection, modéliser le décaissement 2028 depuis l'AV Camille (post-8 ans). Calculer la fiscalité du rachat (PFU après abattement) et la comparer à un financement crédit. Signaler si d'autres enveloppes seraient moins coûteuses fiscalement.

**Ou dans l'UI :** Section Objectifs rapport PDF, projection Monte-Carlo S17, scénario rachat AV.

**Criticite :** Important

- [ ] Détecté
- [ ] Partiellement
- [ ] Manqué

**Notes :**

---

### Piège 17 — Études enfants 220 000 € (2026-2034) : décaissement PEA Antoine post-5 ans

**Description :** Les trois enfants ont des besoins estimés à 220 000 € entre 2026 et 2034. Le PEA d'Antoine (ouvert 2008, > 5 ans) permet des retraits défiscalisés (exonération IR sur PV). Un plan de décaissement étalé sur le PEA minimise la fiscalité vs un retrait AV ou CTO.

**Ce que le tool doit détecter / proposer :** Modéliser un plan de décaissement étalé 2026-2034 depuis le PEA Antoine (exonération IR, PS 17,2 %). Comparer la fiscalité avec un retrait depuis le CTO joint (PFU 30 %). Signaler que les retraits PEA après 5 ans ferment le plan si inférieurs à l'encours (vérifier la règle).

**Ou dans l'UI :** Section Objectifs rapport PDF, projection Monte-Carlo, page S04 (objectifs).

**Criticite :** Important

- [ ] Détecté
- [ ] Partiellement
- [ ] Manqué

**Notes :**

---

### Piège 18 — Inflation différentielle : immobilier Annecy vs actifs financiers

**Description :** La résidence secondaire d'Annecy est en zone touristique alpine. L'hypothèse d'inflation immo locale peut différer significativement de l'hypothèse immo nationale retenue dans les projections. Utiliser une hypothèse unique biaise la valeur nette projetée.

**Ce que le tool doit détecter / proposer :** Permettre de paramétrer une hypothèse d'inflation immo spécifique par bien (pas seulement une hypothèse nationale). Signaler si l'hypothèse par défaut S17 est appliquée à un bien en zone tendue. Afficher la sensibilité de la valeur nette projetée à ± 1 % d'hypothèse immo.

**Ou dans l'UI :** Page S17 Hypothèses (immobilier), projection Monte-Carlo, rapport PDF section Hypothèses.

**Criticite :** Nice-to-have

- [ ] Détecté
- [ ] Partiellement
- [ ] Manqué

**Notes :**

---

## Récapitulatif des scores

| # | Piège | Criticite | Statut |
|---|-------|-----------|--------|
| 1 | TMI variable Antoine (41-45 %) | Critique | |
| 2 | 3,5 parts fiscales vs détachement Léa | Important | |
| 3 | PER Antoine : report 3 ans non utilisés | Critique | |
| 4 | PER Camille TNS : formule spécifique | Critique | |
| 5 | AV : ordre optimal de rachat selon antériorité | Critique | |
| 6 | Versements AV avant 70 ans | Important | |
| 7 | IFI : patrimoine immo net > 1,3 M€ | Critique | |
| 8 | Profil Camille avocate = client averti MIF II ? | Critique | |
| 9 | H2O Multibonds : fonds historiquement suspendu | Critique | |
| 10 | PEE : concentration actionnariat employeur 60 % | Important | |
| 11 | Liquidités 185 k€ vs horizon 10 ans | Important | |
| 12 | Crypto + crowdfunding : actifs alternatifs 1,2 % | Nice-to-have | |
| 13 | PEA Camille jamais ouvert : antériorité à 1 € | Important | |
| 14 | Titres UK CTO : retenue à la source 15 % | Important | |
| 15 | PEA Antoine : 68 k€ restants de capacité | Important | |
| 16 | 3e résidence 2028 : rachat AV Camille > 8 ans | Important | |
| 17 | Études 2026-2034 : décaissement PEA Antoine | Important | |
| 18 | Inflation différentielle immo Annecy | Nice-to-have | |

**Score final : __ / 18 détectés**  
(dont __ / 7 Critiques détectés)

---

*Données 100 % fictives — usage interne dogfood uniquement.*
