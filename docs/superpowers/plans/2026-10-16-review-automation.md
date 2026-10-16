# Review Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn GitHub form submissions into reviewed Markdown records and automatically maintain contributor and restaurant rankings after merge.

**Architecture:** GitHub Issue Forms feed a trusted intake script that opens or updates a review-only PR. Accepted `reviews/*.md` records are the sole ranking source. A separate default-branch workflow rebuilds and commits deterministic ranking pages.

**Tech Stack:** Python 3.12+, standard-library `unittest`, JSON-compatible YAML front matter, GitHub REST API, GitHub Actions, GitHub Issue Forms. Production scripts have no third-party Python dependencies.

**Spec:** `docs/superpowers/specs/2026-10-16-review-automation-design.md`

## Global Constraints

- All repository content, forms, generated files, and automated feedback remain in English.
- Human review remains mandatory; submitting a form never accepts a review automatically.
- No external website, database, Google API key, personal access token, or AI service is required for the initial implementation.
- Every accepted scored review has equal weight. All five criteria have equal weight.
- Memory reviews never contribute scores. Corrections never add a visit or contributor credit.
- The original Big Mac uses the standard local recipe, without extras, removed ingredients, or special editions.
- Only trusted scripts from the default branch run in write-enabled jobs.
- No fabricated reviews are committed as community submissions.

## Review Focus

1. An invalid issue edit after a valid submission must block acceptance of stale review content (Task 3).
2. Concurrent merges and multiple correction submissions must not lose accepted records or double-count a visit (Tasks 2–4).
3. Google Maps short links and full URLs may identify the same restaurant; grouping requires explicit maintainer reconciliation, never guessed equivalence (Tasks 1 and 5).
4. User text resembling form headings, front matter, shell commands, or Markdown links remains inert, and ambiguous fields fail clearly (Tasks 1 and 3).
5. Renamed accounts retain identity by numeric account ID; the automation bot never receives contribution credit (Tasks 1–3).

## File map

| File | Responsibility |
| --- | --- |
| `scripts/reviews/model.py` | Review schema, shared validation, canonical URL and record serialization |
| `scripts/reviews/forms.py` | Issue-body parsing and submission validation |
| `scripts/reviews/rankings.py` | Dataset loading and deterministic Markdown generation |
| `scripts/reviews/github.py` | Small REST client and paginated API access |
| `scripts/reviews/intake.py` | Issue lifecycle, correction authorization, PR orchestration, dry-run CLI |
| `scripts/reviews/publish.py` | Rebuild and publish generated files with conflict retry |
| `scripts/reviews/check.py` | Read-only PR/dataset validation CLI |
| `.github/ISSUE_TEMPLATE/review.yml` | Contributor-facing review form |
| `.github/ISSUE_TEMPLATE/config.yml` | Form chooser guidance without preventing ordinary project issues |
| `.github/workflows/review-intake.yml` | Intake issue events and manual retry |
| `.github/workflows/review-check.yml` | Read-only review validation and tests |
| `.github/workflows/rankings.yml` | Default-branch ranking rebuild and publication |
| `tests/test_model.py`, `tests/test_forms.py` | Schema, URL, form, and untrusted-input tests |
| `tests/test_rankings.py` | Exact ranking math and stable output tests |
| `tests/test_intake.py`, `tests/test_publish.py` | Mocked lifecycle/API and concurrency tests |
| `tests/fixtures/` | Synthetic inputs used only by tests |
| `reviews/.gitkeep` | Empty accepted-review directory |
| `CONTRIBUTORS.md`, `RESTAURANTS.md` | Generated public pages |
| `README.md`, `docs/automation.md` | Contributor walkthrough and maintainer setup/runbook |

Use `scripts/__init__.py` and `scripts/reviews/__init__.py` for package imports. Commands run as `python -m scripts.reviews.<module>` from the repository root.

## Task 1: Canonical review records and form contract

**Interfaces:** `Review` is a typed dataclass; `parse_submission(body: str, author: dict, issue_number: int, existing: Review | None) -> Review`; `load_review(text: str) -> Review`; `dump_review(review: Review) -> str`; `normalize_maps_url(url: str) -> str`; validation failures raise `ValidationError` with actionable field messages.

