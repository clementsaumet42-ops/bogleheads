# Sextant — Vision et chemin officiel

> Document de référence figé. Complète `README.md` (positionnement) et
> `ROADMAP.md` (plan d'exécution). Ici : la **raison d'être**, le **parcours
> client de bout en bout**, et les **principes produit non négociables** qui
> doivent guider toute décision future.
>
> Dernière mise à jour : 2026-05-06.

---

## 1. La promesse en une phrase

**Sextant transforme une mission patrimoniale d'expert-comptable CIF en un
processus industriel de 4 semaines, qui produit des livrables réglementaires
signés et une économie de friction fiscale chiffrée et défendable, pour un
client haut de gamme français.**

Pas un robo-advisor. Pas un Excel survitaminé. Pas un outil de back-office
généraliste. Un **atelier de mission** : input = un patrimoine réel hétérogène,
output = un client servi selon les standards CIF avec un plan d'action chiffré
sur 12 mois.

---

## 2. Pour qui — les deux personae

### Persona principal : l'utilisateur direct

**L'expert-comptable inscrit CIF qui veut industrialiser son offre patrimoniale.**

- Cabinet EC indépendant ou petit groupement (1 à 10 associés).
- Inscrit à l'ORIAS en CIF, au minimum un associé Compétence Confirmée AMF.
- Conseille déjà ses clients sur le pilotage de trésorerie / rémunération /
  arbitrage dividende-salaire — souvent gratuitement, dans le forfait expertise.
- Veut **transformer ce conseil informel en mission facturée récurrente**, avec
  livrables signés et traçabilité réglementaire.
- Bloque aujourd'hui sur trois choses : la lourdeur conformité, l'absence
  d'outil métier français adapté, et le manque de méthodologie reproductible
  d'un dossier à l'autre.

**Ce qu'il achète avec Sextant :** un cadre, une méthode, un moteur, et la
capacité de faire payer 5 à 15 k€ HT une mission qu'il rendait gratuitement.

### Persona secondaire : le client final servi par l'EC

**Un foyer aisé français avec un patrimoine financier hétérogène.**

- Patrimoine financier net 500 k€ à 15 M€.
- Dirigeant de PME, profession libérale, cadre senior, héritier — peu importe
  l'origine. Le point commun : **plusieurs enveloppes** (PEA, AV multiples,
  CTO, PEE/PER, parfois holding IS, contrat de capitalisation).
- A déjà tenté l'autogestion ou subi un CGP "vendeur de produits".
- Cherche un conseiller **non commissionné** (l'EC l'est par construction
  via la facturation horaire ou forfaitaire CIF).
- Comprend qu'un point de friction fiscale annuelle représente, sur 20 ans,
  des dizaines de milliers d'euros.

**Ce qu'il achète :** la tranquillité d'avoir un patrimoine piloté avec
rigueur, par un professionnel de confiance qu'il connaît déjà (son EC),
et la preuve écrite que les arbitrages proposés sont défendables.

---

## 3. Le problème qu'on résout

Trois frictions structurelles qu'aucun outil du marché ne traite ensemble.

### Friction 1 — La fiscalité d'enveloppe

Un même ETF placé en PEA, en AV ou en CTO ne produit pas le même rendement
net après impôt. Multiplier ça par 5 enveloppes et 10 supports, et
l'optimisation devient un problème combinatoire que l'esprit humain ne
résout pas correctement.

**Sans Sextant** : l'EC fait au feeling, ou recopie une allocation type.
Perte typique : **50 à 150 bps de rendement net annuel**.

**Avec Sextant** : optimisation MILP sous contrainte fiscale, le bon ETF
dans la bonne enveloppe, chiffré.

### Friction 2 — Le coût caché du rebalancement

Le rebalancement annuel naïf — "vendre ce qui a monté, acheter ce qui a
baissé" — est ce que tous les outils anglo-saxons recommandent. En France,
c'est une erreur méthodologique : chaque vente sur CTO déclenche du PFU,
chaque arbitrage en holding IS du mark-to-market, chaque sortie PEA avant
5 ans casse l'antériorité.

**Sans Sextant** : soit l'EC ne rebalance jamais (dérive de l'allocation),
soit il rebalance à l'aveugle (frottement fiscal qui mange le rendement).

**Avec Sextant** : rebalancement par les **flux entrants** d'abord (versements
ciblés sur les enveloppes sous-pondérées), arbitrage par vente uniquement si
l'écart à la cible dépasse un seuil et en privilégiant les enveloppes sans
friction. Coût fiscal évité chiffré explicitement.

