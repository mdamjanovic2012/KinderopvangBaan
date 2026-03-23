"""
Unit tests for the jobs app.
Covers: models, serializers, list/create, detail, nearby, apply, my-applications.
"""
import pytest
from rest_framework import status
from jobs.models import Job, JobApplication
from jobs.serializers import JobSerializer


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestJobModel:
    def test_str(self, job):
        assert "Test BSO Medewerker" in str(job)
        assert "Test BSO Amsterdam" in str(job)

    def test_default_is_active(self, job):
        assert job.is_active is True

    def test_default_not_premium(self, job):
        assert job.is_premium is False

    def test_ordering_newest_first(self, db, institution, institution_user):
        j1 = Job.objects.create(
            institution=institution,
            posted_by=institution_user,
            title="Old job",
            job_type="bso",
            contract_type="fulltime",
            description="Old",
            location=institution.location,
            city=institution.city,
        )
        j2 = Job.objects.create(
            institution=institution,
            posted_by=institution_user,
            title="New job",
            job_type="bso",
            contract_type="fulltime",
            description="New",
            location=institution.location,
            city=institution.city,
        )
        jobs = list(Job.objects.all())
        assert jobs[0] == j2  # newest first


@pytest.mark.django_db
class TestJobApplicationModel:
    def test_str(self, job, worker_user):
        app = JobApplication.objects.create(job=job, applicant=worker_user)
        assert "testworker" in str(app)
        assert "Test BSO Medewerker" in str(app)

    def test_default_status_pending(self, job, worker_user):
        app = JobApplication.objects.create(job=job, applicant=worker_user)
        assert app.status == "pending"

    def test_unique_per_job_applicant(self, job, worker_user):
        JobApplication.objects.create(job=job, applicant=worker_user)
        with pytest.raises(Exception):
            JobApplication.objects.create(job=job, applicant=worker_user)


# ---------------------------------------------------------------------------
# Serializer tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestJobSerializer:
    def test_contains_expected_fields(self, job):
        data = JobSerializer(job).data
        for field in ["id", "title", "job_type", "contract_type", "institution_name", "institution_city"]:
            assert field in data

    def test_institution_name_resolved(self, job):
        data = JobSerializer(job).data
        assert data["institution_name"] == "Test BSO Amsterdam"

    def test_distance_km_none_without_annotation(self, job):
        data = JobSerializer(job).data
        assert data["distance_km"] is None


