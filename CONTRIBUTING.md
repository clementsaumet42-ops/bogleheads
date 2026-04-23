# 🤝 Guide de contribution — Bogleheads FR

Merci de votre intérêt pour ce projet ! Ce document explique comment contribuer efficacement.

## 📋 Prérequis

- Python 3.9+
- git

## ⚙️ Installation (mode développeur)

```bash
git clone https://github.com/clementsaumet42-ops/bogleheads.git
cd bogleheads
pip install -e ".[dev]"
pre-commit install
```

## 🧪 Lancer les tests

```bash
pytest
```

Avec couverture :

```bash
pytest --cov=src --cov-report=term
```

## 🔍 Lint et formatage

```bash
# Vérification lint
ruff check .

# Vérification du formatage
ruff format --check .

# Appliquer le formatage automatiquement
ruff format .

# Type checking
mypy src/
```

## 📝 Convention de commits

Ce projet suit la convention [Conventional Commits](https://www.conventionalcommits.org/) :

```
<type>(<scope>): <description courte>

[corps optionnel]

[footer optionnel]
```

Types courants :

| Type | Usage |
|---|---|
| `feat` | Nouvelle fonctionnalité |
| `fix` | Correction de bug |
| `docs` | Documentation uniquement |
| `style` | Formatage (sans changement fonctionnel) |
| `refactor` | Refactoring sans ajout de fonctionnalité ni correction |
| `test` | Ajout ou correction de tests |
| `chore` | Tâches de maintenance (CI, dépendances…) |

Exemples :

```
feat(schemas): ajouter validation Pydantic v2 pour univers_etf.yaml
fix(allocation): corriger normalisation allocation par âge
docs(contributing): ajouter guide de contribution
```

## 🔄 Workflow Pull Request

1. **Forkez** le dépôt et créez une branche depuis `main`
   ```bash
   git checkout -b feat/ma-nouvelle-fonctionnalite
   ```
2. **Développez** votre fonctionnalité avec des tests
3. **Vérifiez** que tous les tests passent (`pytest`) et que le lint est propre (`ruff check .`)
4. **Committez** en suivant la convention Conventional Commits
5. **Ouvrez une Pull Request** vers `main` avec une description claire
6. **Attendez** la revue de code — au moins 1 approbation requise
7. Une fois approuvée, la PR est mergée par un mainteneur

### Checklist avant de soumettre une PR

- [ ] Tests ajoutés ou mis à jour pour les nouvelles fonctionnalités
- [ ] `pytest` passe sans erreur
- [ ] `ruff check .` sans erreur
- [ ] `ruff format --check .` sans erreur
- [ ] Commit message conforme à Conventional Commits
- [ ] Documentation mise à jour si nécessaire

## 🐛 Signaler un bug

Ouvrez une [issue](https://github.com/clementsaumet42-ops/bogleheads/issues/new/choose) en utilisant le template **Bug report**.

## 💡 Proposer une fonctionnalité

Ouvrez une [issue](https://github.com/clementsaumet42-ops/bogleheads/issues/new/choose) en utilisant le template **Feature request**.

## ⚠️ Note légale

Les contributions au code fiscal ou aux paramètres réglementaires doivent être sourcées (loi de finances, articles CGI, BOFiP). Aucun conseil personnalisé ne doit être inclus dans le code.
