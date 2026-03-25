"""
Tests for django-unfold admin dashboard (/pivce-za-zivce/).
"""
import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.gis.geos import Point
from django.test import RequestFactory

from institutions.admin import InstitutionAdmin, ReviewAdmin
from institutions.models import Institution, Review
from jobs.admin import JobAdmin, JobApplicationAdmin
from jobs.models import Job, JobApplication
from users.admin import CustomUserAdmin, WorkerProfileAdmin
from users.models import User, WorkerProfile


def make_superuser():
    return User.objects.create_superuser(
        username="admin_test",
        email="admin@test.com",
        password="testpass123",
    )


def make_institution(name="Test BSO", lrk="LRK-TEST"):
    return Institution.objects.create(
        name=name,
        institution_type="bso",
        street="Teststraat",
        house_number="1",
        postcode="1000AA",
        city="Amsterdam",
        location=Point(4.9, 52.3, srid=4326),
        lrk_number=lrk,
    )


def make_job(institution, user):
    return Job.objects.create(
        institution=institution,
        posted_by=user,
        title="PM KDV",
        job_type="kdv",
        contract_type="fulltime",
        description="Test vacature",
        city="Amsterdam",
    )


# ---------------------------------------------------------------------------
# Admin URL bereikbaar
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAdminUrl:
    def test_admin_url_accessible(self, client):
        user = make_superuser()
        client.force_login(user)
        response = client.get("/pivce-za-zivce/")
        assert response.status_code == 200

    def test_old_admin_url_not_found(self, client):
        user = make_superuser()
        client.force_login(user)
        response = client.get("/admin/")
        assert response.status_code == 404

    def test_anonymous_redirected(self, client):
        response = client.get("/pivce-za-zivce/")
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# InstitutionAdmin
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestInstitutionAdmin:
    def setup_method(self):
        self.site = AdminSite()
        self.admin = InstitutionAdmin(Institution, self.site)
        self.factory = RequestFactory()
        self.superuser = make_superuser()

    def _get_request(self):
        request = self.factory.get("/")
        request.user = self.superuser
        return request

    def test_list_display_fields(self):
        assert "name" in self.admin.list_display
        assert "lrk_verified" in self.admin.list_display
        assert "is_claimed" in self.admin.list_display
        assert "job_count" in self.admin.list_display

    def test_job_count_annotation(self):
        inst = make_institution()
        qs = self.admin.get_queryset(self._get_request())
        obj = qs.get(pk=inst.pk)
        assert self.admin.job_count(obj) == 0

    def test_avg_rating_display_no_reviews(self):
        inst = make_institution(lrk="LRK-NOREV")
        qs = self.admin.get_queryset(self._get_request())
        obj = qs.get(pk=inst.pk)
        assert self.admin.avg_rating_display(obj) == "—"

    def test_mark_verified_action(self):
        inst = make_institution(lrk="LRK-VER")
        inst.lrk_verified = False
        inst.save()
        qs = Institution.objects.filter(pk=inst.pk)
        self.admin.mark_verified(None, qs)
        inst.refresh_from_db()
        assert inst.lrk_verified is True

    def test_mark_unverified_action(self):
        inst = make_institution(lrk="LRK-UNVER")
        inst.lrk_verified = True
        inst.save()
        qs = Institution.objects.filter(pk=inst.pk)
        self.admin.mark_unverified(None, qs)
        inst.refresh_from_db()
        assert inst.lrk_verified is False

    def test_mark_inactive_action(self):
        inst = make_institution(lrk="LRK-INACT")
        qs = Institution.objects.filter(pk=inst.pk)
        self.admin.mark_inactive(None, qs)
        inst.refresh_from_db()
        assert inst.is_active is False

    def test_mark_active_action(self):
        inst = make_institution(lrk="LRK-ACT")
        inst.is_active = False
        inst.save()
        qs = Institution.objects.filter(pk=inst.pk)
        self.admin.mark_active(None, qs)
        inst.refresh_from_db()
        assert inst.is_active is True


