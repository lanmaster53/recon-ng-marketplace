#!/usr/bin/env python3
"""
Test suite for recon-og-marketplace modules.

Runs without a live recon-ng installation by injecting mock stubs into
sys.modules before any marketplace module is loaded.

Usage:
    python3 test_modules.py
    python3 test_modules.py TestCertificateTransparency
"""

import sys
import os
import json
import importlib.util
import unittest
import time
import tempfile
from unittest.mock import MagicMock, patch

# ── paths ──────────────────────────────────────────────────────────────────────
_REPO = os.path.dirname(os.path.abspath(__file__))
_MOD  = os.path.join(_REPO, 'modules')


def _p(*parts):
    return os.path.join(_MOD, *parts)


# ── temp workspace shared across tests ────────────────────────────────────────
_TMP = tempfile.mkdtemp(prefix='recon_test_')


# ═══════════════════════════════════════════════════════════════════════════════
# Framework stubs
# ═══════════════════════════════════════════════════════════════════════════════

class MockBaseModule:
    """Minimal stand-in for recon.core.module.BaseModule."""
    workspace = _TMP
    data_path = _TMP

    def __init__(self):
        self.options    = {}
        self.keys       = {}
        self._hosts     = []
        self._contacts  = []
        self._companies = []
        self._locations = []
        self._netblocks = []
        self._ports     = []
        self._domains   = []
        self._vulnerabilities = []
        self._queries   = []
        self._output    = []
        self._errors    = []

    # network ──────────────────────────────────────────────────────────────────
    def request(self, method, url, **kw):
        raise NotImplementedError('patch me')

    # inserts ──────────────────────────────────────────────────────────────────
    # The public framework's insert_*() methods accept arbitrary trailing
    # kwargs (notes, mute, provenance, ...). Mock variants accept **kw too
    # so module authors using new fields don't need a mock-update PR.
    def insert_hosts(self, host=None, ip_address=None, **kw):
        self._hosts.append({'host': host, 'ip_address': ip_address, **kw})

    def insert_contacts(self, **kw):
        self._contacts.append(kw)

    def insert_companies(self, **kw):
        self._companies.append(kw)

    def insert_locations(self, **kw):
        self._locations.append(kw)

    def insert_netblocks(self, netblock=None, **kw):
        self._netblocks.append({'netblock': netblock, **kw} if kw else netblock)

    def insert_ports(self, **kw):
        self._ports.append(kw)

    def insert_domains(self, domain=None, **kw):
        self._domains.append({'domain': domain, **kw} if kw else domain)

    def insert_vulnerabilities(self, **kw):
        self._vulnerabilities.append(kw)

    # DB ───────────────────────────────────────────────────────────────────────
    def query(self, sql, values=None):
        self._queries.append((sql, values))
        # Tests can stub responses by setting inst._query_responses = {sql_substring: [(row,), ...]}.
        # Match by substring so tests don't have to spell out the whole SQL.
        for needle, rows in getattr(self, '_query_responses', {}).items():
            if needle in sql:
                return rows
        return []

    def get_columns(self, table):
        defaults = {
            'hosts':       [('host',), ('ip_address',)],
            'contacts':    [('first_name',), ('last_name',), ('email',)],
            'credentials': [('username',), ('password',)],
        }
        return defaults.get(table, [('id',)])

    # keys ─────────────────────────────────────────────────────────────────────
    def get_key(self, name):          return self.keys.get(name)

    # output ───────────────────────────────────────────────────────────────────
    def heading(self, text, level=0): pass
    def verbose(self, text):          pass
    def output(self, text):           self._output.append(str(text))
    def error(self, text):            self._errors.append(str(text))
    def alert(self, text):            self._output.append(f'ALERT:{text}')


class _MixinStub:
    """Placeholder base class so `class Module(BaseModule, SomeMixin)` works at import."""
    pass


def _mock_mixins_module(*names):
    """Build a module-like object exposing each mixin name as an _MixinStub subclass."""
    m = type(sys)('_mixin_stubs')
    for name in names:
        setattr(m, name, type(name, (_MixinStub,), {}))
    return m


def _bootstrap():
    """Inject mock recon framework into sys.modules before any module loads."""
    mock_core_module = MagicMock()
    mock_core_module.BaseModule = MockBaseModule

    mock_utils_parsers = MagicMock()
    mock_utils_parsers.parse_name = lambda name: (
        name.split()[0] if name else None,
        None,
        name.split()[-1] if name and len(name.split()) > 1 else None,
    )

    mock_core_framework = type(sys)('recon.core.framework')
    mock_core_framework.FrameworkException = type('FrameworkException', (Exception,), {})

    entries = [
        ('recon',               MagicMock()),
        ('recon.core',          MagicMock()),
        ('recon.core.module',   mock_core_module),
        ('recon.core.framework', mock_core_framework),
        ('recon.utils',         MagicMock()),
        ('recon.utils.parsers', mock_utils_parsers),
        ('recon.mixins',        MagicMock()),
        ('recon.mixins.search', _mock_mixins_module('GoogleWebMixin', 'BingAPIMixin')),
        ('recon.mixins.resolver', _mock_mixins_module('ResolverMixin')),
        ('recon.mixins.threads',  _mock_mixins_module('ThreadingMixin')),
        ('recon.mixins.github',   _mock_mixins_module('GithubMixin')),
        ('recon.mixins.twitter',  _mock_mixins_module('TwitterMixin')),
    ]
    for key, val in entries:
        sys.modules.setdefault(key, val)

    # ghdb.py loads data/ghdb.json at class body time; drop a stub so import works.
    ghdb_stub = os.path.join(_TMP, 'ghdb.json')
    if not os.path.exists(ghdb_stub):
        with open(ghdb_stub, 'w') as fp:
            fp.write('[]')


_bootstrap()


# ── helpers ────────────────────────────────────────────────────────────────────

def load_mod(filepath):
    """Dynamically load a marketplace module file and return the module object."""
    spec = importlib.util.spec_from_file_location('_rm', filepath)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Resp:
    """Lightweight mock HTTP response."""
    def __init__(self, status=200, text='', data=None, headers=None):
        self.status_code = status
        self.text = text
        self._data = data if data is not None else {}
        self.headers = headers if headers is not None else {}

    def json(self):
        return self._data


def _shodan_available():
    try:
        import shodan  # noqa: F401
        return True
    except ImportError:
        return False


_SKIP_SHODAN = unittest.skipUnless(_shodan_available(), 'shodan library not installed')


# ═══════════════════════════════════════════════════════════════════════════════
# module health (global sanity checks)
# ═══════════════════════════════════════════════════════════════════════════════

def _all_module_files():
    paths = []
    for dirpath, _dirs, files in os.walk(_MOD):
        for f in files:
            if f.endswith('.py') and f != '__init__.py':
                paths.append(os.path.join(dirpath, f))
    return sorted(paths)


