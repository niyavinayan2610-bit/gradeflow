# Gradeflow · Mini-project report

| Field | Value |
| --- | --- |
| Project title | Gradeflow — OTP Verification and Student Grading |
| Prepared by | **[FILL IN: Student name and roll number]** |
| Institution / course | **[FILL IN: Institution and course]** |
| Submission date | **[FILL IN: Date]** |
| GitHub repository | [GitHub repository](https://github.com/niyavinayan2610-bit/gradeflow) |
| Live website | [Live website](https://gradeflow-phqb.onrender.com) |

## 1. Abstract and aim

Gradeflow combines two introductory Python programs into a web application. The first demonstrates how a six-digit one-time password can be issued and verified. The second automates calculation of a student's total, average, and grade from subject marks. The aim is to demonstrate form processing, server-side validation, secure random generation, configurable rules, and deployment of a Flask application.

## 2. Scope and features

- Six-digit code generation, including leading zeros, with clear feedback for invalid format, wrong code, expiry, cooldown, and exhausted attempts.
- One active code per browser session, with a 5-minute lifetime, 5 guesses, and a 15-second generation cooldown.
- A name, roll number, and 2–10 subject-and-mark pairs for each result. Marks can have up to two decimal places. Duplicate subjects are rejected after case and whitespace normalization.
- Total and maximum marks, percentage average, letter grade, and a subject-wise table. A print view supports saving the result as a PDF through the browser.
- Responsive pages, keyboard-accessible controls, HTML validation, and server-side validation.

The OTP is displayed in the demo instead of being sent to a verified destination. The grade tool is independently available from the navigation. Results are generated on request and never inserted into SQLite.

## 3. Requirements and architecture

**Local requirements.** Python 3.14, a modern browser, and the Python packages in `requirements.txt`. Git and GitHub are needed for repository publishing. Render runs the hosted Python service with Gunicorn.

**Request flow.**

~~~text
Browser (HTML, CSS, JavaScript)
         |  GET pages / POST form data
         v
Flask routes and CSRF validation
         |---------------------|
         v                     v
OTP service              Grading calculator
         |                     |
SQLite challenge data    Grade thresholds (JSON)
         |---------------------|
         v
Jinja templates render status or result in the browser
~~~

| Module | Responsibility |
| --- | --- |
| `app.py` | Creates the Flask app, handles routes and sessions, validates POST tokens, sets security headers, and renders templates. |
| `otp.py` | Generates codes, stores keyed digests, manages expiry and attempts, and consumes each code atomically. |
| `grading.py` | Loads and validates thresholds, validates marks and subjects, and calculates the result. |
| `grade_rules.json` | Sets the grade labels and inclusive minimum averages. |
| `templates/` | Shared layout, overview, OTP form, grade form, result, and form-error views. |
| `static/styles.css` | Desktop and mobile layouts, focus styles, and print styling. |
| `static/app.js` | Adds and removes subject rows, manages focus, and triggers printing. |
| `tests/test_app.py` | Automated tests using Flask’s test client and temporary SQLite files. |
| `requirements.txt`, `.python-version`, `render.yaml` | Dependencies, Python version, and Render service configuration. |

| Route | Method | Purpose |
| --- | --- | --- |
| `/` | GET | Overview and navigation. |
| `/otp` | GET, POST | View the demo, issue a code, or verify one. |
| `/grades` | GET, POST | Enter marks and produce a result. |
| `/healthz` | GET | Returns a health response for the hosting service. |

## 4. Algorithms

### OTP generation and verification

1. On the initial form view, assign the browser an unpredictable token in a signed, HTTP-only session cookie. Check the matching hidden token on each POST.
2. For generation, start a SQLite write transaction, remove expired records, and check the session’s cooldown.
3. Draw a random integer between 0 and 999999 with Python’s `random.SystemRandom`. Format it as six digits. Store only an HMAC-SHA256 digest tied to that session, the generation timestamp, and the remaining attempts. Return the plaintext code on the generation page for the demo.
4. On verification, require six ASCII digits. Check that the session has an active code, that it has not expired, and that it has attempts remaining.
5. Compare the stored and submitted-code digests with `hmac.compare_digest`. Close the code on success. Decrement the attempt count on a valid-format wrong guess, and close it after the fifth. The SQLite transaction ensures concurrent verifications cannot both succeed.

The app adds cache-control headers to form and result pages and enables Secure cookies on Render. Cooldowns and limits apply to one browser session. A new session can start a separate demo. The SQLite file is temporary on Render and supports this single-instance deployment.

### Student grading

1. Trim and validate the name, roll number, subject names and marks. Check the subject count, reject duplicate subject names, and require every mark to be between 0 and 100.
2. Use decimal arithmetic to sum all subject marks. Compute maximum marks as 100 × the number of subjects.
3. Divide total marks by the subject count to get the average. Since every subject is out of 100, this also gives the percentage.
4. Select the first descending threshold whose minimum × subject count is at most the total. This compares the exact values before rounding the displayed average.
5. Display the student details and result. For example, scores of 90, 84.50, and 79 give 253.50 out of 300, an average of 84.50%, and grade A.

| Minimum average | Grade |
| ---: | :--- |
| 90 | A+ |
| 80 | A |
| 70 | B |
| 60 | C |
| 50 | D |
| 0 | F |

## 5. Testing and validation

The 13 automated tests passed locally with Python 3.14.3, Flask 3.1.3, and a temporary database per test. See the [README](../README.md#run-tests) for the test command.

| Scenario | Expected result |
| --- | --- |
| Leading-zero code with a correct submission | Six digits are shown and verification succeeds once. |
| Reuse or concurrent correct submission | Only one verification succeeds. |
| Five wrong guesses | Attempts decrease to zero and the code closes. |
| Invalid format, expired code, or separate session | The relevant error appears and access to the challenge is rejected. |
| Immediate generation and later replacement | Cooldown returns HTTP 429. A new code replaces the previous code after cooldown. |
| Valid marks and an exact grade boundary | Total and average display correctly. The exact boundary determines the grade. |
| Invalid marks, duplicate subjects, or invalid subject count | Field or form errors identify the problem and valid row structures are preserved. |
| Custom thresholds and malformed configuration | Custom labels take effect. A malformed scale stops startup. |
| Missing form token or oversized body | The route returns a readable form error. |

After deployment, open the site on desktop and mobile. Complete both workflows, add and remove subject rows, and open the print preview for a result. Open `/healthz` on the live service and check that it returns an OK status.

## 6. Screenshot placeholders

Capture the running app using sample student details, save the images in `docs/screenshots/`, and replace each placeholder with the matching Markdown image.

| Figure | Screenshot placeholder | Suggested file |
| --- | --- | --- |
| 1 | **[INSERT: Overview page showing both tools]** | `screenshots/01-overview.png` |
| 2 | **[INSERT: OTP page immediately after issuing a sample code]** | `screenshots/02-otp-generated.png` |
| 3 | **[INSERT: OTP verification success message]** | `screenshots/03-otp-verified.png` |
| 4 | **[INSERT: Student details and subject marks form]** | `screenshots/04-grade-form.png` |
| 5 | **[INSERT: Academic result showing totals, average and grade]** | `screenshots/05-academic-result.png` |
| 6 | **[INSERT: Mobile layout for either tool]** | `screenshots/06-mobile.png` |

For example, replace a placeholder with `![Gradeflow overview](screenshots/01-overview.png)`.

## 7. Publishing to GitHub

1. Extract the ZIP. In a terminal, open the inner `gradeflow` folder that contains `app.py`.
2. Sign in to GitHub. Create an empty repository, for example `gradeflow`. Choose repository visibility appropriate for your submission. Leave GitHub’s initialization options unchecked because the project includes its own README and ignore file.
3. Run the commands below with Git installed. Replace `YOUR-REPOSITORY-CLONE-URL` with the HTTPS clone URL GitHub shows. Git may prompt you to authenticate.

~~~bash
git init -b main
git add .
git status
git commit -m "Initial Gradeflow project"
git remote add origin YOUR-REPOSITORY-CLONE-URL
git push -u origin main
~~~

4. Open the repository on GitHub and confirm that `app.py`, `render.yaml`, and the README are visible. Copy the repository’s web address into the README and this report.

If Git asks for commit identity, set `git config user.name "Your Name"` and `git config user.email "Your GitHub commit email"` from inside the project, then retry the commit. [GitHub guide to uploading local code](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github)

## 8. Deploying on Render

### Blueprint setup

1. Sign in to Render, connect your GitHub account, and grant Render access to the new repository.
2. In the dashboard, select **New → Blueprint**, choose the repository and branch, and review the settings from `render.yaml`. Apply the Blueprint. It defines one Free web service, generates a strong `SECRET_KEY`, and sets `COOKIE_SECURE=true`.
3. Wait for the build and deployment to succeed. Open the service’s URL from the dashboard and run the checks in Section 5. Free services may take longer to load after inactivity.
4. Paste the exact service URL into the README and report. Then run `git add README.md docs/PROJECT_REPORT.md`, `git commit -m "Add published project links"`, and `git push`.

### Manual web service option

Select **New → Web Service**, connect the same GitHub repository, and choose the Python runtime and Free plan. Leave the Root Directory at the repository root. Enter these values:

| Setting | Value |
| --- | --- |
| Build command | `python -m pip install -r requirements.txt` |
| Start command | `gunicorn --workers 2 --bind 0.0.0.0:$PORT app:app` |
| Health check path | `/healthz` |
| Environment variable | `COOKIE_SECURE=true` |
| Environment variable | `SECRET_KEY` set to a strong, private value |

For the manual setup, generate a secret locally using `python -c "import secrets; print(secrets.token_hex(32))"` and enter it in the Render Environment panel. Keep the value out of GitHub and the report. If the service fails to start, check the build and runtime logs, then confirm the commands, root directory, and environment settings. [Render Flask deployment](https://render.com/docs/deploy-flask) · [Blueprint reference](https://render.com/docs/blueprint-spec) · [Free service behavior](https://render.com/docs/free)

## 9. Conclusion

Gradeflow implements both original Python exercises through validated web forms. The OTP flow demonstrates code generation, expiry, and single use, while the grade calculator demonstrates configurable academic rules and a structured, printable result.

