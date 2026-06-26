import csv
import json
import os
import re
import time
from html import unescape
from html.parser import HTMLParser
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from dotenv import load_dotenv

MYOPENMATH_HOST = "www.myopenmath.com"
CANVAS_HOST = "coastdistrict.instructure.com"
CANVAS_COURSE_ID = "151654"
ASSESS_URL = f"https://{MYOPENMATH_HOST}/assess2/"
LOAD_ASSESS_URL = f"{ASSESS_URL}loadassess.php"
LOAD_QUESTION_URL = f"{ASSESS_URL}loadquestion.php"
SCORE_QUESTION_URL = f"{ASSESS_URL}scorequestion.php"
START_ASSESS_URL = f"{ASSESS_URL}startassess.php"
CSV_PATH = Path("openmath_aids.csv")
ANSWERS_DIR = Path("answer_sessions")


class NeedRelaunch(Exception):
    pass


class QuestionParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.inputs: list[dict] = []
        self.labels: dict[str, list[str]] = {}
        self.current_label_for: str | None = None
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value or "" for key, value in attrs}
        classes = set(attr_map.get("class", "").split())

        if self.skip_depth > 0:
            self.skip_depth += 1
            return

        if tag in {"script", "style"} or "autoshowans" in classes or "hidden" in classes:
            self.skip_depth = 1
            return

        if tag == "label":
            self.current_label_for = attr_map.get("for") or None

        if tag in {"input", "textarea", "select"}:
            name = attr_map.get("name", "")
            if name:
                self.inputs.append(
                    {
                        "name": name,
                        "type": attr_map.get("type", tag),
                        "value": attr_map.get("value", ""),
                        "id": attr_map.get("id", ""),
                        "checked": "checked" in {key.lower() for key, _ in attrs},
                    }
                )

        if tag in {"br", "div", "p", "li", "ul"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self.skip_depth > 0:
            self.skip_depth -= 1
            return

        if tag == "label":
            self.current_label_for = None

        if tag in {"div", "p", "li", "ul"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_depth > 0:
            return

        self.parts.append(data)
        if self.current_label_for:
            self.labels.setdefault(self.current_label_for, []).append(data)

    def text(self) -> str:
        lines = [" ".join(line.split()) for line in "".join(self.parts).splitlines()]
        return "\n".join(line for line in lines if line)

    def answer_fields(self) -> list[dict]:
        fields = []
        for item in self.inputs:
            label = ""
            if item["id"] in self.labels:
                label = " ".join("".join(self.labels[item["id"]]).split())
            fields.append({**item, "label": label})
        return fields


class FormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.forms: list[dict] = []
        self.current_form: dict | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value or "" for key, value in attrs}
        if tag == "form":
            self.current_form = {
                "action": unescape(attr_map.get("action", "")),
                "method": attr_map.get("method", "get").lower(),
                "inputs": {},
            }
            return

        if tag == "input" and self.current_form is not None:
            name = attr_map.get("name", "")
            if name:
                self.current_form["inputs"][name] = unescape(attr_map.get("value", ""))

    def handle_endtag(self, tag: str) -> None:
        if tag == "form" and self.current_form is not None:
            self.forms.append(self.current_form)
            self.current_form = None


def parse_cookie_header(cookie_header: str) -> dict[str, str]:
    parsed = SimpleCookie()
    parsed.load(cookie_header)
    return {key: morsel.value for key, morsel in parsed.items()}


def set_session_cookies(session: requests.Session, cookie_header: str, domain: str) -> None:
    if domain == CANVAS_HOST and "=" not in cookie_header:
        session.cookies.set("canvas_session", cookie_header, domain=domain, path="/")
        return

    for key, value in parse_cookie_header(cookie_header).items():
        session.cookies.set(key, value, domain=domain, path="/")


def make_session() -> requests.Session:
    session = requests.Session()
    full_cookie = os.getenv("MYOPENMATH_COOKIE", "").strip()
    session_cookie = os.getenv("MYOPENMATH_SESSION", "").strip()

    if full_cookie:
        set_session_cookies(session, full_cookie, MYOPENMATH_HOST)
    elif session_cookie:
        session.cookies.set("PHPSESSID", session_cookie, domain=MYOPENMATH_HOST, path="/")
    else:
        raise SystemExit("Set MYOPENMATH_SESSION in .env first.")

    canvas_cookie = os.getenv("CANVAS_COOKIE", "").strip()
    if canvas_cookie:
        set_session_cookies(session, canvas_cookie, CANVAS_HOST)

    session.headers.update(
        {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149 Safari/537.36"
            ),
        }
    )
    return session