class TestModuleHealth(unittest.TestCase):
    """
    Cross-cutting checks that apply to every module in the tree:
      - no Python SyntaxWarnings (unescaped backslashes in regex strings, etc.)
      - every module is importable (no dead dependencies, no renamed APIs)
    A single broken module anywhere in the tree fails these tests.
    """

    def test_no_syntax_warnings_in_any_module(self):
        import warnings as _warnings
        failures = []
        for path in _all_module_files():
            with open(path) as f:
                source = f.read()
            with _warnings.catch_warnings(record=True) as caught:
                _warnings.simplefilter('always')
                compile(source, path, 'exec')
                for w in caught:
                    if issubclass(w.category, SyntaxWarning):
                        rel = os.path.relpath(path, _REPO)
                        failures.append(f'{rel}:{w.lineno}: {w.message}')
        self.assertEqual(
            failures, [],
            'SyntaxWarnings found:\n  ' + '\n  '.join(failures),
        )

    def test_all_modules_importable(self):
        failures = []
        for path in _all_module_files():
            try:
                load_mod(path)
            except Exception as e:
                rel = os.path.relpath(path, _REPO)
                failures.append(f'{rel}: {type(e).__name__}: {e}')
        self.assertEqual(
            failures, [],
            'Module import failures:\n  ' + '\n  '.join(failures),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# certificate_transparency (crt.sh)
# ═══════════════════════════════════════════════════════════════════════════════

class _CrtshResp:
    """Mock response that mimics requests.Response for the crt.sh module:
    .status_code, .headers, and .json() that can either return data or raise."""
    def __init__(self, status=200, data=None, headers=None, json_raises=False):
        self.status_code = status
        self.headers = headers or {}
        self._data = data
        self._raises = json_raises

    def json(self):
        if self._raises:
            raise ValueError("not JSON")
        return self._data if self._data is not None else []


class TestCertificateTransparency(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.file = load_mod(_p('recon', 'domains-hosts', 'certificate_transparency.py'))

    def _inst(self):
        return self.file.Module()

    def _resp(self, *certs, **kw):
        return _CrtshResp(data=[{'name_value': '\n'.join(c)} for c in certs], **kw)

    # ── happy path & basic ingestion ──────────────────────────────────────────

    def test_happy_path_inserts_hosts(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: self._resp(
            ['mail.example.com', 'api.example.com'],
        )
        inst.module_run(['example.com'])
        hosts = sorted(h['host'] for h in inst._hosts)
        self.assertEqual(hosts, ['api.example.com', 'mail.example.com'])

    def test_multiple_sans_per_certificate(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: self._resp(
            ['a.example.com', 'b.example.com', 'c.example.com'],
        )
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._hosts), 3)

    def test_multiple_domains_each_queried(self):
        seen = []
        def _req(method, url, **kw):
            seen.append(url)
            return self._resp([])
        inst = self._inst()
        inst.request = _req
        inst.module_run(['alpha.com', 'beta.com'])
        self.assertEqual(len(seen), 2)
        self.assertIn('alpha.com', seen[0])
        self.assertIn('beta.com', seen[1])

    # ── SAN filtering (the same multi-tenant cert leak we fixed in certspotter) ─

    def test_off_domain_san_on_shared_cert_dropped(self):
        """Multi-tenant cert: a single cert listed s7.example.com alongside
        s7.jcrew.com etc. Only the queried domain's subdomain may be ingested."""
        inst = self._inst()
        inst.request = lambda *a, **kw: self._resp(
            ['s7.example.com', 's7.jcrew.com', 's7.madewell.com', 'dam.ey.com'],
        )
        inst.module_run(['example.com'])
        self.assertEqual([h['host'] for h in inst._hosts], ['s7.example.com'])

    def test_apex_match_kept(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: self._resp(['example.com'])
        inst.module_run(['example.com'])
        self.assertEqual([h['host'] for h in inst._hosts], ['example.com'])

    def test_lookalike_suffix_not_matched(self):
        """`evilexample.com` byte-suffix-matches `example.com` but is a
        different registered domain. Must not be ingested."""
        inst = self._inst()
        inst.request = lambda *a, **kw: self._resp(
            ['evilexample.com', 'mail.evilexample.com'],
        )
        inst.module_run(['example.com'])
        self.assertEqual(inst._hosts, [])

    def test_wildcard_san_skipped(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: self._resp(
            ['*.example.com', 'real.example.com'],
        )
        inst.module_run(['example.com'])
        self.assertEqual([h['host'] for h in inst._hosts], ['real.example.com'])

    def test_match_is_case_insensitive(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: self._resp(['MAIL.Example.COM'])
        inst.module_run(['example.com'])
        self.assertEqual([h['host'] for h in inst._hosts], ['mail.example.com'])

    def test_trailing_dot_normalised(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: self._resp(['mail.example.com.'])
        inst.module_run(['example.com'])
        self.assertEqual([h['host'] for h in inst._hosts], ['mail.example.com'])

    # ── email SANs ────────────────────────────────────────────────────────────

    def test_email_san_inserts_contact_when_host_matches(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: self._resp(['admin@example.com'])
        inst.module_run(['example.com'])
        self.assertEqual([c['email'] for c in inst._contacts], ['admin@example.com'])
        self.assertEqual([h['host'] for h in inst._hosts], ['example.com'])

    def test_email_san_with_off_domain_host_skipped(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: self._resp(
            ['admin@unrelated.com', 'admin@example.com'],
        )
        inst.module_run(['example.com'])
        self.assertEqual([c['email'] for c in inst._contacts], ['admin@example.com'])
        self.assertEqual([h['host'] for h in inst._hosts], ['example.com'])

    # ── null/missing name_value ──────────────────────────────────────────────

    def test_null_name_value_handled_gracefully(self):
        """A cert with name_value=None must not crash the module."""
        inst = self._inst()
        # Build a response where one cert is well-formed and one has null
        inst.request = lambda *a, **kw: _CrtshResp(data=[
            {'name_value': None},
            {'name_value': 'mail.example.com'},
        ])
        inst.module_run(['example.com'])
        self.assertEqual([h['host'] for h in inst._hosts], ['mail.example.com'])

    def test_missing_name_value_key_handled_gracefully(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: _CrtshResp(data=[
            {},  # no name_value key at all
            {'name_value': 'mail.example.com'},
        ])
        inst.module_run(['example.com'])
        self.assertEqual([h['host'] for h in inst._hosts], ['mail.example.com'])

    # ── upstream failure modes (crt.sh is overloaded fairly often) ───────────

    def test_502_alerts_and_errors_loudly(self):
        """502 must surface BOTH via alert() and error(), and the message
        must say enumeration is INCOMPLETE — crt.sh is famously flaky."""
        inst = self._inst()
        inst.request = lambda *a, **kw: _CrtshResp(status=502)
        inst.module_run(['example.com'])
        self.assertEqual(inst._hosts, [])
        alerts = [o for o in inst._output if o.startswith('ALERT:')]
        self.assertTrue(any('UPSTREAM ERROR' in a for a in alerts), msg=f"alerts={alerts}")
        self.assertTrue(any('UPSTREAM ERROR' in e for e in inst._errors), msg=f"errors={inst._errors}")
        joined = ' '.join(alerts + inst._errors)
        self.assertIn('INCOMPLETE', joined)
        self.assertIn("'example.com'", joined)
        self.assertIn('502', joined)

    def test_503_504_429_all_alert_loudly(self):
        for code in (503, 504, 429):
            with self.subTest(code=code):
                inst = self._inst()
                inst.request = lambda *a, _c=code, **kw: _CrtshResp(status=_c)
                inst.module_run(['example.com'])
                joined = ' '.join(inst._output) + ' ' + ' '.join(inst._errors)
                self.assertIn('UPSTREAM ERROR', joined)
                self.assertIn(str(code), joined)

    def test_retry_after_header_surfaced_in_message(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: _CrtshResp(
            status=503, headers={'Retry-After': '120'},
        )
        inst.module_run(['example.com'])
        joined = ' '.join(inst._output) + ' ' + ' '.join(inst._errors)
        self.assertIn('Retry-After', joined)
        self.assertIn('120', joined)

    def test_request_raises_treated_as_loud_upstream_failure(self):
        """Connection errors / timeouts / TLS failures must be surfaced
        as loudly as 5xx so the operator sees the partial enumeration."""
        inst = self._inst()
        def _req(*a, **kw):
            raise ConnectionError("name resolution failed")
        inst.request = _req
        inst.module_run(['example.com'])
        joined = ' '.join(inst._output) + ' ' + ' '.join(inst._errors)
        self.assertIn('UPSTREAM ERROR', joined)
        self.assertIn('INCOMPLETE', joined)
        self.assertIn('ConnectionError', joined)

    def test_non_json_body_does_not_crash(self):
        """crt.sh sometimes returns an HTML error page with status 200.
        Module must error cleanly rather than throwing."""
        inst = self._inst()
        inst.request = lambda *a, **kw: _CrtshResp(status=200, json_raises=True)
        inst.module_run(['example.com'])
        self.assertEqual(inst._hosts, [])
        self.assertTrue(any('Non-JSON' in e for e in inst._errors), msg=f"errors={inst._errors}")

    def test_other_4xx_continues_with_simple_error(self):
        """A 404 etc. should log a normal error and continue — no need
        for the loud alert channel."""
        inst = self._inst()
        inst.request = lambda *a, **kw: _CrtshResp(status=404)
        inst.module_run(['example.com'])
        self.assertEqual(inst._hosts, [])
        self.assertTrue(any('404' in e for e in inst._errors))
        # Should NOT have used the loud alert channel for plain 4xx
        alerts = [o for o in inst._output if o.startswith('ALERT:')]
        self.assertEqual(alerts, [], msg=f"unexpected alerts: {alerts}")


# ═══════════════════════════════════════════════════════════════════════════════
# certspotter
# ═══════════════════════════════════════════════════════════════════════════════

class TestCertspotter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.file = load_mod(_p('recon', 'domains-hosts', 'certspotter.py'))

    def _inst(self):
        return self.file.Module()

    def _cert(self, *dns_names, id='1'):
        return {'id': id, 'dns_names': list(dns_names)}

    def _one_page(self, *certs):
        """Mock returning certs on the first call, then [] to stop pagination."""
        calls = [0]
        def _req(*a, **kw):
            calls[0] += 1
            return Resp(data=list(certs) if calls[0] == 1 else [])
        return _req

    def test_happy_path_inserts_hosts(self):
        inst = self._inst()
        inst.request = self._one_page(
            self._cert('mail.example.com', id='1'),
            self._cert('api.example.com',  id='2'),
        )
        inst.module_run(['example.com'])
        hosts = [h['host'] for h in inst._hosts]
        self.assertIn('mail.example.com', hosts)
        self.assertIn('api.example.com', hosts)

    def test_multiple_dns_names_per_cert(self):
        inst = self._inst()
        inst.request = self._one_page(
            self._cert('a.example.com', 'b.example.com', 'c.example.com', id='1'),
        )
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._hosts), 3)

    def test_email_in_dns_names_inserts_contact(self):
        inst = self._inst()
        inst.request = self._one_page(self._cert('admin@example.com', id='1'))
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._contacts), 1)
        self.assertEqual(inst._contacts[0]['email'], 'admin@example.com')
        self.assertEqual(inst._hosts[0]['host'], 'example.com')

    def test_empty_response_stops_pagination(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(data=[])
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._hosts), 0)

    def test_pagination_uses_last_id(self):
        """Second request must include after=<id of last cert from first page>."""
        calls = []
        def mock_req(*a, **kw):
            calls.append(kw.get('params', {}).copy())
            return Resp(data=[self._cert('p1.example.com', id='42')] if len(calls) == 1 else [])
        inst = self._inst()
        inst.request = mock_req
        inst.module_run(['example.com'])
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1].get('after'), '42')

    def test_non_200_calls_error_and_stops(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(status=500, text='error')
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._hosts), 0)
        self.assertTrue(len(inst._errors) > 0)

    def test_rate_limit_429_alerts_and_errors_loudly(self):
        """A 429 must surface BOTH via alert() (highlighted) and error()
        (red prefix) so a multi-hour pipeline run can't bury the failure.
        The message must explicitly say enumeration is INCOMPLETE."""
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(status=429, text='Too Many Requests')
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._hosts), 0)
        # Hits both channels
        alerts = [o for o in inst._output if o.startswith('ALERT:')]
        self.assertTrue(any('RATE LIMITED' in a for a in alerts),
                        msg=f"alerts={alerts!r}")
        self.assertTrue(any('RATE LIMITED' in e for e in inst._errors),
                        msg=f"errors={inst._errors!r}")
        # Mentions affected domain and partial-coverage warning
        joined = ' '.join(alerts + inst._errors)
        self.assertIn("'example.com'", joined)
        self.assertIn('INCOMPLETE', joined)

    def test_rate_limit_429_includes_retry_after(self):
        """If the upstream sends Retry-After, surface it in the message —
        helps the operator decide whether to wait or move on."""
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(
            status=429, text='Too Many Requests',
            headers={'Retry-After': '3600'},
        )
        inst.module_run(['example.com'])
        joined = ' '.join(o for o in inst._output if o.startswith('ALERT:')) \
                 + ' ' + ' '.join(inst._errors)
        self.assertIn('3600', joined)
        self.assertIn('Retry-After', joined)

    def test_null_dns_names_skipped_gracefully(self):
        """Explicit None dns_names (absent expand) should not crash."""
        inst = self._inst()
        inst.request = self._one_page(
            {'id': '1', 'dns_names': None},
            {'id': '2', 'dns_names': ['ok.example.com']},
        )
        inst.module_run(['example.com'])
        self.assertEqual([h['host'] for h in inst._hosts], ['ok.example.com'])

    def test_wildcard_entries_skipped(self):
        """Wildcard SAN entries are not real hosts; the apex they cover is
        already in the domains table, so skip them rather than ingest a
        literal '*.example.com' string."""
        inst = self._inst()
        inst.request = self._one_page(
            self._cert('*.example.com', 'real.example.com', id='1'),
        )
        inst.module_run(['example.com'])
        hosts = [h['host'] for h in inst._hosts]
        self.assertEqual(hosts, ['real.example.com'])

    # ── multi-tenant cert filtering (Adobe Scene7 / Cloudflare Universal SSL) ─
    # Regression: certspotter previously ingested every SAN on every returned
    # cert, so querying starbucks.com leaked SANs like s7.jcrew.com,
    # s7.sears.com, dam.ey.com from shared certificates.

    def test_off_domain_san_on_shared_cert_dropped(self):
        inst = self._inst()
        inst.request = self._one_page(
            self._cert(
                's7.example.com',     # the SAN that matched our query
                's7.jcrew.com',       # unrelated tenants on the same cert
                's7.madewell.com',
                'dam.ey.com',
                id='1',
            ),
        )
        inst.module_run(['example.com'])
        hosts = [h['host'] for h in inst._hosts]
        self.assertEqual(hosts, ['s7.example.com'])

    def test_apex_match_kept(self):
        inst = self._inst()
        inst.request = self._one_page(self._cert('example.com', id='1'))
        inst.module_run(['example.com'])
        self.assertEqual([h['host'] for h in inst._hosts], ['example.com'])

    def test_lookalike_suffix_not_matched(self):
        """`evilexample.com` ends with `example.com` byte-suffix-wise but is
        a different registered domain. Must not match."""
        inst = self._inst()
        inst.request = self._one_page(
            self._cert('evilexample.com', 'mail.evilexample.com', id='1'),
        )
        inst.module_run(['example.com'])
        self.assertEqual(inst._hosts, [])

    def test_match_is_case_insensitive(self):
        inst = self._inst()
        inst.request = self._one_page(
            self._cert('MAIL.Example.COM', id='1'),
        )
        inst.module_run(['example.com'])
        self.assertEqual([h['host'] for h in inst._hosts], ['mail.example.com'])

    def test_email_off_domain_host_skipped(self):
        """An email SAN whose host part is unrelated to the query domain
        should not insert a host or a contact."""
        inst = self._inst()
        inst.request = self._one_page(
            self._cert('admin@unrelated.com', 'admin@example.com', id='1'),
        )
        inst.module_run(['example.com'])
        self.assertEqual([h['host'] for h in inst._hosts], ['example.com'])
        self.assertEqual(
            [c['email'] for c in inst._contacts],
            ['admin@example.com'],
        )

    def test_trailing_dot_in_san_normalised(self):
        """CT logs sometimes include the trailing root dot. Must still match."""
        inst = self._inst()
        inst.request = self._one_page(
            self._cert('mail.example.com.', id='1'),
        )
        inst.module_run(['example.com'])
        self.assertEqual([h['host'] for h in inst._hosts], ['mail.example.com'])

    def test_multiple_domains_each_queried(self):
        call_count = [0]
        def mock_req(*a, **kw):
            call_count[0] += 1
            return Resp(data=[])
        inst = self._inst()
        inst.request = mock_req
        inst.module_run(['alpha.com', 'beta.com'])
        self.assertEqual(call_count[0], 2)


# ═══════════════════════════════════════════════════════════════════════════════
# hackertarget
# ═══════════════════════════════════════════════════════════════════════════════

class TestHackerTarget(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.file = load_mod(_p('recon', 'domains-hosts', 'hackertarget.py'))

    def _inst(self):
        return self.file.Module()

    def test_happy_path_two_hosts(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(
            text='sub1.example.com,1.2.3.4\nsub2.example.com,5.6.7.8'
        )
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._hosts), 2)
        self.assertEqual(inst._hosts[0]['host'], 'sub1.example.com')
        self.assertEqual(inst._hosts[0]['ip_address'], '1.2.3.4')

    def test_non_200_calls_error(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(status=429, text='Too Many Requests')
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._hosts), 0)
        self.assertTrue(len(inst._errors) > 0)

    def test_empty_response_outputs_no_results(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(text='')
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._hosts), 0)
        self.assertTrue(any('No results' in o for o in inst._output))

    def test_error_prefix_calls_error(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(text='error check your API usage')
        inst.module_run(['example.com'])
        self.assertTrue(len(inst._errors) > 0)

    def test_blank_lines_skipped(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(text='sub.example.com,1.2.3.4\n\n')
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._hosts), 1)

    def test_line_with_multiple_commas_first_comma_split(self):
        """Lines with >1 comma: host is everything before first comma, address is the rest."""
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(
            text='bad.example.com,1.2.3.4,extra\ngood.example.com,5.6.7.8'
        )
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._hosts), 2)

    def test_quota_exceeded_breaks_loop_and_errors(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(text='API count exceeded - Increase Quota with Membership')
        inst.module_run(['example.com', 'other.com'])
        self.assertTrue(any('quota exceeded' in e.lower() for e in inst._errors))
        self.assertEqual(len(inst._hosts), 0)


# ═══════════════════════════════════════════════════════════════════════════════
# wayback
# ═══════════════════════════════════════════════════════════════════════════════

class TestWayback(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.file = load_mod(_p('recon', 'domains-hosts', 'wayback.py'))

    def _inst(self):
        return self.file.Module()

    def _urls(self, *urls):
        return Resp(text='\n'.join(urls))

    def test_happy_path_inserts_subdomains(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: self._urls(
            'https://sub1.example.com/page',
            'http://sub2.example.com/other',
        )
        inst.module_run(['example.com'])
        hosts = [h['host'] for h in inst._hosts]
        self.assertIn('sub1.example.com', hosts)
        self.assertIn('sub2.example.com', hosts)

    def test_deduplicates_same_host_from_multiple_urls(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: self._urls(
            'https://sub.example.com/page1',
            'https://sub.example.com/page2',
            'http://sub.example.com/',
        )
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._hosts), 1)
        self.assertEqual(inst._hosts[0]['host'], 'sub.example.com')

    def test_external_domains_filtered_out(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: self._urls(
            'https://sub.example.com/path',
            'https://evil.com/redirect',
            'https://unrelated.org/page',
        )
        inst.module_run(['example.com'])
        hosts = [h['host'] for h in inst._hosts]
        self.assertEqual(hosts, ['sub.example.com'])

    def test_bare_domain_itself_included(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: self._urls('https://example.com/path')
        inst.module_run(['example.com'])
        self.assertEqual(inst._hosts[0]['host'], 'example.com')

    def test_urls_with_ports_parsed_correctly(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: self._urls('http://sub.example.com:8080/app')
        inst.module_run(['example.com'])
        self.assertEqual(inst._hosts[0]['host'], 'sub.example.com')

    def test_empty_response_outputs_message_no_hosts(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(text='')
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._hosts), 0)
        self.assertTrue(any('No archived URLs' in o for o in inst._output))

    def test_non_200_calls_error_and_continues(self):
        results = [Resp(status=503), Resp(text='https://sub.other.com/')]
        idx = [0]
        def _req(*a, **kw):
            r = results[min(idx[0], len(results) - 1)]
            idx[0] += 1
            return r
        inst = self._inst()
        inst.request = _req
        inst.module_run(['example.com', 'other.com'])
        self.assertTrue(any('503' in e for e in inst._errors))
        self.assertEqual(inst._hosts[0]['host'], 'sub.other.com')

    def test_blank_lines_in_response_skipped(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: self._urls(
            'https://sub.example.com/',
            '',
            '   ',
        )
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._hosts), 1)

    def test_wildcard_url_sent_for_domain(self):
        captured = []
        def _req(method, url, params=None, **kw):
            captured.append(params or {})
            return Resp(text='')
        inst = self._inst()
        inst.request = _req
        inst.module_run(['example.com'])
        self.assertEqual(captured[0]['url'], '*.example.com')

    def test_multiple_domains_each_queried(self):
        call_count = [0]
        def _req(*a, **kw):
            call_count[0] += 1
            return Resp(text='')
        inst = self._inst()
        inst.request = _req
        inst.module_run(['alpha.com', 'beta.com'])
        self.assertEqual(call_count[0], 2)

    def test_output_reports_count(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: self._urls(
            'https://a.example.com/', 'https://b.example.com/'
        )
        inst.module_run(['example.com'])
        self.assertTrue(any('2' in o and 'unique hosts' in o for o in inst._output))


# ═══════════════════════════════════════════════════════════════════════════════
# threatcrowd
# ═══════════════════════════════════════════════════════════════════════════════

class TestThreatCrowd(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.file = load_mod(_p('recon', 'domains-hosts', 'threatcrowd.py'))

    def _inst(self):
        return self.file.Module()

    def test_response_code_1_inserts_hosts(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(data={
            'response_code': '1',
            'subdomains': ['a.example.com', 'b.example.com'],
        })
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._hosts), 2)
        self.assertEqual(inst._hosts[0]['host'], 'a.example.com')

    def test_response_code_0_no_insert(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(data={'response_code': '0', 'subdomains': []})
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._hosts), 0)

    def test_missing_response_code_no_insert(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(data={})
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._hosts), 0)

    def test_response_code_1_with_missing_subdomains_skipped_gracefully(self):
        """BUG: `for subdomain in resp.json().get('subdomains')` raises TypeError
        when the 'subdomains' key is absent (get() returns None). Should treat as
        empty result. Currently crashes."""
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(data={'response_code': '1'})
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._hosts), 0)


