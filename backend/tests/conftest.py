import pytest
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def amsterdam():
    """GeoJSON Point for Amsterdam city centre."""
    return Point(4.9041, 52.3676, srid=4326)


@pytest.fixture
def rotterdam():
    return Point(4.4777, 51.9244, srid=4326)


@pytest.fixture
def worker_user(db):
    return User.objects.create_user(
        username="testworker",
        email="worker@test.nl",
        password="testpass123",
        role="worker",
    )


@pytest.fixture
def institution_user(db):
    return User.objects.create_user(
        username="testinstitution",
        email="inst@test.nl",
        password="testpass123",
        role="institution",
    )


@pytest.fixture
def parent_user(db):
    return User.objects.create_user(
        username="testparent",
        email="parent@test.nl",
        password="testpass123",
        role="parent",
    )


@pytest.fixture
def auth_client(api_client, worker_user):
    api_client.force_authenticate(user=worker_user)
    return api_client


@pytest.fixture
def institution_client(api_client, institution_user):
    api_client.force_authenticate(user=institution_user)
    return api_client


@pytest.fixture
def institution(db, institution_user, amsterdam):
    from institutions.models import Institution
    return Institution.objects.create(
        name="Test BSO Amsterdam",
        institution_type="bso",
        street="Damrak",
        house_number="1",
        postcode="1012LG",
        city="Amsterdam",
        province="Noord-Holland",
        location=amsterdam,
        lrk_number="TEST001",
        lrk_verified=True,
        is_active=True,
    )


@pytest.fixture
def institution_rotterdam(db, institution_user, rotterdam):
    from institutions.models import Institution
    return Institution.objects.create(
        name="Test KDV Rotterdam",
        institution_type="kdv",
        street="Coolsingel",
        house_number="5",
        postcode="3011AD",
        city="Rotterdam",
        province="Zuid-Holland",
        location=rotterdam,
        is_active=True,
    )


@pytest.fixture
def job(db, institution, institution_user):
    from jobs.models import Job
    return Job.objects.create(
        institution=institution,
        posted_by=institution_user,
        title="Test BSO Medewerker",
        job_type="bso",
        contract_type="parttime",
        description="Test job description",
        location=institution.location,
        city=institution.city,
        salary_min=13.50,
        salary_max=16.00,
        hours_per_week=20,
        requires_vog=True,
        is_active=True,
    )


@pytest.fixture
def worker_profile(db, worker_user, amsterdam):
    from users.models import WorkerProfile
    return WorkerProfile.objects.create(
        user=worker_user,
        bio="Ik ben een ervaren pedagogisch medewerker.",
        years_experience=3,
        has_vog=True,
        has_diploma=True,
        location=amsterdam,
        city="Amsterdam",
        work_radius_km=15,
        is_available=True,
        availability={"days": ["ma", "di", "wo"]},
    )
