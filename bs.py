import argparse
import base64
import json
import os
import re
from html import unescape
from http.cookies import SimpleCookie
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import requests
from dotenv import load_dotenv

LOAD_QUESTION_URL = "https://www.myopenmath.com/assess2/loadquestion.php"
START_ASSESS_URL = "https://www.myopenmath.com/assess2/startassess.php"
COURSE_ID = "324539"
CANVAS_COURSE_ID = "151654"
START_PRACTICE_CONFIRMATION = "I_UNDERSTAND"


class QuestionTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
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

        if tag in {"br", "div", "p", "li", "ul"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self.skip_depth > 0:
            self.skip_depth -= 1
            return

        if tag in {"div", "p", "li", "ul"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_depth == 0:
            self.parts.append(data)

    def text(self) -> str:
        lines = [" ".join(line.split()) for line in "".join(self.parts).splitlines()]
        return "\n".join(line for line in lines if line)


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


def get_cookies() -> dict[str, str]:
    full_cookie_header = os.getenv("MYOPENMATH_COOKIE", "").strip()
    if full_cookie_header:
        return parse_cookie_header(full_cookie_header)

    session_cookie = os.getenv("MYOPENMATH_SESSION", "").strip()
    if not session_cookie:
        return {}

    if "=" in session_cookie:
        cookies = parse_cookie_header(session_cookie)
        if "PHPSESSID" in cookies:
            return {"PHPSESSID": cookies["PHPSESSID"]}

    return {"PHPSESSID": session_cookie}


def set_session_cookies(session: requests.Session, cookie_header: str, domain: str) -> None:
    for key, value in parse_cookie_header(cookie_header).items():
        session.cookies.set(key, value, domain=domain, path="/")


def load_har_entries(path: str) -> list[dict]:
    with Path(path).expanduser().open(encoding="utf-8", errors="replace") as file:
        return json.load(file).get("log", {}).get("entries", [])


def response_text(entry: dict) -> str:
    content = entry.get("response", {}).get("content", {}) or {}
    text = content.get("text", "")
    if content.get("encoding") == "base64":
        return base64.b64decode(text).decode("utf-8", "replace")
    return text


def get_har_context() -> dict[str, str]:
    har_path = os.getenv("MYOPENMATH_HAR_PATH", "").strip()
    if not har_path:
        return {}

    entries = load_har_entries(har_path)
    context = {}

    for entry in reversed(entries):
        request = entry.get("request", {})
        parsed_url = urlparse(request.get("url", ""))
        if parsed_url.netloc != "www.myopenmath.com":
            continue

        headers = {
            header.get("name", "").lower(): header.get("value", "")
            for header in request.get("headers", [])
        }

        if parsed_url.path == "/assess2/" and "csrfp_token" not in context:
            text = response_text(entry)
            csrf_match = re.search(r'CSRFP\.setToken\("([^"]+)"\)', text)
            if csrf_match:
                context["csrfp_token"] = csrf_match.group(1)

            query = parse_qs(parsed_url.query)
            context.setdefault(
                "assessment_id", get_first_query_value(query, "aid", "id") or ""
            )
            context.setdefault("referer", request.get("url", ""))

        if parsed_url.path != "/assess2/loadquestion.php":
            continue

        query = parse_qs(parsed_url.query)
        post_params = {
            item.get("name"): item.get("value", "")
            for item in (request.get("postData") or {}).get("params", [])
            if item.get("name")
        }

        context.update(
            {
                "course_id": get_first_query_value(query, "cid", "courseid") or "",
                "assessment_id": get_first_query_value(query, "aid", "id") or "",
                "referer": headers.get("referer", ""),
                "csrfp_token": headers.get("csrfp-token", ""),
                "question_number": post_params.get("qn", ""),
                "practice": post_params.get("practice", ""),
            }
        )
        return context

    return context


def get_header(headers: list[dict], name: str) -> str:
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def extract_canvas_assignments_from_har(path: str) -> list[dict]:
    entries = load_har_entries(path)
    modules_data = None
    assignment_info = {}

    for entry in entries:
        url = entry.get("request", {}).get("url", "")
        parsed = urlparse(url)
        if (
            parsed.netloc == "coastdistrict.instructure.com"
            and parsed.path == f"/api/v1/courses/{CANVAS_COURSE_ID}/modules"
            and "include[]=items" in unquote(parsed.query)
        ):
            modules_data = json.loads(response_text(entry))
        elif (
            parsed.netloc == "coastdistrict.instructure.com"
            and parsed.path
            == f"/courses/{CANVAS_COURSE_ID}/modules/items/assignment_info"
        ):
            assignment_info = json.loads(response_text(entry))

    if modules_data is None:
        raise SystemExit(
            "Could not find the Canvas modules API response in the HAR. "
            "Record the modules page with Network open, or set CANVAS_COURSE_HAR_PATH "
            "to the HAR that contains /api/v1/courses/.../modules?include[]=items."
        )

    assignments = []
    for module in modules_data:
        for item in module.get("items", []):
            if item.get("type") != "Assignment":
                continue

            module_item_id = item.get("id")
            info = assignment_info.get(str(module_item_id), {})
            assignments.append(
                {
                    "canvas_assignment_id": str(item.get("content_id", "")),
                    "module_item_id": str(module_item_id or ""),
                    "title": item.get("title", ""),
                    "module": module.get("name", ""),
                    "due_date": info.get("due_date") or "",
                    "points_possible": info.get("points_possible"),
                }
            )

    return assignments


def find_canvas_assignment(assignments: list[dict]) -> dict | None:
    selected_id = os.getenv("CANVAS_ASSIGNMENT_ID", "").strip()
    selected_title = os.getenv("CANVAS_ASSIGNMENT_TITLE", "").strip().lower()

    if selected_id:
        for assignment in assignments:
            if assignment["canvas_assignment_id"] == selected_id:
                return assignment

    if selected_title:
        matches = [
            assignment
            for assignment in assignments
            if selected_title in assignment["title"].lower()
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise SystemExit(
                "CANVAS_ASSIGNMENT_TITLE matched multiple assignments. "
                "Use CANVAS_ASSIGNMENT_ID instead."
            )

    return None


def print_canvas_assignments(assignments: list[dict]) -> None:
    for assignment in assignments:
        due = assignment["due_date"] or "no due date"
        points = assignment["points_possible"]
        print(
            f"{assignment['canvas_assignment_id']}\t"
            f"{assignment['module_item_id']}\t"
            f"{assignment['title']}\t"
            f"{due}\t"
            f"{points}"
        )


def parse_forms(html: str) -> list[dict]:
    parser = FormParser()
    parser.feed(html)
    return parser.forms


def find_form(html: str, action_substring: str | None = None) -> dict | None:
    for form in parse_forms(html):
        if action_substring is None or action_substring in form["action"]:
            return form
    return None


def first_url_matching(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text)
    return unescape(match.group(0)) if match else None


def extract_openmath_launch_from_har(path: str) -> dict[str, str]:
    entries = load_har_entries(path)
    launch = {}

    for entry in entries:
        request = entry.get("request", {})
        response = entry.get("response", {})
        url = request.get("url", "")
        parsed = urlparse(url)

        assignment_match = re.search(
            rf"/courses/{CANVAS_COURSE_ID}/assignments/(\d+)", parsed.path
        )
        if assignment_match:
            launch["canvas_assignment_id"] = assignment_match.group(1)
            launch["module_item_id"] = get_first_query_value(
                parse_qs(parsed.query), "module_item_id"
            ) or launch.get("module_item_id", "")

        if parsed.netloc == "coastdistrict.instructure.com":
            target_match = re.search(
                r'name="target_link_uri"[^>]+value="([^"]+)"', response_text(entry)
            )
            if target_match:
                target_link_uri = unquote(target_match.group(1).replace("&amp;", "&"))
                launch["target_link_uri"] = target_link_uri
                place_match = re.search(r"custom_place_aid=(\d+)", target_link_uri)
                if place_match:
                    launch["custom_place_aid"] = place_match.group(1)

        location = get_header(response.get("headers", []), "location")
        parsed_location = urlparse(location)
        if (
            parsed.netloc == "www.myopenmath.com"
            and parsed.path == "/lti/finishlogin.php"
            and parsed_location.netloc == "www.myopenmath.com"
            and parsed_location.path == "/assess2/"
        ):
            query = parse_qs(parsed_location.query)
            launch["myopenmath_course_id"] = get_first_query_value(query, "cid") or ""
            launch["myopenmath_assessment_id"] = (
                get_first_query_value(query, "aid") or ""
            )
            launch["myopenmath_assessment_url"] = location

    return launch


def openmath_launch_from_url(url: str) -> dict[str, str] | None:
    parsed = urlparse(url)
    if parsed.netloc != "www.myopenmath.com" or parsed.path != "/assess2/":
        return None

    query = parse_qs(parsed.query)
    course_id = get_first_query_value(query, "cid")
    assessment_id = get_first_query_value(query, "aid")
    if not course_id or not assessment_id:
        return None

    return {
        "myopenmath_course_id": course_id,
        "myopenmath_assessment_id": assessment_id,
        "myopenmath_assessment_url": url,
    }


def maybe_extract_openmath_launch(response: requests.Response) -> dict[str, str] | None:
    launch = openmath_launch_from_url(response.url)
    if launch:
        return launch

    location = response.headers.get("location", "")
    if location:
        launch = openmath_launch_from_url(location)
        if launch:
            return launch

    for previous in response.history:
        launch = openmath_launch_from_url(previous.headers.get("location", ""))
        if launch:
            return launch

    return None


def submit_or_follow_next_lti_step(
    session: requests.Session,
    response: requests.Response,
) -> requests.Response | None:
    html = response.text

    form = find_form(html)
    if form and form["action"]:
        action = urljoin(response.url, form["action"])
        if form["method"] == "get":
            return session.get(action, params=form["inputs"], timeout=20)
        return session.post(action, data=form["inputs"], timeout=20)

    next_url = first_url_matching(
        html,
        r"https://sso\.canvaslms\.com/api/lti/authorize_redirect[^\"'<>\\\s]+",
    )
    if next_url:
        return session.get(next_url, timeout=20)

    next_url = first_url_matching(
        html,
        r"https://coastdistrict\.instructure\.com/api/lti/authorize[^\"'<>\\\s]+",
    )
    if next_url:
        return session.get(next_url, timeout=20)

    return None


def resolve_openmath_aid_live(selected_assignment: dict) -> dict[str, str]:
    canvas_cookie = os.getenv("CANVAS_COOKIE", "").strip()
    if not canvas_cookie:
        raise SystemExit(
            "Set CANVAS_COOKIE to your coastdistrict.instructure.com Cookie header "
            "to resolve MyOpenMath aids live."
        )

    session = requests.Session()
    set_session_cookies(session, canvas_cookie, "coastdistrict.instructure.com")
    myopenmath_cookie = os.getenv("MYOPENMATH_COOKIE", "").strip()
    if myopenmath_cookie:
        set_session_cookies(session, myopenmath_cookie, "www.myopenmath.com")
    elif os.getenv("MYOPENMATH_SESSION", "").strip():
        session.cookies.set(
            "PHPSESSID",
            os.getenv("MYOPENMATH_SESSION", "").strip(),
            domain="www.myopenmath.com",
            path="/",
        )

    session.headers.update(
        {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149 Safari/537.36"
            ),
        }
    )

    module_item_url = (
        f"https://coastdistrict.instructure.com/courses/{CANVAS_COURSE_ID}"
        f"/modules/items/{selected_assignment['module_item_id']}"
    )
    response = session.get(
        module_item_url,
        headers={"Referer": f"https://coastdistrict.instructure.com/courses/{CANVAS_COURSE_ID}/modules"},
        timeout=20,
    )
    response.raise_for_status()

    form = find_form(response.text, "www.myopenmath.com/lti/login.php")
    if not form:
        raise SystemExit(
            "Could not find the MyOpenMath LTI launch form on the Canvas assignment page. "
            "Check that CANVAS_COOKIE is current and the assignment is an external tool."
        )

    target_link_uri = form["inputs"].get("target_link_uri", "")
    launch = {"target_link_uri": target_link_uri}
    place_match = re.search(r"custom_place_aid=(\d+)", target_link_uri)
    if place_match:
        launch["custom_place_aid"] = place_match.group(1)

    response = session.post(urljoin(response.url, form["action"]), data=form["inputs"], timeout=20)

    for _ in range(12):
        found = maybe_extract_openmath_launch(response)
        if found:
            launch.update(found)
            return launch

        next_response = submit_or_follow_next_lti_step(session, response)
        if next_response is None:
            break
        response = next_response

    raise SystemExit(
        "Could not complete the live LTI flow. Re-recording a click HAR may be easier "
        "if Canvas or MyOpenMath changed the launch page shape."
    )


def resolve_selected_openmath_aid() -> None:
    course_har_path = os.getenv("CANVAS_COURSE_HAR_PATH", "").strip()
    click_har_path = (
        os.getenv("CANVAS_CLICK_HAR_PATH", "").strip()
        or os.getenv("MYOPENMATH_HAR_PATH", "").strip()
    )

    if not course_har_path:
        raise SystemExit("Set CANVAS_COURSE_HAR_PATH to your course/modules HAR.")
    if not click_har_path:
        raise SystemExit("Set CANVAS_CLICK_HAR_PATH to the HAR from clicking the assignment.")

    assignments = extract_canvas_assignments_from_har(course_har_path)
    selected_assignment = find_canvas_assignment(assignments)
    if not selected_assignment:
        print_canvas_assignments(assignments)
        raise SystemExit(
            "Set CANVAS_ASSIGNMENT_ID to one of the IDs above, or set "
            "CANVAS_ASSIGNMENT_TITLE to a unique title substring."
        )

    launch = extract_openmath_launch_from_har(click_har_path)
    if not launch.get("myopenmath_assessment_id"):
        raise SystemExit(
            "The click HAR does not include the completed MyOpenMath LTI redirect. "
            "Click the Canvas assignment while recording until MyOpenMath finishes loading."
        )

    if (
        launch.get("canvas_assignment_id")
        and launch["canvas_assignment_id"] != selected_assignment["canvas_assignment_id"]
    ):
        raise SystemExit(
            "The selected Canvas assignment does not match the click HAR. "
            f"Selected {selected_assignment['canvas_assignment_id']}, but click HAR "
            f"contains {launch['canvas_assignment_id']}."
        )

    print(f"Canvas assignment: {selected_assignment['canvas_assignment_id']}")
    print(f"Title: {selected_assignment['title']}")
    print(f"Canvas module item: {selected_assignment['module_item_id']}")
    print(f"MyOpenMath course id: {launch.get('myopenmath_course_id')}")
    print(f"MyOpenMath assessment id: {launch.get('myopenmath_assessment_id')}")
    print(f"MyOpenMath URL: {launch.get('myopenmath_assessment_url')}")


def resolve_selected_openmath_aid_live() -> None:
    course_har_path = os.getenv("CANVAS_COURSE_HAR_PATH", "").strip()
    if not course_har_path:
        raise SystemExit("Set CANVAS_COURSE_HAR_PATH to your course/modules HAR.")

    assignments = extract_canvas_assignments_from_har(course_har_path)
    selected_assignment = find_canvas_assignment(assignments)
    if not selected_assignment:
        print_canvas_assignments(assignments)
        raise SystemExit(
            "Set CANVAS_ASSIGNMENT_ID to one of the IDs above, or set "
            "CANVAS_ASSIGNMENT_TITLE to a unique title substring."
        )

    launch = resolve_openmath_aid_live(selected_assignment)
    print(f"Canvas assignment: {selected_assignment['canvas_assignment_id']}")
    print(f"Title: {selected_assignment['title']}")
    print(f"Canvas module item: {selected_assignment['module_item_id']}")
    print(f"MyOpenMath custom_place_aid: {launch.get('custom_place_aid', '')}")
    print(f"MyOpenMath course id: {launch.get('myopenmath_course_id')}")
    print(f"MyOpenMath assessment id: {launch.get('myopenmath_assessment_id')}")
    print(f"MyOpenMath URL: {launch.get('myopenmath_assessment_url')}")


def get_first_query_value(query: dict[str, list[str]], *keys: str) -> str | None:
    for key in keys:
        values = query.get(key)
        if values and values[0]:
            return values[0]
    return None


def get_assessment_context(har_context: dict[str, str]) -> tuple[str, str, str]:
    assessment_url = os.getenv("MYOPENMATH_ASSESSMENT_URL", "").strip()
    query = parse_qs(urlparse(assessment_url).query) if assessment_url else {}

    course_id = COURSE_ID
    assessment_id = (
        os.getenv("MYOPENMATH_ASSESSMENT_ID", "").strip()
        or get_first_query_value(query, "aid", "id")
        or har_context.get("assessment_id")
    )

    if not course_id or not assessment_id:
        raise SystemExit(
            "Missing MyOpenMath assessment context. Add either "
            "MYOPENMATH_ASSESSMENT_URL or both MYOPENMATH_COURSE_ID and "
            "MYOPENMATH_ASSESSMENT_ID to .env."
        )

    if assessment_url:
        referer = assessment_url
    elif har_context.get("referer"):
        referer = har_context["referer"]
    else:
        referer = f"https://www.myopenmath.com/assess2/?cid={course_id}&aid={assessment_id}"

    return course_id, assessment_id, referer


def get_headers(referer: str, har_context: dict[str, str]) -> dict[str, str]:
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.myopenmath.com",
        "Referer": referer,
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
        ),
    }

    csrfp_token = (
        os.getenv("MYOPENMATH_CSRFP_TOKEN", "").strip()
        or har_context.get("csrfp_token", "")
    )
    if csrfp_token:
        headers["csrfp-token"] = csrfp_token

    return headers


