# ManeeMena · PDPA Data Masking

A privacy workspace for a **Theory of Computation** assignment. ManeeMena detects five types of personal information in text logs using **Python's standard-library `re` module**, partially masks them, and explains each match. The English interface supports Thai text and emoji.

The original exercises in `regex/` are retained and turned into reusable modules. Detection and masking never use JavaScript regex, external detection libraries, AI or third-party services.

## Run locally

Python **3.10 or newer** is required. Tested with Python 3.14.6 and Flask 3.1.3.

From the project directory, on Windows PowerShell:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe app.py
```

On macOS or Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

Open **http://127.0.0.1:5000**. Stop the server with `Ctrl+C`. No database, Node.js build, API key or external account is needed. The server binds to the loopback interface with debug mode off. Flask's development server is intended for local development and demonstration.

## Run with Docker

Install Docker with Compose (Docker Desktop on Windows, using Linux containers), then run from the project directory:

```sh
docker compose up --build -d --wait
```

Open **http://127.0.0.1:8080**. Python and dependencies are installed inside the image; no local Python environment is needed. The image runs Gunicorn with two workers as a non-root user and includes an HTTP health check. No source bind mount, database or persistent volume is used.

```sh
docker compose ps
docker compose logs -f web
docker compose down
```

Stop following logs with `Ctrl+C`; `docker compose down` stops and removes this project's container and network. After editing application files, rerun `docker compose up --build -d --wait`.

Optional settings can be placed in an untracked `.env` file alongside `compose.yaml`:

```dotenv
MANEEMENA_PORT=8080
GITHUB_URL=https://github.com/YOUR_ACCOUNT/YOUR_REPOSITORY
```

`MANEEMENA_PORT` changes the host port; leave `GITHUB_URL` unset until the real repository is available. Compose publishes only on `127.0.0.1`. The local Python server can continue to use port 5000 independently. `.dockerignore` excludes the virtual environment, Git metadata, tests, screenshots and environment files from the build context.

To use only the Dockerfile without Compose:

```sh
docker build -t maneemena-masker .
docker run --rm --name maneemena-masker -p 127.0.0.1:8080:8000 maneemena-masker
```

Use either the Compose or standalone command for port 8080, not both at once. The container serves the same application and five masking rules as the local setup. Gunicorn is a container-only dependency in `requirements-docker.txt`, so Windows local installs remain unchanged.

## Assignment requirements and features

| Capability | Behavior |
| --- | --- |
| Scan & Mask | Submit text to Python `re`; output appears without a page reload. `Ctrl+Enter` / `Cmd+Enter` also scans. |
| Highlight sensitive data | Select **Detections** above the input to highlight original matches by category. |
| Statistics | Total matches, individual rule counts, original characters concealed and enabled rule count. |
| Before / After | **Compare** highlights only replaced spans; separators and visible digits remain unhighlighted. |
| Regex Playground | `/regex-playground` displays the actual compiled patterns and token explanations, with a sample and live test for each rule. |
| State machine diagram | Each pattern is drawn as the automaton it expands to: one state per character read, self-loops for `+` and `*`, dashed ε arcs for optional parts and dashed rings for lookarounds. **Run sample** walks the rule's own sample through it one transition at a time. |
| Rule toggles | Disable/enable each rule. Disabled rules are neither detected nor counted; all start enabled. |
| Sample logs | Load a fictional customer log or choose one of three scenarios on `/examples`. |
| About Us | `/about-us` shows one card per team member — nickname, student ID and full name — read from `team.py`. Fields left empty render as a blank line. |
| Bring your own text | **Upload** a plain-text file, **Paste** from the clipboard, or drop a file on the input box. Binary files and text past the 50,000-character limit are refused. |
| Demo risk | Safe = 0, Low = 1–2, Medium = 3–5, High = 6–10, Critical = 11+ enabled-rule matches. |
| Inspector | Review masked previews and original line numbers; click a row or highlight to explain it. |
| Copy, download, clear | Copy masked output, download UTF-8 `masked_log.txt`, or discard the workspace. |
| Temporary processing | No database, scan history, third-party processing or raw-input logging. |
| Live counters | Unicode code-point and line counters update as you type. |
| Explain detection | See the exact pattern and its parts; expose raw matched text only by choosing **Reveal matched text**. |

Loading, empty, error and no-match states are included. Changing input or rules invalidates old output and disables export until another scan succeeds. Late responses cannot restore stale results. The UI supports keyboard navigation and stacks the input/output panels on mobile.

**Demo Privacy Risk Score is not a PDPA compliance score.** Zero matches means no enabled patterns matched. Partial masking does not guarantee anonymity: names, domains, last digits and most of an address intentionally remain visible.

## Technology and project structure

- Flask and Jinja for the backend and pages.
- Standard-library `re` for **all detection and replacements**.
- CSS and vanilla JavaScript for UI and visualization; no frontend framework.
- Standard-library `unittest` for regex/API tests; optional Playwright for browser checks.
- Locally served styles, scripts and SVG icons; system fonts.

```text
app.py                       Flask app factory, routes, validation and privacy headers
samples.py                   Bundled fictional logs
team.py                      About Us roster: nickname, student ID and full name
regex/
  __init__.py                Local package; no third-party regex package required
  rule.py                    Shared rule metadata, replacement spans and state-machine steps
  masker.py                  Registry, scan orchestration, counts and positions
  creditcardreg.py            Original credit-card exercise, refactored
  gmailreg.py                 Original email exercise, refactored
  phonereg.py                 Original phone exercise, adapted to the assignment
  birthdayreg.py              Original DOB exercise, refactored
  address.py                 Original address exercise, relaxed to match the specification
