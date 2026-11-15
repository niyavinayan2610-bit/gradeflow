# Gradeflow

A Flask mini-project with two independent tools: six-digit OTP verification and academic result generation.

| Project link | Status |
| --- | --- |
| GitHub repository | **[FILL IN AFTER UPLOAD: GitHub repository URL]** |
| Live website | **[FILL IN AFTER DEPLOYMENT: Render service URL]** |

The [project report](docs/PROJECT_REPORT.md) describes the design, algorithms, tests, screenshot slots, and full publishing steps.

## Features

- **OTP demo** — Generate a code, enter it in the same browser, and see a success or error message. Codes expire after 5 minutes, allow 5 valid-format guesses, and are single-use. Generation has a 15-second cooldown per browser session.
- **Student grading** — Enter a name, roll number and 2–10 distinct subjects. The app validates marks, totals them, computes the average, and produces a printable result with a subject breakdown.
- **Configurable grade scale** — Edit [grade_rules.json](grade_rules.json) and restart the app. The grading page shows the active scale.
- **Responsive interface** — The layouts stack on narrow screens. Forms provide keyboard focus, field-level errors, and clear status messages.

## Run locally

Install Python 3.14 and extract the ZIP. Open a terminal in the extracted `gradeflow` folder, where `app.py` lives.

**Windows PowerShell**

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app app run
~~~

**macOS or Linux**

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m flask --app app run
~~~

Open [the local app](http://127.0.0.1:5000). To stop it, press Ctrl+C in your terminal. If port 5000 is occupied, add `--port 5001` to the last command and open that port instead.

## Try both tools

1. Open **OTP demo**, select **Generate code**, then copy the six digits, including any leading zero. Enter the digits and choose **Verify code**. Try the same code again to see the reuse error. A new code replaces the previous one.
2. Open **Grades** and enter a sample name and roll number such as Ananya Rao and CS-024. Enter Mathematics 90, Physics 84.50, and English 79. The result is **253.50 / 300**, **84.50%**, and **A**. Use **Print result** to print the result or save it as a PDF through your browser.

## Configure grading

Each subject is worth 100 marks and has equal weight. Default minimum averages are **A+ 90**, **A 80**, **B 70**, **C 60**, **D 50**, and **F 0**. Thresholds are inclusive. Supply unique nonempty labels and strictly descending whole-number minimums between 0 and 100, with the final minimum set to 0. The server rejects an invalid scale on startup. The grade uses the exact total and subject count, while the displayed average is rounded to two decimal places.

## Run tests

In the terminal used to install dependencies, run:

~~~powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
~~~

On macOS and Linux, replace the interpreter path with `.venv/bin/python`. Tests cover OTP expiry, reuse, attempts, cooldown, isolation, concurrency, and grade calculation, configuration, validation, and escaping.

## Deploy on Render

1. Push the extracted project to GitHub with `render.yaml` at the repository root.
2. In Render, choose **New → Blueprint**, connect the repository, and apply the configuration. The Blueprint declares a Free Python web service, generates `SECRET_KEY`, enables secure cookies, and runs Gunicorn on Render’s port.
3. When the service is live, copy its service URL from the Render dashboard, open the app, and test both tools. Update the project link table above and the corresponding fields in the project report.

See the [publishing walkthrough](docs/PROJECT_REPORT.md#publishing-to-github) for Git commands and a manual Render setup option. [Render Flask guide](https://render.com/docs/deploy-flask) · [Render Blueprint reference](https://render.com/docs/blueprint-spec)

## Demo scope

The code is displayed on screen to teach the verification flow. The app uses no SMS, email, or user accounts. Use fictional student details in the public demo. Student results are calculated on request and are not written to a database. OTP state lives in `instance/otp.sqlite3`, a local SQLite file shared by workers on a single service instance. Restarts or deploys may invalidate active codes. Production authentication would need verified delivery, account-level controls and a shared state store for multiple instances.

