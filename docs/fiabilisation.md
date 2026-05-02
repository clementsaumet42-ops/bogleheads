# Fiabilisation — Documentation interne

> Version : Bloc A — mai 2026

## 1. Lancer la suite de régression missions localement

```bash
# Suite complète
make test-missions

# Équivalent direct
pytest tests/missions/ -v

# Une seule mission
pytest tests/missions/mission_dirigeant_is_holding/ -v
```

Les tests chargent `inputs.yaml`, font tourner le pipeline complet (alertes → allocation → fiscalité) et comparent ligne à ligne avec `expected_outputs.json`.

**Tolérances** : `1e-6` pour les fractions, `0.01 €` pour les montants.

## 2. Ajouter un 4ème dossier de test

### Procédure

1. Créer `tests/missions/mission_<nom>/` avec :
   - `inputs.yaml` — description du client (reprendre la structure des 3 missions existantes)
   - `expected_outputs.json` — valeurs attendues (voir format ci-dessous)
   - `test_mission_<nom>.py` — test pytest

2. Nommer le dossier avec un nom descriptif en snake_case.

3. Exigences de déterminisme :
   - Fixer `MISSION_TEST_FROZEN_TIME` pour tous les calculs date-dépendants
   - Fixer le seed numpy via le fixture `rng_seed` de `tests/missions/conftest.py`
   - Ne pas utiliser de valeurs aléatoires sans seed

4. Générer les expected_outputs :
   ```bash
   make missions-update-baselines MISSION=mission_<nom>
   ```
   Puis **réviser manuellement** les valeurs fiscales ligne par ligne avant commit.

### Format `expected_outputs.json`

```json
{
  "alertes_codes": ["R1", "R7"],
  "nb_alertes_min": 1,
  "allocation_cible": {
    "actions_monde_acwi": 0.70,
    "obligations_agg_monde": 0.25
  },
  "allocation_tolerance": 1e-6,
  "profil_mif2": "dynamique_75_25",
  "fiscal": {
    "taux_pfu_total": 0.314,
    "taux_ps": 0.186
  }
}
```

## 3. Regénérer les expected_outputs après une modification fiscale volontaire

**⚠️ À utiliser avec discernement — déclenche toujours une revue manuelle.**

```bash
# Regénère les baselines de toutes les missions
make missions-update-baselines

# Regénère une seule mission
make missions-update-baselines MISSION=mission_dirigeant_is_holding
```

### Checklist de revue manuelle obligatoire avant commit

Après régénération :

- [ ] Vérifier que les nouveaux `alertes_codes` correspondent aux règles modifiées intentionnellement
- [ ] Vérifier que les allocations restent cohérentes avec le profil MIF II
- [ ] Vérifier les taux fiscaux : `taux_pfu_total`, `taux_ps`, `is_taux_normal`
- [ ] Vérifier les plafonds : `per_deduction_max_eur`, `pea_plafond_atteint`
- [ ] Tester la CI localement (`make test-missions`) avant push
- [ ] Documenter la modification fiscale dans `CHANGELOG.md`

## 4. Vérifier un snapshot cryptographique d'une mission archivée

```bash
# Vérification complète (signature + SHA-256 livrables)
python -m bogleheads.snapshot verify annexes/snapshot/snapshot_<mission>_<ts>.json

# Avec clé publique explicite (si la clé auto-détectée n'est pas la bonne)
python -m bogleheads.snapshot verify snapshot.json --public-key /path/to/public.pem
```

Exit codes : `0` = valide, `1` = signature/SHA invalide, `2` = erreur (fichier manquant).

### Structure d'un ZIP livrables

```
mission_NOM_2026.zip
├── diagnostic_NOM.pdf
├── allocation_NOM.pdf
├── plan_action_NOM.pdf
├── raa_mif2_NOM.pdf
└── annexes/
    └── snapshot/
        ├── snapshot_<mission_id>_<timestamp>.json
        └── snapshot_<mission_id>_<timestamp>.json.sig
```

## 5. Procédure de rotation de la clé cabinet

1. **Générer une nouvelle paire** :
   ```bash
   python tools/init_cabinet_keys.py
   ```
   L'ancienne clé est sauvegardée en `*.pem.bak`.

2. **Conserver l'ancienne clé publique** pour la vérification des snapshots archivés.

3. **Re-signer les snapshots existants** si nécessaire (rare — uniquement si la chaîne de confiance est compromise).

4. **Mettre à jour `config/cabinet/keys/public.pem`** dans le repo git si vous commitez la clé publique.

5. **Ne jamais committer `private.pem`** — vérifier `.gitignore`.

---

*Document maintenu par le cabinet. Dernière mise à jour : Bloc A, mai 2026.*