def load_assignments() -> list[dict]:
    if not CSV_PATH.exists():
        raise SystemExit("Run resolve_openmath_aids.py first to create openmath_aids.csv.")

    with CSV_PATH.open(newline="", encoding="utf-8") as file:
        rows = [
            row
            for row in csv.DictReader(file)
            if row.get("status") == "ok" and row.get("myopenmath_assessment_id")
        ]

    if not rows:
        raise SystemExit("openmath_aids.csv has no resolved MyOpenMath assignments.")

    return rows


def parse_forms(html: str) -> list[dict]:
    parser = FormParser()
    parser.feed(html)
    return parser.forms


def find_form(html: str, action_substring: str | None = None) -> dict | None:
    for form in parse_forms(html):
        if action_substring is None or action_substring in form["action"]:
            return form
    return None


def find_next_lti_url(html: str) -> str | None:
    patterns = [
        r"https://sso\.canvaslms\.com/api/lti/authorize_redirect[^\"'<>\\\s]+",
        rf"https://{re.escape(CANVAS_HOST)}/api/lti/authorize[^\"'<>\\\s]+",
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            return unescape(match.group(0))
    return None


def find_js_retry_url(base_url: str, html: str) -> str | None:
    match = re.search(r"window\.location\.pathname\s*\+\s*'([^']+)'", html)
    if not match:
        return None

    parsed = urlparse(base_url)
    query = match.group(1).replace("&amp;", "&")
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}{query}"


def is_selected_assessment_url(url: str, course_id: str, assessment_id: str) -> bool:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    return (
        parsed.netloc == MYOPENMATH_HOST
        and parsed.path == "/assess2/"
        and query.get("cid", [""])[0] == course_id
        and query.get("aid", [""])[0] == assessment_id
    )


def maybe_landed_on_assessment(
    response: requests.Response,
    course_id: str,
    assessment_id: str,
) -> bool:
    if is_selected_assessment_url(response.url, course_id, assessment_id):
        return True
    if is_selected_assessment_url(response.headers.get("location", ""), course_id, assessment_id):
        return True
    return any(
        is_selected_assessment_url(previous.headers.get("location", ""), course_id, assessment_id)
        for previous in response.history
    )


def submit_or_follow_next_lti_step(
    session: requests.Session,
    response: requests.Response,
) -> requests.Response | None:
    form = find_form(response.text)
    if form and form["action"]:
        action = urljoin(response.url, form["action"])
        if form["method"] == "get":
            return session.get(action, params=form["inputs"], timeout=20)
        return session.post(action, data=form["inputs"], timeout=20)

    next_url = find_next_lti_url(response.text)
    if next_url:
        return session.get(next_url, timeout=20)

    retry_url = find_js_retry_url(response.url, response.text)
    if retry_url:
        return session.get(retry_url, timeout=20)

    return None


def relaunch_assignment_lti(
    assignment: dict,
    course_id: str,
    assessment_id: str,
) -> requests.Session:
    if not os.getenv("CANVAS_COOKIE", "").strip():
        raise SystemExit(
            "MyOpenMath says this assignment needs a fresh LTI launch. "
            "Set CANVAS_COOKIE in .env so the script can reopen it through Canvas."
        )

    from resolve_openmath_aids import make_session as make_lti_session
    from resolve_openmath_aids import resolve_assignment_aid

    session = make_lti_session()
    result = resolve_assignment_aid(session, assignment)
    if (
        result.get("status") == "ok"
        and result.get("myopenmath_course_id") == course_id
        and result.get("myopenmath_assessment_id") == assessment_id
    ):
        return session

    raise SystemExit(
        "Could not complete the Canvas -> MyOpenMath LTI relaunch. "
        f"Resolver status: {result.get('status')}"
    )


def choose_assignment(assignments: list[dict]) -> dict:
    for index, row in enumerate(assignments, start=1):
        print(
            f"{index:2}. {row['title']} "
            f"(aid {row['myopenmath_assessment_id']}, {row['points_possible']} pts)"
        )

    while True:
        try:
            choice = input("\nChoose assignment number: ").strip()
        except EOFError:
            raise SystemExit("No assignment selected.")
        if not choice:
            raise SystemExit("No assignment selected.")
        if choice.isdigit() and 1 <= int(choice) <= len(assignments):
            return assignments[int(choice) - 1]
        print("Enter one of the listed numbers.")