### Friction 3 — La conformité CIF

DER, lettre de mission, profilage MIF II, RAA, journal de mission, signature
eIDAS, archivage. C'est lourd, c'est obligatoire, et ça décourage 90% des EC
de se lancer en CIF.

**Sans Sextant** : Word + PDF + classeur papier + risque réel de redressement
ACPR/AMF en cas de contrôle.

**Avec Sextant** : tout est généré, signé, horodaté, archivé. Le ZIP de fin
de mission est juridiquement défendable.

---

## 4. Le parcours mission de bout en bout

C'est **le fil rouge** auquel toute fonctionnalité de Sextant doit se
rattacher. Si une feature ne sert pas une étape de ce parcours, elle n'a
pas sa place dans le produit.

### Phase 0 — Avant la mission (hors outil)

L'EC identifie un client de son cabinet pour qui une mission patrimoniale
fait sens (patrimoine > 500 k€, hétérogénéité d'enveloppes, projet à 5+ ans).
Il propose une mission cadrée, non liée à la mission d'expertise comptable.

**Sextant n'intervient pas ici.** Mais le marketing produit doit fournir à
l'EC les arguments commerciaux (cf. section 5).

### Phase 1 — Qualification (30 min, page Mission_EC)

Score 0–10 sur 8 questions standardisées : pertinence de la mission,
complexité estimée, risque déontologique, charge de travail, pricing
indicatif. **Output : décision go / no-go documentée.**

Si go → ouverture d'une mission dans Sextant avec ID unique.

### Phase 2 — Onboarding (2h cumulées EC + client, page Profil + Profilage)

- Saisie du foyer (état civil, situation familiale, revenus, fiscalité).
- Profilage MIF II complet : connaissance, expérience, tolérance au risque,
  capacité de perte, horizon, objectifs.
- Génération automatique du **DER** (Document d'Entrée en Relation) et de
  la **Lettre de Mission** : envoi au client pour signature eIDAS.

**Output Phase 2 :** DER signé + LM signée + profil MIF II validé. Le client
est juridiquement entré en relation. La mission peut commencer.

### Phase 3 — Diagnostic (4h EC, pages Import_Patrimoine + Alertes_Fiscales + Simulateur_Fiscal)

C'est ici que le **module S20 (import patrimoine PDF)** prend tout son sens :

1. Le client envoie ses 3 à 8 derniers relevés (PEA, AV, CTO, PEE…).
2. L'EC les uploade dans la page `24_Import_Patrimoine`.
3. Sextant détecte l'émetteur, extrait les lignes, score la confiance.
4. L'EC valide ligne par ligne (jamais de merge silencieux).
5. **Le moteur d'alertes tourne** : concentration, frais courants, mark-to-market,
   pièges MIF II, H2O, titres UK post-Brexit, concentration PEE…
6. Le simulateur fiscal chiffre la friction actuelle annuelle.

**Output Phase 3 :** un état des lieux chiffré que l'EC peut présenter au
client lors d'une revue à mi-parcours. *"Aujourd'hui vous payez X € de frais
courants et Y € de friction fiscale par an. Voici comment on peut le réduire."*

### Phase 4 — Recommandations (2h EC, pages Allocation + Asset_Location)

- L'EC fixe une **allocation cible** Boglehead adaptée au profil (ex. 60/40,
  70/30) avec choix du cœur indiciel mondial et de la poche obligataire.
- Sextant calcule l'**asset location optimale par MILP** : pour chaque ETF
  cible, dans quelle enveloppe le placer pour minimiser la fiscalité sur la
  durée de détention prévue.
- L'EC ajuste si besoin (toujours modifiable, jamais imposé).

**Output Phase 4 :** une allocation cible documentée + un mapping
ETF → enveloppe défendable.

### Phase 5 — Plan d'action (2h EC, page Plan_Execution)

C'est ici que le **rebalancement par les flux** (Bloc C de la roadmap)
devient central. Sextant produit :

- Une **cascade trimestrielle 12 mois** de versements ciblés.
- Les arbitrages par vente uniquement si nécessaire, avec coût fiscal chiffré.
- Le screener ETF (ISIN éligibles par enveloppe, frais, taille du fonds).
- Les ordres prêts à passer (CSV ou copier-coller dans le broker).

**Output Phase 5 :** un planning d'exécution opérationnel sur 12 mois.

### Phase 6 — Livrables signés (1h EC, bouton "Tout générer")

Un clic, un ZIP horodaté contenant :

- **PDF diagnostic client** (40-60 pages) : profil, patrimoine actuel,
  alertes, allocation cible, asset location, plan d'action, hypothèses,
  annexes réglementaires.
- **DER signé + LM signée + profilage MIF II + RAA MIF II** signés eIDAS.
- **Excel de suivi** opérationnel pour l'EC.
- **CSV des ordres** trimestriels.
- **Journal de mission** complet (audit trail).

**Output Phase 6 :** une mission terminée, archivée, défendable en cas de
contrôle ACPR/AMF, et utilisable comme preuve de valeur pour la facturation.

### Phase 7 — Suivi annuel (2h EC/an, page Suivi)

Un an plus tard, l'EC ré-importe les relevés, Sextant compare :

- Allocation réalisée vs cible → écart, dérive, besoin de rebalancement ?
- **Friction fiscale réellement évitée** vs scénario naïf → ROI chiffré.
- **Frais réellement payés** vs benchmark → gain.
- Mise à jour DER si changement de situation.
- Nouveau plan 12 mois pour l'année à venir.

**Output Phase 7 :** un livrable de revue annuelle qui justifie la
récurrence de la mission. **C'est ici que se joue la rétention client de
l'EC** — et donc la pérennité du modèle économique de Sextant.

---

## 5. La proposition de valeur chiffrée

### Pour l'expert-comptable

| Avant Sextant | Avec Sextant |
|---|---|
| Conseil patrimonial gratuit dans le forfait expertise | Mission CIF facturée 5–15 k€ HT par client |
| 1 à 2 dossiers / an traités au feeling | 10 à 30 dossiers / an industrialisés |
| Risque déontologique flou | Audit trail complet, archive eIDAS, défendable |
| Méthodologie réinventée à chaque dossier | Parcours unique reproductible |
| Pas de récurrence | Revue annuelle facturée 1,5–3 k€ / an / client |

**Modèle économique cabinet :** 20 clients récurrents × 2 k€ revue annuelle
= 40 k€ de chiffre d'affaires récurrent à marge nette > 60% (l'outil fait
le gros du travail).

