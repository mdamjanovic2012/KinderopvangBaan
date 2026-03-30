import hashlib
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from rest_framework import status

from .models import Company, GeocodedLocation, Job, VacatureClick

User = get_user_model()


def make_company(**kwargs):
    defaults = {
        "name": "TestBedrijf",
        "slug": "testbedrijf",
        "job_board_url": "https://example.com/vacatures",
        "scraper_class": "TestScraper",
    }
    defaults.update(kwargs)
    return Company.objects.create(**defaults)


def make_job(company, **kwargs):
    defaults = {
        "title": "Pedagogisch Medewerker",
        "source_url": "https://example.com/vacatures/1",
        "city": "Amsterdam",
    }
    defaults.update(kwargs)
    return Job.objects.create(company=company, **defaults)


class CompanyModelTest(TestCase):
    def test_str(self):
        c = make_company()
        self.assertEqual(str(c), "TestBedrijf")

    def test_slug_unique(self):
        make_company()
        with self.assertRaises(Exception):
            make_company(name="Ander", slug="testbedrijf")


class GeocodedLocationModelTest(TestCase):
    def test_str(self):
        loc = GeocodedLocation.objects.create(
            location_name="TestOpvang Rotterdam",
            city="Rotterdam",
        )
        self.assertEqual(str(loc), "TestOpvang Rotterdam → Rotterdam")

    def test_location_name_unique(self):
        GeocodedLocation.objects.create(location_name="Uniek")
        with self.assertRaises(Exception):
            GeocodedLocation.objects.create(location_name="Uniek")


class JobModelTest(TestCase):
    def setUp(self):
        self.company = make_company()

    def test_str(self):
        job = make_job(self.company)
        self.assertIn("Pedagogisch Medewerker", str(job))
        self.assertIn("TestBedrijf", str(job))

    def test_source_url_unique(self):
        make_job(self.company, source_url="https://example.com/1")
        with self.assertRaises(Exception):
            make_job(self.company, source_url="https://example.com/1")

    def test_default_not_expired(self):
        job = make_job(self.company)
        self.assertFalse(job.is_expired)
        self.assertTrue(job.is_active)


class JobListViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = make_company()
        for i in range(5):
            make_job(self.company, title=f"Job {i}", source_url=f"https://example.com/{i}")

    def test_guest_ziet_max_3_resultaten(self):
        response = self.client.get("/api/jobs/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 5)
        self.assertEqual(response.data["shown"], 3)
        self.assertTrue(response.data["blurred"])

    def test_geauthenticeerde_gebruiker_ziet_alle(self):
        user = User.objects.create_user(username="tester", password="pass")
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/jobs/")
        self.assertEqual(response.data["total"], 5)
        self.assertEqual(response.data["shown"], 5)
        self.assertFalse(response.data["blurred"])

    def test_expired_jobs_niet_zichtbaar(self):
        make_job(self.company, source_url="https://example.com/expired", is_expired=True)
        response = self.client.get("/api/jobs/")
        self.assertEqual(response.data["total"], 5)  # expired telt niet mee

    def test_geen_blurred_als_minder_dan_3(self):
        Job.objects.all().delete()
        for i in range(2):
            make_job(self.company, source_url=f"https://example.com/klein/{i}")
        response = self.client.get("/api/jobs/")
        self.assertFalse(response.data["blurred"])


class JobClickViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = make_company()
        self.job = make_job(self.company, source_url="https://kinderdam.nl/vacature/1")

    def test_klik_registreert_en_geeft_source_url(self):
        response = self.client.post(f"/api/jobs/{self.job.pk}/click/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["source_url"], "https://kinderdam.nl/vacature/1")
        self.assertEqual(VacatureClick.objects.count(), 1)

    def test_klik_zonder_user_is_anoniem(self):
        self.client.post(f"/api/jobs/{self.job.pk}/click/")
        click = VacatureClick.objects.first()
        self.assertIsNone(click.user)

    def test_klik_met_user_slaat_user_op(self):
        user = User.objects.create_user(username="klikker", password="pass")
        self.client.force_authenticate(user=user)
        self.client.post(f"/api/jobs/{self.job.pk}/click/")
        click = VacatureClick.objects.first()
        self.assertEqual(click.user, user)

    def test_klik_ip_wordt_gehashed(self):
        self.client.post(
            f"/api/jobs/{self.job.pk}/click/",
            REMOTE_ADDR="1.2.3.4",
        )
        click = VacatureClick.objects.first()
        verwacht = hashlib.sha256(b"1.2.3.4").hexdigest()
        self.assertEqual(click.ip_hash, verwacht)

    def test_klik_op_verlopen_job_geeft_404(self):
        self.job.is_expired = True
        self.job.save()
        response = self.client.post(f"/api/jobs/{self.job.pk}/click/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class NearbyJobsViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = make_company()
        make_job(
            self.company,
            source_url="https://example.com/amsterdam",
            city="Amsterdam",
            location=Point(4.9041, 52.3676, srid=4326),
        )
        make_job(
            self.company,
            source_url="https://example.com/groningen",
            city="Groningen",
            location=Point(6.5665, 53.2194, srid=4326),
        )

    def test_nearby_vindt_job_in_radius(self):
        response = self.client.get("/api/jobs/nearby/?lat=52.37&lng=4.89&radius=10")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 1)

    def test_nearby_zonder_lat_lng_geeft_400(self):
        response = self.client.get("/api/jobs/nearby/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CompanyListViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_geeft_actieve_companies(self):
        make_company(name="Actief", slug="actief")
        make_company(name="Inactief", slug="inactief", is_active=False)
        response = self.client.get("/api/jobs/companies/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data if isinstance(response.data, list) else response.data.get("results", response.data)
        namen = [c["name"] for c in results]
        self.assertIn("Actief", namen)
        self.assertNotIn("Inactief", namen)
