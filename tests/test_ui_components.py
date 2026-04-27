"""Tests S19 — Composants UI Private Banking (Lots A & B)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

# ─── Helpers mock Streamlit ───────────────────────────────────────────────────


def _mock_st():
    """Retourne un mock de streamlit pour tester les composants sans serveur."""
    mock = MagicMock()
    mock.markdown = MagicMock()
    mock.dataframe = MagicMock()
    mock.button = MagicMock(return_value=False)
    return mock


# ─── Lot A — Theme ────────────────────────────────────────────────────────────


class TestTheme:
    """Tests du module src/ui/theme.py."""

    def test_importable(self):
        """Le module theme est importable."""
        from src.ui import theme  # noqa: F401

        assert theme is not None

    def test_palette_constants(self):
        """Toutes les constantes de palette sont définies avec les bons hex."""
        from src.ui.theme import (
            ARDOISE,
            ARDOISE_CLAIRE,
            BLANC_CASSE,
            BLEU_NUIT,
            BLEU_PROFOND,
            IVOIRE,
            OR_CLAIR,
            OR_VIEILLI,
            ROUGE_BORDEAUX,
            VERT_FORET,
        )

        assert BLEU_NUIT == "#0B1929"
        assert BLEU_PROFOND == "#16263F"
        assert IVOIRE == "#F5F1EA"
        assert BLANC_CASSE == "#FAF7F2"
        assert OR_VIEILLI == "#8B6F47"
        assert OR_CLAIR == "#B8946A"
        assert ARDOISE == "#2C2C2C"
        assert ARDOISE_CLAIRE == "#5A5A5A"
        assert ROUGE_BORDEAUX == "#6B1E2C"
        assert VERT_FORET == "#2D4A3E"

    def test_injecter_css_ne_leve_pas_derreur(self):
        """injecter_css() ne lève pas d'exception."""
        from src.ui.theme import injecter_css

        mock_st = _mock_st()
        with patch("src.ui.theme.st", mock_st):
            injecter_css()
        mock_st.markdown.assert_called_once()

    def test_injecter_css_contient_garamond(self):
        """Le CSS injecté référence EB Garamond."""
        from src.ui.theme import _CSS

        assert "EB Garamond" in _CSS or "EB+Garamond" in _CSS

    def test_injecter_css_contient_inter(self):
        """Le CSS injecté référence Inter."""
        from src.ui.theme import _CSS

        assert "Inter" in _CSS

    def test_injecter_css_contient_variables_css(self):
        """Le CSS définit les variables CSS de palette."""
        from src.ui.theme import _CSS

        assert "--bleu-nuit" in _CSS
        assert "--or-vieilli" in _CSS
        assert "--ivoire" in _CSS

    def test_injecter_css_html_non_vide(self):
        """injecter_css() appelle st.markdown avec une chaîne non vide."""
        from src.ui.theme import injecter_css

        mock_st = _mock_st()
        with patch("src.ui.theme.st", mock_st):
            injecter_css()
        call_args = mock_st.markdown.call_args
        assert call_args is not None
        html_arg = call_args[0][0]
        assert len(html_arg) > 100  # doit être substantiel


# ─── Lot B — Composants ───────────────────────────────────────────────────────


