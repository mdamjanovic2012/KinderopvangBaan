"""
Unit tests for the institutions app.
Covers: models, serializers, all views (list, detail, nearby, reviews).
"""
import pytest
from django.contrib.gis.geos import Point
from django.urls import reverse
from rest_framework import status
from institutions.models import Institution, Review
from institutions.serializers import InstitutionSerializer, ReviewSerializer


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestInstitutionModel:
    def test_str(self, institution):
        assert "Test BSO Amsterdam" in str(institution)

    def test_default_is_active(self, db):
        inst = Institution(
            name="X",
            institution_type="bso",
            street="A",
            house_number="1",
            postcode="1000AA",
            city="X",
            location=Point(4.9, 52.3, srid=4326),
        )
        assert inst.is_active is True

    def test_default_not_lrk_verified(self, db):
        inst = Institution(
            name="X",
            institution_type="bso",
            street="A",
            house_number="1",
            postcode="1000AA",
            city="X",
            location=Point(4.9, 52.3, srid=4326),
        )
        assert inst.lrk_verified is False

    def test_institution_type_choices(self, institution):
        valid = ["bso", "kdv", "gastouder", "peuterspeelzaal"]
        assert institution.institution_type in valid

    def test_lrk_number_unique(self, db, institution):
        with pytest.raises(Exception):
            Institution.objects.create(
                name="Dupe",
                institution_type="bso",
                street="B",
                house_number="2",
                postcode="1000BB",
                city="Amsterdam",
                location=Point(4.9, 52.3, srid=4326),
                lrk_number="TEST001",  # already used
            )


@pytest.mark.django_db
class TestReviewModel:
    def test_str(self, institution, worker_user):
        review = Review.objects.create(
            institution=institution,
            author=worker_user,
            rating=4,
            text="Goed!",
        )
        assert "Test BSO Amsterdam" in str(review)
        assert "4" in str(review)

    def test_rating_range(self, institution, worker_user):
        review = Review.objects.create(
            institution=institution, author=worker_user, rating=5
        )
        assert 1 <= review.rating <= 5

    def test_unique_per_user_institution(self, institution, worker_user):
        Review.objects.create(institution=institution, author=worker_user, rating=3)
        with pytest.raises(Exception):
            Review.objects.create(institution=institution, author=worker_user, rating=4)


# ---------------------------------------------------------------------------
# Serializer tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestInstitutionSerializer:
    def test_contains_expected_fields(self, institution):
        data = InstitutionSerializer(institution).data
        for field in ["id", "name", "institution_type", "city", "lrk_verified", "location"]:
            assert field in data

    def test_distance_km_none_without_annotation(self, institution):
        data = InstitutionSerializer(institution).data
        assert data["distance_km"] is None

    def test_avg_rating_none_without_reviews(self, institution):
        data = InstitutionSerializer(institution).data
        assert data["avg_rating"] is None

    def test_avg_rating_with_reviews(self, institution, worker_user, parent_user):
        Review.objects.create(institution=institution, author=worker_user, rating=4)
        Review.objects.create(institution=institution, author=parent_user, rating=2)
        data = InstitutionSerializer(institution).data
        assert data["avg_rating"] == 3.0