# ═══════════════════════════════════════════════════════════════════════════════
# threatminer
# ═══════════════════════════════════════════════════════════════════════════════

class TestThreatMiner(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.file = load_mod(_p('recon', 'domains-hosts', 'threatminer.py'))

    def _inst(self):
        return self.file.Module()

    def test_status_200_inserts_hosts(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(data={
            'status_code': '200',
            'results': ['a.example.com', 'b.example.com'],
        })
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._hosts), 2)

    def test_other_status_no_insert(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(data={'status_code': '404', 'results': []})
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._hosts), 0)

    def test_status_200_with_missing_results_skipped_gracefully(self):
        """BUG: `for subdomain in resp.json().get('results')` raises TypeError
        when the 'results' key is absent (get() returns None). Should treat as
        empty result. Currently crashes."""
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(data={'status_code': '200'})
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._hosts), 0)


# ═══════════════════════════════════════════════════════════════════════════════
# mangle
# ═══════════════════════════════════════════════════════════════════════════════

class TestMangle(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.file = load_mod(_p('recon', 'contacts-contacts', 'mangle.py'))

    def _inst(self, **overrides):
        inst = self.file.Module()
        inst.options = {
            'domain':     None,
            'pattern':    '<fn>.<ln>',
            'substitute': '-',
            'max-length': 30,
            'overwrite':  False,
        }
        inst.options.update(overrides)
        return inst

    # contacts rows: (rowid, first_name, middle_name, last_name, email)

    def test_fn_ln_pattern_produces_correct_username(self):
        inst = self._inst()
        inst.module_run([(1, 'John', None, 'Doe', None)])
        self.assertEqual(inst._queries[0][1][0], 'john.doe')

    def test_domain_appended_when_set(self):
        inst = self._inst(domain='example.com')
        inst.module_run([(1, 'John', None, 'Doe', None)])
        self.assertEqual(inst._queries[0][1][0], 'john.doe@example.com')

    def test_overwrite_false_skips_existing_email(self):
        inst = self._inst()
        inst.module_run([(1, 'John', None, 'Doe', 'existing@x.com')])
        self.assertEqual(len(inst._queries), 0)

    def test_overwrite_true_updates_existing_email(self):
        inst = self._inst(overwrite=True, domain='example.com')
        inst.module_run([(1, 'John', None, 'Doe', 'existing@x.com')])
        self.assertEqual(len(inst._queries), 1)

    def test_max_length_truncation(self):
        inst = self._inst(**{'max-length': 5})
        inst.module_run([(1, 'Johnathan', None, 'Doeling', None)])
        result = inst._queries[0][1][0]
        self.assertLessEqual(len(result), 5)

    def test_fi_ln_pattern(self):
        inst = self._inst(pattern='<fi><ln>')
        inst.module_run([(1, 'John', None, 'Doe', None)])
        self.assertEqual(inst._queries[0][1][0], 'jdoe')

    def test_spaces_in_name_replaced_by_substitute(self):
        inst = self._inst(substitute='-')
        inst.module_run([(1, 'Mary Jane', None, 'Watson', None)])
        result = inst._queries[0][1][0]
        self.assertIn('mary-jane', result)

    def test_missing_first_name_handled_gracefully(self):
        inst = self._inst(pattern='<fi><ln>')
        inst.module_run([(1, None, None, 'Doe', None)])
        # <fi> becomes '' when fname is None
        result = inst._queries[0][1][0]
        self.assertEqual(result, 'doe')


# ═══════════════════════════════════════════════════════════════════════════════
# unmangle
# ═══════════════════════════════════════════════════════════════════════════════

class TestUnmangle(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            cls.file = load_mod(_p('recon', 'contacts-contacts', 'unmangle.py'))
        except ImportError as e:
            raise unittest.SkipTest(f'unmangle deps unavailable: {e}')

    def _inst(self, **overrides):
        inst = self.file.Module()
        inst.options = {'pattern': '<fn>.<ln>', 'overwrite': False}
        inst.options.update(overrides)
        return inst

    # contacts rows: (rowid, first_name, middle_name, last_name, email)

    def test_fn_ln_pattern_extracts_names(self):
        inst = self._inst()
        inst.module_run([(1, None, None, None, 'john.doe@example.com')])
        self.assertEqual(len(inst._queries), 1)
        values = inst._queries[0][1]
        self.assertIn('John', values)
        self.assertIn('Doe', values)

    def test_no_match_skips_contact(self):
        inst = self._inst()
        # No dot in username, so <fn>.<ln> pattern won't match
        inst.module_run([(1, None, None, None, 'johndoe@example.com')])
        self.assertEqual(len(inst._queries), 0)

    def test_invalid_regex_calls_error_and_returns(self):
        inst = self._inst(pattern='[invalid(regex')
        inst.module_run([(1, None, None, None, 'john.doe@example.com')])
        self.assertTrue(len(inst._errors) > 0)
        self.assertEqual(len(inst._queries), 0)

    def test_overwrite_false_preserves_existing_names(self):
        inst = self._inst()
        inst.module_run([(1, 'Existing', None, 'Name', 'john.doe@example.com')])
        self.assertEqual(len(inst._queries), 0)

    def test_overwrite_true_replaces_existing_names(self):
        inst = self._inst(overwrite=True)
        inst.module_run([(1, 'Existing', None, 'Name', 'john.doe@example.com')])
        self.assertEqual(len(inst._queries), 1)

    def test_custom_regex_with_named_groups(self):
        inst = self._inst(pattern=r'(?P<first_name>\w+)_(?P<last_name>\w+)')
        inst.module_run([(1, None, None, None, 'alice_smith@example.com')])
        self.assertEqual(len(inst._queries), 1)
        values = inst._queries[0][1]
        self.assertIn('Alice', values)
        self.assertIn('Smith', values)

    def test_predefined_fn_ln_pattern_resolves(self):
        inst = self._inst()
        # Confirm predefined patterns table is populated
        self.assertIn('<fn>.<ln>', self.file.Module.patterns)


# ═══════════════════════════════════════════════════════════════════════════════
# whois_pocs
# ═══════════════════════════════════════════════════════════════════════════════

class TestWhoisPocs(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.file = load_mod(_p('recon', 'domains-contacts', 'whois_pocs.py'))

    def _inst(self):
        return self.file.Module()

    def _poc_data(self, email='alice@example.com'):
        return {
            'poc': {
                'firstName': {'$': 'Alice'},
                'lastName':  {'$': 'Smith'},
                'emails':    {'email': {'$': email}},
                'city':      {'$': 'Springfield'},
                'iso3166-2': {'$': 'IL'},
                'iso3166-1': {'name': {'$': 'United States'}},
            }
        }

    def test_no_results_string_outputs_message(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(text='Sorry, there were no results.', data={})
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._contacts), 0)
        self.assertTrue(any('No contacts' in o for o in inst._output))

    def test_single_poc_ref_dict_inserts_contact(self):
        inst = self._inst()
        calls = [0]
        def _req(*a, **kw):
            if calls[0] == 0:
                calls[0] += 1
                return Resp(text='ok', data={'pocs': {'pocRef': {'@handle': 'ALICE-ARIN'}}})
            return Resp(text='ok', data=self._poc_data())
        inst.request = _req
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._contacts), 1)
        self.assertEqual(inst._contacts[0]['email'], 'alice@example.com')

    def test_list_of_poc_refs_inserts_all(self):
        inst = self._inst()
        calls = [0]
        def _req(*a, **kw):
            if calls[0] == 0:
                calls[0] += 1
                return Resp(text='ok', data={'pocs': {'pocRef': [
                    {'@handle': 'A-ARIN'},
                    {'@handle': 'B-ARIN'},
                ]}})
            return Resp(text='ok', data=self._poc_data())
        inst.request = _req
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._contacts), 2)

    def test_email_domain_mismatch_skips_insert(self):
        inst = self._inst()
        calls = [0]
        def _req(*a, **kw):
            if calls[0] == 0:
                calls[0] += 1
                return Resp(text='ok', data={'pocs': {'pocRef': {'@handle': 'X'}}})
            return Resp(text='ok', data=self._poc_data(email='bob@otherdomain.com'))
        inst.request = _req
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._contacts), 0)

    def test_no_first_name_handled(self):
        """firstName is optional in ARIN POC records."""
        inst = self._inst()
        calls = [0]
        poc_no_fname = {
            'poc': {
                'lastName':  {'$': 'Smith'},
                'emails':    {'email': {'$': 'nofirst@example.com'}},
                'city':      {'$': 'NYC'},
                'iso3166-1': {'name': {'$': 'United States'}},
            }
        }
        def _req(*a, **kw):
            if calls[0] == 0:
                calls[0] += 1
                return Resp(text='ok', data={'pocs': {'pocRef': {'@handle': 'X'}}})
            return Resp(text='ok', data=poc_no_fname)
        inst.request = _req
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._contacts), 1)
        self.assertIsNone(inst._contacts[0]['first_name'])

    def test_missing_last_name_skipped_gracefully(self):
        """BUG: poc['lastName']['$'] has no guard (unlike firstName which checks
        'if firstName in poc'). Raises KeyError if ARIN returns a POC without
        lastName. Should skip the contact. Currently crashes."""
        inst = self._inst()
        calls = [0]
        poc_no_lname = {
            'poc': {
                'firstName': {'$': 'John'},
                'emails':    {'email': {'$': 'jdoe@example.com'}},
                'city':      {'$': 'NYC'},
                'iso3166-1': {'name': {'$': 'United States'}},
                # no 'lastName' key
            }
        }
        def _req(*a, **kw):
            if calls[0] == 0:
                calls[0] += 1
                return Resp(text='ok', data={'pocs': {'pocRef': {'@handle': 'X'}}})
            return Resp(text='ok', data=poc_no_lname)
        inst.request = _req
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._contacts), 0)  # incomplete POC skipped


# ═══════════════════════════════════════════════════════════════════════════════
# whois_miner (companies-multi)
# ═══════════════════════════════════════════════════════════════════════════════

