# 🍔 Big Mac World Ranking

A community ranking of Big Macs around the world, built from real experiences by the people who ate them.

This project started with a travel habit: visit McDonald's, order a Big Mac, and compare it with previous ones. Here, that curiosity becomes an open record with shared criteria and community contributions. Every review carries the same weight, including reviews by the project's creator.

## What we review

Each review represents **one Big Mac eaten at a specific restaurant on a specific date**. A single experience at one location does not represent an entire country.

**Only the original Big Mac using the standard local recipe is accepted: no extras, no ingredients removed, and no special editions.** Differences between standard local recipes are part of the experience. This requirement applies to all contributions, including reviews from memory.

## Criteria

Give each criterion a whole-number score from **1 to 5**, with a brief explanation of what you observed.

| Criterion | What to look for |
| --- | --- |
| Flavor and balance | Do the beef, sauce, cheese, and vegetables work well together? Is there too much or too little of any ingredient? |
| Texture | Is the bun soft, the lettuce crisp, and the beef neither dry nor rubbery? |
| Temperature | Did the burger arrive at the temperature you would expect for eating? |
| Perceived freshness | Do the bun and vegetables seem fresh? Are there signs that the burger sat ready for a while? Describe your perception without making assumptions about kitchen conditions. |
| Assembly | Are the ingredients evenly distributed and well proportioned? Is the burger easy to eat? |

Use the same scale for every criterion:

| Score | Reference |
| --- | --- |
| 1 | Very poor: major problems that seriously hurt the experience. |
| 2 | Below expectations: noticeable problems that hurt the experience. |
| 3 | Good/standard: meets expectations for a Big Mac. |
| 4 | Very good: stands out positively on this criterion. |
| 5 | Exceptional: a standout experience supported by a concrete explanation. |

**Price, service, and atmosphere do not affect the burger's score.** You can record them separately as context.

## How the ranking works

Each review's final score is the simple average of its five criterion scores:

`Final score = (flavor + texture + temperature + freshness + assembly) / 5`

For example, scores of 4, 3, 4, 3, and 5 produce **3.8/5**.

The community ranking for a restaurant, city, or country uses the average final score of eligible reviews for that location. Every accepted review has the same weight. Calculate using unrounded values and display two decimal places; identical exact averages are tied.

Every published average must include the **number of reviews and unique contributors**, as well as the date range of the visits. An average based on one visit is still an initial sample and should be interpreted accordingly.

Dine-in, takeout, and delivery reviews are welcome when clearly labeled. Keep this information visible when comparing results: transport and time before eating can affect the experience.

## How to contribute

1. Open a pull request using the [contribution template](.github/pull_request_template.md).
2. Use the title `Review: city, country — YYYY-MM-DD`.
3. Submit one review per PR, including all required fields and the five scores with explanations.
4. Wait for review. We may ask for missing information or clarify how the criteria apply before accepting the contribution.

**At this stage, reviews are recorded in the bodies of accepted, merged PRs.** You do not need to create a data file to contribute. Open a PR with a small repository change, such as adding a line to the index below, and fill out the template in the PR body. The consolidated ranking is not generated automatically yet.

### Review index

When contributing, add a line here using the format `- City, country — visit date — @username`. The PR associated with that change contains the full review.

<!-- Add reviews below this line. -->

### Required information

- A Google Maps link to the specific McDonald's restaurant you visited. Open the restaurant's place listing in Google Maps and use **Share → Copy link**; link to the individual location, rather than a general search or city map.
- Visit date in `YYYY-MM-DD` format.
- Order type: dine-in, takeout, or delivery.
- Confirmation that the order was an original Big Mac using the standard local recipe, with no extras, no ingredients removed, and no special editions.
- All five scores and their explanations to qualify for the main ranking.
- An overall comment about the experience.

The PR author identifies the reviewer, and the Google Maps listing identifies the restaurant and its location; these do not need separate fields in the review template.

Photos are optional. Use your own photos or photos you have permission to share, and avoid exposing other people. Price and local currency are also optional; specify whether the price covers the burger alone or a meal.

### Rules for useful comparisons

- Review only what you personally ate. Do not submit scores on someone else's behalf.
- Submit one review per person per visit. Do not submit multiple reviews of the same burger or duplicate existing reviews.
- Repeat visits to the same restaurant are welcome: record each visit's date.
- Base scores on your observed experience and explain them. Disagreement with a review is not a reason to reject it.
- Review checks focus on completeness, consistency with the criteria, and duplicates; agreement with your taste is not required.
- To correct an accepted review, open a PR referencing the original PR and explain what changed. A correction replaces the previous review and does not count as a new visit.
- Keep comments respectful and focused on the experience.

### Reviews from memory

Older stories are welcome, even without an exact date or enough detail to assign scores. Mark the contribution as a **review from memory**, share only what you remember, and make uncertainties explicit. If you cannot identify the exact restaurant, leave the Google Maps link blank and explain this uncertainty instead of guessing.

These accounts remain on record but **do not count toward ranking averages**. Do not invent dates or scores to complete the form.

## Independence

This is an independent community project with no affiliation with McDonald's. Big Mac and McDonald's are trademarks of their respective owners.