# ---------------------------------------------------------------------------
# View tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestInstitutionListView:
    def test_list_returns_200(self, api_client, institution):
        res = api_client.get("/api/institutions/")
        assert res.status_code == status.HTTP_200_OK

    def test_list_contains_institution(self, api_client, institution):
        res = api_client.get("/api/institutions/")
        names = [i["name"] for i in res.data["results"]]
        assert "Test BSO Amsterdam" in names

    def test_inactive_excluded(self, api_client, institution):
        institution.is_active = False
        institution.save()
        res = api_client.get("/api/institutions/")
        names = [i["name"] for i in res.data["results"]]
        assert "Test BSO Amsterdam" not in names

    def test_filter_by_type(self, api_client, institution, institution_rotterdam):
        res = api_client.get("/api/institutions/?institution_type=kdv")
        names = [i["name"] for i in res.data["results"]]
        assert "Test KDV Rotterdam" in names
        assert "Test BSO Amsterdam" not in names

    def test_filter_by_city(self, api_client, institution, institution_rotterdam):
        res = api_client.get("/api/institutions/?city=Amsterdam")
        names = [i["name"] for i in res.data["results"]]
        assert "Test BSO Amsterdam" in names
        assert "Test KDV Rotterdam" not in names

    def test_no_auth_required(self, api_client, institution):
        res = api_client.get("/api/institutions/")
        assert res.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestInstitutionDetailView:
    def test_detail_returns_200(self, api_client, institution):
        res = api_client.get(f"/api/institutions/{institution.pk}/")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["name"] == "Test BSO Amsterdam"

    def test_detail_returns_404_for_missing(self, api_client):
        res = api_client.get("/api/institutions/99999/")
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_detail_returns_404_for_inactive(self, api_client, institution):
        institution.is_active = False
        institution.save()
        res = api_client.get(f"/api/institutions/{institution.pk}/")
        assert res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestNearbyInstitutionsView:
    def test_returns_200_with_valid_params(self, api_client, institution):
        res = api_client.get("/api/institutions/nearby/?lat=52.3676&lng=4.9041&radius=5")
        assert res.status_code == status.HTTP_200_OK

    def test_finds_institution_within_radius(self, api_client, institution):
        res = api_client.get("/api/institutions/nearby/?lat=52.3676&lng=4.9041&radius=10")
        names = [i["name"] for i in res.data]
        assert "Test BSO Amsterdam" in names

    def test_excludes_institution_outside_radius(self, api_client, institution, institution_rotterdam):
        # Querying from Amsterdam with 5km radius — Rotterdam is ~70km away
        res = api_client.get("/api/institutions/nearby/?lat=52.3676&lng=4.9041&radius=5")
        names = [i["name"] for i in res.data]
        assert "Test KDV Rotterdam" not in names

    def test_returns_distance_km(self, api_client, institution):
        res = api_client.get("/api/institutions/nearby/?lat=52.3676&lng=4.9041&radius=10")
        for item in res.data:
            if item["name"] == "Test BSO Amsterdam":
                assert item["distance_km"] is not None

    def test_filter_by_type(self, api_client, institution, institution_rotterdam):
        res = api_client.get("/api/institutions/nearby/?lat=52.3676&lng=4.9041&radius=200&type=kdv")
        types = [i["institution_type"] for i in res.data]
        assert all(t == "kdv" for t in types)

    def test_missing_lat_returns_400(self, api_client):
        res = api_client.get("/api/institutions/nearby/?lng=4.9041")
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_lng_returns_400(self, api_client):
        res = api_client.get("/api/institutions/nearby/?lat=52.37")
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_ordered_by_distance(self, api_client, institution, institution_rotterdam):
        res = api_client.get("/api/institutions/nearby/?lat=52.3676&lng=4.9041&radius=200")
        distances = [i["distance_km"] for i in res.data]
        assert distances == sorted(distances)


