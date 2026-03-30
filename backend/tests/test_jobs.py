"""
Unit tests voor de jobs app (scraper-model).

Job comes van scrapers (Kinderdam, Partou) — geen POST endpoint.
Dekt: model, serializer, list, detail, nearby, click, choices.
"""
import pytest
from django.contrib.gis.geos import Point
from rest_framework import status
from jobs.models import Company, Job, VacatureClick
from jobs.serializers import JobSerializer
from jobs.constants import CAO_FUNCTIONS, CAO_FUNCTION_VALUES


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestJobModel:
    def test_str(self, job):
        assert "Test BSO Medewerker" in str(job)
        assert "Test Kinderopvang BV" in str(job)

    def test_default_is_active(self, job):
        assert job.is_active is True

    def test_default_not_expired(self, job):
        assert job.is_expired is False

    def test_default_not_premium(self, job):
        assert job.is_premium is False

    def test_source_url_unique(self, db, company, amsterdam):
        Job.objects.create(
            company=company, title="A", job_type="pm3", contract_type="fulltime",
            source_url="https://example.com/job/1", location=amsterdam, city="Amsterdam",
        )
        with pytest.raises(Exception):
            Job.objects.create(
                company=company, title="B", job_type="pm3", contract_type="fulltime",
                source_url="https://example.com/job/1", location=amsterdam, city="Amsterdam",
            )

    def test_ordering_newest_first(self, db, company, amsterdam):
        j1 = Job.objects.create(
            company=company, title="Old job", job_type="pm3", contract_type="fulltime",
            source_url="https://example.com/job/old", location=amsterdam, city="Amsterdam",
        )
        j2 = Job.objects.create(
            company=company, title="New job", job_type="pm3", contract_type="fulltime",
            source_url="https://example.com/job/new", location=amsterdam, city="Amsterdam",
        )
        jobs = list(Job.objects.filter(source_url__in=[
            "https://example.com/job/old", "https://example.com/job/new"
        ]).order_by("-created_at"))
        assert jobs[0] == j2


@pytest.mark.django_db
class TestCompanyModel:
    def test_str(self, company):
        assert str(company) == "Test Kinderopvang BV"

    def test_slug_unique(self, db):
        Company.objects.create(
            name="A", slug="slug-unique", job_board_url="https://a.nl/vacatures",
            scraper_class="A",
        )
        with pytest.raises(Exception):
            Company.objects.create(
                name="B", slug="slug-unique", job_board_url="https://b.nl/vacatures",
                scraper_class="B",
            )


# ---------------------------------------------------------------------------
# Serializer tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestJobSerializer:
    def test_contains_expected_fields(self, job):
        data = JobSerializer(job).data
        for field in ["id", "title", "job_type", "contract_type",
                      "company_name", "company_logo", "source_url",
                      "city", "location_name", "hours_min", "hours_max",
                      "salary_min", "salary_max", "distance_km"]:
            assert field in data

    def test_company_name_resolved(self, job):
        assert JobSerializer(job).data["company_name"] == "Test Kinderopvang BV"

    def test_distance_km_none_without_annotation(self, job):
        assert JobSerializer(job).data["distance_km"] is None


# ---------------------------------------------------------------------------
# View tests — list
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestJobListView:
    def test_list_returns_200(self, api_client, job):
        res = api_client.get("/api/jobs/")
        assert res.status_code == status.HTTP_200_OK

    def test_list_contains_job(self, api_client, job):
        res = api_client.get("/api/jobs/")
        titles = [j["title"] for j in res.data["results"]]
        assert "Test BSO Medewerker" in titles

    def test_guest_ziet_max_3_resultaten(self, api_client, company, amsterdam):
        for i in range(5):
            Job.objects.create(
                company=company, title=f"Job {i}", job_type="pm3",
                contract_type="fulltime",
                source_url=f"https://example.com/job/{i}",
                location=amsterdam, city="Amsterdam", is_active=True,
            )
        res = api_client.get("/api/jobs/")
        assert len(res.data["results"]) <= 3
        assert res.data["blurred"] is True

    def test_geauthenticeerde_gebruiker_ziet_alle(self, auth_client, company, amsterdam):
        for i in range(5):
            Job.objects.create(
                company=company, title=f"Auth Job {i}", job_type="pm3",
                contract_type="fulltime",
                source_url=f"https://example.com/authjob/{i}",
                location=amsterdam, city="Amsterdam", is_active=True,
            )
        res = auth_client.get("/api/jobs/")
        assert res.data["blurred"] is False

    def test_expired_jobs_niet_zichtbaar(self, api_client, job):
        job.is_expired = True
        job.save()
        res = api_client.get("/api/jobs/")
        titles = [j["title"] for j in res.data["results"]]
        assert "Test BSO Medewerker" not in titles

    def test_filter_by_job_type(self, api_client, job):
        res = api_client.get("/api/jobs/?job_type=pm3")
        types = [j["job_type"] for j in res.data["results"]]
        assert all(t == "pm3" for t in types)

    def test_filter_by_contract_type(self, api_client, job):
        res = api_client.get("/api/jobs/?contract_type=parttime")
        results = res.data["results"]
        assert any(j["title"] == "Test BSO Medewerker" for j in results)

    def test_post_niet_toegestaan(self, api_client):
        res = api_client.post("/api/jobs/", {}, format="json")
        assert res.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


