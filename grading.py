import json
import re
from decimal import Decimal
from pathlib import Path

MARK = re.compile(r"[0-9]{1,3}(?:\.[0-9]{1,2})?")
MIN_SUBJECTS = 2
MAX_SUBJECTS = 10


def load_rules(path):
    rules = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(rules, list) or not rules:
        raise ValueError("Grade rules must be a nonempty list.")
    ceiling = 101
    labels = set()
    for entry in rules:
        if not isinstance(entry, dict):
            raise ValueError("Every grade rule must be an object.")
        minimum, grade = entry.get("minimum"), entry.get("grade")
        if type(minimum) is not int or not 0 <= minimum < ceiling:
            raise ValueError("Grade minimums must be descending integers from 0 to 100.")
        if not isinstance(grade, str) or not grade.strip() or grade in labels:
            raise ValueError("Grade labels must be unique nonempty strings.")
        ceiling = minimum
        labels.add(grade)
    if ceiling != 0:
        raise ValueError("The last grade rule must start at 0.")
    return rules


def calculate_result(form, rules):
    name = form.get("name", "").strip()
    roll = form.get("roll", "").strip()
    subjects = form.getlist("subject")
    marks = form.getlist("mark")
    errors = {}
    if not 1 <= len(name) <= 80:
        errors["name"] = "Enter a student name with 1–80 characters."
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 /_-]{0,29}", roll):
        errors["roll"] = "Enter a roll number with 1–30 letters, digits, spaces, slashes, hyphens or underscores."
    if len(subjects) != len(marks) or not MIN_SUBJECTS <= len(subjects) <= MAX_SUBJECTS:
        errors["rows"] = "Provide a subject name and mark for each of 2–10 subjects."
        return None, errors

    rows = []
    seen = set()
    for index, (subject, mark) in enumerate(zip(subjects, marks), 1):
        subject = subject.strip()
        key = " ".join(subject.casefold().split())
        mark = mark.strip()
        value = Decimal(mark) if MARK.fullmatch(mark) else None
        if not 1 <= len(subject) <= 60:
            errors[f"subject{index}"] = "Enter a subject name with 1–60 characters."
        elif key in seen:
            errors[f"subject{index}"] = "Enter a different subject name."
        if value is None or value > 100:
            errors[f"mark{index}"] = "Enter a mark from 0 to 100 with up to two decimal places."
        seen.add(key)
        rows.append((subject, value))

    if errors:
        return None, errors

    total = sum(value for _, value in rows)
    count = len(rows)
    # Comparing the total to minimum × count avoids rounding at grade boundaries.
    grade = next(rule["grade"] for rule in rules if total >= rule["minimum"] * count)
    return dict(name=name, roll=roll, rows=rows, total=total,
                maximum=100 * count, average=total / count, grade=grade), {}

