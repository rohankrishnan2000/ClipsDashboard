# Project Memory

## Canvas / MyOpenMath Flow

- Canvas course ID: `151654`
- MyOpenMath course ID: `324539`
- `openmath_aids.csv` stores the mapping between Canvas assignments and MyOpenMath assessments.
- Important CSV fields:
  - `canvas_assignment_id`
  - `module_item_id`
  - `custom_place_aid`
  - `myopenmath_course_id`
  - `myopenmath_assessment_id`
  - `myopenmath_assessment_url`
- `resolve_openmath_aids.py` uses `CANVAS_COOKIE` to list point-bearing Canvas assignments, follow the Canvas LTI launch flow, and resolve MyOpenMath `aid`s.
- `do_assignment_local.py` lets the user choose a resolved assignment, loads questions when an active/practice attempt exists, and saves typed answers locally under `answer_sessions/`.

## Auth / Session Notes

- `CANVAS_COOKIE` authenticates requests to `coastdistrict.instructure.com`.
- `CANVAS_COOKIE` can be either the raw `canvas_session` value or a full Cookie header.
- `MYOPENMATH_SESSION` is the MyOpenMath `PHPSESSID`.
- `MYOPENMATH_COOKIE` is optional and can stay blank if `MYOPENMATH_SESSION` works.
- Canvas and MyOpenMath cookies expire independently.

## Endpoint Behavior

- Canvas module assignment list:
  - `GET https://coastdistrict.instructure.com/api/v1/courses/151654/modules?include[]=items&per_page=100`
- Canvas module item click:
  - `GET https://coastdistrict.instructure.com/courses/151654/modules/items/{module_item_id}`
  - redirects to `/courses/151654/assignments/{canvas_assignment_id}?module_item_id={module_item_id}`
- Canvas assignment page contains the MyOpenMath LTI form targeting:
  - `https://www.myopenmath.com/lti/login.php`
- Final MyOpenMath LTI redirect contains the usable assessment URL:
  - `https://www.myopenmath.com/assess2/?cid=324539&aid={myopenmath_assessment_id}`

## MyOpenMath Question Loading

- Calling `loadquestion.php` needs:
  - `cid`
  - `aid`
  - MyOpenMath session cookie
  - CSRF token from the assessment page
  - an active graded or practice attempt
- Canvas/LTI launch unlocks MyOpenMath access for a given `aid`.
- Starting an assessment/practice attempt is a separate step.
- `need_relaunch` or `no_access` means relaunch through Canvas/LTI.
- `not_ready` or missing question list means there is no active attempt.
- Scripts should not automatically start graded attempts.
- Scripts should ask explicitly before starting ungraded practice because MyOpenMath warns that practice can affect LatePass eligibility.

## Current Known Results

- `resolve_openmath_aids.py` resolved `54` MyOpenMath aids from `57` point-bearing Canvas assignments.
- Non-resolved rows included reflection journals with `no_lti_form` and one `lti_incomplete`.
- Example mapping:
  - Canvas assignment `3304359`
  - Module item `10550951`
  - Title `Exercises 2.2: Slope Fields`
  - `custom_place_aid=19436288`
  - MyOpenMath `aid=22494216`
