"""
Tests for django-unfold admin dashboard (/pivce-za-zivce/).
"""
import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from jobs.admin import JobAdmin
from jobs.models import Company, Job
from users.admin import CustomUserAdmin, WorkerProfileAdmin
from users.models import User, WorkerProfile


def make_superuser():
    return User.objects.create_superuser(
        username="admin_test",
        email="admin@test.com",
        password="testpass123",
    )


def make_company(slug="test-co"):
    return Company.objects.create(
        name="Test BV",
        slug=slug,
        job_board_url="https://testbv.nl/vacatures",
        scraper_class="TestScraper",
    )


def make_job(company, slug="test-pm-kdv"):
    return Job.objects.create(
        company=company,
        title="PM KDV",
        job_type="pm4",
        contract_type="fulltime",
        description="Test vacature",
        city="Amsterdam",
        source_url=f"https://testbv.nl/vacatures/{slug}",
        is_active=True,
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
        company = make_company("co-act")
        job = make_job(company, "pm-act")
        job.is_active = False
        job.save()
        self.admin.activate_jobs(None, Job.objects.filter(pk=job.pk))
        job.refresh_from_db()
        assert job.is_active is True

    def test_deactivate_jobs_action(self):
        company = make_company("co-deact")
        job = make_job(company, "pm-deact")
        self.admin.deactivate_jobs(None, Job.objects.filter(pk=job.pk))
        job.refresh_from_db()
        assert job.is_active is False

    def test_mark_premium_action(self):
        company = make_company("co-prem")
        job = make_job(company, "pm-prem")
        self.admin.mark_premium(None, Job.objects.filter(pk=job.pk))
        job.refresh_from_db()
        assert job.is_premium is True

    def test_unmark_premium_action(self):
        company = make_company("co-unprem")
        job = make_job(company, "pm-unprem")
        job.is_premium = True
        job.save()
        self.admin.unmark_premium(None, Job.objects.filter(pk=job.pk))
        job.refresh_from_db()
        assert job.is_premium is False


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