# ---------------------------------------------------------------------------
# View tests — detail
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestJobDetailView:
    def test_detail_returns_200(self, api_client, job):
        res = api_client.get(f"/api/jobs/{job.pk}/")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["title"] == "Test BSO Medewerker"

    def test_detail_404_for_missing(self, api_client):
        res = api_client.get("/api/jobs/99999/")
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_detail_404_for_inactive(self, api_client, job):
        job.is_active = False
        job.save()
        res = api_client.get(f"/api/jobs/{job.pk}/")
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_detail_404_for_expired(self, api_client, job):
        job.is_expired = True
        job.save()
        res = api_client.get(f"/api/jobs/{job.pk}/")
        assert res.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# View tests — nearby
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestNearbyJobsView:
    def test_returns_200(self, api_client, job):
        res = api_client.get("/api/jobs/nearby/?lat=52.3676&lng=4.9041&radius=10")
        assert res.status_code == status.HTTP_200_OK

    def test_vindt_job_in_radius(self, api_client, job):
        res = api_client.get("/api/jobs/nearby/?lat=52.3676&lng=4.9041&radius=10")
        titles = [j["title"] for j in res.data["results"]]
        assert "Test BSO Medewerker" in titles

    def test_sluit_job_buiten_radius_uit(self, api_client, job, company, rotterdam):
        Job.objects.create(
            company=company, title="Rotterdam job", job_type="pm4",
            contract_type="fulltime",
            source_url="https://example.com/job/rotterdam",
            location=rotterdam, city="Rotterdam", is_active=True,
        )
        res = api_client.get("/api/jobs/nearby/?lat=52.3676&lng=4.9041&radius=5")
        titles = [j["title"] for j in res.data["results"]]
        assert "Rotterdam job" not in titles

    def test_missing_lat_returns_400(self, api_client):
        res = api_client.get("/api/jobs/nearby/?lng=4.9041")
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_lng_returns_400(self, api_client):
        res = api_client.get("/api/jobs/nearby/?lat=52.37")
        assert res.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# View tests — click (redirect naar source_url)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestJobClickView:
    def test_klik_registreert_en_geeft_source_url(self, api_client, job):
        res = api_client.post(f"/api/jobs/{job.pk}/click/")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["source_url"] == job.source_url

    def test_klik_zonder_user_is_anoniem(self, api_client, job):
        api_client.post(f"/api/jobs/{job.pk}/click/")
        click = VacatureClick.objects.get(job=job)
        assert click.user is None

    def test_klik_met_user_slaat_user_op(self, auth_client, job, worker_user):
        auth_client.post(f"/api/jobs/{job.pk}/click/")
        click = VacatureClick.objects.get(job=job)
        assert click.user == worker_user

    def test_klik_op_verlopen_job_geeft_404(self, api_client, job):
        job.is_expired = True
        job.save()
        res = api_client.post(f"/api/jobs/{job.pk}/click/")
        assert res.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# View tests — choices
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestJobChoicesView:
    def test_choices_returns_200(self, api_client):
        res = api_client.get("/api/jobs/choices/")
        assert res.status_code == status.HTTP_200_OK

    def test_choices_contains_cao_functions(self, api_client):
        res = api_client.get("/api/jobs/choices/")
        assert "cao_functions" in res.data
        values = [f["value"] for f in res.data["cao_functions"]]
        assert "pm3" in values
        assert "bso_begeleider" in values

    def test_choices_contains_contract_types(self, api_client):
        res = api_client.get("/api/jobs/choices/")
        assert "contract_types" in res.data
        values = [c["value"] for c in res.data["contract_types"]]
        assert "fulltime" in values
        assert "parttime" in values

    def test_cao_functions_have_value_and_label(self, api_client):
        res = api_client.get("/api/jobs/choices/")
        for fn in res.data["cao_functions"]:
            assert "value" in fn
            assert "label" in fn

    def test_cao_constants_all_present(self, api_client):
        res = api_client.get("/api/jobs/choices/")
        api_values = {f["value"] for f in res.data["cao_functions"]}
        for v in CAO_FUNCTION_VALUES:
            assert v in api_values


# ---------------------------------------------------------------------------
# WorkerProfile CAO function
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWorkerProfileCaoFunction:
    def test_patch_cao_function(self, auth_client, worker_profile):
        res = auth_client.patch("/api/auth/worker-profile/", {"cao_function": "pm3"}, format="json")
        assert res.status_code == 200
        worker_profile.refresh_from_db()
        assert worker_profile.cao_function == "pm3"

    def test_cao_function_in_serializer_response(self, auth_client, worker_profile):
        worker_profile.cao_function = "bso_begeleider"
        worker_profile.save()
        res = auth_client.get("/api/auth/worker-profile/")
        assert res.status_code == 200
        assert res.data["cao_function"] == "bso_begeleider"


# ---------------------------------------------------------------------------
# Job vereistenvelden
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestJobRequirementsFields:
    def test_default_requires_bevoegdheid_empty(self, job):
        assert job.requires_bevoegdheid == []

    def test_default_min_experience_none(self, job):
        assert job.min_experience is None

    def test_requires_bevoegdheid_in_serializer(self, job):
        job.requires_bevoegdheid = ["peuterspeelzaal"]
        job.save()
        assert JobSerializer(job).data["requires_bevoegdheid"] == ["peuterspeelzaal"]

    def test_min_experience_in_serializer(self, job):
        job.min_experience = 2
        job.save()
        assert JobSerializer(job).data["min_experience"] == 2