### Pour le client final

| Avant Sextant | Avec Sextant |
|---|---|
| 50–150 bps de friction fiscale annuelle | Friction réduite à 10–30 bps |
| Conseil ponctuel, fragmenté, oublié | Plan 12 mois suivi, revue annuelle |
| Documents dans un placard, pas signés | Archive eIDAS, juridiquement opposable |
| Conseiller commissionné (CGP) ou personne | Conseiller non commissionné de confiance (son EC) |

**Pour un patrimoine de 2 M€ :** 100 bps de friction évitée = 20 k€/an
soit ~600 k€ sur 30 ans (sans réinvestissement) ou bien plus avec capitalisation.
Le coût de la mission Sextant est amorti **la première année**.

---

## 6. Principes produit non négociables

Ces principes guident toute décision technique et fonctionnelle. Aucun
ticket ne doit les violer sans débat explicite.

### P1 — 100% local, zéro cloud

Aucun appel LLM, aucun envoi de données client à un tiers. Patrimoine
client = donnée ultra-sensible. Sextant tourne sur le poste de l'EC (ou
sur un serveur du cabinet). Point.

### P2 — Jamais de merge silencieux

Toute donnée importée, toute suggestion, tout calcul est **validable
explicitement par l'EC**. L'outil propose, l'EC dispose. Pas de magie
qui s'exécute en arrière-plan sans confirmation.

### P3 — Tout est traçable et défendable

Chaque chiffre du livrable client doit pouvoir être justifié par :
- une ligne d'import patrimoine (hash + score de confiance), OU
- un calcul reproductible documenté, OU
- une hypothèse versionnée (snapshot SHA-256).

Si on ne peut pas défendre un chiffre devant l'AMF, on ne le sort pas.

### P4 — Rétro-compatibilité totale des missions

Une mission ouverte en S16 doit rester chargeable sans erreur en S30.
Les schémas évoluent additivement. Pas de migration destructive.

### P5 — Pas de dette de vocabulaire

Le langage de l'outil = le langage de l'EC-CIF. Pas de jargon Boglehead
anglo (no "DCA", "lump sum" sans traduction), pas de jargon CGP commercial
("placement", "produit"), pas de jargon LLM hype.