@pytest.mark.django_db
class TestReviewViews:
    def test_list_reviews_200(self, api_client, institution):
        res = api_client.get(f"/api/institutions/{institution.pk}/reviews/")
        assert res.status_code == status.HTTP_200_OK

    def test_create_review_requires_auth(self, api_client, institution):
        res = api_client.post(
            f"/api/institutions/{institution.pk}/reviews/",
            {"rating": 4, "text": "Goed"},
            format="json",
        )
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_review_authenticated(self, auth_client, institution):
        res = auth_client.post(
            f"/api/institutions/{institution.pk}/reviews/",
            {"rating": 5, "text": "Uitstekend!"},
            format="json",
        )
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["rating"] == 5

    def test_review_appears_in_list(self, auth_client, institution, worker_user):
        Review.objects.create(institution=institution, author=worker_user, rating=3, text="OK")
        res = auth_client.get(f"/api/institutions/{institution.pk}/reviews/")
        results = res.data.get("results", res.data)
        assert len(results) == 1
        assert results[0]["rating"] == 3

    def test_duplicate_review_rejected(self, auth_client, institution, worker_user):
        Review.objects.create(institution=institution, author=worker_user, rating=4)
        res = auth_client.post(
            f"/api/institutions/{institution.pk}/reviews/",
            {"rating": 5},
            format="json",
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# Coverage gap: serializer location=None paths + MapPinsView
# ---------------------------------------------------------------------------

class TestInstitutionSerializerLocationNone:
    def test_get_location_returns_none_when_no_location(self):
        from unittest.mock import MagicMock
        from institutions.serializers import InstitutionSerializer, InstitutionPinSerializer
        obj = MagicMock()
        obj.location = None
        obj.reviews.all.return_value = []
        assert InstitutionSerializer().get_location(obj) is None
        assert InstitutionPinSerializer().get_location(obj) is None


@pytest.mark.django_db
class TestMapPinsView:
    def test_returns_200(self, api_client, institution):
        res = api_client.get("/api/institutions/map-pins/")
        assert res.status_code == status.HTTP_200_OK

    def test_returns_institutions_with_location(self, api_client, institution):
        res = api_client.get("/api/institutions/map-pins/")
        names = [i["name"] for i in res.data]
        assert "Test BSO Amsterdam" in names

    def test_filter_by_type(self, api_client, institution, institution_rotterdam):
        res = api_client.get("/api/institutions/map-pins/?type=bso")
        types = [i["institution_type"] for i in res.data]
        assert all(t == "bso" for t in types)

    def test_pin_fields(self, api_client, institution):
        res = api_client.get("/api/institutions/map-pins/")
        pin = next(i for i in res.data if i["name"] == "Test BSO Amsterdam")
        for field in ["id", "name", "institution_type", "city", "lrk_verified", "location"]:
            assert field in pin


# ---------------------------------------------------------------------------
# InstitutionDetailSerializer — moeder-dochter structuur
# ---------------------------------------------------------------------------

def make_inst(name, lrk, **kwargs):
    from django.contrib.gis.geos import Point
    return Institution.objects.create(
        name=name,
        institution_type="bso",
        street="Straat",
        house_number="1",
        postcode="1000AA",
        city="Amsterdam",
        location=Point(4.9, 52.3, srid=4326),
        lrk_number=lrk,
        **kwargs,
    )


@pytest.mark.django_db
class TestInstitutionDetailSerializer:
    def test_parent_info_none_when_no_parent(self):
        from institutions.serializers import InstitutionDetailSerializer
        inst = make_inst("Solo BSO", "LRK-SOLO")
        data = InstitutionDetailSerializer(inst).data
        assert data["parent_info"] is None

    def test_parent_info_populated_for_child(self):
        from institutions.serializers import InstitutionDetailSerializer
        parent = make_inst("Gro-up Hoofd", "LRK-PH", naam_houder="Gro-up", kvk_nummer_houder="12345678")
        child = make_inst("Gro-up Noord", "LRK-PN", naam_houder="Gro-up", kvk_nummer_houder="12345678")
        child.parent = parent
        child.save()
        data = InstitutionDetailSerializer(child).data
        assert data["parent_info"]["id"] == parent.id
        assert data["parent_info"]["name"] == parent.name

    def test_locations_empty_when_standalone(self):
        from institutions.serializers import InstitutionDetailSerializer
        inst = make_inst("Enige BSO", "LRK-ENIG")
        data = InstitutionDetailSerializer(inst).data
        assert data["locations"] == []

    def test_locations_shows_siblings_for_child(self):
        from institutions.serializers import InstitutionDetailSerializer
        parent = make_inst("Org Hoofd", "LRK-OH2", naam_houder="Org", kvk_nummer_houder="22223333")
        child1 = make_inst("Org Noord", "LRK-ON2", naam_houder="Org", kvk_nummer_houder="22223333")
        child2 = make_inst("Org Zuid", "LRK-OZ2", naam_houder="Org", kvk_nummer_houder="22223333")
        child1.parent = parent
        child1.save()
        child2.parent = parent
        child2.save()
        data = InstitutionDetailSerializer(child1).data
        location_ids = [loc["id"] for loc in data["locations"]]
        assert child2.id in location_ids
        assert child1.id not in location_ids  # zichzelf niet tonen

    def test_locations_shows_children_for_parent(self):
        from institutions.serializers import InstitutionDetailSerializer
        parent = make_inst("Keten Hoofd", "LRK-KH", naam_houder="Keten", kvk_nummer_houder="44445555")
        child = make_inst("Keten BSO", "LRK-KB", naam_houder="Keten", kvk_nummer_houder="44445555")
        child.parent = parent
        child.save()
        data = InstitutionDetailSerializer(parent).data
        location_ids = [loc["id"] for loc in data["locations"]]
        assert child.id in location_ids

    def test_locations_active_job_count(self, db):
        from institutions.serializers import InstitutionDetailSerializer
        from jobs.models import Job
        from users.models import User
        parent = make_inst("Org Met Jobs", "LRK-MJ", naam_houder="Org", kvk_nummer_houder="66667777")
        child = make_inst("Locatie A", "LRK-LA", naam_houder="Org", kvk_nummer_houder="66667777")
        child.parent = parent
        child.save()
        user = User.objects.create_user(username="poster_test99", password="x", role="institution")
        Job.objects.create(
            institution=child,
            posted_by=user,
            title="PM",
            job_type="pm3",
            contract_type="fulltime",
            description="test",
            city="Amsterdam",
            is_active=True,
        )
        data = InstitutionDetailSerializer(parent).data
        loc = next(l for l in data["locations"] if l["id"] == child.id)
        assert loc["active_job_count"] == 1

    def test_detail_view_returns_parent_info(self, api_client):
        parent = make_inst("View Hoofd", "LRK-VH")
        child = make_inst("View Kind", "LRK-VK")
        child.parent = parent
        child.save()
        res = api_client.get(f"/api/institutions/{child.pk}/")
        assert res.status_code == 200
        assert res.data["parent_info"]["id"] == parent.id

    def test_detail_view_returns_locations(self, api_client):
        parent = make_inst("Groep A", "LRK-GA")
        child = make_inst("Locatie A1", "LRK-A1")
        child.parent = parent
        child.save()
        res = api_client.get(f"/api/institutions/{parent.pk}/")
        assert res.status_code == 200
        location_ids = [l["id"] for l in res.data["locations"]]
        assert child.id in location_ids
