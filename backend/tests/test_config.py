"""
Configuratietests — productie-instellingen validatie

Deze tests draaien in CI/CD en valideren dat kritieke instellingen
correct geconfigureerd zijn vóór deployment. Ze vangen
misconfiguraties op die pas op productie zichtbaar zouden worden
(bijv. ontbrekend CORS-domein, onveilige DEBUG-instelling).
"""
import os
import pytest
from django.conf import settings
from django.test import override_settings


# Productiedomeinen die altijd in CORS_ALLOWED_ORIGINS moeten staan
REQUIRED_CORS_ORIGINS = [
    "https://werkeninopvang.nl",
    "https://www.werkeninopvang.nl",
    "https://kinderopvangbaan-web.azurewebsites.net",
]

# Productiedomeinen die altijd in ALLOWED_HOSTS moeten staan
REQUIRED_ALLOWED_HOSTS = [
    "kinderopvangbaan-api.azurewebsites.net",
]

IS_CI = os.getenv("CI", "false").lower() == "true"


@pytest.mark.django_db
class TestCorsConfiguratie:
    """CORS-origins validatie — voorkomt dat frontenddomein geblokkeerd wordt."""

    @pytest.mark.skipif(not IS_CI, reason="Enkel in CI gecontroleerd — lokaal niet gezet")
    def test_cors_allowed_origins_bevat_productiedomein(self):
        """werkeninopvang.nl moet altijd in de CORS-lijst staan (CI-only)."""
        origins = getattr(settings, "CORS_ALLOWED_ORIGINS", [])
        assert "https://werkeninopvang.nl" in origins, (
            "https://werkeninopvang.nl ontbreekt in CORS_ALLOWED_ORIGINS. "
            "Voeg het toe als Azure App Setting."
        )

    @override_settings(CORS_ALLOWED_ORIGINS=["https://werkeninopvang.nl"])
    def test_cors_preflight_geeft_200_terug(self, client):
        """OPTIONS-request van toegestaan domein moet 200 teruggeven."""
        response = client.options(
            "/api/jobs/",
            HTTP_ORIGIN="https://werkeninopvang.nl",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
        )
        assert response.status_code == 200

    @override_settings(CORS_ALLOWED_ORIGINS=["https://werkeninopvang.nl"])
    def test_cors_header_aanwezig_in_response(self, client):
        """Access-Control-Allow-Origin header moet aanwezig zijn voor bekende origins."""
        response = client.get(
            "/api/jobs/",
            HTTP_ORIGIN="https://werkeninopvang.nl",
        )
        assert "Access-Control-Allow-Origin" in response

    @override_settings(CORS_ALLOWED_ORIGINS=["https://werkeninopvang.nl"])
    def test_cors_blokkeert_onbekend_domein(self, client):
        """Onbekende origins mogen geen CORS-header ontvangen."""
        response = client.get(
            "/api/jobs/",
            HTTP_ORIGIN="https://kwaadaardig-domein.nl",
        )
        assert response.get("Access-Control-Allow-Origin") != "https://kwaadaardig-domein.nl"

    @pytest.mark.skipif(not IS_CI, reason="Enkel in CI strikt gecontroleerd")
    def test_alle_verplichte_cors_origins_aanwezig(self):
        """Alle productiedomeinen moeten in CORS_ALLOWED_ORIGINS staan (CI-only)."""
        origins = getattr(settings, "CORS_ALLOWED_ORIGINS", [])
        for domein in REQUIRED_CORS_ORIGINS:
            assert domein in origins, (
                f"{domein} ontbreekt in CORS_ALLOWED_ORIGINS"
            )


class TestBeveiligingsinstellingen:
    """Basiscontroles op veilige Django-instellingen."""

    @pytest.mark.skipif(not IS_CI, reason="Enkel in CI gecontroleerd")
    def test_debug_is_uit_in_productie(self):
        """DEBUG mag niet True zijn in productie."""
        assert not settings.DEBUG, (
            "DEBUG=True in productie is een veiligheidsrisico. "
            "Stel DEBUG=False in als Azure App Setting."
        )

    def test_secret_key_is_ingesteld(self):
        """SECRET_KEY mag niet leeg of standaardwaarde zijn."""
        assert settings.SECRET_KEY, "SECRET_KEY is niet ingesteld"
        assert settings.SECRET_KEY != "django-insecure-change-me", (
            "SECRET_KEY heeft nog de standaardwaarde"
        )
