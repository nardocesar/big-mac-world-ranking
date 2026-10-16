# Review automation: maintainer guide

Contributors use the **Submit a review** Issue Form (`review.yml`); accepted reviews are fixed through the separate **Correct a review** form (`correction.yml`). GitHub Issue Forms have no conditional fields, so the two forms keep each one free of irrelevant inputs. They never need to clone, fork, edit Markdown, or create a PR. The bot opens a review-only PR; a maintainer decides whether to merge. Accepted `reviews/<original-issue-number>.md` files are the source for both public rankings.

## Activate after merging this feature

1. Keep Issues and GitHub Actions enabled.
2. In **Settings → Actions → General → Workflow permissions**, enable **Allow GitHub Actions to create and approve pull requests**. The workflows only create PRs; they do not approve or merge them. Explicit per-job permissions are declared in the workflows, so the default token permission can remain read-only.
3. Check default-branch rules. The ranking job needs to commit `CONTRIBUTORS.md` and `RESTAURANTS.md` directly using `GITHUB_TOKEN`. If repository rules reject that commit, publication fails visibly. The job publishes the named validity status for its own generated-only commit before updating the branch. An additional rule requiring every change to arrive via PR, extra required checks, signed commits, or restricted pushes still needs a compatible repository policy; these scripts do not change or bypass branch protections or add credentials.
4. Require the named **`review/latest-submission`** status on PRs targeting `main`. Review validation runs for all PRs: ordinary code/documentation PRs receive a successful “not applicable” status when they do not change review records. Generated review PRs must match the latest valid form and the complete accepted dataset. Maintenance PRs that change `reviews/` without coming from the form (for example, schema migrations) pass only when opened from a branch of this repository by someone with write access; fork PRs and non-maintainers fail. The trusted validator cannot parse records in a newer schema version, so dataset validity for these PRs comes from the read-only **Tests** workflow, which runs the PR's own code: check it is green before merging. No bypass is needed for these migrations. This avoids pretending that a destination-branch rule can selectively protect only `codex/review-*` source branches. Do not merge a generated review PR without this successful current status.
5. If GitHub asks **Approve workflows to run** on a bot-created PR, a maintainer must approve those runs. Intake validates and sets its own status without depending on another bot-triggered workflow.
6. After deployment, use a real Big Mac review for the first live test. Confirm form feedback, one generated Markdown file, human approval, merge, and the subsequent ranking commit. Local tests are not proof that repository permissions are configured.

The repository was observed with PR creation by Actions disabled when this feature was prepared. No repository settings were changed by implementation.

## What each workflow does

| Workflow | Trigger | Writes |
| --- | --- | --- |
| Review intake | Review issues opened, edited, reopened, or closed; manual retry | A review branch/file, its PR, one feedback comment, and the named validity status |
| Review validation | Any PR opened, synchronized, reopened, or edited | Only its validity status; review code and files are read as data |
| Tests | PRs and pushes to `main` | No API writes |
| Update rankings | Pushes to `main` affecting reviews or generator code; manual rebuild | Both ranking pages in one commit, its validity status, and accepted-submission feedback |

Intake status writes and PR validation share a concurrency lock per original review. The current issue is checked again before a validator publishes success, so an older check cannot overwrite a newer processed failure. GitHub concurrency keeps at most one pending run per group; if several different corrections are submitted together, a superseded pending run may need a manual retry. Unrelated reviews have different locks.

Write-enabled workflows check out trusted default-branch scripts. They never run code from a submitted PR. User text is passed as JSON data; Google Maps URLs are not fetched. Workflow actions are pinned to official commit SHAs. A separate read-only job tests proposed code changes.

Ranking-only commits do not trigger ranking publication again. Events from `GITHUB_TOKEN` may also suppress downstream workflow runs; the design does not depend on those events. A human merge produces the default-branch push used for publication. The default branch is currently `main`; if renamed, update the explicit push branch filters in `rankings.yml` and `tests.yml`.

## Reviewing a generated PR

- Confirm that it changes exactly one numeric file in `reviews/` and credits the issue creator, not the bot.
- Check the original-recipe confirmation, date, Maps listing, and scores. All five scores must be whole numbers from 1 to 5. The final score is calculated, not supplied by the contributor.
- Check duplicates: one reviewer, one visit, one record. Different people may independently review the same visit/location, and repeat visits are allowed.
- Compare the location against existing records. Reconcile alternate Maps links before merging, as explained below.
- Check that the latest source issue remains valid and open and that `review/latest-submission` is successful for the current PR commit. Do not merge around a failing/missing status.
- Merge to accept. The PR closes its source issue, then the default-branch job rebuilds both rankings. A rejected, closed PR is not automatically recreated on an ordinary edit.

## Restaurant identity and alternate Maps links