# ---------------------------------------------------------------------------
# View tests — list & create
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestJobListCreateView:
    def test_list_returns_200(self, api_client, job):
        res = api_client.get("/api/jobs/")
        assert res.status_code == status.HTTP_200_OK

    def test_list_contains_job(self, api_client, job):
        res = api_client.get("/api/jobs/")
        titles = [j["title"] for j in res.data["results"]]
        assert "Test BSO Medewerker" in titles

    def test_inactive_excluded_from_list(self, api_client, job):
        job.is_active = False
        job.save()
        res = api_client.get("/api/jobs/")
        titles = [j["title"] for j in res.data["results"]]
        assert "Test BSO Medewerker" not in titles

    def test_filter_by_job_type(self, api_client, job, db, institution, institution_user):
        Job.objects.create(
            institution=institution, posted_by=institution_user,
            title="KDV job", job_type="kdv", contract_type="fulltime",
            description="X", location=institution.location, city=institution.city,
        )
        res = api_client.get("/api/jobs/?job_type=bso")
        types = [j["job_type"] for j in res.data["results"]]
        assert all(t == "bso" for t in types)

    def test_filter_by_contract_type(self, api_client, job):
        res = api_client.get("/api/jobs/?contract_type=parttime")
        results = res.data["results"]
        assert any(j["title"] == "Test BSO Medewerker" for j in results)

    def test_create_requires_auth(self, api_client, institution):
        res = api_client.post("/api/jobs/", {
            "institution": institution.pk,
            "title": "New job",
            "job_type": "bso",
            "contract_type": "parttime",
            "description": "Test",
        }, format="json")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_by_authenticated_user(self, institution_client, institution):
        res = institution_client.post("/api/jobs/", {
            "institution": institution.pk,
            "title": "New Vacancy",
            "job_type": "kdv",
            "contract_type": "fulltime",
            "description": "We are looking for a medewerker.",
            "requires_vog": True,
        }, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["title"] == "New Vacancy"

    def test_create_inherits_location_from_institution(self, institution_client, institution):
        res = institution_client.post("/api/jobs/", {
            "institution": institution.pk,
            "title": "Location Test",
            "job_type": "bso",
            "contract_type": "parttime",
            "description": "Test",
        }, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["city"] == institution.city


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


# ---------------------------------------------------------------------------
# View tests — nearby
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestNearbyJobsView:
    def test_returns_200(self, api_client, job):
        res = api_client.get("/api/jobs/nearby/?lat=52.3676&lng=4.9041&radius=10")
        assert res.status_code == status.HTTP_200_OK

    def test_finds_job_within_radius(self, api_client, job):
        res = api_client.get("/api/jobs/nearby/?lat=52.3676&lng=4.9041&radius=10")
        titles = [j["title"] for j in res.data]
        assert "Test BSO Medewerker" in titles

    def test_excludes_job_outside_radius(self, api_client, job, db, institution_rotterdam, institution_user):
        from jobs.models import Job
        Job.objects.create(
            institution=institution_rotterdam, posted_by=institution_user,
            title="Rotterdam job", job_type="kdv", contract_type="fulltime",
            description="X", location=institution_rotterdam.location,
            city="Rotterdam",
        )
        res = api_client.get("/api/jobs/nearby/?lat=52.3676&lng=4.9041&radius=5")
        titles = [j["title"] for j in res.data]
        assert "Rotterdam job" not in titles

    def test_missing_lat_returns_400(self, api_client):
        res = api_client.get("/api/jobs/nearby/?lng=4.9041")
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_lng_returns_400(self, api_client):
        res = api_client.get("/api/jobs/nearby/?lat=52.37")
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_ordered_by_distance(self, api_client, job, db, institution, institution_user):
        from django.contrib.gis.geos import Point
        from institutions.models import Institution
        # Create a second institution slightly further away
        inst2 = Institution.objects.create(
            name="Far BSO",
            institution_type="bso",
            street="B",
            house_number="1",
            postcode="1000BB",
            city="Amsterdam",
            location=Point(4.95, 52.40, srid=4326),
            is_active=True,
        )
        Job.objects.create(
            institution=inst2, posted_by=institution_user,
            title="Far job", job_type="bso", contract_type="parttime",
            description="X", location=inst2.location, city="Amsterdam",
        )
        res = api_client.get("/api/jobs/nearby/?lat=52.3676&lng=4.9041&radius=50")
        distances = [j["distance_km"] for j in res.data]
        assert distances == sorted(d for d in distances if d is not None)

    def test_filter_by_job_type(self, api_client, job):
        res = api_client.get("/api/jobs/nearby/?lat=52.3676&lng=4.9041&radius=50&job_type=bso")
        types = [j["job_type"] for j in res.data]
        assert all(t == "bso" for t in types)


# ---------------------------------------------------------------------------
# View tests — apply
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestApplyView:
    def test_apply_requires_auth(self, api_client, job):
        res = api_client.post(f"/api/jobs/{job.pk}/apply/", {}, format="json")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_apply_creates_application(self, auth_client, job):
        res = auth_client.post(
            f"/api/jobs/{job.pk}/apply/",
            {"cover_letter": "Ik ben gemotiveerd!"},
            format="json",
        )
        assert res.status_code == status.HTTP_201_CREATED
        assert JobApplication.objects.filter(job=job).count() == 1

    def test_apply_default_status_pending(self, auth_client, job):
        res = auth_client.post(f"/api/jobs/{job.pk}/apply/", {}, format="json")
        assert res.data["status"] == "pending"

    def test_apply_to_inactive_job_returns_404(self, auth_client, job):
        job.is_active = False
        job.save()
        res = auth_client.post(f"/api/jobs/{job.pk}/apply/", {}, format="json")
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_apply_to_nonexistent_job_returns_404(self, auth_client):
        res = auth_client.post("/api/jobs/99999/apply/", {}, format="json")
        assert res.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# View tests — my-applications
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMyApplicationsView:
    def test_requires_auth(self, api_client):
        res = api_client.get("/api/jobs/my-applications/")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_own_applications_only(self, auth_client, job, worker_user, institution_user):
        JobApplication.objects.create(job=job, applicant=worker_user, cover_letter="Mine")
        JobApplication.objects.create(job=job, applicant=institution_user, cover_letter="Other")
        res = auth_client.get("/api/jobs/my-applications/")
        results = res.data.get("results", res.data)
        assert len(results) == 1
        assert results[0]["cover_letter"] == "Mine"

    def test_empty_when_no_applications(self, auth_client):
        res = auth_client.get("/api/jobs/my-applications/")
        results = res.data.get("results", res.data)
        assert results == []