# ---------------------------------------------------------------------------
# JobAdmin
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestJobAdmin:
    def setup_method(self):
        self.site = AdminSite()
        self.admin = JobAdmin(Job, self.site)

    def test_list_display_fields(self):
        assert "title" in self.admin.list_display
        assert "is_active" in self.admin.list_display
        assert "is_premium" in self.admin.list_display

    def test_activate_jobs_action(self):
        inst = make_institution(lrk="LRK-JACT")
        user = make_superuser()
        job = make_job(inst, user)
        job.is_active = False
        job.save()
        qs = Job.objects.filter(pk=job.pk)
        self.admin.activate_jobs(None, qs)
        job.refresh_from_db()
        assert job.is_active is True

    def test_deactivate_jobs_action(self):
        inst = make_institution(lrk="LRK-JDACT")
        user = User.objects.create_user(username="poster2", password="x", role="institution")
        job = make_job(inst, user)
        qs = Job.objects.filter(pk=job.pk)
        self.admin.deactivate_jobs(None, qs)
        job.refresh_from_db()
        assert job.is_active is False

    def test_mark_premium_action(self):
        inst = make_institution(lrk="LRK-JPREM")
        user = User.objects.create_user(username="poster3", password="x", role="institution")
        job = make_job(inst, user)
        qs = Job.objects.filter(pk=job.pk)
        self.admin.mark_premium(None, qs)
        job.refresh_from_db()
        assert job.is_premium is True

    def test_unmark_premium_action(self):
        inst = make_institution(lrk="LRK-JUPREM")
        user = User.objects.create_user(username="poster4", password="x", role="institution")
        job = make_job(inst, user)
        job.is_premium = True
        job.save()
        qs = Job.objects.filter(pk=job.pk)
        self.admin.unmark_premium(None, qs)
        job.refresh_from_db()
        assert job.is_premium is False


# ---------------------------------------------------------------------------
# JobApplicationAdmin
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestJobApplicationAdmin:
    def setup_method(self):
        self.site = AdminSite()
        self.admin = JobApplicationAdmin(JobApplication, self.site)

    def test_job_institution_method(self):
        inst = make_institution(lrk="LRK-APPINST")
        poster = User.objects.create_user(username="poster5", password="x", role="institution")
        applicant = User.objects.create_user(username="applic1", password="x", role="worker")
        job = make_job(inst, poster)
        app = JobApplication.objects.create(job=job, applicant=applicant, status="pending")
        assert self.admin.job_institution(app) == inst.name

    def test_mark_viewed_action(self):
        inst = make_institution(lrk="LRK-APPVIEW")
        poster = User.objects.create_user(username="poster6", password="x", role="institution")
        applicant = User.objects.create_user(username="applic2", password="x", role="worker")
        job = make_job(inst, poster)
        app = JobApplication.objects.create(job=job, applicant=applicant, status="pending")
        self.admin.mark_viewed(None, JobApplication.objects.filter(pk=app.pk))
        app.refresh_from_db()
        assert app.status == "viewed"

    def test_mark_accepted_action(self):
        inst = make_institution(lrk="LRK-APPACC")
        poster = User.objects.create_user(username="poster7", password="x", role="institution")
        applicant = User.objects.create_user(username="applic3", password="x", role="worker")
        job = make_job(inst, poster)
        app = JobApplication.objects.create(job=job, applicant=applicant, status="pending")
        self.admin.mark_accepted(None, JobApplication.objects.filter(pk=app.pk))
        app.refresh_from_db()
        assert app.status == "accepted"

    def test_mark_rejected_action(self):
        inst = make_institution(lrk="LRK-APPREJ")
        poster = User.objects.create_user(username="poster8", password="x", role="institution")
        applicant = User.objects.create_user(username="applic4", password="x", role="worker")
        job = make_job(inst, poster)
        app = JobApplication.objects.create(job=job, applicant=applicant, status="pending")
        self.admin.mark_rejected(None, JobApplication.objects.filter(pk=app.pk))
        app.refresh_from_db()
        assert app.status == "rejected"


# ---------------------------------------------------------------------------
# UserAdmin
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserAdmin:
    def setup_method(self):
        self.site = AdminSite()
        self.admin = CustomUserAdmin(User, self.site)

    def test_list_display_includes_role(self):
        assert "role" in self.admin.list_display

    def test_activate_users_action(self):
        user = User.objects.create_user(username="inactive1", password="x", is_active=False)
        self.admin.activate_users(None, User.objects.filter(pk=user.pk))
        user.refresh_from_db()
        assert user.is_active is True

    def test_deactivate_users_action(self):
        user = User.objects.create_user(username="active1", password="x", is_active=True)
        self.admin.deactivate_users(None, User.objects.filter(pk=user.pk))
        user.refresh_from_db()
        assert user.is_active is False


# ---------------------------------------------------------------------------
# WorkerProfileAdmin
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWorkerProfileAdmin:
    def setup_method(self):
        self.site = AdminSite()
        self.admin = WorkerProfileAdmin(WorkerProfile, self.site)

    def test_list_display_fields(self):
        assert "user" in self.admin.list_display
        assert "is_available" in self.admin.list_display
        assert "vog_verified" in self.admin.list_display

    def test_worker_profile_visible(self):
        user = User.objects.create_user(username="worker_p", password="x", role="worker")
        profile = WorkerProfile.objects.create(user=user, city="Rotterdam")
        assert WorkerProfile.objects.filter(pk=profile.pk).exists()
