# Form-based reviews and generated rankings

## Goal and approved experience

Allow anyone with a GitHub account to contribute a Big Mac review without cloning the repository, editing Markdown, or opening a pull request manually.

The approved flow is: README link → GitHub Issue Form → automatically created review PR → maintainer review and merge → automatic updates to `CONTRIBUTORS.md` and `RESTAURANTS.md`.

All repository content, forms, generated files, and automated feedback remain in English. Human review remains mandatory; submitting a form never accepts a review automatically.

## Current state

The repository has a README, a local SVG banner, and a PR template. Issues are enabled. There are no review files, review forms, ranking scripts, or workflows. Previous documentation-only PRs must not become reviews or contributor credits.

## Selected approach

Use GitHub Issue Forms for intake and version-controlled Markdown for accepted reviews. Compared with manual review-file PRs, this removes Git knowledge from the contributor experience. Compared with generating rankings directly from issue or PR descriptions, committed review files provide a stable, auditable record of what maintainers actually accepted.

No external website, database, Google API key, personal access token, or AI service is required for the initial implementation.

## Intake form

Replace `.github/pull_request_template.md` with an Issue Form and a prominent README “Submit a review” link. The form explains the original-recipe rule and asks for:

- Contribution type: scored review, review from memory, or correction.
- Original review issue number for corrections.
- Google Maps link to the exact restaurant.
- Visit date and order type: dine-in, takeout, or delivery.
- Five whole-number scores from 1 to 5, with an explanation for each.
- Overall experience.
- Optional price, currency, burger-versus-meal context, wait time, and photo links.
- Confirmations of personal consumption, the standard local recipe without extras or removed ingredients, no special editions, and permission to share any photos.

Keep memory submissions possible without an exact date, identifiable restaurant, or scores. GitHub forms have limited conditional fields: fields that memory submissions may omit must be optional in the UI and validated according to contribution type by the intake script. Invalid submissions receive one actionable, updated feedback comment and do not produce a PR until fixed.

The author comes from the issue creator, not a user-supplied field and not the bot author of the generated PR. Preserve the existing absence of username, country, city, restaurant address, and customization fields. The form must not require contributors to modify the README index.

## Review files

Each original issue maps to `reviews/<issue-number>.md`. The Markdown file includes machine-readable metadata and a readable review body, keeping both in one canonical record.

Metadata includes schema version, original source issue, latest submission issue, original reviewer's GitHub login and numeric account ID, contribution type, restaurant identifier and Google Maps URL, visit date, order type, and individual scores. The review body preserves explanations, overall experience, and optional context. The final score is calculated from the five scores, never trusted from submitted text. Use one parser and validator shared by intake, checks, and ranking generation.

Memory reviews have explicit type and nullable unknown values. They never contribute scores, even if the person remembers some scores.

## Restaurant identity

A restaurant's internal identifier is separate from its display URL. New reviews start with a deterministic identifier derived from a conservatively normalized Google Maps URL. Accept only HTTPS Google Maps hosts and supported paths; do not fetch arbitrary user URLs or expand short links through unrestricted redirects.

Identical normalized links reuse the same identifier. Different links can refer to the same location, so before merge maintainers must check for an existing restaurant and, if necessary, set the new review's identifier and canonical display URL to match that location. This is an internal review step, not another contributor form field. Do not claim that URL normalization automatically resolves restaurant identity.

The restaurant table can identify each location by its stable ID linked to Google Maps. Extracted place names may be displayed when unambiguous; otherwise use a neutral location label. No geographic metadata is invented from coordinates or URL text.

## Intake workflow

React to review-form issues being opened, edited, or reopened, and provide a manual retry option for maintainers. Distinguish review submissions with an explicit form marker and expected fields; ignore unrelated issues and PRs.

Validate the current issue body and create or update a deterministic branch and one PR per submission. A valid edit before merge updates the same file and PR. Repeated runs with unchanged input produce no additional commits or PRs. An invalid edit marks the pending submission as invalid with actionable feedback; it must not leave a stale valid version silently eligible for merge. Validation checks verify that a pending PR still matches the latest valid issue revision.

The generated PR links its source issue, credits the actual reviewer, and changes only the intended review file. The intake workflow validates internally before creating or updating a PR, without relying on a second workflow firing automatically for a bot-created PR. GitHub may require a maintainer to approve additional checks on bot-created PRs.

After acceptance, edits to the original issue do not rewrite the accepted record or open another PR. Direct the contributor to the correction option. If a maintainer closes an unmerged PR, do not recreate it on ordinary edits; explicit maintainer retry can reopen the submission. Closing an unaccepted source issue closes its pending PR.