def get_question_html(data: dict, question_number: str) -> str:
    questions = data.get("questions")
    if isinstance(questions, dict):
        question = questions.get(question_number)
    elif isinstance(questions, list):
        try:
            question = questions[int(question_number)]
        except (IndexError, ValueError):
            question = None
    else:
        question = None

    if not isinstance(question, dict) or "html" not in question:
        raise SystemExit(f"Unexpected response shape: {data}")

    return question["html"]


def question_html_to_text(html: str) -> str:
    parser = QuestionTextParser()
    parser.feed(html)
    return parser.text()


def should_start_practice() -> bool:
    return os.getenv("MYOPENMATH_START_PRACTICE", "").strip() == START_PRACTICE_CONFIRMATION


def start_practice_attempt(
    course_id: str,
    assessment_id: str,
    referer: str,
    har_context: dict[str, str],
) -> None:
    response = requests.post(
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
        cookies=get_cookies(),
        headers=get_headers(referer, har_context),
        timeout=15,
    )
    response.raise_for_status()

    data = response.json()
    if "error" in data:
        raise SystemExit(f"MyOpenMath could not start practice: {data['error']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--list-assignments",
        action="store_true",
        help="List Canvas assignments from CANVAS_COURSE_HAR_PATH.",
    )
    parser.add_argument(
        "--resolve-aid",
        action="store_true",
        help="Resolve a selected Canvas assignment to a MyOpenMath aid from a click HAR.",
    )
    parser.add_argument(
        "--resolve-aid-live",
        action="store_true",
        help="Resolve a selected Canvas assignment to a MyOpenMath aid using CANVAS_COOKIE.",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv(Path(__file__).with_name(".env"))
    args = parse_args()

    if args.list_assignments:
        course_har_path = os.getenv("CANVAS_COURSE_HAR_PATH", "").strip()
        if not course_har_path:
            raise SystemExit("Set CANVAS_COURSE_HAR_PATH to your course/modules HAR.")
        print_canvas_assignments(extract_canvas_assignments_from_har(course_har_path))
        return

    if args.resolve_aid:
        resolve_selected_openmath_aid()
        return

    if args.resolve_aid_live:
        resolve_selected_openmath_aid_live()
        return

    har_context = get_har_context()
    course_id, assessment_id, referer = get_assessment_context(har_context)
    question_number = (
        os.getenv("MYOPENMATH_QUESTION_NUMBER", "").strip()
        or har_context.get("question_number")
        or "0"
    )

    params = {"cid": course_id, "aid": assessment_id}
    payload = {
        "qn": question_number,
        "practice": (
            os.getenv("MYOPENMATH_PRACTICE", "").strip()
            or har_context.get("practice")
            or "false"
        ),
        "regen": "0",
        "jumptoans": "0",
    }

    response = requests.post(
        LOAD_QUESTION_URL,
        params=params,
        data=payload,
        cookies=get_cookies(),
        headers=get_headers(referer, har_context),
        timeout=15,
    )
    response.raise_for_status()

    data = response.json()

    if data.get("error") == "not_ready" and should_start_practice():
        start_practice_attempt(course_id, assessment_id, referer, har_context)
        response = requests.post(
            LOAD_QUESTION_URL,
            params=params,
            data=payload,
            cookies=get_cookies(),
            headers=get_headers(referer, har_context),
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

    if "error" in data:
        extra = ""
        if data["error"] == "not_avail":
            extra = " The graded assessment is not currently available."
        elif data["error"] == "not_ready":
            extra = (
                " The assignment has no active attempt. To start ungraded practice, "
                f"set MYOPENMATH_START_PRACTICE={START_PRACTICE_CONFIRMATION!r}; "
                "the MyOpenMath page says this can block later LatePass use."
            )
        raise SystemExit(
            f"MyOpenMath returned error: {data['error']}.{extra} "
            "Check that your cookie is current and the assessment URL/course ID/"
            "assessment ID and CSRF token match an assessment you can access."
        )

    print(question_html_to_text(get_question_html(data, question_number)))


if __name__ == "__main__":
    main()