class TestComponents:
    """Tests du module src/ui/components.py."""

    def test_importable(self):
        """Le module components est importable."""
        from src.ui import components  # noqa: F401

        assert components is not None

    def test_icone_lucide_existante(self):
        """icone_lucide() retourne du HTML pour une icône connue."""
        from src.ui.components import icone_lucide

        html = icone_lucide("download")
        assert html != ""
        assert "<svg" in html

    def test_icone_lucide_inexistante(self):
        """icone_lucide() retourne chaîne vide si l'icône n'existe pas."""
        from src.ui.components import icone_lucide

        html = icone_lucide("icone-qui-nexiste-pas-xxxxxx")
        assert html == ""

    def test_monogramme_html(self):
        """monogramme_html() retourne du HTML non vide."""
        from src.ui.components import monogramme_html

        html = monogramme_html()
        assert "<svg" in html

    def test_monogramme_html_taille(self):
        """monogramme_html() adapte la taille."""
        from src.ui.components import monogramme_html

        html_small = monogramme_html(32)
        assert 'width="32"' in html_small

    def test_titre_page_rend_html(self):
        """titre_page() appelle st.markdown avec du HTML non vide."""
        from src.ui.components import titre_page

        mock_st = _mock_st()
        with patch("src.ui.components.st", mock_st):
            titre_page("Test titre")
        mock_st.markdown.assert_called_once()
        html = mock_st.markdown.call_args[0][0]
        assert "Test titre" in html

    def test_titre_page_avec_sous_titre(self):
        """titre_page() inclut le sous-titre si fourni."""
        from src.ui.components import titre_page

        mock_st = _mock_st()
        with patch("src.ui.components.st", mock_st):
            titre_page("Titre", sous_titre="Mon sous-titre")
        html = mock_st.markdown.call_args[0][0]
        assert "Mon sous-titre" in html

    def test_kpi_card_rend_html(self):
        """kpi_card() appelle st.markdown avec la valeur dans le HTML."""
        from src.ui.components import kpi_card

        mock_st = _mock_st()
        with patch("src.ui.components.st", mock_st):
            kpi_card("Patrimoine", "1 234 567 €")
        html = mock_st.markdown.call_args[0][0]
        assert "1 234 567" in html
        assert "Patrimoine" in html

    def test_panneau_avertissement_info(self):
        """panneau_avertissement('info') appelle st.markdown."""
        from src.ui.components import panneau_avertissement

        mock_st = _mock_st()
        with patch("src.ui.components.st", mock_st):
            panneau_avertissement("info", "Titre info", "Description info")
        mock_st.markdown.assert_called_once()
        html = mock_st.markdown.call_args[0][0]
        assert "Titre info" in html
        assert "Description info" in html

    def test_panneau_avertissement_danger(self):
        """panneau_avertissement('danger') utilise la couleur bordeaux."""
        from src.ui.components import panneau_avertissement
        from src.ui.theme import ROUGE_BORDEAUX

        mock_st = _mock_st()
        with patch("src.ui.components.st", mock_st):
            panneau_avertissement("danger", "Alerte", "Problème critique")
        html = mock_st.markdown.call_args[0][0]
        assert ROUGE_BORDEAUX in html

    def test_bouton_principal_retourne_bool(self):
        """bouton_principal() retourne un booléen."""
        from src.ui.components import bouton_principal

        mock_st = _mock_st()
        mock_st.button = MagicMock(return_value=True)
        with patch("src.ui.components.st", mock_st):
            result = bouton_principal("Générer", key="test_btn")
        assert isinstance(result, bool)
        assert result is True

    def test_bouton_secondaire_retourne_bool(self):
        """bouton_secondaire() retourne un booléen."""
        from src.ui.components import bouton_secondaire

        mock_st = _mock_st()
        mock_st.button = MagicMock(return_value=False)
        with patch("src.ui.components.st", mock_st):
            result = bouton_secondaire("Annuler", key="test_sec_btn")
        assert isinstance(result, bool)

    def test_section_appelle_callback(self):
        """section() appelle le callback de contenu."""
        from src.ui.components import section

        appelé = []

        def mon_callback():
            appelé.append(True)

        mock_st = _mock_st()
        with patch("src.ui.components.st", mock_st):
            section("Ma section", mon_callback)
        assert appelé == [True]

    def test_lettrine_affiche_premiere_lettre(self):
        """lettrine() affiche la première lettre en grand."""
        from src.ui.components import lettrine

        mock_st = _mock_st()
        with patch("src.ui.components.st", mock_st):
            lettrine("Boglehead est une philosophie")
        html = mock_st.markdown.call_args[0][0]
        assert "B" in html

    def test_tableau_elegant_appelle_dataframe(self):
        """tableau_elegant() appelle st.dataframe."""
        import pandas as pd

        from src.ui.components import tableau_elegant

        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        mock_st = _mock_st()
        with patch("src.ui.components.st", mock_st):
            tableau_elegant(df)
        mock_st.dataframe.assert_called_once()


# ─── Intégration — Export __init__ ───────────────────────────────────────────


class TestUIInit:
    """Vérifie que src/ui/__init__.py exporte correctement."""

    def test_exports_theme_et_components(self):
        """__init__ exporte les symboles theme et components."""
        import src.ui

        # Les anciens exports doivent toujours être présents
        assert hasattr(src.ui, "format_euro")
        assert hasattr(src.ui, "format_pct")
