"""
Tests voor link_validator.py

Dekt:
  - _check_url: dead codes, homepage redirects, DNS errors, timeouts, success
  - _process_chunk: parallel URL checks
  - _ensure_blacklist_table: DB call
  - _flush_dead: DB batch update
  - run_link_validation: happy path + error path
"""

import asyncio
import sys
import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.link_validator import (
    _check_url,
    _process_chunk,
    _ensure_blacklist_table,
    _flush_dead,
    DEAD_STATUS_CODES,
    HOMEPAGE_PATHS,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_head_response(status: int, final_url: str) -> AsyncMock:
    resp = AsyncMock()
    resp.status = status
    resp.url = final_url
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


def _make_session(head_resp=None, get_resp=None) -> AsyncMock:
    session = AsyncMock()
    session.head = MagicMock(return_value=head_resp or _make_head_response(200, "https://example.com/job/1"))
    session.get = MagicMock(return_value=get_resp or _make_head_response(200, "https://example.com/job/1"))
    return session


def _sem():
    return asyncio.Semaphore(10)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ── _check_url tests ──────────────────────────────────────────────────────────

class TestCheckUrl:
    def test_success_returns_not_dead(self):
        session = _make_session(
            head_resp=_make_head_response(200, "https://example.com/job/123")
        )
        result = _run(_check_url(session, _sem(), {}, 1, "https://example.com/job/123"))
        job_id, url, is_dead, reason = result
        assert job_id == 1
        assert is_dead is False
        assert reason == ""

    def test_404_returns_dead(self):
        session = _make_session(
            head_resp=_make_head_response(404, "https://example.com/job/123")
        )
        result = _run(_check_url(session, _sem(), {}, 5, "https://example.com/job/123"))
        job_id, url, is_dead, reason = result
        assert is_dead is True
        assert "404" in reason

    def test_410_returns_dead(self):
        session = _make_session(
            head_resp=_make_head_response(410, "https://example.com/job/123")
        )
        _, _, is_dead, reason = _run(_check_url(session, _sem(), {}, 5, "https://example.com/job/123"))
        assert is_dead is True
        assert "410" in reason

    def test_homepage_redirect_returns_dead(self):
        """Redirect naar /vacatures/ wordt als dode link beschouwd."""
        session = _make_session(
            head_resp=_make_head_response(301, "https://example.com/vacatures/")
        )
        _, _, is_dead, reason = _run(_check_url(session, _sem(), {}, 7, "https://example.com/job/old"))
        assert is_dead is True
        assert "homepage" in reason

    def test_root_redirect_returns_dead(self):
        session = _make_session(
            head_resp=_make_head_response(301, "https://example.com/")
        )
        _, _, is_dead, _ = _run(_check_url(session, _sem(), {}, 8, "https://example.com/job/x"))
        assert is_dead is True

    def test_405_falls_back_to_get(self):
        """HEAD 405 → GET-fallback; GET 200 + geldige URL → niet dood."""
        get_resp = _make_head_response(200, "https://example.com/job/123")
        head_resp = _make_head_response(405, "https://example.com/job/123")
        session = _make_session(head_resp=head_resp, get_resp=get_resp)
        _, _, is_dead, _ = _run(_check_url(session, _sem(), {}, 9, "https://example.com/job/123"))
        assert is_dead is False

    def test_405_fallback_with_dead_get(self):
        """HEAD 405 → GET 404 → dead."""
        get_resp = _make_head_response(404, "https://example.com/job/123")
        head_resp = _make_head_response(405, "https://example.com/job/123")
        session = _make_session(head_resp=head_resp, get_resp=get_resp)
        _, _, is_dead, reason = _run(_check_url(session, _sem(), {}, 9, "https://example.com/job/123"))
        assert is_dead is True

    def test_dns_error_returns_dead(self):
        import aiohttp
        session = AsyncMock()
        session.head = MagicMock()
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(side_effect=aiohttp.ClientConnectorError(
            connection_key=MagicMock(), os_error=OSError("nodename")
        ))
        ctx.__aexit__ = AsyncMock(return_value=False)
        session.head.return_value = ctx
        _, _, is_dead, reason = _run(_check_url(session, _sem(), {}, 10, "https://nodomain.invalid/job"))
        assert is_dead is True
        assert "verbinding" in reason or "DNS" in reason

    def test_timeout_returns_dead(self):
        session = AsyncMock()
        session.head = MagicMock()
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
        ctx.__aexit__ = AsyncMock(return_value=False)
        session.head.return_value = ctx
        _, _, is_dead, reason = _run(_check_url(session, _sem(), {}, 11, "https://example.com/job/slow"))
        assert is_dead is True
        assert "timeout" in reason

    def test_unknown_exception_returns_not_dead(self):
        """Onbekende exception → niet blacklisten (twijfelgeval)."""
        session = AsyncMock()
        session.head = MagicMock()
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(side_effect=RuntimeError("unexpected"))
        ctx.__aexit__ = AsyncMock(return_value=False)
        session.head.return_value = ctx
        _, _, is_dead, _ = _run(_check_url(session, _sem(), {}, 12, "https://example.com/job/x"))
        assert is_dead is False

    def test_domain_semaphore_created_per_domain(self):
        """Elke nieuwe domeinnaam krijgt een eigen semaphore in domain_sems."""
        session = _make_session(
            head_resp=_make_head_response(200, "https://site-a.nl/job/1")
        )
        domain_sems: dict = {}
        _run(_check_url(session, _sem(), domain_sems, 1, "https://site-a.nl/job/1"))
        assert "site-a.nl" in domain_sems

    def test_aiohttp_response_error_dead_status(self):
        import aiohttp
        err = aiohttp.ClientResponseError(MagicMock(), (), status=404)
        session = AsyncMock()
        session.head = MagicMock()
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(side_effect=err)
        ctx.__aexit__ = AsyncMock(return_value=False)
        session.head.return_value = ctx
        _, _, is_dead, reason = _run(_check_url(session, _sem(), {}, 13, "https://example.com/j"))
        assert is_dead is True

    def test_aiohttp_response_error_non_dead_status(self):
        import aiohttp
        err = aiohttp.ClientResponseError(MagicMock(), (), status=503)
        session = AsyncMock()
        session.head = MagicMock()
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(side_effect=err)
        ctx.__aexit__ = AsyncMock(return_value=False)
        session.head.return_value = ctx
        _, _, is_dead, _ = _run(_check_url(session, _sem(), {}, 14, "https://example.com/j"))
        assert is_dead is False


# ── _process_chunk tests ──────────────────────────────────────────────────────

class TestProcessChunk:
    def test_returns_only_dead_urls(self):
        """_process_chunk filtert alleen dode URLs."""
        async def run():
            session = AsyncMock()
            session.head = MagicMock()

            def make_ctx(status, url):
                resp = AsyncMock()
                resp.status = status
                resp.url = url
                ctx = AsyncMock()
                ctx.__aenter__ = AsyncMock(return_value=resp)
                ctx.__aexit__ = AsyncMock(return_value=False)
                return ctx

            session.head.side_effect = [
                make_ctx(200, "https://a.com/job/1"),
                make_ctx(404, "https://b.com/job/2"),
            ]
            g_sem = asyncio.Semaphore(10)
            d_sems: dict = {}
            rows = [(1, "https://a.com/job/1"), (2, "https://b.com/job/2")]
            dead = await _process_chunk(session, g_sem, d_sems, rows)
            return dead

        dead = _run(run())
        assert len(dead) == 1
        job_id, url, reason = dead[0]
        assert job_id == 2
        assert "404" in reason

    def test_empty_chunk_returns_empty(self):
        async def run():
            session = AsyncMock()
            return await _process_chunk(session, asyncio.Semaphore(10), {}, [])
        assert _run(run()) == []


# ── _ensure_blacklist_table tests ─────────────────────────────────────────────

class TestEnsureBlacklistTable:
    def test_executes_create_table(self):
        cur = MagicMock()
        _ensure_blacklist_table(cur)
        cur.execute.assert_called_once()
        sql = cur.execute.call_args[0][0]
        assert "jobs_blacklisted_url" in sql
        assert "CREATE TABLE IF NOT EXISTS" in sql


# ── _flush_dead tests ─────────────────────────────────────────────────────────

class TestFlushDead:
    def test_does_nothing_on_empty_list(self):
        conn = MagicMock()
        _flush_dead(conn, [])
        conn.cursor.assert_not_called()

    def test_updates_db_on_dead_urls(self):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        dead = [(1, "https://a.com/job/1", "HTTP 404"),
                (2, "https://b.com/job/2", "timeout (12s)")]

        with patch("scrapers.link_validator.execute_values") as mock_ev:
            _flush_dead(conn, dead)

        mock_ev.assert_called_once()
        cur.execute.assert_called_once()
        sql = cur.execute.call_args[0][0]
        assert "is_expired" in sql
        conn.commit.assert_called_once()


# ── run_link_validation tests ─────────────────────────────────────────────────

class TestRunLinkValidation:
    def test_returns_stats_dict(self):
        """Happy path: lege database, geen URLs → stats met nullen."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchmany.return_value = []
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        async def fake_run_all():
            pass

        with patch("scrapers.link_validator.get_connection", return_value=mock_conn), \
             patch("scrapers.link_validator.aiohttp.TCPConnector") as mock_tc:
            mock_tc.return_value = MagicMock()
            from scrapers.link_validator import run_link_validation
            stats = run_link_validation()

        assert "checked" in stats
        assert "blacklisted" in stats
        assert "errors" in stats

    def test_error_increments_errors_and_reraises(self):
        """Als get_connection faalt, wordt errors verhoogd en de exception gegooid."""
        from scrapers.link_validator import run_link_validation
        with patch("scrapers.link_validator.get_connection", side_effect=RuntimeError("db down")):
            with pytest.raises(RuntimeError, match="db down"):
                run_link_validation()


# ── Constanten tests ──────────────────────────────────────────────────────────

def test_dead_status_codes_contains_404():
    assert 404 in DEAD_STATUS_CODES

def test_dead_status_codes_contains_410():
    assert 410 in DEAD_STATUS_CODES

def test_homepage_paths_contains_root():
    assert "/" in HOMEPAGE_PATHS

def test_homepage_paths_contains_vacatures():
    assert "/vacatures" in HOMEPAGE_PATHS