def get_csrf_token(session: requests.Session, course_id: str, assessment_id: str) -> str:
    response = session.get(
        ASSESS_URL,
        params={"cid": course_id, "aid": assessment_id},
        timeout=20,
    )
    response.raise_for_status()
    match = re.search(r'CSRFP\.setToken\("([^"]+)"\)', response.text)
    if not match:
        raise SystemExit("Could not find MyOpenMath CSRF token. Refresh MYOPENMATH_SESSION.")
    return match.group(1)


def myopenmath_headers(csrf_token: str, course_id: str, assessment_id: str) -> dict[str, str]:
    return {
        "Origin": f"https://{MYOPENMATH_HOST}",
        "Referer": f"{ASSESS_URL}?cid={course_id}&aid={assessment_id}",
        "csrfp-token": csrf_token,
    }


def load_assess_info(
    session: requests.Session,
    course_id: str,
    assessment_id: str,
) -> dict:
    response = session.get(
        LOAD_ASSESS_URL,
        params={"cid": course_id, "aid": assessment_id},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        if data["error"] == "need_relaunch":
            raise NeedRelaunch
        raise SystemExit(f"MyOpenMath returned error from loadassess: {data['error']}")
    return data


def start_practice(
    session: requests.Session,
    course_id: str,
    assessment_id: str,
    csrf_token: str,
) -> None:
    response = session.post(
        START_ASSESS_URL,
        params={"cid": course_id, "aid": assessment_id},
        data={
            "practice": "true",
            "preview_all": "0",
            "password": "",
            "in_print": "0",
            "new_group_members": "",
            "cur_group": "0",
            "has_ltisourcedid": "false",
        },
        headers=myopenmath_headers(csrf_token, course_id, assessment_id),
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise SystemExit(f"MyOpenMath could not start practice: {data['error']}")


def load_question(
    session: requests.Session,
    course_id: str,
    assessment_id: str,
    csrf_token: str,
    question_number: int,
    practice: bool,
) -> dict:
    response = session.post(
        LOAD_QUESTION_URL,
        params={"cid": course_id, "aid": assessment_id},
        data={
            "qn": str(question_number),
            "practice": "true" if practice else "false",
            "regen": "0",
            "jumptoans": "0",
        },
        headers=myopenmath_headers(csrf_token, course_id, assessment_id),
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise SystemExit(f"MyOpenMath returned error from loadquestion: {data['error']}")

    questions = data.get("questions")
    if isinstance(questions, list) and question_number < len(questions):
        return questions[question_number]
    if isinstance(questions, dict) and str(question_number) in questions:
        return questions[str(question_number)]
    raise SystemExit(f"Unexpected question response shape for question {question_number + 1}.")


def scorable_field_names(fields: list[dict]) -> list[str]:
    names = []
    seen = set()
    ignored_types = {"button", "file", "hidden", "image", "reset", "submit"}

    for field in fields:
        name = field.get("name", "")
        field_type = field.get("type", "").lower()
        if not name or field_type in ignored_types or name.endswith("-val"):
            continue
        if name not in seen:
            seen.add(name)
            names.append(name)

    return names


def build_practice_score_payload(
    question_number: int,
    question: dict,
    fields: list[dict],
    answer_values: dict[str, str],
    *,
    time_active_ms: int = 1000,
    last_loaded_ms: int | None = None,
) -> dict[str, str]:
    field_names = scorable_field_names(fields)
    if not field_names:
        field_names = [
            name
            for name in answer_values
            if name.startswith("qn") and not name.endswith("-val")
        ]

    payload = {name: value for name, value in answer_values.items() if value is not None}
    payload.update(
        {
            "toscoreqn": json.dumps({str(question_number): list(range(len(field_names)))}),
            "timeactive": str(time_active_ms),
            "lastloaded": str(last_loaded_ms or int(time.time() * 1000)),
            "verification": json.dumps(
                {
                    str(question_number): {
                        "tries": [int(question.get("try", 0) or 0)],
                        "regen": int(question.get("regen", 0) or 0),
                    }
                }
            ),
            "practice": "true",
            "autosave-tosaveqn": "{}",
            "autosave-lastloaded": "{}",
            "autosave-verification": "{}",
            "autosave-timeactive": "{}",
        }
    )
    return payload


def submit_practice_answer(
    session: requests.Session,
    course_id: str,
    assessment_id: str,
    csrf_token: str,
    question_number: int,
    question: dict,
    fields: list[dict],
    answer_values: dict[str, str],
    *,
    practice: bool,
) -> dict:
    if not practice:
        raise SystemExit("Refusing to submit: submit_practice_answer only works in practice mode.")

    payload = build_practice_score_payload(
        question_number,
        question,
        fields,
        answer_values,
    )
    response = session.post(
        SCORE_QUESTION_URL,
        params={"cid": course_id, "aid": assessment_id},
        data=payload,
        headers=myopenmath_headers(csrf_token, course_id, assessment_id),
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise SystemExit(f"MyOpenMath returned error from scorequestion: {data['error']}")
    return data


def parse_question(html: str) -> tuple[str, list[dict]]:
    parser = QuestionParser()
    parser.feed(html)
    return parser.text(), parser.answer_fields()


def safe_slug(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return slug[:80] or "assignment"


def save_answers(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def prompt_answer(question_number: int, fields: list[dict]) -> dict:
    print("\nDetected answer fields:")
    if not fields:
        print("  No answer fields detected in the HTML.")
    else:
        for field in fields:
            label = f" - {field['label']}" if field.get("label") else ""
            value = f" value={field['value']!r}" if field.get("value") else ""
            print(f"  {field['name']} ({field['type']}){value}{label}")

    print("\nType your answer locally. Commands: /skip, /quit")
    answer = input(f"Answer for question {question_number + 1}: ").strip()
    return {"answer": answer, "skipped": answer == "/skip"}


def main() -> None:
    load_dotenv(Path(__file__).with_name(".env"))
    assignments = load_assignments()
    assignment = choose_assignment(assignments)

    course_id = assignment["myopenmath_course_id"]
    assessment_id = assignment["myopenmath_assessment_id"]
    session = make_session()
    csrf_token = get_csrf_token(session, course_id, assessment_id)
    try:
        assess_info = load_assess_info(session, course_id, assessment_id)
    except NeedRelaunch:
        print("\nRefreshing MyOpenMath access through Canvas LTI...")
        session = relaunch_assignment_lti(assignment, course_id, assessment_id)
        csrf_token = get_csrf_token(session, course_id, assessment_id)
        assess_info = load_assess_info(session, course_id, assessment_id)

    print(f"\nSelected: {assignment['title']}")
    print(f"MyOpenMath aid: {assessment_id}")
    print(f"Availability: {assess_info.get('available')}")

    practice = bool(assess_info.get("in_practice"))
    questions = assess_info.get("questions")

    if not isinstance(questions, list):
        if assess_info.get("available") == "practice":
            print(
                "\nThis assignment is only available as ungraded practice right now. "
                "MyOpenMath warns that opening practice can affect LatePass eligibility."
            )
            confirm = input("Type START PRACTICE to continue, or press Enter to cancel: ")
            if confirm != "START PRACTICE":
                raise SystemExit("Canceled without starting practice.")
            start_practice(session, course_id, assessment_id, csrf_token)
            practice = True
            assess_info = load_assess_info(session, course_id, assessment_id)
            questions = assess_info.get("questions")
        else:
            raise SystemExit(
                "No active question list is available. Open/start the assignment in "
                "MyOpenMath first; this script will not start a graded attempt."
            )

    if not isinstance(questions, list):
        raise SystemExit("Could not determine the question count after loading the assignment.")

    answers_path = ANSWERS_DIR / f"{safe_slug(assignment['title'])}-{assessment_id}.json"
    answer_log = {
        "title": assignment["title"],
        "canvas_assignment_id": assignment["canvas_assignment_id"],
        "myopenmath_course_id": course_id,
        "myopenmath_assessment_id": assessment_id,
        "answers": [],
    }

    total = len(questions)
    print(f"\nLoaded {total} questions. Answers will be saved to {answers_path}.")

    for question_number in range(total):
        question = load_question(
            session,
            course_id,
            assessment_id,
            csrf_token,
            question_number,
            practice,
        )
        text, fields = parse_question(unescape(question.get("html", "")))

        print("\n" + "=" * 72)
        print(f"Question {question_number + 1} of {total}")
        print("=" * 72)
        print(text)

        answer = prompt_answer(question_number, fields)
        if answer["answer"] == "/quit":
            save_answers(answers_path, answer_log)
            raise SystemExit(f"Stopped. Saved progress to {answers_path}.")

        answer_log["answers"].append(
            {
                "question_number": question_number,
                "display_question_number": question_number + 1,
                "fields": fields,
                **answer,
            }
        )
        save_answers(answers_path, answer_log)

    print(f"\nDone. Saved answers locally to {answers_path}.")
    print("Nothing was submitted to MyOpenMath.")


if __name__ == "__main__":
    main()
