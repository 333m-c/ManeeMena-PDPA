"""Local, stateless Flask interface for the assignment's Python regex rules."""

import os
from urllib.parse import urlparse

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from regex.masker import RULES, RULE_MAP, mask_text
from samples import SAMPLES
from team import FIELDS, TEAM

MAX_CHARACTERS = 50_000


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(MAX_CONTENT_LENGTH=1_048_576, GITHUB_URL=os.environ.get("GITHUB_URL", ""))
    if test_config:
        app.config.update(test_config)
    app.json.ensure_ascii = False

    @app.context_processor
    def page_data():
        github = app.config["GITHUB_URL"]
        parsed = urlparse(github)
        if parsed.scheme != "https" or parsed.hostname != "github.com" or parsed.username or parsed.password:
            github = ""
        return {"rules": [rule.public() for rule in RULES], "samples": SAMPLES, "machines": {},
                "github_url": github, "max_characters": MAX_CHARACTERS}

    @app.get("/")
    def index():
        return render_template("index.html", page="masker")

    @app.get("/regex-playground")
    def playground():
        # Only this page draws the automata, so their data stays off the others.
        return render_template("playground.html", page="playground",
                               machines={rule.key: rule.machine() for rule in RULES})

    @app.get("/examples")
    def examples():
        return render_template("examples.html", page="examples")

    @app.get("/about-us")
    def about_us():
        return render_template("about_us.html", page="team", team=TEAM, fields=FIELDS)

    @app.get("/api/rules")
    def rule_catalog():
        return jsonify(rules=[rule.public() for rule in RULES])

    @app.post("/api/mask")
    def mask():
        if not request.is_json:
            return error("Send a JSON request with Content-Type: application/json.", 415)
        payload = request.get_json()
        if not isinstance(payload, dict):
            return error("The request must be a JSON object.")
        text = payload.get("text")
        if not isinstance(text, str) or not text.strip():
            return error("Enter some text to scan.")
        if len(text) > MAX_CHARACTERS:
            return error("Keep your input within 50,000 characters.", 413)
        try:
            text.encode("utf-8")
        except UnicodeEncodeError:
            return error("Use valid UTF-8 text.")
        settings = payload.get("rules", {})
        if not isinstance(settings, dict) or settings.keys() - RULE_MAP.keys():
            return error("Use only the five supported masking rule names.")
        if any(type(value) is not bool for value in settings.values()):
            return error("Each rule must be true or false.")
        enabled = [key for key in RULE_MAP if settings.get(key, True)]
        return jsonify(success=True, **mask_text(text, enabled))

    def error(message, status=400):
        return jsonify(success=False, error=message), status

    @app.errorhandler(BadRequest)
    def bad_request(_exception):
        return error("The request contains invalid JSON.")

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_exception):
        return error("The request is too large. Use at most 50,000 characters.", 413)

    @app.after_request
    def privacy_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; font-src 'self'; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        )
        return response

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
