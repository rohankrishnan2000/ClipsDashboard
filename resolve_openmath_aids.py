import csv
import os
import re
from html import unescape
from html.parser import HTMLParser
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import requests
from dotenv import load_dotenv

CANVAS_HOST = "coastdistrict.instructure.com"
CANVAS_COURSE_ID = "151654"
MYOPENMATH_HOST = "www.myopenmath.com"
OUTPUT_PATH = Path("openmath_aids.csv")
REQUEST_TIMEOUT = 15


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
    if "=" not in cookie_header:
        session.cookies.set("canvas_session", cookie_header, domain=domain, path="/")
        return

    for key, value in parse_cookie_header(cookie_header).items():
        session.cookies.set(key, value, domain=domain, path="/")


def get_first_query_value(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key)
    return values[0] if values else ""


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


def make_session() -> requests.Session:
    canvas_cookie = os.getenv("CANVAS_COOKIE", "").strip()
    if not canvas_cookie:
        raise SystemExit("Set CANVAS_COOKIE in .env to your Canvas Cookie header.")

    session = requests.Session()
    set_session_cookies(session, canvas_cookie, CANVAS_HOST)

    myopenmath_cookie = os.getenv("MYOPENMATH_COOKIE", "").strip()
    myopenmath_session = os.getenv("MYOPENMATH_SESSION", "").strip()
    if myopenmath_cookie:
        set_session_cookies(session, myopenmath_cookie, MYOPENMATH_HOST)
    elif myopenmath_session:
        session.cookies.set(
            "PHPSESSID",
            myopenmath_session,
            domain=MYOPENMATH_HOST,
            path="/",
        )

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


def get_json_paginated(session: requests.Session, url: str) -> list[dict]:
    rows: list[dict] = []
    next_url = url

    while next_url:
        response = session.get(next_url, timeout=REQUEST_TIMEOUT)
        if response.status_code == 401:
            raise SystemExit(
                "Canvas returned 401 Unauthorized. Refresh CANVAS_COOKIE in .env. "
                "You can paste either the raw canvas_session value or the full Cookie "
                "header from a coastdistrict.instructure.com request."
            )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list):
            rows.extend(payload)
        else:
            raise SystemExit(f"Expected list JSON from Canvas, got: {type(payload).__name__}")

        next_url = ""
        links = requests.utils.parse_header_links(response.headers.get("Link", ""))
        for link in links:
            if link.get("rel") == "next" and link.get("url"):
                next_url = link["url"]
                break

    return rows


def load_canvas_assignments(session: requests.Session) -> list[dict]:
    modules_url = (
        f"https://{CANVAS_HOST}/api/v1/courses/{CANVAS_COURSE_ID}"
        "/modules?include[]=items&per_page=100"
    )
    info_url = f"https://{CANVAS_HOST}/courses/{CANVAS_COURSE_ID}/modules/items/assignment_info"

    modules = get_json_paginated(session, modules_url)
    info_response = session.get(info_url, timeout=REQUEST_TIMEOUT)
    info_response.raise_for_status()
    assignment_info = info_response.json()

    assignments = []
    for module in modules:
        for item in module.get("items", []):
            if item.get("type") != "Assignment":
                continue

            module_item_id = str(item.get("id", ""))
            info = assignment_info.get(module_item_id, {})
            points = info.get("points_possible")
            if points is None or float(points) <= 0:
                continue

            assignments.append(
                {
                    "canvas_assignment_id": str(item.get("content_id", "")),
                    "module_item_id": module_item_id,
                    "title": item.get("title", ""),
                    "module": module.get("name", ""),
                    "due_date": info.get("due_date") or "",
                    "points_possible": points,
                }
            )

    return assignments


def openmath_launch_from_url(url: str) -> dict[str, str] | None:
    parsed = urlparse(url)
    if parsed.netloc != MYOPENMATH_HOST or parsed.path != "/assess2/":
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


def submit_or_follow_next_step(
    session: requests.Session,
    response: requests.Response,
) -> requests.Response | None:
    form = find_form(response.text)
    if form and form["action"]:
        action = urljoin(response.url, form["action"])
        if form["method"] == "get":
            return session.get(action, params=form["inputs"], timeout=REQUEST_TIMEOUT)
        return session.post(action, data=form["inputs"], timeout=REQUEST_TIMEOUT)

    next_url = find_next_lti_url(response.text)
    if next_url:
        return session.get(next_url, timeout=REQUEST_TIMEOUT)

    retry_url = find_js_retry_url(response.url, response.text)
    if retry_url:
        return session.get(retry_url, timeout=REQUEST_TIMEOUT)

    return None


def resolve_assignment_aid(session: requests.Session, assignment: dict) -> dict:
    module_item_url = (
        f"https://{CANVAS_HOST}/courses/{CANVAS_COURSE_ID}"
        f"/modules/items/{assignment['module_item_id']}"
    )
    response = session.get(
        module_item_url,
        headers={"Referer": f"https://{CANVAS_HOST}/courses/{CANVAS_COURSE_ID}/modules"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    form = find_form(response.text, f"{MYOPENMATH_HOST}/lti/login.php")
    if not form:
        return {**assignment, "status": "no_lti_form"}

    target_link_uri = form["inputs"].get("target_link_uri", "")
    custom_place_aid = ""
    place_match = re.search(r"custom_place_aid=(\d+)", unquote(target_link_uri))
    if place_match:
        custom_place_aid = place_match.group(1)

    response = session.post(
        urljoin(response.url, form["action"]),
        data=form["inputs"],
        timeout=REQUEST_TIMEOUT,
    )

    for _ in range(12):
        launch = maybe_extract_openmath_launch(response)
        if launch:
            return {
                **assignment,
                **launch,
                "custom_place_aid": custom_place_aid,
                "status": "ok",
            }

        next_response = submit_or_follow_next_step(session, response)
        if next_response is None:
            break
        response = next_response

    return {
        **assignment,
        "custom_place_aid": custom_place_aid,
        "status": "lti_incomplete",
    }


def write_results(rows: list[dict]) -> None:
    fieldnames = [
        "status",
        "canvas_assignment_id",
        "module_item_id",
        "title",
        "module",
        "due_date",
        "points_possible",
        "custom_place_aid",
        "myopenmath_course_id",
        "myopenmath_assessment_id",
        "myopenmath_assessment_url",
    ]
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def main() -> None:
    load_dotenv(Path(__file__).with_name(".env"))
    session = make_session()
    assignments = load_canvas_assignments(session)
    print(f"Found {len(assignments)} point-bearing Canvas assignments.", flush=True)

    rows = []
    for index, assignment in enumerate(assignments, start=1):
        print(
            f"[{index}/{len(assignments)}] {assignment['canvas_assignment_id']} "
            f"{assignment['title']}",
            flush=True,
        )
        try:
            row = resolve_assignment_aid(session, assignment)
        except requests.RequestException as exc:
            row = {**assignment, "status": f"request_error: {exc.__class__.__name__}"}
        rows.append(row)
        write_results(rows)
        print(
            f"  -> {row.get('status')} {row.get('myopenmath_assessment_id', '')}",
            flush=True,
        )

    print(f"Wrote {OUTPUT_PATH.resolve()}", flush=True)


if __name__ == "__main__":
    main()