class TestWhoisMiner(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.file = load_mod(_p('recon', 'companies-multi', 'whois_miner.py'))

    def _inst(self):
        return self.file.Module()

    def test_enum_ref_with_list_returns_list(self):
        result = self.file._enum_ref([{'a': 1}, {'b': 2}])
        self.assertEqual(result, [{'a': 1}, {'b': 2}])

    def test_enum_ref_with_single_dict_wraps_in_list(self):
        result = self.file._enum_ref({'a': 1})
        self.assertEqual(result, [{'a': 1}])

    def test_whois_location_parses_full_object(self):
        obj = {
            'streetAddress': {'line': {'$': '123 Main St'}},
            'city':          {'$': 'springfield'},
            'iso3166-2':     {'$': 'il'},
            'postalCode':    {'$': '62701'},
            'iso3166-1':     {'name': {'$': 'united states'}},
        }
        loc = self.file.WhoisLocation(obj)
        self.assertEqual(loc.city, 'Springfield')
        self.assertEqual(loc.state, 'IL')
        self.assertEqual(loc.postal_code, '62701')
        self.assertIn('Main St', loc.address)
        self.assertIn('United States', loc.address)

    def test_whois_location_optional_fields_absent(self):
        obj = {
            'city':      {'$': 'London'},
            'iso3166-1': {'name': {'$': 'United Kingdom'}},
        }
        loc = self.file.WhoisLocation(obj)
        self.assertIsNone(loc.street_address)
        self.assertIsNone(loc.state)
        self.assertEqual(loc.country, 'United Kingdom')

    def test_street_address_as_empty_list_skipped_gracefully(self):
        """BUG: _enum_ref(obj['streetAddress']['line'])[-1] raises IndexError
        if 'line' is an empty list. ARIN occasionally returns streetAddress with
        an empty line array. Should treat as no street address. Currently crashes."""
        obj = {
            'streetAddress': {'line': []},
            'city':          {'$': 'Boston'},
            'iso3166-1':     {'name': {'$': 'United States'}},
        }
        loc = self.file.WhoisLocation(obj)
        self.assertIsNone(loc.street_address)

    def test_no_results_string_skips_entity(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(
            text='Sorry, there were no results.',
            data={'orgs': {}, 'customers': {}}
        )
        inst.module_run(['TestCorp'])
        self.assertEqual(len(inst._companies), 0)

    def test_happy_path_full_flow(self):
        """
        Exercises the full org → entity detail → nets → pocs chain.
        Call sequence for one org entity:
          0: org search (_request)
          1: entity detail (direct request)
          2: nets (_request)
          3: pocs (_request)
          4: POC detail (direct request)
          5: customer search (_request) → no results
        """
        inst = self._inst()
        calls = [0]

        def _req(*a, **kw):
            c = calls[0]
            calls[0] += 1
            if c == 0:   # org search
                return Resp(text='ok', data={'orgs': {'orgRef': [{
                    '@name': 'Example Corp',
                    '@handle': 'EXAMPLECORP',
                    '$': 'https://whois.arin.net/rest/org/EXAMPLECORP',
                }]}})
            elif c == 1: # entity detail
                return Resp(text='ok', data={'org': {
                    'streetAddress': {'line': {'$': '1 Main St'}},
                    'city':          {'$': 'Boston'},
                    'iso3166-1':     {'name': {'$': 'United States'}},
                }})
            elif c == 2: # nets
                return Resp(text='ok', data={'nets': {'netRef': [{
                    '@startAddress': '1.2.3.0',
                    '@endAddress':   '1.2.3.255',
                }]}})
            elif c == 3: # pocs
                return Resp(text='ok', data={'pocs': {'pocLinkRef': [{
                    '$':             'https://whois.arin.net/rest/poc/JDOE',
                    '@description':  'Tech',
                }]}})
            elif c == 4: # POC detail
                return Resp(text='ok', data={'poc': {
                    'firstName': {'$': 'John'},
                    'lastName':  {'$': 'Doe'},
                    'emails':    {'email': {'$': 'jdoe@example.com'}},
                    'city':      {'$': 'Boston'},
                    'iso3166-1': {'name': {'$': 'United States'}},
                }})
            # customer search → no results
            return Resp(text='Sorry, there were no results.', data={'customers': {}})

        inst.request = _req
        inst.module_run(['TestCorp'])

        self.assertEqual(len(inst._companies), 1)
        self.assertEqual(inst._companies[0]['company'], 'Example Corp')
        self.assertEqual(len(inst._locations), 1)
        self.assertIn('Main St', inst._locations[0]['street_address'])
        self.assertEqual(len(inst._netblocks), 1)
        self.assertEqual(inst._netblocks[0], '1.2.3.0/24')
        self.assertEqual(len(inst._contacts), 1)
        self.assertEqual(inst._contacts[0]['email'], 'jdoe@example.com')
        self.assertEqual(inst._contacts[0]['first_name'], 'John')
        self.assertEqual(inst._contacts[0]['last_name'], 'Doe')


# ═══════════════════════════════════════════════════════════════════════════════
# whois_orgs (netblocks-companies)
# ═══════════════════════════════════════════════════════════════════════════════

class TestWhoisOrgs(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.file = load_mod(_p('recon', 'netblocks-companies', 'whois_orgs.py'))

    def _inst(self):
        return self.file.Module()

    def test_no_record_found_outputs_message_and_no_insert(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(
            text='No record found for the handle provided.',
            data={'net': {}}
        )
        inst.module_run(['192.168.1.0/24'])
        self.assertEqual(len(inst._companies), 0)
        self.assertTrue(any('No companies' in o for o in inst._output))

    def test_orgref_present_inserts_company(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(
            text='ok',
            data={'net': {
                'orgRef': {'@name': 'Example Corp', '$': 'https://whois.arin.net/rest/org/EX'}
            }}
        )
        inst.module_run(['192.168.1.0/24'])
        # module issues 2 URLs (cidr + ip), each returning an orgRef
        self.assertEqual(len(inst._companies), 2)
        self.assertEqual(inst._companies[0]['company'], 'Example Corp')

    def test_no_ref_in_net_no_insert(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(text='ok', data={'net': {}})
        inst.module_run(['10.0.0.0/8'])
        self.assertEqual(len(inst._companies), 0)

    def test_customer_ref_also_handled(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(
            text='ok',
            data={'net': {
                'customerRef': {'@name': 'Acme Inc', '$': 'https://whois.arin.net/rest/customer/AC'}
            }}
        )
        inst.module_run(['1.2.3.0/24'])
        self.assertTrue(len(inst._companies) > 0)
        self.assertEqual(inst._companies[0]['company'], 'Acme Inc')


# ═══════════════════════════════════════════════════════════════════════════════
# nmap XML importer
# ═══════════════════════════════════════════════════════════════════════════════

class TestNmapImporter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.file = load_mod(_p('import', 'nmap.py'))

    def _write_xml(self, xml_str):
        f = tempfile.NamedTemporaryFile(
            mode='w', suffix='.xml', delete=False, dir=_TMP
        )
        f.write(xml_str)
        f.close()
        return f.name

    def test_hostname_and_open_port_all_inserted(self):
        fname = self._write_xml('''<?xml version="1.0"?>
<nmaprun>
  <host>
    <address addr="1.2.3.4"/>
    <hostnames><hostname name="host.example.com"/></hostnames>
    <ports>
      <port protocol="tcp" portid="443">
        <state state="open"/>
      </port>
    </ports>
  </host>
</nmaprun>''')
        inst = self.file.Module()
        inst.options = {'filename': fname}
        inst.module_run()
        self.assertIn('host.example.com', inst._domains)
        self.assertEqual(inst._hosts[0]['host'], 'host.example.com')
        self.assertEqual(inst._hosts[0]['ip_address'], '1.2.3.4')
        self.assertEqual(inst._ports[0]['port'], '443')
        self.assertEqual(inst._ports[0]['protocol'], 'tcp')

    def test_no_hostname_inserts_ip_only(self):
        fname = self._write_xml('''<?xml version="1.0"?>
<nmaprun>
  <host>
    <address addr="5.6.7.8"/>
  </host>
</nmaprun>''')
        inst = self.file.Module()
        inst.options = {'filename': fname}
        inst.module_run()
        self.assertEqual(len(inst._hosts), 1)
        self.assertIsNone(inst._hosts[0]['host'])
        self.assertEqual(inst._hosts[0]['ip_address'], '5.6.7.8')

    def test_closed_port_not_inserted(self):
        fname = self._write_xml('''<?xml version="1.0"?>
<nmaprun>
  <host>
    <address addr="1.2.3.4"/>
    <ports>
      <port protocol="tcp" portid="22"><state state="open"/></port>
      <port protocol="tcp" portid="80"><state state="closed"/></port>
    </ports>
  </host>
</nmaprun>''')
        inst = self.file.Module()
        inst.options = {'filename': fname}
        inst.module_run()
        self.assertEqual(len(inst._ports), 1)
        self.assertEqual(inst._ports[0]['port'], '22')

    def test_no_ports_section_no_crash(self):
        fname = self._write_xml('''<?xml version="1.0"?>
<nmaprun>
  <host>
    <address addr="9.9.9.9"/>
    <hostnames><hostname name="dns.example.com"/></hostnames>
  </host>
</nmaprun>''')
        inst = self.file.Module()
        inst.options = {'filename': fname}
        inst.module_run()
        self.assertEqual(len(inst._hosts), 1)
        self.assertEqual(len(inst._ports), 0)

    def test_multiple_hosts_all_processed(self):
        fname = self._write_xml('''<?xml version="1.0"?>
<nmaprun>
  <host>
    <address addr="1.1.1.1"/>
    <hostnames><hostname name="one.example.com"/></hostnames>
  </host>
  <host>
    <address addr="2.2.2.2"/>
    <hostnames><hostname name="two.example.com"/></hostnames>
  </host>
</nmaprun>''')
        inst = self.file.Module()
        inst.options = {'filename': fname}
        inst.module_run()
        self.assertEqual(len(inst._hosts), 2)

    def test_port_without_state_element_skips_only_bad_port(self):
        """BUG: host_port.find('state').get('state') raises AttributeError when
        <state> element is absent. The outer `except AttributeError: pass` was
        meant to handle a missing <ports> element, but it also catches this
        error — so ALL subsequent ports are silently lost too. A valid open port
        after a malformed one should still be inserted. Currently it is not."""
        fname = self._write_xml('''<?xml version="1.0"?>
<nmaprun>
  <host>
    <address addr="1.2.3.4"/>
    <ports>
      <port protocol="tcp" portid="80"/>
      <port protocol="tcp" portid="443"><state state="open"/></port>
    </ports>
  </host>
</nmaprun>''')
        inst = self.file.Module()
        inst.options = {'filename': fname}
        inst.module_run()
        # Port 80 has no <state> so it should be skipped.
        # Port 443 is valid and open — it should be inserted.
        # Currently 0 ports are inserted because the loop exits on the first error.
        self.assertEqual(len(inst._ports), 1)
        self.assertEqual(inst._ports[0]['port'], '443')


# ═══════════════════════════════════════════════════════════════════════════════
# pgp_search
# ═══════════════════════════════════════════════════════════════════════════════

class TestPgpSearch(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.file = load_mod(_p('recon', 'domains-contacts', 'pgp_search.py'))

    def _inst(self):
        return self.file.Module()

    def test_happy_path_inserts_contact(self):
        inst = self._inst()
        # pgp_search splits on [\n<>] and matches ^(.*)&lt;(.*)&gt;$
        inst.request = lambda *a, **kw: Resp(
            text='John Smith &lt;john.smith@example.com&gt;'
        )
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._contacts), 1)
        self.assertEqual(inst._contacts[0]['email'], 'john.smith@example.com')

    def test_no_matching_lines_outputs_no_results(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(text='<html>no pgp keys found</html>')
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._contacts), 0)
        self.assertTrue(any('No results' in o for o in inst._output))

    def test_email_domain_mismatch_not_inserted(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(
            text='Bob Jones &lt;bob@otherdomain.com&gt;'
        )
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._contacts), 0)

    def test_parenthesized_comment_stripped(self):
        """Names like 'Alice (Work) &lt;alice@example.com&gt;' are handled."""
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(
            text='Alice (Work Account) &lt;alice@example.com&gt;'
        )
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._contacts), 1)

    def test_deduplication_of_results(self):
        inst = self._inst()
        # Same entry repeated on two lines
        line = 'Jane Doe &lt;jane@example.com&gt;'
        inst.request = lambda *a, **kw: Resp(text=f'{line}\n{line}')
        inst.module_run(['example.com'])
        self.assertEqual(len(inst._contacts), 1)


# ═══════════════════════════════════════════════════════════════════════════════
# reporting/json
# ═══════════════════════════════════════════════════════════════════════════════

class TestReportingJson(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.file = load_mod(_p('reporting', 'json.py'))

    def test_writes_valid_json_file(self):
        outfile = os.path.join(_TMP, 'rpt_test.json')
        inst = self.file.Module()
        inst.options = {'tables': 'hosts', 'filename': outfile}
        inst.get_columns = lambda t: [('host',), ('ip_address',)]
        inst.query      = lambda sql, v=None: [('host.example.com', '1.2.3.4')]
        inst.module_run()
        self.assertTrue(os.path.exists(outfile))
        with open(outfile) as f:
            data = json.load(f)
        self.assertIn('hosts', data)
        self.assertEqual(data['hosts'][0]['host'], 'host.example.com')
        self.assertEqual(data['hosts'][0]['ip_address'], '1.2.3.4')

    def test_output_message_contains_record_count(self):
        outfile = os.path.join(_TMP, 'rpt_count.json')
        inst = self.file.Module()
        inst.options = {'tables': 'hosts', 'filename': outfile}
        inst.get_columns = lambda t: [('host',)]
        inst.query      = lambda sql, v=None: [('a.com',), ('b.com',)]
        inst.module_run()
        self.assertTrue(any('2' in o for o in inst._output))

    def test_multiple_tables_merged_into_one_file(self):
        outfile = os.path.join(_TMP, 'rpt_multi.json')
        inst = self.file.Module()
        inst.options = {'tables': 'hosts, contacts', 'filename': outfile}
        inst.get_columns = lambda t: [('id',)]
        inst.query      = lambda sql, v=None: [('row1',)]
        inst.module_run()
        with open(outfile) as f:
            data = json.load(f)
        self.assertIn('hosts', data)
        self.assertIn('contacts', data)

    def test_empty_table_writes_empty_list(self):
        outfile = os.path.join(_TMP, 'rpt_empty.json')
        inst = self.file.Module()
        inst.options = {'tables': 'hosts', 'filename': outfile}
        inst.get_columns = lambda t: [('host',)]
        inst.query      = lambda sql, v=None: []
        inst.module_run()
        with open(outfile) as f:
            data = json.load(f)
        self.assertEqual(data['hosts'], [])


# ═══════════════════════════════════════════════════════════════════════════════
# reporting/csv
# ═══════════════════════════════════════════════════════════════════════════════

class TestReportingCsv(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.file = load_mod(_p('reporting', 'csv.py'))

    def test_writes_csv_rows(self):
        outfile = os.path.join(_TMP, 'rpt_rows.csv')
        inst = self.file.Module()
        inst.options = {'table': 'hosts', 'filename': outfile, 'headers': False}
        inst.get_columns = lambda t: [('host',), ('ip_address',)]
        inst.query      = lambda sql, v=None: [('host.example.com', '1.2.3.4')]
        inst.module_run()
        self.assertTrue(os.path.exists(outfile))
        with open(outfile) as f:
            content = f.read()
        self.assertIn('host.example.com', content)
        self.assertIn('1.2.3.4', content)

    def test_csv_injection_at_symbol_prefixed(self):
        outfile = os.path.join(_TMP, 'rpt_inj.csv')
        inst = self.file.Module()
        inst.options = {'table': 'hosts', 'filename': outfile, 'headers': False}
        inst.get_columns = lambda t: [('host',)]
        inst.query      = lambda sql, v=None: [('@evil.formula',)]
        inst.module_run()
        with open(outfile) as f:
            content = f.read()
        self.assertIn(' @evil.formula', content)

    def test_csv_injection_dash_prefixed(self):
        outfile = os.path.join(_TMP, 'rpt_dash.csv')
        inst = self.file.Module()
        inst.options = {'table': 'hosts', 'filename': outfile, 'headers': False}
        inst.get_columns = lambda t: [('host',)]
        inst.query      = lambda sql, v=None: [('-1+1',)]
        inst.module_run()
        with open(outfile) as f:
            content = f.read()
        self.assertIn(' -1+1', content)

    def test_headers_written_when_enabled(self):
        outfile = os.path.join(_TMP, 'rpt_hdr.csv')
        inst = self.file.Module()
        inst.options = {'table': 'hosts', 'filename': outfile, 'headers': True}
        inst.get_columns = lambda t: [('host',), ('ip_address',)]
        inst.query      = lambda sql, v=None: []
        inst.module_run()
        with open(outfile) as f:
            first_line = f.readline()
        self.assertIn('host', first_line)
        self.assertIn('ip_address', first_line)

    def test_integer_cell_handled_gracefully(self):
        """BUG: `if cell and cell[0] in badcharacters` assumes cell is a string.
        SQLite can return integers (e.g. a port number column). cell[0] on an int
        raises TypeError. Should coerce to string first. Currently crashes."""
        outfile = os.path.join(_TMP, 'rpt_int.csv')
        inst = self.file.Module()
        inst.options = {'table': 'ports', 'filename': outfile, 'headers': False}
        inst.get_columns = lambda t: [('port',)]
        inst.query      = lambda sql, v=None: [(443,)]  # integer, not string
        inst.module_run()
        with open(outfile) as f:
            content = f.read()
        self.assertIn('443', content)

    def test_record_count_in_output(self):
        outfile = os.path.join(_TMP, 'rpt_cnt.csv')
        inst = self.file.Module()
        inst.options = {'table': 'hosts', 'filename': outfile, 'headers': False}
        inst.get_columns = lambda t: [('host',)]
        inst.query      = lambda sql, v=None: [('a.com',), ('b.com',), ('c.com',)]
        inst.module_run()
        self.assertTrue(any('3' in o for o in inst._output))



# ═══════════════════════════════════════════════════════════════════════════════
# Shodan modules (mocked API — zero real network calls)
# ═══════════════════════════════════════════════════════════════════════════════

@_SKIP_SHODAN
class TestShodanOrg(unittest.TestCase):
    """shodan_org.py — searches by org: operator."""

    @classmethod
    def setUpClass(cls):
        cls.file = load_mod(_p('recon', 'companies-multi', 'shodan_org.py'))

    def _inst(self):
        inst = self.file.Module()
        inst.options = {'limit': 0}
        inst.keys    = {'shodan_api': 'test_key'}
        return inst

    def _single_result(self, **extra):
        base = {'ip_str': '1.2.3.4', 'port': 443, 'transport': 'tcp'}
        base.update(extra)
        return {'total': 1, 'matches': [base]}

    def test_host_with_hostname_inserts_host_and_port(self):
        inst = self._inst()
        with patch('shodan.Shodan') as MockShodan:
            MockShodan.return_value.search.return_value = self._single_result(
                hostnames=['host.example.com']
            )
            inst.module_run(['Example Corp'])
        self.assertEqual(len(inst._hosts), 1)
        self.assertEqual(inst._hosts[0]['host'], 'host.example.com')
        self.assertEqual(len(inst._ports), 1)
        self.assertEqual(inst._ports[0]['port'], 443)

    def test_missing_hostnames_key_inserts_port_with_ip(self):
        """BUG: except KeyError block references undefined 'ipaddr' (should be
        port['ip_str']), causing NameError. A match with no 'hostnames' key
        should fall back to inserting by IP only. Currently crashes."""
        inst = self._inst()
        with patch('shodan.Shodan') as MockShodan:
            MockShodan.return_value.search.return_value = self._single_result()
            inst.module_run(['Example Corp'])
        self.assertEqual(len(inst._ports), 1)
        self.assertEqual(inst._ports[0]['ip_address'], '1.2.3.4')

    def test_empty_result_set_no_inserts(self):
        inst = self._inst()
        with patch('shodan.Shodan') as MockShodan:
            MockShodan.return_value.search.return_value = {'total': 0, 'matches': []}
            inst.module_run(['Example Corp'])
        self.assertEqual(len(inst._hosts), 0)
        self.assertEqual(len(inst._ports), 0)


@_SKIP_SHODAN
class TestShodanNet(unittest.TestCase):
    """shodan_net.py — searches by net: operator, no undefined-variable bug."""

    @classmethod
    def setUpClass(cls):
        cls.file = load_mod(_p('recon', 'netblocks-hosts', 'shodan_net.py'))

    def _inst(self):
        inst = self.file.Module()
        inst.options = {'limit': 0}
        inst.keys    = {'shodan_api': 'test_key'}
        return inst

    def _single_result(self, **extra):
        base = {'ip_str': '192.168.1.1', 'port': 22, 'transport': 'tcp', 'hostnames': []}
        base.update(extra)
        return {'total': 1, 'matches': [base]}

    def test_host_with_hostname_inserts_hostname_and_port(self):
        inst = self._inst()
        with patch('shodan.Shodan') as MockShodan:
            MockShodan.return_value.search.return_value = self._single_result(
                hostnames=['router.example.com']
            )
            inst.module_run(['192.168.1.0/24'])
        self.assertEqual(inst._hosts[0]['host'], 'router.example.com')
        self.assertEqual(inst._ports[0]['host'], 'router.example.com')

    def test_host_without_hostname_inserts_ip_only(self):
        inst = self._inst()
        with patch('shodan.Shodan') as MockShodan:
            MockShodan.return_value.search.return_value = self._single_result(hostnames=[])
            inst.module_run(['10.0.0.0/8'])
        self.assertIsNone(inst._hosts[0]['host'])
        self.assertEqual(inst._hosts[0]['ip_address'], '192.168.1.1')
        # Port inserted with ip_address only
        self.assertNotIn('host', inst._ports[0])


@_SKIP_SHODAN
class TestShodanIp(unittest.TestCase):
    """shodan_ip.py — uses api.host() not api.search()."""

    @classmethod
    def setUpClass(cls):
        cls.file = load_mod(_p('recon', 'hosts-ports', 'shodan_ip.py'))

    def _inst(self):
        inst = self.file.Module()
        inst.options = {'limit': 0}
        inst.keys    = {'shodan_api': 'test_key'}
        return inst

    def test_host_with_hostnames_inserts_ports(self):
        inst = self._inst()
        with patch('shodan.Shodan') as MockShodan:
            MockShodan.return_value.host.return_value = {
                'data': [{'hostnames': ['host.example.com'], 'port': 443, 'transport': 'tcp'}]
            }
            inst.module_run(['1.2.3.4'])
        self.assertEqual(len(inst._ports), 1)
        self.assertEqual(inst._ports[0]['host'], 'host.example.com')
        self.assertEqual(inst._ports[0]['port'], 443)

    def test_host_without_hostnames_key_falls_to_except(self):
        """Missing 'hostnames' key → KeyError → insert_ports with ip only (no bug here)."""
        inst = self._inst()
        with patch('shodan.Shodan') as MockShodan:
            MockShodan.return_value.host.return_value = {
                'data': [{'port': 80, 'transport': 'tcp'}]
            }
            inst.module_run(['1.2.3.4'])
        self.assertEqual(len(inst._ports), 1)
        self.assertEqual(inst._ports[0]['ip_address'], '1.2.3.4')

    def test_api_error_suppressed(self):
        import shodan
        inst = self._inst()
        with patch('shodan.Shodan') as MockShodan:
            MockShodan.return_value.host.side_effect = shodan.exception.APIError('No info')
            inst.module_run(['9.9.9.9'])
        self.assertEqual(len(inst._ports), 0)


@_SKIP_SHODAN
class TestShodanHostname(unittest.TestCase):
    """
    shodan_hostname.py — searches by hostname: operator.
    Contains two known bugs: undefined 'ipaddr' and self.insert_host() typo.
    """

    @classmethod
    def setUpClass(cls):
        cls.file = load_mod(_p('recon', 'domains-hosts', 'shodan_hostname.py'))

    def _inst(self):
        inst = self.file.Module()
        inst.options = {'limit': 0}
        inst.keys    = {'shodan_api': 'test_key'}
        return inst

    def test_host_with_hostnames_inserts_correctly(self):
        inst = self._inst()
        with patch('shodan.Shodan') as MockShodan:
            MockShodan.return_value.search.return_value = {
                'total': 1,
                'matches': [{'ip_str': '1.2.3.4', 'port': 443, 'transport': 'tcp',
                             'hostnames': ['host.example.com']}]
            }
            inst.module_run(['example.com'])
        self.assertEqual(len(inst._hosts), 1)
        self.assertEqual(inst._hosts[0]['host'], 'host.example.com')

    def test_missing_hostnames_key_inserts_port_with_ip(self):
        """BUG: except KeyError block references undefined 'ipaddr' (NameError)
        and calls self.insert_host() instead of self.insert_hosts() (AttributeError).
        A match with no 'hostnames' key should fall back to inserting by IP only.
        Currently crashes on both counts."""
        inst = self._inst()
        with patch('shodan.Shodan') as MockShodan:
            MockShodan.return_value.search.return_value = {
                'total': 1,
                'matches': [{'ip_str': '1.2.3.4', 'port': 80, 'transport': 'tcp'}]
            }
            inst.module_run(['example.com'])
        self.assertEqual(len(inst._ports), 1)
        self.assertEqual(inst._ports[0]['ip_address'], '1.2.3.4')


# ═══════════════════════════════════════════════════════════════════════════════
# asn_lookup
# ═══════════════════════════════════════════════════════════════════════════════

class TestAsnLookup(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.file = load_mod(_p('recon', 'companies-netblocks', 'asn_lookup.py'))

    def _inst(self, api_key=None):
        inst = self.file.Module()
        inst.keys = {'hackertarget_api': api_key} if api_key else {}
        return inst

    # HackerTarget response for a company search: list of "ASNNUM","NAME" lines
    def _asn_search_resp(self, *entries):
        lines = '\n'.join(f'"{num}","{name}"' for num, name in entries)
        return Resp(text=lines)

    # HackerTarget response for a prefix lookup: ASN descriptor line + CIDR lines
    def _prefix_resp(self, asn_num, asn_name, *prefixes):
        lines = [f'"{asn_num}","{asn_name}"'] + list(prefixes)
        return Resp(text='\n'.join(lines))

    def test_happy_path_inserts_prefixes(self):
        inst = self._inst()
        calls = [0]
        def _req(method, url, params=None, **kw):
            calls[0] += 1
            if calls[0] == 1:
                return self._asn_search_resp(('15169', 'GOOGLE, US'))
            return self._prefix_resp('15169', 'GOOGLE, US', '8.8.8.0/24', '8.8.4.0/24')
        inst.request = _req
        inst.module_run(['Google'])
        self.assertEqual(inst._netblocks, ['8.8.8.0/24', '8.8.4.0/24'])

    def test_no_matching_asn_outputs_message(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: self._asn_search_resp(('99999', 'UNRELATED-ORG, DE'))
        inst.module_run(['Google'])
        self.assertEqual(inst._netblocks, [])
        self.assertTrue(any('No ASNs matched' in o for o in inst._output))

    def test_api_error_text_outputs_message(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(text='error check your query')
        inst.module_run(['Google'])
        self.assertEqual(inst._netblocks, [])
        self.assertTrue(any('No ASNs found' in o for o in inst._output))

    def test_429_on_search_breaks_loop(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(status=429)
        inst.module_run(['Google', 'Amazon'])
        self.assertTrue(any('Rate limit' in e for e in inst._errors))
        self.assertEqual(inst._netblocks, [])

    def test_429_on_prefix_fetch_returns_early(self):
        inst = self._inst()
        calls = [0]
        def _req(method, url, params=None, **kw):
            calls[0] += 1
            if calls[0] == 1:
                return self._asn_search_resp(('15169', 'GOOGLE, US'))
            return Resp(status=429)
        inst.request = _req
        inst.module_run(['Google'])
        self.assertTrue(any('Rate limit' in e for e in inst._errors))
        self.assertEqual(inst._netblocks, [])

    def test_non_200_search_response_continues(self):
        inst = self._inst()
        results = [Resp(status=503), self._asn_search_resp(('15169', 'GOOGLE, US'))]
        idx = [0]
        def _req(*a, **kw):
            r = results[min(idx[0], len(results) - 1)]
            idx[0] += 1
            return r
        inst.request = _req
        inst.module_run(['Google', 'Google'])
        self.assertTrue(any('Unexpected response' in e for e in inst._errors))

    def test_api_key_included_in_params(self):
        inst = self._inst(api_key='mykey123')
        captured = []
        def _req(method, url, params=None, **kw):
            captured.append(params or {})
            return self._asn_search_resp(('15169', 'GOOGLE, US')) if len(captured) == 1 \
                else self._prefix_resp('15169', 'GOOGLE, US', '8.8.8.0/24')
        inst.request = _req
        inst.module_run(['Google'])
        self.assertTrue(all(p.get('apikey') == 'mykey123' for p in captured))

    def test_no_api_key_omits_param(self):
        inst = self._inst()
        captured = []
        def _req(method, url, params=None, **kw):
            captured.append(params or {})
            return self._asn_search_resp(('15169', 'GOOGLE, US')) if len(captured) == 1 \
                else self._prefix_resp('15169', 'GOOGLE, US', '8.8.8.0/24')
        inst.request = _req
        inst.module_run(['Google'])
        self.assertTrue(all('apikey' not in p for p in captured))

    def test_short_company_name_logs_error(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: (_ for _ in ()).throw(AssertionError('should not call request'))
        inst.module_run(['Co'])
        self.assertTrue(any('too short' in e for e in inst._errors))
        self.assertEqual(inst._netblocks, [])

    def test_multiple_asns_for_company_all_fetched(self):
        inst = self._inst()
        calls = [0]
        def _req(method, url, params=None, **kw):
            calls[0] += 1
            if calls[0] == 1:
                return self._asn_search_resp(
                    ('15169', 'GOOGLE, US'),
                    ('36040', 'GOOGLE-CLOUD, US'),
                )
            if calls[0] == 2:
                return self._prefix_resp('15169', 'GOOGLE, US', '8.8.8.0/24')
            return self._prefix_resp('36040', 'GOOGLE-CLOUD, US', '34.0.0.0/8')
        inst.request = _req
        inst.module_run(['Google'])
        self.assertIn('8.8.8.0/24', inst._netblocks)
        self.assertIn('34.0.0.0/8', inst._netblocks)

    def test_ipv6_prefixes_inserted(self):
        inst = self._inst()
        calls = [0]
        def _req(method, url, params=None, **kw):
            calls[0] += 1
            if calls[0] == 1:
                return self._asn_search_resp(('15169', 'GOOGLE, US'))
            return self._prefix_resp('15169', 'GOOGLE, US', '8.8.8.0/24', '2001:4860::/32')
        inst.request = _req
        inst.module_run(['Google'])
        self.assertIn('2001:4860::/32', inst._netblocks)

    def test_multiple_companies_each_queried(self):
        inst = self._inst()
        search_queries = []
        calls = [0]
        def _req(method, url, params=None, **kw):
            calls[0] += 1
            q = (params or {}).get('q', '')
            if not q.startswith('AS'):
                search_queries.append(q)
                if 'Google' in q:
                    return self._asn_search_resp(('15169', 'GOOGLE, US'))
                return self._asn_search_resp(('16509', 'AMAZON-02, US'))
            if '15169' in q:
                return self._prefix_resp('15169', 'GOOGLE, US', '8.8.8.0/24')
            return self._prefix_resp('16509', 'AMAZON-02, US', '54.0.0.0/8')
        inst.request = _req
        inst.module_run(['Google', 'Amazon'])
        self.assertEqual(len(search_queries), 2)
        self.assertIn('8.8.8.0/24', inst._netblocks)
        self.assertIn('54.0.0.0/8', inst._netblocks)

    def test_quota_exceeded_on_search_breaks_loop(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: Resp(text='API count exceeded - Increase Quota with Membership')
        inst.module_run(['Google', 'Amazon'])
        self.assertTrue(any('quota exceeded' in e.lower() for e in inst._errors))
        self.assertEqual(inst._netblocks, [])

    def test_quota_exceeded_on_prefix_fetch_returns_early(self):
        inst = self._inst()
        calls = [0]
        def _req(method, url, params=None, **kw):
            calls[0] += 1
            if calls[0] == 1:
                return self._asn_search_resp(('15169', 'GOOGLE, US'))
            return Resp(text='API count exceeded - Increase Quota with Membership')
        inst.request = _req
        inst.module_run(['Google'])
        self.assertTrue(any('quota exceeded' in e.lower() for e in inst._errors))
        self.assertEqual(inst._netblocks, [])


# ═══════════════════════════════════════════════════════════════════════════════
# permute
# ═══════════════════════════════════════════════════════════════════════════════

class _FakeRdata:
    def __init__(self, address, rdtype=1):
        self.address = address
        self.rdtype = rdtype


class _FakeAnswers:
    def __init__(self, rdatas):
        self._rdatas = rdatas
    def __iter__(self):
        return iter(self._rdatas)


class _FakeResolver:
    """DNS resolver stub: table maps hostname -> list[address] | exception | None (NXDOMAIN)."""
    def __init__(self, table):
        self.table = table
        self.queried = []

    def query(self, host):
        import dns.resolver
        self.queried.append(host)
        if host not in self.table:
            raise dns.resolver.NXDOMAIN()
        val = self.table[host]
        if isinstance(val, Exception):
            raise val
        return _FakeAnswers([_FakeRdata(a) for a in val])


class TestPermute(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.file = load_mod(_p('recon', 'hosts-hosts', 'permute.py'))

    def _inst(self, words=None):
        inst = self.file.Module()
        word_list = words if words is not None else 'dev,api'
        inst.options = {'words': word_list}
        return inst

    def _run(self, inst, dns_table, hosts):
        resolver = _FakeResolver(dns_table)
        inst.get_resolver = lambda: resolver
        inst.module_run(hosts)
        return resolver

    def test_happy_path_inserts_resolved_permutations(self):
        inst = self._inst(words='dev')
        self._run(inst, {
            'dev.api.example.com': ['10.0.0.1'],
            'dev-api.example.com': ['10.0.0.2'],
        }, ['api.example.com'])
        hosts = {h['host']: h['ip_address'] for h in inst._hosts}
        self.assertEqual(hosts['dev.api.example.com'], '10.0.0.1')
        self.assertEqual(hosts['dev-api.example.com'], '10.0.0.2')

    def test_nxdomain_not_inserted(self):
        inst = self._inst(words='dev')
        self._run(inst, {}, ['api.example.com'])
        self.assertEqual(inst._hosts, [])

    def test_original_host_not_reinserted(self):
        inst = self._inst(words='dev')
        self._run(inst, {'api.example.com': ['10.0.0.99']}, ['api.example.com'])
        hosts = [h['host'] for h in inst._hosts]
        self.assertNotIn('api.example.com', hosts)

    def test_single_label_host_skipped(self):
        inst = self._inst(words='dev')
        resolver = self._run(inst, {}, ['localhost'])
        self.assertEqual(resolver.queried, [])
        self.assertEqual(inst._hosts, [])

    def test_numeric_suffix_pattern_generated(self):
        inst = self._inst(words='')
        resolver = self._run(inst, {'api2.example.com': ['10.0.0.7']}, ['api.example.com'])
        self.assertIn('api1.example.com', resolver.queried)
        self.assertIn('api2.example.com', resolver.queried)
        self.assertIn('api3.example.com', resolver.queried)
        self.assertEqual(inst._hosts[0]['host'], 'api2.example.com')

    def test_insertion_prefix_suffix_patterns(self):
        inst = self._inst(words='dev')
        resolver = self._run(inst, {}, ['api.example.com'])
        self.assertIn('dev.api.example.com', resolver.queried)
        self.assertIn('dev-api.example.com', resolver.queried)
        self.assertIn('api-dev.example.com', resolver.queried)

    def test_deep_host_permutes_only_leftmost_label(self):
        inst = self._inst(words='dev')
        resolver = self._run(inst, {}, ['foo.bar.example.com'])
        self.assertIn('dev.foo.bar.example.com', resolver.queried)
        self.assertIn('dev-foo.bar.example.com', resolver.queried)
        self.assertIn('foo1.bar.example.com', resolver.queried)
        self.assertNotIn('dev.foo.example.com', resolver.queried)

    def test_dns_error_skipped_gracefully(self):
        import dns.resolver
        inst = self._inst(words='dev')
        self._run(inst, {
            'dev.api.example.com': dns.resolver.Timeout(),
            'dev-api.example.com': ['10.0.0.2'],
        }, ['api.example.com'])
        hosts = [h['host'] for h in inst._hosts]
        self.assertIn('dev-api.example.com', hosts)
        self.assertNotIn('dev.api.example.com', hosts)

    def test_no_answer_skipped_gracefully(self):
        import dns.resolver
        inst = self._inst(words='dev')
        self._run(inst, {'dev.api.example.com': dns.resolver.NoAnswer()}, ['api.example.com'])
        self.assertEqual(inst._hosts, [])

    def test_duplicate_candidates_queried_once(self):
        inst = self._inst(words='dev')
        resolver = self._run(inst, {'dev.api.example.com': ['10.0.0.1']},
                             ['api.example.com', 'api.example.com'])
        self.assertEqual(resolver.queried.count('dev.api.example.com'), 1)

    def test_non_a_records_not_inserted(self):
        inst = self._inst(words='dev')
        resolver = _FakeResolver({})
        def _q(host):
            if host == 'dev.api.example.com':
                return _FakeAnswers([_FakeRdata('2001:db8::1', rdtype=28)])
            import dns.resolver as _r
            raise _r.NXDOMAIN()
        resolver.query = _q
        inst.get_resolver = lambda: resolver
        inst.module_run(['api.example.com'])
        self.assertEqual(inst._hosts, [])

    def test_multiple_source_hosts_each_processed(self):
        inst = self._inst(words='dev')
        self._run(inst, {
            'dev.a.example.com': ['10.0.0.1'],
            'dev.b.example.com': ['10.0.0.2'],
        }, ['a.example.com', 'b.example.com'])
        hosts = {h['host'] for h in inst._hosts}
        self.assertIn('dev.a.example.com', hosts)
        self.assertIn('dev.b.example.com', hosts)

    def test_custom_wordlist_respected(self):
        inst = self._inst(words='qux,flux')
        resolver = self._run(inst, {}, ['api.example.com'])
        self.assertIn('qux.api.example.com', resolver.queried)
        self.assertIn('flux-api.example.com', resolver.queried)
        self.assertNotIn('dev.api.example.com', resolver.queried)

    def test_host_casing_normalised(self):
        inst = self._inst(words='dev')
        resolver = self._run(inst, {}, ['API.Example.COM'])
        self.assertIn('dev.api.example.com', resolver.queried)

    # ── scope filter (regression: brute_hosts captures CNAME targets like
    #    *.cdn.cloudflare.net / *.outlook.com; permute used to fan out from
    #    them, multiplying vendor-infrastructure noise by 30-40x via DNS
    #    fan-out. The fix scopes permute to hosts under domains in the
    #    `domains` table.)

    def test_off_domain_host_skipped_when_in_scope_set(self):
        """A CNAME-target-style off-domain host must be skipped when
        `domains` table has at least one in-scope entry."""
        inst = self._inst(words='dev')
        inst._query_responses = {
            'SELECT domain FROM domains': [('starbucks.com',)],
        }
        resolver = _FakeResolver({})
        inst.get_resolver = lambda: resolver
        # Off-domain CNAME target (the kind brute_hosts records); must NOT be permuted.
        inst.module_run([
            'webfarm-50.q4web.com',
            'autodiscover.outlook.com',
            'd1zsws4x9b0vy6.cloudfront.net',
        ])
        # Resolver should never have been queried (all hosts filtered out)
        self.assertEqual(resolver.queried, [],
                         msg=f"unexpectedly queried: {resolver.queried}")
        # And no rows inserted
        self.assertEqual(inst._hosts, [])
        # And the summary line was emitted
        self.assertTrue(any('outside of in-scope domains' in o for o in inst._output))

    def test_in_scope_host_permuted_when_in_scope_set(self):
        inst = self._inst(words='dev')
        inst._query_responses = {
            'SELECT domain FROM domains': [('starbucks.com',)],
        }
        resolver = _FakeResolver({'dev.www.starbucks.com': ['10.0.0.1']})
        inst.get_resolver = lambda: resolver
        inst.module_run(['www.starbucks.com'])
        self.assertIn('dev.www.starbucks.com', [h['host'] for h in inst._hosts])

    def test_apex_in_scope_host_permuted(self):
        """The apex domain itself (e.g. starbucks.com) must be a valid
        permutation seed when it's in the domains table."""
        inst = self._inst(words='dev')
        inst._query_responses = {
            'SELECT domain FROM domains': [('example.com',)],
        }
        resolver = _FakeResolver({'dev.example.com': ['10.0.0.1']})
        inst.get_resolver = lambda: resolver
        inst.module_run(['example.com'])
        self.assertIn('dev.example.com', [h['host'] for h in inst._hosts])

    def test_lookalike_suffix_not_in_scope(self):
        """`evilexample.com` byte-suffix-matches `example.com` but is a
        different registered domain. Must be skipped."""
        inst = self._inst(words='dev')
        inst._query_responses = {
            'SELECT domain FROM domains': [('example.com',)],
        }
        resolver = _FakeResolver({})
        inst.get_resolver = lambda: resolver
        inst.module_run(['mail.evilexample.com'])
        self.assertEqual(resolver.queried, [])

    def test_multiple_in_scope_domains(self):
        """Acquisition workflow: starbucks.com plus 23-5degrees.com etc.
        all in the domains table — hosts under any of them should permute."""
        inst = self._inst(words='dev')
        inst._query_responses = {
            'SELECT domain FROM domains': [
                ('starbucks.com',), ('23-5degrees.com',), ('teavana.com',),
            ],
        }
        resolver = _FakeResolver({
            'dev.www.starbucks.com':   ['10.0.0.1'],
            'dev.www.23-5degrees.com': ['10.0.0.2'],
            'dev.www.teavana.com':     ['10.0.0.3'],
        })
        inst.get_resolver = lambda: resolver
        inst.module_run([
            'www.starbucks.com',
            'www.23-5degrees.com',
            'www.teavana.com',
            'unrelated.tenant.com',  # off-domain — must be skipped
        ])
        hosts = {h['host'] for h in inst._hosts}
        self.assertIn('dev.www.starbucks.com', hosts)
        self.assertIn('dev.www.23-5degrees.com', hosts)
        self.assertIn('dev.www.teavana.com', hosts)

    def test_empty_domains_falls_back_to_permit_all_with_warning(self):
        """Backwards compatibility: if domains table is empty, permute
        falls back to its legacy 'permute everything' behaviour but
        SHOUTS about the scope filter being disabled."""
        inst = self._inst(words='dev')
        inst._query_responses = {}  # nothing returned by query
        resolver = _FakeResolver({'dev.example.com': ['10.0.0.1']})
        inst.get_resolver = lambda: resolver
        inst.module_run(['example.com'])
        self.assertIn('dev.example.com', [h['host'] for h in inst._hosts])
        # Loud warning fires
        self.assertTrue(any('Scope filter DISABLED' in e for e in inst._errors),
                        msg=f"errors: {inst._errors}")

    # ── provenance chain composition (Phase 2 pilot opt-in)

    def test_provenance_chain_extends_parent_provenance(self):
        """When the input row carries a parent provenance string, permute
        appends '.permute' to it on each insert."""
        inst = self._inst(words='dev')
        inst._query_responses = {
            'SELECT domain FROM domains': [('example.com',)],
        }
        resolver = _FakeResolver({'dev.www.example.com': ['10.0.0.1']})
        inst.get_resolver = lambda: resolver
        # Multi-column input row: (host, parent_module, parent_provenance)
        inst.module_run([('www.example.com', 'brute_hosts', 'alienvault.brute_hosts')])
        hosts = [h for h in inst._hosts if h['host'] == 'dev.www.example.com']
        self.assertEqual(len(hosts), 1)
        self.assertEqual(hosts[0]['provenance'], 'alienvault.brute_hosts.permute')

    def test_provenance_falls_back_to_parent_module_when_no_provenance(self):
        """If the parent row had a module set but no provenance recorded
        (a non-opt-in module produced the host), permute uses the module
        name as the chain root."""
        inst = self._inst(words='dev')
        inst._query_responses = {
            'SELECT domain FROM domains': [('example.com',)],
        }
        resolver = _FakeResolver({'dev.www.example.com': ['10.0.0.1']})
        inst.get_resolver = lambda: resolver
        # Provenance is None — only module is known
        inst.module_run([('www.example.com', 'certspotter', None)])
        hosts = [h for h in inst._hosts if h['host'] == 'dev.www.example.com']
        self.assertEqual(hosts[0]['provenance'], 'certspotter.permute')

    def test_provenance_root_when_input_has_no_parent_info(self):
        """Bare-string input (file source, etc.) has no parent provenance.
        The chain root is just 'permute'."""
        inst = self._inst(words='dev')
        inst._query_responses = {
            'SELECT domain FROM domains': [('example.com',)],
        }
        resolver = _FakeResolver({'dev.www.example.com': ['10.0.0.1']})
        inst.get_resolver = lambda: resolver
        inst.module_run(['www.example.com'])
        hosts = [h for h in inst._hosts if h['host'] == 'dev.www.example.com']
        self.assertEqual(hosts[0]['provenance'], 'permute')


# ═══════════════════════════════════════════════════════════════════════════════
# alienvault
# ═══════════════════════════════════════════════════════════════════════════════

def _otx_page(entries, has_next=False):
    """Build a Resp mimicking the OTX url_list response shape.
    entries is a list of dicts like {'hostname': 'x.example.com'} or
    {'url': 'https://x.example.com/path'}."""
    return Resp(status=200, data={
        'url_list': entries,
        'has_next': has_next,
        'full_size': len(entries),
        'actual_size': len(entries),
        'page_num': 1,
        'limit': 100,
        'paged': True,
    })


class TestAlienVault(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.file = load_mod(_p('recon', 'domains-hosts', 'alienvault.py'))

    def _inst(self, per_page=500, max_pages=100):
        inst = self.file.Module()
        inst.options = {'per_page': per_page, 'max_pages': max_pages}
        return inst

    def test_happy_path_extracts_hostnames(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: _otx_page([
            {'hostname': 'a.example.com', 'url': 'https://a.example.com/'},
            {'hostname': 'b.example.com', 'url': 'https://b.example.com/x'},
        ])
        inst.module_run(['example.com'])
        hosts = [h['host'] for h in inst._hosts]
        self.assertIn('a.example.com', hosts)
        self.assertIn('b.example.com', hosts)

    def test_external_hostnames_filtered(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: _otx_page([
            {'hostname': 'good.example.com'},
            {'hostname': 'evil.attacker.com'},
            {'hostname': 'unrelated.org'},
        ])
        inst.module_run(['example.com'])
        hosts = [h['host'] for h in inst._hosts]
        self.assertEqual(hosts, ['good.example.com'])

    def test_bare_domain_included(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: _otx_page([{'hostname': 'example.com'}])
        inst.module_run(['example.com'])
        self.assertEqual(inst._hosts[0]['host'], 'example.com')

    def test_deduplicates_across_pages(self):
        pages = [
            _otx_page([{'hostname': 'a.example.com'}, {'hostname': 'b.example.com'}], has_next=True),
            _otx_page([{'hostname': 'b.example.com'}, {'hostname': 'c.example.com'}], has_next=False),
        ]
        idx = [0]
        def _req(*a, **kw):
            r = pages[idx[0]]
            idx[0] += 1
            return r
        inst = self._inst()
        inst.request = _req
        inst.module_run(['example.com'])
        hosts = sorted(h['host'] for h in inst._hosts)
        self.assertEqual(hosts, ['a.example.com', 'b.example.com', 'c.example.com'])

    def test_pagination_stops_on_has_next_false(self):
        calls = [0]
        def _req(*a, **kw):
            calls[0] += 1
            if calls[0] == 1:
                return _otx_page([{'hostname': 'a.example.com'}], has_next=True)
            return _otx_page([{'hostname': 'b.example.com'}], has_next=False)
        inst = self._inst()
        inst.request = _req
        inst.module_run(['example.com'])
        self.assertEqual(calls[0], 2)

    def test_max_pages_respected(self):
        def _req(*a, **kw):
            return _otx_page([{'hostname': 'a.example.com'}], has_next=True)
        inst = self._inst(max_pages=3)
        inst.request = _req
        calls = [0]
        def _counting(*a, **kw):
            calls[0] += 1
            return _req()
        inst.request = _counting
        inst.module_run(['example.com'])
        self.assertEqual(calls[0], 3)

    def test_falls_back_to_url_parsing(self):
        """Entries without hostname field should still resolve via urlparse on url."""
        inst = self._inst()
        inst.request = lambda *a, **kw: _otx_page([
            {'url': 'https://sub.example.com:8080/path'},
            {'url': 'http://other.example.com/'},
        ])
        inst.module_run(['example.com'])
        hosts = [h['host'] for h in inst._hosts]
        self.assertIn('sub.example.com', hosts)
        self.assertIn('other.example.com', hosts)

    def test_empty_entries_empty_result(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: _otx_page([], has_next=False)
        inst.module_run(['example.com'])
        self.assertEqual(inst._hosts, [])

    def test_non_200_errors_and_continues(self):
        results = [Resp(status=503, data={}), _otx_page([{'hostname': 'ok.other.com'}])]
        idx = [0]
        def _req(*a, **kw):
            r = results[min(idx[0], len(results) - 1)]
            idx[0] += 1
            return r
        inst = self._inst()
        inst.request = _req
        inst.module_run(['example.com', 'other.com'])
        self.assertTrue(any('503' in e for e in inst._errors))
        self.assertEqual(inst._hosts[0]['host'], 'ok.other.com')

    def test_host_casing_normalised(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: _otx_page([
            {'hostname': 'A.Example.COM'},
            {'hostname': 'B.EXAMPLE.COM'},
        ])
        inst.module_run(['Example.COM'])
        hosts = [h['host'] for h in inst._hosts]
        self.assertEqual(sorted(hosts), ['a.example.com', 'b.example.com'])

    def test_multiple_domains_each_queried(self):
        seen = []
        def _req(method, url, params=None, **kw):
            seen.append(url)
            return _otx_page([], has_next=False)
        inst = self._inst()
        inst.request = _req
        inst.module_run(['a.com', 'b.com'])
        self.assertEqual(len(seen), 2)
        self.assertIn('/indicators/domain/a.com/url_list', seen[0])
        self.assertIn('/indicators/domain/b.com/url_list', seen[1])

    def test_per_page_parameter_forwarded(self):
        captured = []
        def _req(method, url, params=None, **kw):
            captured.append(params or {})
            return _otx_page([], has_next=False)
        inst = self._inst(per_page=250)
        inst.request = _req
        inst.module_run(['example.com'])
        self.assertEqual(captured[0].get('limit'), 250)


# ═══════════════════════════════════════════════════════════════════════════════
# subdomain_center
# ═══════════════════════════════════════════════════════════════════════════════

class _SCResp:
    """Mock for subdomain.center: status, headers, json() return list-of-strings or raise."""
    def __init__(self, status=200, payload=None, headers=None, json_raises=False):
        self.status_code = status
        self.headers = headers or {}
        self._payload = payload if payload is not None else []
        self._raises = json_raises

    def json(self):
        if self._raises:
            raise ValueError('not JSON')
        return self._payload


class TestSubdomainCenter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.file = load_mod(_p('recon', 'domains-hosts', 'subdomain_center.py'))

    def _inst(self):
        return self.file.Module()

    def test_happy_path_inserts_filtered_hosts(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: _SCResp(payload=[
            'mail.example.com', 'api.example.com', 'orphan.unrelated.com',
            '*.example.com', 'WWW.Example.COM', 'evilexample.com',
        ])
        inst.module_run(['example.com'])
        hosts = sorted(h['host'] for h in inst._hosts)
        # off-domain dropped, wildcard skipped, lookalike rejected, casing normalised
        self.assertEqual(hosts, ['api.example.com', 'mail.example.com', 'www.example.com'])

    def test_429_disables_source_for_remaining_domains(self):
        """First domain hits 429 → remaining domains in this run must be
        skipped without further requests, and a single loud alert fires."""
        inst = self._inst()
        calls = []
        def _req(*a, **kw):
            calls.append(a[1] if len(a) > 1 else kw.get('url'))
            return _SCResp(status=429, headers={'Retry-After': '60'})
        inst.request = _req
        inst.module_run(['a.example', 'b.example', 'c.example'])
        # Only one request actually made
        self.assertEqual(len(calls), 1, msg=f"calls: {calls}")
        # Loud alert + error fired exactly once
        alerts = [o for o in inst._output if o.startswith('ALERT:')]
        self.assertEqual(len(alerts), 1, msg=f"alerts: {alerts}")
        joined = ' '.join(alerts + inst._errors)
        self.assertIn('UPSTREAM ERROR', joined)
        self.assertIn('429', joined)
        self.assertIn('60', joined)
        self.assertIn('disabling', joined)
        self.assertIn('rest of this run', joined)

    def test_521_cloudflare_origin_unreachable_disables_source(self):
        """Cloudflare 521/522/523/524 (origin unreachable) is the most common
        subdomain.center failure mode — must be treated as fail-fast."""
        for code in (521, 522, 523, 524):
            with self.subTest(code=code):
                inst = self._inst()
                calls = [0]
                def _req(*a, _c=code, **kw):
                    calls[0] += 1
                    return _SCResp(status=_c)
                inst.request = _req
                inst.module_run(['a.example', 'b.example', 'c.example'])
                self.assertEqual(calls[0], 1)
                joined = ' '.join(inst._output) + ' ' + ' '.join(inst._errors)
                self.assertIn('UPSTREAM ERROR', joined)
                self.assertIn(str(code), joined)

    def test_request_exception_disables_source(self):
        inst = self._inst()
        calls = [0]
        def _req(*a, **kw):
            calls[0] += 1
            raise ConnectionError('connect refused')
        inst.request = _req
        inst.module_run(['a.example', 'b.example'])
        self.assertEqual(calls[0], 1)
        joined = ' '.join(inst._output) + ' ' + ' '.join(inst._errors)
        self.assertIn('UPSTREAM ERROR', joined)
        self.assertIn('ConnectionError', joined)

    def test_non_200_4xx_continues_without_disabling(self):
        """A 404 on one domain is not necessarily a source-wide problem; keep
        going, just log a normal error for that domain."""
        inst = self._inst()
        calls = [0]
        def _req(*a, **kw):
            calls[0] += 1
            if calls[0] == 1:
                return _SCResp(status=404)
            return _SCResp(payload=['ok.example'])
        inst.request = _req
        inst.module_run(['first.example', 'second.example'])
        self.assertEqual(calls[0], 2)
        # No loud alert for 4xx
        alerts = [o for o in inst._output if o.startswith('ALERT:')]
        self.assertEqual(alerts, [])
        # 'ok.example' might match second.example? No — sanity: it doesn't.
        # The point is just that the second domain's request was attempted.

    def test_non_json_body_does_not_crash(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: _SCResp(status=200, json_raises=True)
        inst.module_run(['example.com'])
        self.assertEqual(inst._hosts, [])
        self.assertTrue(any('Non-JSON' in e for e in inst._errors))

    def test_unexpected_response_shape_handled(self):
        """If subdomain.center ever changes to return a dict, don't crash."""
        inst = self._inst()
        inst.request = lambda *a, **kw: _SCResp(payload={'subdomains': ['ok.example.com']})
        inst.module_run(['example.com'])
        self.assertEqual(inst._hosts, [])
        self.assertTrue(any('expected list' in e for e in inst._errors))


# ═══════════════════════════════════════════════════════════════════════════════
# shodan_ct (ctl.shodan.io — free CT log mirror, no API key, no credits)
# ═══════════════════════════════════════════════════════════════════════════════

class _ShodanCTResp:
    """Mock for ctl.shodan.io /hostnames: status, headers, json() -> list or raise."""
    def __init__(self, status=200, payload=None, headers=None, json_raises=False):
        self.status_code = status
        self.headers = headers or {}
        self._payload = payload if payload is not None else []
        self._raises = json_raises

    def json(self):
        if self._raises:
            raise ValueError('not JSON')
        return self._payload


class TestShodanCT(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.file = load_mod(_p('recon', 'domains-hosts', 'shodan_ct.py'))

    def _inst(self):
        return self.file.Module()

    def test_hits_hostnames_endpoint_no_key(self):
        """Must call the keyless ctl.shodan.io /hostnames endpoint — never the
        metered api.shodan.io and never with an API key/credit param."""
        captured = []
        inst = self._inst()
        def _req(method, url, **kw):
            captured.append(url)
            return _ShodanCTResp(payload=['api.example.com'])
        inst.request = _req
        inst.module_run(['example.com'])
        self.assertEqual(len(captured), 1)
        self.assertEqual(
            captured[0],
            'https://ctl.shodan.io/api/v1/domain/example.com/hostnames',
        )
        self.assertNotIn('api.shodan.io', captured[0])
        self.assertNotIn('key=', captured[0])

    def test_happy_path_inserts_filtered_hosts(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: _ShodanCTResp(payload=[
            'mail.example.com', 'api.example.com', 'orphan.unrelated.com',
            '*.example.com', 'WWW.Example.COM', 'evilexample.com',
        ])
        inst.module_run(['example.com'])
        hosts = sorted(h['host'] for h in inst._hosts)
        # off-domain dropped, wildcard skipped, lookalike rejected, casing normalised
        self.assertEqual(hosts, ['api.example.com', 'mail.example.com', 'www.example.com'])

    def test_apex_itself_included(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: _ShodanCTResp(payload=['example.com'])
        inst.module_run(['example.com'])
        self.assertEqual([h['host'] for h in inst._hosts], ['example.com'])

    def test_trailing_dot_normalised(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: _ShodanCTResp(payload=['api.example.com.'])
        inst.module_run(['example.com'])
        self.assertEqual([h['host'] for h in inst._hosts], ['api.example.com'])

    def test_429_disables_source_for_remaining_domains(self):
        inst = self._inst()
        calls = []
        def _req(method, url, **kw):
            calls.append(url)
            return _ShodanCTResp(status=429, headers={'Retry-After': '60'})
        inst.request = _req
        inst.module_run(['a.example', 'b.example', 'c.example'])
        self.assertEqual(len(calls), 1, msg=f"calls: {calls}")
        alerts = [o for o in inst._output if o.startswith('ALERT:')]
        self.assertEqual(len(alerts), 1, msg=f"alerts: {alerts}")
        joined = ' '.join(alerts + inst._errors)
        self.assertIn('UPSTREAM ERROR', joined)
        self.assertIn('429', joined)
        self.assertIn('60', joined)
        self.assertIn('rest of this run', joined)

    def test_5xx_and_cloudflare_origin_codes_disable_source(self):
        for code in (502, 503, 504, 521, 522, 523, 524):
            with self.subTest(code=code):
                inst = self._inst()
                calls = [0]
                def _req(method, url, _c=code, **kw):
                    calls[0] += 1
                    return _ShodanCTResp(status=_c)
                inst.request = _req
                inst.module_run(['a.example', 'b.example', 'c.example'])
                self.assertEqual(calls[0], 1)
                joined = ' '.join(inst._output) + ' ' + ' '.join(inst._errors)
                self.assertIn('UPSTREAM ERROR', joined)
                self.assertIn(str(code), joined)

    def test_request_exception_disables_source(self):
        inst = self._inst()
        calls = [0]
        def _req(method, url, **kw):
            calls[0] += 1
            raise ConnectionError('connect refused')
        inst.request = _req
        inst.module_run(['a.example', 'b.example'])
        self.assertEqual(calls[0], 1)
        joined = ' '.join(inst._output) + ' ' + ' '.join(inst._errors)
        self.assertIn('UPSTREAM ERROR', joined)
        self.assertIn('ConnectionError', joined)

    def test_non_200_4xx_continues_without_disabling(self):
        inst = self._inst()
        calls = [0]
        def _req(method, url, **kw):
            calls[0] += 1
            if calls[0] == 1:
                return _ShodanCTResp(status=404)
            return _ShodanCTResp(payload=['ok.example'])
        inst.request = _req
        inst.module_run(['first.example', 'second.example'])
        self.assertEqual(calls[0], 2)
        alerts = [o for o in inst._output if o.startswith('ALERT:')]
        self.assertEqual(alerts, [])

    def test_non_json_body_does_not_crash(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: _ShodanCTResp(status=200, json_raises=True)
        inst.module_run(['example.com'])
        self.assertEqual(inst._hosts, [])
        self.assertTrue(any('Non-JSON' in e for e in inst._errors))

    def test_unexpected_response_shape_handled(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: _ShodanCTResp(payload={'hostnames': ['ok.example.com']})
        inst.module_run(['example.com'])
        self.assertEqual(inst._hosts, [])
        self.assertTrue(any('expected list' in e for e in inst._errors))

    def test_non_string_entries_skipped(self):
        inst = self._inst()
        inst.request = lambda *a, **kw: _ShodanCTResp(payload=['api.example.com', None, 42])
        inst.module_run(['example.com'])
        self.assertEqual([h['host'] for h in inst._hosts], ['api.example.com'])

    def test_multiple_domains_each_queried(self):
        seen = []
        inst = self._inst()
        def _req(method, url, **kw):
            seen.append(url)
            return _ShodanCTResp(payload=[])
        inst.request = _req
        inst.module_run(['one.example', 'two.example'])
        self.assertEqual(len(seen), 2)


# ═══════════════════════════════════════════════════════════════════════════════
# Fail-fast retrofit regression tests for the two existing CT modules
# ═══════════════════════════════════════════════════════════════════════════════

class TestCTFailFast(unittest.TestCase):
    """Regression: when a CT source hits 429 / upstream-error on the first
    domain, it must NOT continue retrying every remaining domain. That was
    the bug that produced 7+ alerts per run (one per domain) and burned wall
    time."""

    @classmethod
    def setUpClass(cls):
        cls.certspotter = load_mod(_p('recon', 'domains-hosts', 'certspotter.py'))
        cls.crtsh = load_mod(_p('recon', 'domains-hosts', 'certificate_transparency.py'))

    def test_certspotter_429_skips_remaining_domains(self):
        inst = self.certspotter.Module()
        calls = []
        def _req(method, url, **kw):
            calls.append(kw.get('params', {}).get('domain'))
            return Resp(status=429, text='Too Many Requests')
        inst.request = _req
        inst.module_run(['a.example', 'b.example', 'c.example', 'd.example'])
        # Exactly one request — the first 429 disabled the source
        self.assertEqual(len(calls), 1, msg=f"calls: {calls}")
        # Exactly one loud alert
        alerts = [o for o in inst._output if o.startswith('ALERT:')]
        self.assertEqual(len(alerts), 1, msg=f"alerts: {alerts}")

    def test_crtsh_502_skips_remaining_domains(self):
        # _CrtshResp from earlier in the file
        inst = self.crtsh.Module()
        calls = [0]
        def _req(method, url, **kw):
            calls[0] += 1
            return _CrtshResp(status=502)
        inst.request = _req
        inst.module_run(['a.example', 'b.example', 'c.example'])
        self.assertEqual(calls[0], 1)
        alerts = [o for o in inst._output if o.startswith('ALERT:')]
        self.assertEqual(len(alerts), 1, msg=f"alerts: {alerts}")

    def test_crtsh_request_exception_skips_remaining_domains(self):
        inst = self.crtsh.Module()
        calls = [0]
        def _req(method, url, **kw):
            calls[0] += 1
            raise ConnectionError('connection refused')
        inst.request = _req
        inst.module_run(['a.example', 'b.example', 'c.example'])
        self.assertEqual(calls[0], 1)


# ═══════════════════════════════════════════════════════════════════════════════
# Pretty runner
# ═══════════════════════════════════════════════════════════════════════════════

class _PrettyResult(unittest.TestResult):
    PASS  = '✓'
    FAIL  = '✗'
    SKIP  = '○'
    ERROR = '⚠'

    def __init__(self, stream):
        super().__init__()
        self.stream   = stream
        self._start   = {}
        self._seen    = set()

    def _suite(self, test):
        return type(test).__name__

    def _label(self, test):
        return test._testMethodName.replace('test_', '', 1).replace('_', ' ')

    def _print_suite_header(self, test):
        name = self._suite(test)
        if name not in self._seen:
            self._seen.add(name)
            display = name.replace('Test', '', 1)
            self.stream.write(f'\n  {display}\n')

    def startTest(self, test):
        super().startTest(test)
        self._print_suite_header(test)
        self._start[test.id()] = time.perf_counter()

    def _elapsed(self, test):
        return time.perf_counter() - self._start.get(test.id(), time.perf_counter())

    def addSuccess(self, test):
        t = self._elapsed(test)
        self.stream.write(f'    {self.PASS}  {self._label(test):<56} {t:.3f}s\n')

    def addFailure(self, test, err):
        super().addFailure(test, err)
        t = self._elapsed(test)
        msg = str(err[1]).splitlines()[0][:64]
        self.stream.write(f'    {self.FAIL}  {self._label(test):<56} {t:.3f}s\n')
        self.stream.write(f'       └─ {msg}\n')

    def addError(self, test, err):
        super().addError(test, err)
        t = self._elapsed(test)
        msg = str(err[1]).splitlines()[0][:64]
        self.stream.write(f'    {self.ERROR}  {self._label(test):<56} {t:.3f}s\n')
        self.stream.write(f'       └─ {msg}\n')

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.stream.write(f'    {self.SKIP}  {self._label(test):<56} skipped\n')
        self.stream.write(f'       └─ {reason[:64]}\n')

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self.stream.write(f'    {self.PASS}  {self._label(test):<56} xfail\n')

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.stream.write(f'    {self.FAIL}  {self._label(test):<56} unexpected pass\n')


class _PrettyRunner:
    WIDTH = 76

    def run(self, suite):
        s = sys.stdout
        bar = '═' * self.WIDTH
        title = ' recon-og-marketplace — module test suite '
        pad_l = (self.WIDTH - len(title)) // 2
        pad_r = self.WIDTH - len(title) - pad_l

        s.write('╔' + '═' * self.WIDTH + '╗\n')
        s.write('║' + ' ' * pad_l + title + ' ' * pad_r + '║\n')
        s.write('╚' + '═' * self.WIDTH + '╝\n')

        result = _PrettyResult(s)
        t0     = time.perf_counter()
        suite.run(result)
        elapsed = time.perf_counter() - t0

        passed  = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)
        s.write(f'\n{bar}\n')
        s.write(
            f'  passed: {passed}   failed: {len(result.failures)}'
            f'   errors: {len(result.errors)}   skipped: {len(result.skipped)}'
            f'   total: {result.testsRun}   time: {elapsed:.3f}s\n'
        )
        s.write(f'{bar}\n')

        if result.failures or result.errors:
            s.write('\nfailure details:\n')
            for test, tb in result.failures + result.errors:
                s.write(f'\n  — {test.id()}\n')
                for line in tb.splitlines()[-8:]:
                    s.write(f'    {line}\n')

        return result


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite  = loader.loadTestsFromModule(sys.modules[__name__])
    result = _PrettyRunner().run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
