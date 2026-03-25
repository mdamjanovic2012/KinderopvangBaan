"""
Unit tests for the users app.
Covers: User model, WorkerProfile model, register, login/token, me, worker-profile, worker-list.
"""
import pytest
from rest_framework import status
from django.contrib.auth import get_user_model
from users.models import WorkerProfile
from users.serializers import UserSerializer, WorkerProfileSerializer, PublicWorkerSerializer

User = get_user_model()


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserModel:
    def test_str(self, worker_user):
        assert "testworker" in str(worker_user)
        assert "worker" in str(worker_user)

    def test_default_role_worker(self, db):
        user = User.objects.create_user(username="x", password="pass1234")
        assert user.role == "worker"

    def test_role_institution(self, institution_user):
        assert institution_user.role == "institution"

    def test_role_parent(self, parent_user):
        assert parent_user.role == "parent"

    def test_valid_role_choices(self, worker_user):
        assert worker_user.role in ["worker", "institution", "parent"]


@pytest.mark.django_db
class TestWorkerProfileModel:
    def test_str(self, worker_profile):
        assert "testworker" in str(worker_profile)

    def test_default_is_available(self, worker_profile):
        assert worker_profile.is_available is True

    def test_default_not_vog_verified(self, db, worker_user):
        profile = WorkerProfile.objects.create(user=worker_user)
        assert profile.vog_verified is False

    def test_one_to_one_constraint(self, db, worker_user):
        WorkerProfile.objects.create(user=worker_user)
        with pytest.raises(Exception):
            WorkerProfile.objects.create(user=worker_user)


# ---------------------------------------------------------------------------
# Serializer tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserSerializer:
    def test_contains_expected_fields(self, worker_user):
        data = UserSerializer(worker_user).data
        for field in ["id", "username", "email", "role"]:
            assert field in data

    def test_id_is_read_only(self, worker_user):
        s = UserSerializer(worker_user, data={"id": 9999, "username": "new"}, partial=True)
        s.is_valid()
        assert s.validated_data.get("id") is None


@pytest.mark.django_db
class TestWorkerProfileSerializer:
    def test_contains_username(self, worker_profile):
        data = WorkerProfileSerializer(worker_profile).data
        assert data["username"] == "testworker"

    def test_excludes_vog_verified(self, worker_profile):
        data = WorkerProfileSerializer(worker_profile).data
        assert "vog_verified" not in data


@pytest.mark.django_db
class TestPublicWorkerSerializer:
    def test_available_days_from_availability_json(self, worker_profile):
        data = PublicWorkerSerializer(worker_profile).data
        assert data["available_days"] == ["ma", "di", "wo"]

    def test_available_days_empty_when_no_availability(self, db, worker_user):
        profile = WorkerProfile.objects.create(user=worker_user)
        data = PublicWorkerSerializer(profile).data
        assert data["available_days"] == []

    def test_does_not_expose_location_coordinates(self, worker_profile):
        data = PublicWorkerSerializer(worker_profile).data
        assert "location" not in data


