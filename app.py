import hmac
import os
import secrets
from pathlib import Path

from flask import Flask, abort, render_template, request, session

from grading import calculate_result, load_rules, MIN_SUBJECTS, MAX_SUBJECTS
from otp import OtpStore


def create_app(config=None):
    app = Flask(__name__)
    secret = os.environ.get("SECRET_KEY")
    secure_cookie = os.environ.get("COOKIE_SECURE", "").lower() == "true"
    if (secure_cookie or os.environ.get("RENDER") == "true") and not secret:
        raise RuntimeError("Set SECRET_KEY before deploying Gradeflow.")
    app.config.from_mapping(
        SECRET_KEY=secret or secrets.token_hex(32),
        SESSION_COOKIE_SECURE=secure_cookie,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=16 * 1024,
        OTP_DATABASE=str(Path(app.instance_path) / "otp.sqlite3"),
        GRADE_RULES_PATH=str(Path(app.root_path) / "grade_rules.json"),
    )
    if config:
        app.config.update(config)
    db_path = Path(app.config["OTP_DATABASE"])
    db_path.parent.mkdir(parents=True, exist_ok=True)
    otp = OtpStore(db_path, app.secret_key)
    rules = load_rules(app.config["GRADE_RULES_PATH"])

    @app.before_request
    def protect_forms():
        if request.method == "POST":
            token = session.get("browser", "")
            submitted = request.form.get("csrf_token", "")
            if not token or not hmac.compare_digest(token.encode(), submitted.encode()):
                abort(400, "This form has expired. Reopen the page and submit it again.")

    @app.after_request
    def protect_responses(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.context_processor
    def form_token():
        if "browser" not in session:
            session["browser"] = secrets.token_urlsafe(32)
        return {"csrf_token": session["browser"]}

    @app.get("/")
    def home():
        return render_template("home.html")

    @app.route("/otp", methods=["GET", "POST"])
    def otp_page():
        if request.method == "GET":
            return render_template("otp.html")
        action = request.form.get("action")
        browser = session["browser"]
        if action == "generate":
            code, message = otp.issue(browser)
            # A cooldown warning leaves the preceding generation response in browser history.
            return render_template("otp.html", code=code, message=message,
                                   kind="success" if code else "warning"), 200 if code else 429
        if action == "verify":
            success, message = otp.verify(browser, request.form.get("code", "").strip())
            return render_template("otp.html", message=message,
                                   kind="success" if success else "error"), 200 if success else 422
        abort(400, "Choose a code action and try again.")

    @app.route("/grades", methods=["GET", "POST"])
    def grade_page():
        fields = {"name": "", "roll": ""}
        rows = [("", "")] * 3
        errors, result = {}, None
        if request.method == "POST":
            fields = {key: request.form.get(key, "") for key in fields}
            subjects, marks = request.form.getlist("subject"), request.form.getlist("mark")
            if MIN_SUBJECTS <= len(subjects) == len(marks) <= MAX_SUBJECTS:
                rows = list(zip(subjects, marks))
            result, errors = calculate_result(request.form, rules)
        return render_template("grades.html", fields=fields, rows=rows, errors=errors,
                               result=result, rules=rules, minimum=MIN_SUBJECTS,
                               maximum=MAX_SUBJECTS), 422 if errors else 200

    @app.get("/healthz")
    def health():
        return {"status": "ok"}

    @app.errorhandler(400)
    @app.errorhandler(413)
    def form_error(error):
        return render_template("error.html", message=error.description), error.code

    return app


app = create_app()