### P6 — Esthétique Private Banking

Charte S19 (or, ivoire, bleu nuit, EB Garamond, Inter, Lucide). **Zéro
emoji dans l'UI rendue.** Le client final voit du sérieux, pas du startup.

### P7 — Le parcours mission est la colonne vertébrale

Toute feature qui ne se rattache pas à une des 7 phases du parcours est
rejetée par défaut. Pas de feature "cool". Pas de page Streamlit
pédagogique grand public. Pas de Monte-Carlo récréatif. Si c'est pas
dans le parcours, c'est dans `archive/`.

---

## 7. Ce que Sextant n'est PAS (anti-vision)

Pour clarifier les limites, ce que **nous refusons de devenir** :

- ❌ **Pas un robo-advisor.** L'EC garde la main, toujours.
- ❌ **Pas un outil grand public.** Cible exclusive : EC-CIF.
- ❌ **Pas un agrégateur bancaire.** Pas de connexion API banque, pas de
  PSD2 ; on parse des PDF que le client envoie volontairement.
- ❌ **Pas un outil de gestion de portefeuille en temps réel.** Pas de cours
  live, pas de tracking quotidien. La mission s'inscrit sur 12 mois.
- ❌ **Pas un CRM.** Le suivi client riche reste dans le CRM du cabinet.
- ❌ **Pas un moteur d'OPCVM actifs ou de produits structurés.** Philosophie
  Bogleheads = ETF passifs à frais bas, point.
- ❌ **Pas un outil multilingue.** France first, droit français, fiscalité
  française. Si un client n'est pas résident fiscal français → mission refusée.
- ❌ **Pas un outil SaaS multi-tenant.** Un cabinet = une instance.

---

## 8. Critères de succès (à 12 mois)

1. **10 cabinets EC** utilisent Sextant en production sur des missions facturées.
2. **100 missions complètes** réalisées avec livrables signés archivés.
3. **Aucun incident de conformité** remonté lors d'un contrôle ACPR/AMF
   sur une mission produite par Sextant.
4. **NPS > 50** chez les EC utilisateurs.
5. **Friction fiscale moyenne évitée chiffrée** : > 50 bps/an documentée
   sur les missions terminées.
6. **Temps moyen mission complète** : < 12h homme par dossier (vs ~40h sans
   outil).

---

## 9. Évolutions envisagées (horizon 12-24 mois, hors scope court terme)

À documenter mais **pas à implémenter avant que les Blocs A+B+C de la
roadmap ne soient livrés.**

- Pack "Holding IS dirigeant" plus profond (fusion-cession, OBO, 150-0 B ter).
- Module successoral (donation-partage, démembrement, assurance-vie clause
  bénéficiaire).
- Connexion comptable cabinet (pré-remplissage depuis le dossier permanent EC).
- Mode "associé junior" — assistant qui aide l'EC à former un collaborateur
  sur la mission.
- Marketplace de templates d'import additionnels (Yomoni, Nalo, Ramify…).

**Tout ajout à cette liste doit être jugé à l'aune de la section 6 (principes)
et de la section 4 (parcours).** Si ça ne sert pas une phase du parcours, ça
n'entre pas.

---

## 10. Documents associés

- [`README.md`](README.md) — positionnement produit, fonctionnalités, état actuel
- [`ROADMAP.md`](ROADMAP.md) — plan d'exécution en 3 blocs (Mesurer, Propre & Logique, Efficace)
- [`CHANGELOG.md`](CHANGELOG.md) — historique des sprints et décisions
- [`archive/README.md`](archive/README.md) — modules archivés post-pivot
- [`dogfood/cas_rousseau/README.md`](dogfood/cas_rousseau/README.md) — cas de test E2E

---

## Préambule à coller en tête d'une nouvelle conversation

> Voici la vision figée du projet **Sextant** (repo `clementsaumet42-ops/bogleheads`).
> Avant toute proposition, lis ce fichier en entier, puis `README.md`, puis `ROADMAP.md`.
>
> Trois règles :
> 1. Le parcours mission (section 4) est la colonne vertébrale — toute feature s'y rattache ou est rejetée.
> 2. Les 7 principes produit (section 6) sont non négociables.
> 3. La liste anti-vision (section 7) borne ce qu'on refuse de devenir.
>
> Dis-moi où on en est sur la `ROADMAP.md` et propose la prochaine action concrète.
