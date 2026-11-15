import json
import re
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from werkzeug.datastructures import MultiDict

from app import create_app
from otp import OtpStore


class GradeflowTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "testing-only",
            "OTP_DATABASE": self.root / "test.sqlite3",
        })
        self.client = self.app.test_client()

    def token(self, route, client=None):
        client = client or self.client
        page = client.get(route).get_data(as_text=True)
        return re.search(r'name="csrf_token" value="([^"]+)"', page)[1]

    def issue(self, token, number=48216, now=1000):
        with patch("otp.time", return_value=now), patch("otp.random.SystemRandom") as rng:
            rng.return_value.randrange.return_value = number
            return self.client.post("/otp", data={"csrf_token": token, "action": "generate"})

    def verify(self, token, code, now=1001):
        with patch("otp.time", return_value=now):
            return self.client.post("/otp", data={"csrf_token": token, "action": "verify", "code": code})

    def grade(self, marks, subjects=("Math", "Physics"), name="Ananya Rao"):
        token = self.token("/grades")
        return self.client.post("/grades", data=MultiDict({
            "csrf_token": token, "name": name, "roll": "CS-024",
            "subject": list(subjects), "mark": list(marks),
        }))

    def test_routes_and_security_headers(self):
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn("frame-ancestors", home.headers["Content-Security-Policy"])
        self.assertEqual(self.client.get("/healthz").json, {"status": "ok"})
        self.assertEqual(self.client.post("/otp", data={"action": "generate"}).status_code, 400)
        self.assertEqual(self.client.post("/grades", data={"name": "a" * 17000}).status_code, 413)

    def test_otp_leading_zero_valid_then_replay(self):
        token = self.token("/otp")
        issued = self.issue(token)
        self.assertIn(b'id="demo-code">048216', issued.data)
        self.assertEqual(issued.headers["Cache-Control"], "no-store")
        success = self.verify(token, "048216")
        self.assertEqual(success.status_code, 200)
        self.assertIn(b"verified successfully", success.data)
        self.assertIn(b"code is closed", self.verify(token, "048216").data)

    def test_otp_cooldown_and_replacement(self):
        token = self.token("/otp")
        self.issue(token)
        self.assertEqual(self.issue(token, now=1014).status_code, 429)
        self.assertEqual(self.issue(token, number=123456, now=1015).status_code, 200)
        self.assertIn(b"Incorrect code", self.verify(token, "048216", now=1016).data)
        self.assertEqual(self.verify(token, "123456", now=1016).status_code, 200)

    def test_otp_expiration(self):
        token = self.token("/otp")
        self.issue(token)
        self.assertIn(b"code expired", self.verify(token, "048216", now=1300).data)

    def test_otp_attempt_limit_and_format(self):
        token = self.token("/otp")
        self.issue(token)
        self.assertIn(b"exactly six digits", self.verify(token, "abc").data)
        for remaining in range(4, 0, -1):
            response = self.verify(token, "999999")
            self.assertEqual(response.status_code, 422)
            self.assertIn(f"Attempts remaining: {remaining}".encode(), response.data)
        self.assertIn(b"No attempts left", self.verify(token, "999999").data)
        self.assertIn(b"code is closed", self.verify(token, "048216").data)

    def test_otp_isolated_between_browser_sessions(self):
        token = self.token("/otp")
        self.issue(token)
        second_client = self.app.test_client()
        second_token = self.token("/otp", second_client)
        response = second_client.post("/otp", data={
            "csrf_token": second_token, "action": "verify", "code": "048216",
        })
        self.assertIn(b"Generate a demo code first", response.data)

    def test_concurrent_verification_consumes_code_once(self):
        store = OtpStore(self.root / "parallel.sqlite3", "testing-only")
        code, _ = store.issue("browser")
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: store.verify("browser", code)[0], range(2)))
        self.assertEqual(sorted(outcomes), [False, True])

    def test_grade_result(self):
        response = self.grade(["90", "79"])
        self.assertEqual(response.status_code, 200)
        for expected in (b"Ananya Rao", b"CS-024", b"169.00", b"84.50%", b"<dd>A</dd>"):
            self.assertIn(expected, response.data)

    def test_grade_boundary_uses_exact_total(self):
        self.assertIn(b"<dd>A</dd>", self.grade(["90", "89.99"]).data)
        self.assertIn(b"<dd>A+</dd>", self.grade(["90", "90"]).data)

    def test_validation_preserves_input_and_escapes_html(self):
        response = self.grade(["100.01", "1e2"], ("Math", " math "), "<b>Test</b>")
        self.assertEqual(response.status_code, 422)
        self.assertIn(b"Enter a different subject name", response.data)
        self.assertEqual(response.data.count(b"Enter a mark from 0 to 100"), 2)
        self.assertIn(b"&lt;b&gt;Test&lt;/b&gt;", response.data)
        self.assertNotIn(b"<b>Test</b>", response.data)

    def test_supported_subject_counts(self):
        self.assertEqual(self.grade(["50"], ["Math"]).status_code, 422)
        self.assertEqual(self.grade(["50"] * 10, [str(i) for i in range(10)]).status_code, 200)
        self.assertEqual(self.grade(["50"] * 11, [str(i) for i in range(11)]).status_code, 422)
        self.assertEqual(self.grade(["50"], ["Math", "Physics"]).status_code, 422)

    def test_invalid_scheme_fails_at_startup(self):
        rules = self.root / "invalid.json"
        rules.write_text(json.dumps([{"minimum": 50, "grade": "A"}]), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "start at 0"):
            create_app({"GRADE_RULES_PATH": rules, "OTP_DATABASE": self.root / "invalid.sqlite3"})

    def test_custom_thresholds(self):
        rules = self.root / "custom.json"
        rules.write_text(json.dumps([{"minimum": 75, "grade": "Pass"},
                                     {"minimum": 0, "grade": "Review"}]), encoding="utf-8")
        self.client = create_app({
            "TESTING": True, "SECRET_KEY": "testing-only",
            "GRADE_RULES_PATH": rules, "OTP_DATABASE": self.root / "custom.sqlite3",
        }).test_client()
        self.assertIn(b"<dd>Pass</dd>", self.grade(["75", "75"]).data)