# ---------------------------------------------------------------------------
# Register view
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRegisterView:
    def test_register_creates_user(self, api_client):
        res = api_client.post("/api/auth/register/", {
            "username": "newuser",
            "email": "new@test.nl",
            "password": "securepass123",
            "role": "worker",
        }, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(username="newuser").exists()

    def test_register_returns_user_data(self, api_client):
        res = api_client.post("/api/auth/register/", {
            "username": "newuser2",
            "email": "new2@test.nl",
            "password": "securepass123",
            "role": "institution",
        }, format="json")
        assert res.data["username"] == "newuser2"
        assert res.data["role"] == "institution"

    def test_register_short_password_rejected(self, api_client):
        res = api_client.post("/api/auth/register/", {
            "username": "badpass",
            "password": "abc",
            "role": "worker",
        }, format="json")
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_username_rejected(self, api_client, worker_user):
        res = api_client.post("/api/auth/register/", {
            "username": "testworker",
            "email": "dup@test.nl",
            "password": "securepass123",
            "role": "worker",
        }, format="json")
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_not_in_response(self, api_client):
        res = api_client.post("/api/auth/register/", {
            "username": "securenewuser",
            "email": "sec@test.nl",
            "password": "securepass123",
            "role": "worker",
        }, format="json")
        assert "password" not in res.data

    def test_register_as_parent_rejected(self, api_client):
        res = api_client.post("/api/auth/register/", {
            "username": "parentuser",
            "email": "parent@test.nl",
            "password": "securepass123",
            "role": "parent",
        }, format="json")
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert not User.objects.filter(username="parentuser").exists()

    def test_register_as_worker_allowed(self, api_client):
        res = api_client.post("/api/auth/register/", {
            "username": "newworker",
            "email": "newworker@test.nl",
            "password": "securepass123",
            "role": "worker",
        }, format="json")
        assert res.status_code == status.HTTP_201_CREATED

    def test_register_as_institution_allowed(self, api_client):
        res = api_client.post("/api/auth/register/", {
            "username": "newinst",
            "email": "newinst@test.nl",
            "password": "securepass123",
            "role": "institution",
        }, format="json")
        assert res.status_code == status.HTTP_201_CREATED


# ---------------------------------------------------------------------------
# JWT token views
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTokenView:
    def test_obtain_token(self, api_client, worker_user):
        res = api_client.post("/api/auth/token/", {
            "username": "testworker",
            "password": "testpass123",
        }, format="json")
        assert res.status_code == status.HTTP_200_OK
        assert "access" in res.data
        assert "refresh" in res.data

    def test_wrong_password_returns_401(self, api_client, worker_user):
        res = api_client.post("/api/auth/token/", {
            "username": "testworker",
            "password": "wrongpassword",
        }, format="json")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token(self, api_client, worker_user):
        login_res = api_client.post("/api/auth/token/", {
            "username": "testworker",
            "password": "testpass123",
        }, format="json")
        refresh = login_res.data["refresh"]
        res = api_client.post("/api/auth/token/refresh/", {"refresh": refresh}, format="json")
        assert res.status_code == status.HTTP_200_OK
        assert "access" in res.data


# ---------------------------------------------------------------------------
# Me view
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMeView:
    def test_get_me_requires_auth(self, api_client):
        res = api_client.get("/api/auth/me/")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_me_returns_current_user(self, auth_client, worker_user):
        res = auth_client.get("/api/auth/me/")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["username"] == "testworker"

    def test_patch_me_updates_email(self, auth_client, worker_user):
        res = auth_client.patch("/api/auth/me/", {"email": "updated@test.nl"}, format="json")
        assert res.status_code == status.HTTP_200_OK
        worker_user.refresh_from_db()
        assert worker_user.email == "updated@test.nl"

    def test_patch_me_cannot_change_id(self, auth_client, worker_user):
        original_id = worker_user.pk
        auth_client.patch("/api/auth/me/", {"id": 9999}, format="json")
        worker_user.refresh_from_db()
        assert worker_user.pk == original_id


# ---------------------------------------------------------------------------
# Worker profile view
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWorkerProfileView:
    def test_requires_auth(self, api_client):
        res = api_client.get("/api/auth/worker-profile/")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_creates_profile_if_missing(self, auth_client, worker_user):
        res = auth_client.get("/api/auth/worker-profile/")
        assert res.status_code == status.HTTP_200_OK
        assert WorkerProfile.objects.filter(user=worker_user).exists()

    def test_patch_updates_bio(self, auth_client, worker_profile):
        res = auth_client.patch("/api/auth/worker-profile/", {"bio": "New bio"}, format="json")
        assert res.status_code == status.HTTP_200_OK
        worker_profile.refresh_from_db()
        assert worker_profile.bio == "New bio"

    def test_patch_updates_work_radius(self, auth_client, worker_profile):
        res = auth_client.patch("/api/auth/worker-profile/", {"work_radius_km": 25}, format="json")
        assert res.status_code == status.HTTP_200_OK
        worker_profile.refresh_from_db()
        assert worker_profile.work_radius_km == 25

    def test_patch_updates_has_vog(self, auth_client, worker_profile):
        res = auth_client.patch("/api/auth/worker-profile/", {"has_vog": True}, format="json")
        assert res.status_code == status.HTTP_200_OK
        worker_profile.refresh_from_db()
        assert worker_profile.has_vog is True

    def test_patch_updates_availability(self, auth_client, worker_profile):
        avail = {"days": ["ma", "di"], "from": "2026-04-01"}
        res = auth_client.patch("/api/auth/worker-profile/", {"availability": avail}, format="json")
        assert res.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# Worker list view (public)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWorkerListView:
    def test_list_returns_200(self, api_client, worker_profile):
        res = api_client.get("/api/users/workers/")
        assert res.status_code == status.HTTP_200_OK

    def test_lists_available_workers(self, api_client, worker_profile):
        res = api_client.get("/api/users/workers/")
        assert len(res.data) >= 1

    def test_excludes_unavailable_workers(self, api_client, worker_profile):
        worker_profile.is_available = False
        worker_profile.save()
        res = api_client.get("/api/users/workers/")
        usernames = [w["username"] for w in res.data]
        assert "testworker" not in usernames

    def test_nearby_workers_within_radius(self, api_client, worker_profile):
        # Worker is in Amsterdam, querying from Amsterdam
        res = api_client.get("/api/users/workers/?lat=52.3676&lng=4.9041&radius=10")
        assert res.status_code == status.HTTP_200_OK
        usernames = [w["username"] for w in res.data]
        assert "testworker" in usernames

    def test_nearby_workers_excludes_far_workers(self, api_client, worker_profile):
        # Querying from Rotterdam — Amsterdam worker is ~70km away
        res = api_client.get("/api/users/workers/?lat=51.9244&lng=4.4777&radius=5")
        usernames = [w["username"] for w in res.data]
        assert "testworker" not in usernames

    def test_worker_has_diploma_field(self, api_client, worker_profile):
        res = api_client.get("/api/users/workers/")
        worker = next((w for w in res.data if w["username"] == "testworker"), None)
        assert worker is not None
        assert worker["has_diploma"] is True

    def test_worker_has_available_days(self, api_client, worker_profile):
        res = api_client.get("/api/users/workers/")
        worker = next((w for w in res.data if w["username"] == "testworker"), None)
        assert worker["available_days"] == ["ma", "di", "wo"]

    def test_no_auth_required(self, api_client, worker_profile):
        res = api_client.get("/api/users/workers/")
        assert res.status_code == status.HTTP_200_OK

    def test_invalid_lat_lng_ignored_returns_all(self, api_client, worker_profile):
        res = api_client.get("/api/users/workers/?lat=notanumber&lng=alsonotanumber")
        assert res.status_code == status.HTTP_200_OK
        usernames = [w["username"] for w in res.data]
        assert "testworker" in usernames


# ---------------------------------------------------------------------------
# first_name + last_name bij registratie en /me/ endpoint
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFirstLastName:
    def test_register_with_first_last_name(self, api_client):
        res = api_client.post("/api/auth/register/", {
            "username": "mikitest",
            "email": "miki@test.nl",
            "password": "TestPass123",
            "role": "worker",
            "first_name": "Miki",
            "last_name": "Janssen",
        }, format="json")
        assert res.status_code == 201
        assert res.data["first_name"] == "Miki"
        assert res.data["last_name"] == "Janssen"

    def test_register_without_name_still_works(self, api_client):
        res = api_client.post("/api/auth/register/", {
            "username": "naamloze",
            "email": "naamloos@test.nl",
            "password": "TestPass123",
            "role": "worker",
        }, format="json")
        assert res.status_code == 201
        assert res.data["first_name"] == ""
        assert res.data["last_name"] == ""

    def test_me_returns_first_last_name(self, auth_client, worker_user):
        worker_user.first_name = "Anna"
        worker_user.last_name = "de Vries"
        worker_user.save()
        res = auth_client.get("/api/auth/me/")
        assert res.status_code == 200
        assert res.data["first_name"] == "Anna"
        assert res.data["last_name"] == "de Vries"

    def test_me_patch_updates_first_last_name(self, auth_client, worker_user):
        res = auth_client.patch("/api/auth/me/", {
            "first_name": "Sofie",
            "last_name": "Bakker",
        }, format="json")
        assert res.status_code == 200
        assert res.data["first_name"] == "Sofie"
        assert res.data["last_name"] == "Bakker"


# ---------------------------------------------------------------------------
# Nieuwe profielvelden: bevoegdheid, hours_per_week, immediate_available, adres
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWorkerProfileNewFields:
    def test_patch_bevoegdheid(self, auth_client, worker_profile):
        res = auth_client.patch("/api/auth/worker-profile/", {
            "bevoegdheid": ["bso", "dagopvang"],
        }, format="json")
        assert res.status_code == 200
        worker_profile.refresh_from_db()
        assert worker_profile.bevoegdheid == ["bso", "dagopvang"]

    def test_patch_hours_per_week(self, auth_client, worker_profile):
        res = auth_client.patch("/api/auth/worker-profile/", {
            "hours_per_week": 32,
        }, format="json")
        assert res.status_code == 200
        worker_profile.refresh_from_db()
        assert worker_profile.hours_per_week == 32

    def test_patch_immediate_available(self, auth_client, worker_profile):
        res = auth_client.patch("/api/auth/worker-profile/", {
            "immediate_available": True,
        }, format="json")
        assert res.status_code == 200
        worker_profile.refresh_from_db()
        assert worker_profile.immediate_available is True

    def test_patch_address_fields(self, auth_client, worker_profile):
        res = auth_client.patch("/api/auth/worker-profile/", {
            "postcode": "1234AB",
            "house_number": "10",
            "street": "Teststraat",
            "city": "Amsterdam",
        }, format="json")
        assert res.status_code == 200
        worker_profile.refresh_from_db()
        assert worker_profile.postcode == "1234AB"
        assert worker_profile.house_number == "10"
        assert worker_profile.street == "Teststraat"

    def test_default_bevoegdheid_empty(self, db, worker_user):
        profile = WorkerProfile.objects.create(user=worker_user)
        assert profile.bevoegdheid == []

    def test_default_immediate_available_false(self, db, worker_user):
        profile = WorkerProfile.objects.create(user=worker_user)
        assert profile.immediate_available is False

    def test_default_hours_per_week_none(self, db, worker_user):
        profile = WorkerProfile.objects.create(user=worker_user)
        assert profile.hours_per_week is None

    def test_public_serializer_exposes_bevoegdheid(self, worker_profile):
        worker_profile.bevoegdheid = ["peuterspeelzaal"]
        worker_profile.save()
        data = PublicWorkerSerializer(worker_profile).data
        assert data["bevoegdheid"] == ["peuterspeelzaal"]

    def test_public_serializer_exposes_immediate_available(self, worker_profile):
        worker_profile.immediate_available = True
        worker_profile.save()
        data = PublicWorkerSerializer(worker_profile).data
        assert data["immediate_available"] is True

    def test_public_serializer_does_not_expose_address(self, worker_profile):
        data = PublicWorkerSerializer(worker_profile).data
        assert "postcode" not in data
        assert "house_number" not in data
        assert "street" not in data
