"""
Tests for LRK enrichment management command and parent-child structure.
"""
import csv
import io
import pytest
from unittest.mock import patch, MagicMock
from django.contrib.gis.geos import Point
from django.core.management import call_command

from institutions.models import Institution


def make_institution(db, name, lrk_number, kvk="", naam_houder="", **kwargs):
    return Institution.objects.create(
        name=name,
        institution_type="bso",
        street="Straat",
        house_number="1",
        postcode="1000AA",
        city="Amsterdam",
        location=Point(4.9, 52.3, srid=4326),
        lrk_number=lrk_number,
        kvk_nummer_houder=kvk,
        naam_houder=naam_houder,
        **kwargs,
    )


def build_csv(rows):
    """Build a minimal LRK-style CSV string."""
    fieldnames = [
        "lrk_id", "naam_houder", "kvk_nummer_houder",
        "verantwoordelijke_gemeente", "lrk_url",
        "contact_telefoon", "contact_emailadres", "contact_website",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, delimiter=";")
    writer.writeheader()
    for row in rows:
        full = {f: "" for f in fieldnames}
        full.update(row)
        writer.writerow(full)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Model field tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestInstitutionNewFields:
    def test_new_fields_default_empty(self, institution):
        assert institution.kvk_nummer_houder == ""
        assert institution.naam_houder == ""
        assert institution.gemeente == ""
        assert institution.lrk_url == ""
        assert institution.parent is None

    def test_parent_fk_self_referencing(self, db):
        parent = make_institution(db, "Gro-up Hoofd", "LRK-PARENT", kvk="12345678")
        child = make_institution(db, "Gro-up BSO", "LRK-CHILD", kvk="12345678")
        child.parent = parent
        child.save()
        child.refresh_from_db()
        assert child.parent == parent
        assert parent.children.count() == 1

    def test_parent_set_null_on_delete(self, db):
        parent = make_institution(db, "Hoofd", "LRK-P2", kvk="99999999")
        child = make_institution(db, "Dochter", "LRK-C2", kvk="99999999")
        child.parent = parent
        child.save()
        parent.delete()
        child.refresh_from_db()
        assert child.parent is None

    def test_serializer_includes_new_fields(self, institution):
        from institutions.serializers import InstitutionSerializer
        data = InstitutionSerializer(institution).data
        for field in ["kvk_nummer_houder", "naam_houder", "gemeente", "lrk_url", "parent"]:
            assert field in data


# ---------------------------------------------------------------------------
# Management command: enrich_from_lrk
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEnrichFromLrk:
    def _run(self, csv_content, **kwargs):
        with patch(
            "institutions.management.commands.enrich_from_lrk.Command._load_csv",
            return_value=self._parse(csv_content),
        ):
            call_command("enrich_from_lrk", **kwargs)

    def _parse(self, csv_content):
        dialect = csv.Sniffer().sniff(csv_content[:512], delimiters=";,")
        reader = csv.DictReader(io.StringIO(csv_content), dialect=dialect)
        return [{k.strip().lower(): v for k, v in row.items()} for row in reader]

    def test_enriches_naam_houder(self, db):
        inst = make_institution(db, "Test BSO", "12345")
        csv_data = build_csv([{
            "lrk_id": "12345",
            "naam_houder": "Gro-up",
            "kvk_nummer_houder": "87654321",
            "verantwoordelijke_gemeente": "Amsterdam",
            "lrk_url": "https://lrk.nl/12345",
        }])
        self._run(csv_data)
        inst.refresh_from_db()
        assert inst.naam_houder == "Gro-up"
        assert inst.kvk_nummer_houder == "87654321"
        assert inst.gemeente == "Amsterdam"
        assert inst.lrk_url == "https://lrk.nl/12345"

    def test_fills_empty_phone(self, db):
        inst = make_institution(db, "Test BSO", "11111")
        csv_data = build_csv([{
            "lrk_id": "11111",
            "contact_telefoon": "020-1234567",
        }])
        self._run(csv_data)
        inst.refresh_from_db()
        assert inst.phone == "020-1234567"

    def test_does_not_overwrite_existing_phone(self, db):
        inst = make_institution(db, "Test BSO", "22222", phone="bestaand")
        csv_data = build_csv([{
            "lrk_id": "22222",
            "contact_telefoon": "nieuw-nummer",
        }])
        self._run(csv_data)
        inst.refresh_from_db()
        assert inst.phone == "bestaand"

    def test_dry_run_makes_no_changes(self, db):
        inst = make_institution(db, "Test BSO", "33333")
        csv_data = build_csv([{
            "lrk_id": "33333",
            "naam_houder": "Zou niet opslaan",
        }])
        self._run(csv_data, dry_run=True)
        inst.refresh_from_db()
        assert inst.naam_houder == ""

    def test_unmatched_lrk_number_skipped(self, db):
        inst = make_institution(db, "Onbekend", "99999")
        csv_data = build_csv([{"lrk_id": "00000", "naam_houder": "Niemand"}])
        self._run(csv_data)
        inst.refresh_from_db()
        assert inst.naam_houder == ""


# ---------------------------------------------------------------------------
# Parent-child linking
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestParentChildLinking:
    def test_links_children_to_parent(self, db):
        parent = make_institution(db, "Gro-up Hoofd", "LRK-GH", kvk="11112222", naam_houder="Gro-up")
        child1 = make_institution(db, "Gro-up BSO Noord", "LRK-GN", kvk="11112222", naam_houder="Gro-up")
        child2 = make_institution(db, "Gro-up KDV Zuid", "LRK-GZ", kvk="11112222", naam_houder="Gro-up")

        from institutions.management.commands.enrich_from_lrk import Command
        cmd = Command()
        cmd.stdout = MagicMock()
        cmd._link_parents(dry_run=False)

        child1.refresh_from_db()
        child2.refresh_from_db()
        # Both children should point to the same parent (lowest pk = Hoofd)
        assert child1.parent_id == parent.id
        assert child2.parent_id == parent.id

    def test_single_institution_not_linked(self, db):
        inst = make_institution(db, "Alleen BSO", "LRK-ALONE", kvk="55556666", naam_houder="Solo")
        from institutions.management.commands.enrich_from_lrk import Command
        cmd = Command()
        cmd.stdout = MagicMock()
        cmd._link_parents(dry_run=False)
        inst.refresh_from_db()
        assert inst.parent is None

    def test_dry_run_link_makes_no_changes(self, db):
        make_institution(db, "A", "LRK-A", kvk="77778888", naam_houder="Keten")
        child = make_institution(db, "B", "LRK-B", kvk="77778888", naam_houder="Keten")
        from institutions.management.commands.enrich_from_lrk import Command
        cmd = Command()
        cmd.stdout = MagicMock()
        cmd._link_parents(dry_run=True)
        child.refresh_from_db()
        assert child.parent is None