- [ ] Write failing `test_model.py` and `test_forms.py` cases for scored and memory reviews, no exact date in memory, missing confirmations, duplicate required headings, future/invalid dates, fractional/out-of-range scores, unsafe URLs, arbitrary front matter in user text, and account identity from API metadata.
- [ ] Run `python -m unittest tests.test_model tests.test_forms -v`; confirm the missing-module failure before implementation.
- [ ] Implement the model with schema version 1 and JSON inside `---` delimiters (JSON is valid YAML). Metadata owns identity, issue provenance, type, restaurant ID/link, date, order type, and scores; body owns explanations and optional context. Validate file identity against its numeric filename during dataset loading. Compute final scores from criteria.
- [ ] Implement conservative HTTPS URL normalization, explicit accepted Google Maps hosts/paths, no network URL expansion, and full SHA-256 URL-derived restaurant IDs. Unknown memory locations have null IDs/URLs; scored reviews require both. Support a maintainer-edited ID/canonical URL without changing other issue-derived content.
- [ ] Create `review.yml` with a distinctive visible form-version marker, stable field headings, five score dropdowns, five explanations, contribution/correction fields, order type, experience, optional context, and confirmations. Include an explicit scored/memory field for corrections. Conditional requirements live in the parser. Contributor text cannot override author identity or inject extra fields. Reject ambiguous duplicate headings rather than silently taking one value.
- [ ] Add fixture round-trip and form/parser agreement assertions; run the same tests and confirm all pass.
- [ ] Commit as `feat: add review form and canonical Markdown records`.

## Task 2: Deterministic ranking pages

**Interfaces:** `load_dataset(root: Path) -> list[Review]`; `render_contributors(reviews: list[Review]) -> str`; `render_restaurants(reviews: list[Review]) -> str`; CLI `python -m scripts.reviews.rankings --root PATH [--check]` validates all records before updating either output.

- [ ] Write failing `test_rankings.py` cases: empty state; author versus bot; numeric account identity across login changes; exact score ties; distinct averages displaying the same rounded number; memory counts; correction replacement; deleted records; source links; escaped table text; and repeat builds yielding identical bytes.
- [ ] Run `python -m unittest tests.test_rankings -v` and confirm failure before implementation.
- [ ] Implement exact `fractions.Fraction` comparisons, competition ranks (`1, 1, 3`), two-decimal display, stable numeric-account/restaurant-ID tie ordering, separate memory/scored contribution counts, distinct reviewers, and visit ranges. For renamed accounts choose the login from the greatest latest-submission issue number, with a deterministic fallback. Require records sharing a restaurant ID to agree on canonical URL; report mismatches for maintainer reconciliation.
- [ ] Generate both complete outputs in memory before writing; fail without modifying either page if any record is invalid. Generated pages include links to review files and rebuild instructions. No timestamps or unstable iteration order.
- [ ] Add conflicting identity/duplicate source issue tests. Run `python -m unittest tests.test_model tests.test_forms tests.test_rankings -v` and confirm pass; generate empty real pages and sample rankings only in a temporary directory.
- [ ] Commit as `feat: generate contributor and restaurant rankings`.

## Task 3: Issue-to-PR lifecycle

**Interfaces:** `GitHubClient` provides JSON REST requests, pagination, and API errors; `handle_issue(client: GitHubClient, repo: str, issue_number: int, retry: bool = False, dry_run: bool = False) -> dict` returns a structured outcome. CLI: `python -m scripts.reviews.intake --issue NUMBER [--retry] [--dry-run]`, with repository/token from environment. Dry run performs reads only and outputs intended mutations.

- [ ] Write failing `test_intake.py` with a fake API: opened valid/invalid forms; edit updates one PR; repeat event no-op; invalid edit sets failing status; late edits after merge do not mutate accepted records; unrelated issues ignored; closed issue closes pending PR; rejected PR stays closed unless explicit retry; unauthorized correction rejected; parallel corrections detected; bot author never credited.
- [ ] Run `python -m unittest tests.test_intake -v`; confirm failure before implementation.
- [ ] Implement API-based branch/file updates on `codex/review-<submission-number>` from the default branch, never from issue-derived refs. Read the current issue on each run; use numeric issue IDs for paths. Maintain a single marked feedback comment and a PR linking the issue with `Closes #N`. Commit only the intended review record and preserve reviewed restaurant-ID reconciliation on later edits.
- [ ] Store a digest of relevant current issue data in generated metadata, and set a named commit status for latest-submission validity directly from intake. Re-read issue data before final success. Invalid/closed submissions fail that status; document it as a required branch check. Read-only PR validation checks trusted serialization against current issue data, allowing only deliberate restaurant reconciliation and rendered context.
- [ ] Authorize corrections by original numeric author ID or repository write/maintain/admin permission. Resolve original provenance from the accepted record. Keep original reviewer and filename, replace content, record the correction issue. Detect existing pending corrections before branch creation; serialize intake events repository-wide to close the creation race.
- [ ] Add mocked race/retry, partial API failure, pagination, and form-heading injection cases; run `python -m unittest tests.test_intake -v` to pass. Demonstrate dry-run with mocked API fixtures and assert no mutation endpoints were called.
- [ ] Commit as `feat: create and maintain review PRs from issue submissions`.