Automated comments are limited to review submissions and their generated PRs: validation feedback, PR link, correction instructions, and acceptance status. The feature itself explicitly includes these application messages.

## Corrections

A correction form references the original review issue. It updates the existing `reviews/<original-issue-number>.md`, preserving original authorship and review identity, and adds the correction issue as the latest submission reference. Only the original reviewer or a repository maintainer may submit a correction. One pending correction per review is allowed; conflicting corrections require resolution before acceptance.

Maintain a single effective review per original issue. A correction never adds a contributor credit or another visit. A change between memory and scored type adjusts the existing review's eligibility after maintainer approval.

## Generated rankings

### CONTRIBUTORS.md

Recommended initial policy: rank people by total accepted review records, including memory reviews, with separate columns for scored reviews and memory reviews. Corrections and documentation PRs do not count. Credit the original issue creator, never the workflow bot. Equal totals share a rank; stable account identity and login provide deterministic ordering within ties.

### RESTAURANTS.md

Rank restaurants by the exact average final score of accepted scored reviews, highest first. The five criteria and every review have equal weight. Exclude memory reviews. Include position, restaurant link, mean score with two decimal places, review count, distinct reviewer count, first and last visit dates, and links to source review files. Equal exact averages share a position; restaurant ID provides stable ordering within ties. Use exact arithmetic for comparisons rather than rounded display values.

Show an explicit empty state in both files before the first qualifying contribution. Include generation instructions and explain that single-review averages are initial samples.

## Ranking workflow

Run after a human merges changes into the default branch, using a push trigger scoped to `reviews/`, the generator, and its workflow. Also allow manual rebuilds. This observes accepted repository contents and supports merge commits, squash merges, and rebase merges without depending on PR-body parsing.

Read all committed review files and regenerate both rankings deterministically. Validate the entire dataset before writing. Invalid records fail the run without publishing partial rankings. Rebuilding from files makes retries safe and handles corrections and deletions without incremental counter drift.

Commit only the two generated Markdown files, only when they change. Serialize updates and retry against the latest default branch to avoid overwriting a concurrent merge. The bot's ranking-only commit must not retrigger generation. If a merge arrives during a run, the subsequent run rebuilds from the latest accepted dataset.

## Repository setup and trust boundaries

Use the built-in `GITHUB_TOKEN` with job-specific permissions for contents, PRs, and issue feedback. Repository settings must allow Actions to create PRs. Direct ranking commits also require permission under the default branch's rules. Document these requirements; if branch rules block writing, fail clearly rather than changing protection settings or silently leaving stale rankings.

Only trusted scripts from the default branch run in write-enabled jobs. Treat issue bodies and review text as untrusted data: never interpolate them into executable shell commands, execute submitted code, or use form input as file paths or Git refs. Escape Markdown table cells and restrict generated links. Pin third-party actions to commit SHAs during implementation.

The initial setup uses no additional credentials. Workflow-created PR checks may need a maintainer's “Approve workflows to run” action, depending on GitHub behavior and repository policy. Do not request a personal access token just to bypass that step.

## Documentation changes

Update the README contribution walkthrough to describe the form and generated PR, remove instructions to fork the repository or edit the index, link both rankings, and explain memory counts and restaurant grouping. Replace the manual index with links to accepted review files through the generated pages. Remove the obsolete PR template. Keep the existing visual identity and original-recipe requirement.

## Verification and acceptance

Use fixtures for valid scored submissions, memory submissions, invalid dates and scores, missing confirmations, unsafe URLs, injected Markdown, unauthorized corrections, different URL variants, and repeated events. Test parser validation, author attribution, correction replacement, exact averages, ties, contributor counts, empty output, and deterministic rebuilds.

Validate Issue Form and workflow syntax. Exercise intake in dry-run mode without posting or opening test PRs, and generate rankings from sample files outside the real review dataset. Never commit fabricated reviews as community submissions.

After deployment to the default branch, perform the first live form-to-PR test with a real review supplied by a contributor. Confirm merge-to-ranking automation on that accepted review. Until then, report live operation as unverified rather than claiming that a local test proves GitHub execution.

## References

- GitHub token behavior: https://docs.github.com/en/actions/concepts/security/github_token
- Repository Actions permissions: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository

## Scope

The implementation introduces intake, canonical Markdown reviews, and two generated rankings. It does not add a standalone website, automated moderation or acceptance, geocoding, fraud detection, weighted ratings, or per-country rankings.