The form asks only for a Maps link. A new record starts with a full SHA-256 `restaurant_id` derived from its normalized link. Identical normalized links group together; short links and full URLs are **not** assumed to be equivalent. Accepted links use HTTPS with `maps.app.goo.gl`, `goo.gl/maps`, or a supported specific-place URL on `google.com`, `www.google.com`, or `maps.google.com`. Use the restaurant's **Share → Copy link**, not a general Maps search.

If two submissions describe the same restaurant with different links, a maintainer must reconcile the pending review:

1. Copy `restaurant_id` and `maps_url` from an accepted record for that location.
2. In the pending file's JSON-compatible front matter, replace **only** those two values. Keep `input_maps_url` as the contributor submitted it. This makes it possible to preserve reconciliation on future edits without overriding a contributor's deliberate location change.
3. Re-render the readable body from the metadata, then commit the file to the review branch. With Python 3.12+ in a local checkout:

   ```sh
   python -m scripts.reviews.model --render reviews/123.md
   ```

4. Wait for review validation. It permits these two internal grouping changes while rejecting altered scores, authorship, or narrative not matching the latest form.

Records with the same restaurant ID must use the same canonical Maps URL. The restaurant name shown in `RESTAURANTS.md` comes from the submission issue title (without the `[Review]` prefix), using the most recent submission for that location. To fix a name before merge, edit the issue title: intake updates the pending PR. If the title still contains the `[street address]` placeholder or is empty, the table falls back to the neutral label `Location <ID prefix>`. The system does not look up or invent addresses.

If intake edits the same location later, it preserves the maintainer's grouping. If the contributor changes the submitted location link, intake derives a new ID and the maintainer checks grouping again.

## Editing, corrections, and retrying

Before acceptance, contributors can edit their issue. Valid edits update the same PR; repeated events with identical content do not create extra commits or PRs. Keep form headings unchanged. Markdown headings starting with `###` inside free text are ambiguous and should be removed if validation reports them.

Invalid edits set the current review status to failure and update the same feedback comment. A maintainer must wait for the corrected form to pass before merging. Review status checks are not a substitute for human judgment about whether a restaurant or experience is genuine.

After acceptance, issue edits do not modify the record. The separate **Correct a review** form (`correction.yml`) references the original review issue and contains the complete replacement review. Only the original reviewer (by stable numeric account ID) or a maintainer with write access may submit one. The correction keeps original authorship and filename. It does not count as another review or contribution.

Only one correction for an original review may be pending at a time. Intake uses a stable branch per original review plus non-force ref updates; conflicting submissions fail with instructions rather than overwrite one another. To replace a rejected correction with a different submission, first delete the abandoned review branch using GitHub's normal branch controls; the next correction can reserve it afresh. Do not delete a branch with an open PR or pending intake run. Reusing the existing submission via manual retry is simpler.

Closing an unaccepted issue closes its pending PR. To retry a rejected or interrupted submission, reopen the issue if necessary, then run **Actions → Review intake → Run workflow** on the default branch and enter its issue number. Manual retry requires repository write access. API failures may leave a prepared branch without a PR; a retry resumes it without adding another review.

Advanced local dry run (read-only, token stays in the environment):

```sh
export GITHUB_REPOSITORY=nardocesar/big-mac-world-ranking
# Provide GH_TOKEN through your usual credential environment; do not paste it here.
python -m scripts.reviews.intake --issue 123 --dry-run
```

Dry run prints the intended record and outcome without comments, branches, statuses, commits, or PR mutations.

## Rebuilding rankings

Run **Actions → Update rankings → Run workflow** on the default branch after resolving a failed publication. The job reads a fresh accepted-data snapshot, validates every record, and updates both pages in one commit only if output changed. A concurrent merge causes a fresh rebuild and non-force retry, up to three attempts. Persistent conflicts, invalid data, or branch protection failures stop publication with an error.

For a local preview:

```sh
python -m unittest discover -s tests -v
python -m scripts.reviews.check
python -m scripts.reviews.rankings
python -m scripts.reviews.rankings --check
```

Contributors are ranked by accepted review count. Restaurants use equal criterion/review weights, exact averages, and two-decimal display. Equal totals or exact averages share a position (`1, 1, 3`). Corrections and deleted records are handled by rebuilding from the current files.

Structured metadata is authoritative; the readable body must match the renderer. To change a record manually, use a reviewed correction rather than editing generated ranking tables. Schema migrations go through a maintainer PR that re-renders affected records; never edit generated ranking tables. Tests and fixtures contain synthetic reviews outside `reviews/`; do not submit them as public contributions.

## GitHub references

- [Built-in token behavior and workflow triggering](https://docs.github.com/en/actions/concepts/security/github_token)
- [Repository Actions permissions](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)