## Task 4: Workflows and publication

**Interfaces:** `publish_rankings(client: GitHubClient, repo: str, max_attempts: int = 3) -> dict`; CLI `python -m scripts.reviews.publish`; `python -m scripts.reviews.check --pr NUMBER` validates only the intended review-file changes against issue provenance using trusted code. A dataset-only check mode validates local fixture data without API calls.

- [ ] Write failing `test_publish.py`: no changes causes no commit; both pages published in one commit; default branch changes mid-run triggers fresh dataset reload; validation failure causes zero writes; protected-branch failure is explicit; retries are bounded and non-force updates never overwrite concurrent commits.
- [ ] Run `python -m unittest tests.test_publish -v` and confirm failure before implementation.
- [ ] Implement publish through GitHub Git tree/commit/ref APIs: snapshot current default-branch SHA, load its accepted records, generate both pages, create a commit with that parent, and update the ref without force. On conflict, retry against the latest snapshot. Never publish arbitrary modified working-directory files.
- [ ] Add `review-intake.yml` for `issues` opened/edited/reopened/closed plus manual numeric retry; repository-wide concurrency, `cancel-in-progress: false`; contents/PRs/issues/statuses write only for the intake job. Check out trusted default-branch code. Validate manual retry permissions. Keep event data in JSON/environment, never inline shell interpolation.
- [ ] Add `review-check.yml`: read-only `pull_request` checks and tests; use default-branch validation code for submissions and read changed record contents as data, never execute PR code in a privileged context. General automation-code tests may run as a separate read-only job. Do not depend on bot-created PR events for intake validation.
- [ ] Add `rankings.yml` for default-branch pushes to review files, model/ranking/publish scripts, or the workflow, plus manual dispatch. Default branch is currently `main`; guard jobs against nondefault dispatches. Serialize publication, allow bounded non-force retry, and exclude ranking-only output commits to prevent loops. After human merges of generated review PRs, close/update source feedback idempotently from accepted record provenance.
- [ ] Resolve action commit SHAs from official action repositories, pin them, and validate workflow/form YAML plus intended triggers/permissions. Use an available reputable YAML validator as a development-only dependency if necessary; do not add runtime dependencies to production scripts.
- [ ] Run `python -m unittest discover -s tests -v` to pass and validate workflow syntax. Commit as `feat: automate review intake checks and ranking publication`.

## Task 5: Contribution experience and delivery

- [ ] Remove `.github/pull_request_template.md`; update README CTA and walkthrough to the Issue Form URL, link both generated pages, remove manual index/fork instructions, and retain visual identity and eligibility rules.
- [ ] Write `docs/automation.md`: required Actions PR-creation permission, branch rules permitting ranking commits, named validity check, possible bot-workflow approval, manual retry/rebuild commands, corrections, closed submissions, and exact restaurant reconciliation using stable IDs and canonical URLs. Do not automatically weaken repository protection or add credentials.
- [ ] Test the documented cases of two URLs for one location and a maintainer-reconciled restaurant ID surviving an issue edit. Assert ordinary contributors never need to supply an internal ID or manually create a PR.
- [ ] Run full tests once after final changes; validate YAML, all local Markdown/asset links and Issue Form field coverage; verify empty rankings regenerate without a diff; run `git diff --check`. Review the full diff for arbitrary input reaching shell, wrong attribution, or write-enabled execution of submitted code.
- [ ] Commit as `docs: explain form contributions and automation setup`; push the implementation branch and open an English PR describing behavior, required setup, test evidence, and live verification limits.
- [ ] Do not create fake public issues, messages, or review PRs as tests. After merge, a real contributor submission is the end-to-end verification. Report local tests separately from the still-unverified live GitHub flow.

## Self-review outcome

Every spec section maps to a task: records/form/identity (1), rankings (2), lifecycle/corrections (3), triggers/concurrency/trust (4), contributor experience/setup/live verification (5). All five review-focus risks have assigned tests. Named interfaces and CLIs are consistent across tasks; no extra credential or service is introduced. This plan is one sequential feature because intake and publication share the accepted-review schema.