templates/                   Dashboard, workspace, Playground, Examples and About Us
static/css/style.css         Responsive navy / mint dashboard
static/js/app.js             UI, safe highlights, requests and client-side export
tests/test_regex.py          Rule regressions, boundaries, overlaps and span metadata
tests/test_app.py            HTTP contract, input validation and privacy checks
tests/browser_check.py       Desktop/mobile browser integration checks
requirements.txt             Runtime dependency
requirements-dev.txt         Runtime + optional browser-test dependencies
requirements-docker.txt      Runtime + Gunicorn for Linux containers
Dockerfile                   Non-root Python/Gunicorn image with a health check
compose.yaml                 Local container service on port 8080
.dockerignore                Restricts the build context to runtime files
```

## Regular expressions used

The patterns below are the compiled patterns. The UI obtains them directly from `Rule.pattern.pattern`; it does not maintain another set of regex strings. Matching is case-sensitive. Numeric rules use `[0-9]` to make the intended ASCII digit format explicit.

### 1. Credit card

```regex
(?<![\w-])(?P<first>[0-9]{4})-(?P<second>[0-9]{4})-(?P<third>[0-9]{4})-(?P<last>[0-9]{4})(?![\w-])
```

- `[0-9]{4}` matches exactly four digits; literal `-` separates the groups.
- `(?P<first>...)`, `second`, `third` and `last` are named capture groups. Their spans let the application hide the first three groups and preserve the fourth.
- `(?<![\w-])` is a negative lookbehind: the previous character cannot be a word character or hyphen. `\w` includes Unicode word characters.
- `(?![\w-])` is a negative lookahead: the next character cannot continue a word or hyphenated number.
- These guards prevent matching inside longer tokens. No Luhn check is performed.

```text
1234-5678-9012-3456 → XXXX-XXXX-XXXX-3456
1234567890123456   → unchanged
```

### 2. Email

```regex
(?<![A-Za-z0-9._%+@*\-])(?P<username>[A-Za-z0-9._%+\-]+)@(?P<domain>[A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![A-Za-z0-9_@\-])
```

- The original character classes are retained. `+` outside a character class means **one or more** characters.
- `(?P<username>...)` captures the local part before the literal `@`.
- `[A-Za-z0-9.-]+` accepts domain characters; `\.` is a literal dot; `[A-Za-z]{2,}` requires at least two letters in the final suffix.
- `\-` inside the username character class means a literal hyphen. `%`, `_`, `+` and `.` are also allowed there.
- Lookaround guards prevent matching a suffix of an invalid token or an already-masked username. `*` inside the left character class is a literal asterisk.
- Replacement keeps the first/last username characters, inserts exactly `len(username) - 2` asterisks, and preserves the domain. Usernames of length one or two have no middle characters and remain unchanged.

```text
card@gmail.com                 → c**d@gmail.com
somchai.d@company.com           → s*******d@company.com
somchai.jaidee@company.co.th     → s************e@company.co.th
a@gmail.com                     → a@gmail.com
ab@gmail.com                    → ab@gmail.com
```

Short emails count as detections but contribute **zero** masked characters. This follows the selected assignment policy. Some star counts in `prompt.md` conflict with its written rule; this implementation follows the rule and actual username length. This is a practical format matcher, not full RFC email validation.

### 3. Phone

```regex
(?<![\w-])(?P<first>[0-9]{3})-(?P<second>[0-9]{3})-(?P<last>[0-9]{4})(?![\w-])
```

The structure resembles the card pattern, with groups of **3, 3 and 4 digits**. The first two groups become `XXX`; the last four digits remain visible. Boundary guards prevent partial matches. Any digits matching the assignment's format are accepted; the old Thai-mobile prefix restriction is not applied.

```text
093-245-7894 → XXX-XXX-7894
0811234567  → unchanged
```

### 4. Date of birth

```regex
(?<!\w)DOB:[ \t]*(?P<day>[0-9]{2})/(?P<month>[0-9]{2})/(?P<century>[0-9]{2})(?P<year_end>[0-9]{2})(?![\w/])
```

- `DOB:` is required with exactly this capitalization; `(?<!\w)` prevents a label embedded in a larger word.
- `[ \t]*` accepts zero or more spaces/tabs and preserves them. Unlike `\s*`, it does not consume line breaks.
- Named groups capture the day, month and two halves of the year. Day, month and the final year group become `XX`.
- Literal `/` separators, the label, whitespace and the first two year digits remain unchanged.
- This checks `DD/MM/YYYY` shape, not calendar validity or a Buddhist/Gregorian year range.

```text
DOB:25/12/2549   → DOB:XX/XX/25XX
DOB: 25/12/2549  → DOB: XX/XX/25XX
25/12/2549       → unchanged
```

### 5. Address

```regex
(?<!\w)Address:[ \t]*(?P<house>[0-9]+(?:/[0-9]+)?)(?![\w/\-])
```

- The exact `Address:` label and optional horizontal whitespace establish context.
- `[0-9]+` matches one or more house-number digits.
- `(?:/[0-9]+)?` is an optional slash and more digits. `(?:...)` groups without capturing; `?` means zero or one occurrence.
- `(?P<house>...)` captures the entire house number. Each digit inside it becomes one `X`, so the masked number keeps its original length; a slash between the two parts stays visible.
- The final guard prevents hiding just a prefix of `12/3/4`, `12-34` or `123abc`.
- No full address grammar is required; remaining text is preserved, including soi and village numbers.

```text
Address: 99/12 ถนนสุขุมวิท หมู่ 4 → Address: XX/XX ถนนสุขุมวิท หมู่ 4
Address: 689 ซอยลาดกระบัง → Address: XXX ซอยลาดกระบัง
```

### Reuse and changes from the original code

| Original file | Reused | Necessary change |
| --- | --- | --- |
| `creditcardreg.py` | Four digit groups; keep the last four digits | Add token boundaries/capture spans; make it callable instead of printing an example. |
| `gmailreg.py` | Email character classes and first/last username policy | Match throughout logs instead of validating the entire input; remove `input()`; add guards/spans. Preserve the `email_parse` helper. |
| `phonereg.py` | Numeric regex exercise | Replace the old `^0[689]\d{8}$` validator with the required hyphenated format and add masking. |
| `birthdayreg.py` | `DOB:` context and preserved year prefix | Accept/preserve spaces and tabs; remove import-time reads of `data.txt` and writes to `censored.txt`. |
| `address.py` | Leading house number, optional `/digits`, one `X` per digit | Remove full-address validation and start-of-input restriction; support log lines. Unmatched text passes through instead of returning `Not an address`. Preserve `censor_house_number`. |

Each rule exposes its compiled pattern, explanation and edit callback through one `Rule` object. `re.sub` applies its edits. The unified masker finds matches on the **original** text and builds output with consistent metadata. Overlaps resolve leftmost first, then longest at the same position. A card-shaped email username therefore becomes one email detection rather than overlapping detections. This prevents double counting and broken highlighting.

## API and Python interfaces

### Python

```python
from regex.masker import mask_text
from regex.creditcardreg import mask_credit_card
from regex.gmailreg import mask_email
from regex.phonereg import mask_phone
from regex.birthdayreg import mask_dob
from regex.address import mask_address

mask_email("Contact card@gmail.com")  # "Contact c**d@gmail.com"
result = mask_text("card@gmail.com 093-245-7894", enabled_rules=["email"])
print(result["masked_text"])  # "c**d@gmail.com 093-245-7894"
```

Individual helpers return strings. `mask_text` returns a dictionary; `enabled_rules=None` enables all and `[]` disables all. Empty text is valid for Python helpers. Unknown rule names raise `ValueError`.

### HTTP

`POST /api/mask` with `Content-Type: application/json`:

```json
{
  "text": "Customer email is card@gmail.com",
  "rules": {"credit_card": true, "email": true, "phone": true, "dob": true, "address": true}
}
```

Response:

```json
{
  "success": true,
  "masked_text": "Customer email is c**d@gmail.com",
  "total_detected": 1,
  "counts": {"credit_card": 0, "email": 1, "phone": 0, "dob": 0, "address": 0},
  "masked_characters": 2,
  "detections": [{
    "id": 0,
    "rule": "email",
    "start": 18,
    "end": 32,
    "output_start": 18,
    "output_end": 32,
    "line": 1,
    "masked_preview": "c**d@gmail.com",
    "changes": [{"start": 19, "end": 21, "output_start": 19, "output_end": 21}]
  }]
}
```

- Offsets are **zero-based Unicode code-point indexes**, end-exclusive. Lines are one-based; LF, CRLF and CR are supported. JavaScript uses `Array.from(text)` to avoid UTF-16/emoji offset errors.
- `masked_characters` counts original characters replaced, never separators. Replacing `99/12` with `XX/XX` contributes four, because the slash is kept.
- Omitted `rules`, or missing keys, default to enabled. Values must be JSON booleans; unknown rule keys are rejected.
- Empty/whitespace-only text and malformed requests return HTTP 400. Non-JSON content returns 415. More than 50,000 code points or a body larger than 1 MiB returns 413.
- Errors use `{"success": false, "error": "..."}` without echoing the submitted log.
- Responses contain masked previews and spans, not separate raw-match copies. Explicit reveal reads the existing input in browser memory.
- `GET /api/rules` returns the actual compiled pattern strings, descriptions, token explanations and fictional examples.

## Example input and output

Input:

```text
Email: somchai.jaidee@example.com
Phone: 093-245-7894
DOB:25/12/2549
Credit Card: 1234-5678-9012-3456
Address: 689 ซอยลาดกระบัง 19 ถนนลาดกระบัง แขวงลาดกระบัง เขตลาดกระบัง กรุงเทพฯ
```

Output:

```text
Email: s************e@example.com
Phone: XXX-XXX-7894
DOB:XX/XX/25XX
Credit Card: XXXX-XXXX-XXXX-3456
Address: XXX ซอยลาดกระบัง 19 ถนนลาดกระบัง แขวงลาดกระบัง เขตลาดกระบัง กรุงเทพฯ
```

Five detections, 39 original characters masked. The API preserves surrounding text/formatting. Browser textareas normalize pasted line endings; the OS clipboard may normalize them again (CRLF on Windows). Downloads contain the current masked result as UTF-8.

## Privacy design

Input goes only to this application's server. In the default local setup, that server runs on your own machine. The application does not write user input/output to disk, a database, browser storage or logs. It does not use sessions, cookies, telemetry or third-party assets. Clear discards the working data; navigation clears it before a possible back/forward cache restore.

Responses use `Cache-Control: no-store`. Log content is rendered as text nodes, never HTML. A same-origin Content Security Policy reinforces this. Downloads occur only on explicit request; copied data remains under the user's/OS's control afterward.

These are application behavior choices, not guarantees of secure memory erasure or third-party hosting behavior. Review output before sharing it. Public deployment is outside this implementation; a hosted version would need appropriate HTTPS and infrastructure logging configuration.

## Tests

Regex/API tests require only the runtime dependency:

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py" -v
```

Real-browser checks use Playwright and installed Google Chrome by default:

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
.venv/Scripts/python.exe tests/browser_check.py
```

The runner starts/stops its own local server on an unused port. It checks desktop/mobile layouts, toggles, exact spans, HTML-safe rendering, stale responses, errors, Playground, inspector/reveal, clipboard contents and downloaded bytes. Only fictional test data is used. Screenshots go into ignored `test-results/`.

If Chrome is unavailable, use Playwright's Chromium:

```powershell
.venv/Scripts/python.exe -m playwright install chromium
$env:PLAYWRIGHT_CHANNEL = "chromium"
.venv/Scripts/python.exe tests/browser_check.py
```

On macOS/Linux use `.venv/bin/python` and `PLAYWRIGHT_CHANNEL=chromium .venv/bin/python tests/browser_check.py` for the override.

## Presentation flow (under 10 minutes)

1. **0:00–1:00:** Explain accidental data exposure in logs and the five assignment formats.
2. **1:00–2:00:** Load the customer sample, scan, and explain counts and masking policy.
3. **2:00–3:30:** Open Detections and an Inspector item; explain its pattern/capture groups.
4. **3:30–4:30:** Compare before/after: unchanged separators, last digits and address context.
5. **4:30–5:30:** Disable email, scan again, then restore all rules.
6. **5:30–7:30:** Use Playground for DOB spacing, short emails and address fractions.
7. **7:30–8:30:** Copy/download, then Clear the workspace.
8. **8:30–9:30:** Explain temporary processing and why demo risk does not establish PDPA compliance.

## Team members and responsibilities

Fill in actual members before submission; no identities are invented here.

| Member | Responsibility |
| --- | --- |
| To be supplied | Original regex exercises and masking rules |
| To be supplied | Flask API, tests and privacy design |
| To be supplied | Frontend, documentation and demonstration |

## GitHub and demo URL

There is no configured Git remote in the supplied project. Set the real repository URL before starting the server to activate the external source link:

```powershell
$env:GITHUB_URL = "https://github.com/YOUR_ACCOUNT/YOUR_REPOSITORY"
.venv/Scripts/python.exe app.py
```

On macOS/Linux: `GITHUB_URL=https://github.com/YOUR_ACCOUNT/YOUR_REPOSITORY .venv/bin/python app.py`.

Only HTTPS URLs on `github.com` are accepted. Without one, no source link is shown at all; no fake project repository is linked.

- Local demo: **http://127.0.0.1:5000**
- Docker demo: **http://127.0.0.1:8080**
- Public demo URL: **To be supplied if deployed**
- GitHub repository: **To be supplied via `GITHUB_URL`**

## References

- [Python `re` documentation](https://docs.python.org/3/library/re.html) — matching, groups, lookarounds and substitution.
- [Flask documentation](https://flask.palletsprojects.com/en/stable/) — setup, requests and test clients.
- [Thailand PDPA on the Ministry of Digital Economy and Society website](https://www.mdes.go.th/law/detail/3577-Personal-Data--Protection-Act-B-E--) — background reading for the assignment.
