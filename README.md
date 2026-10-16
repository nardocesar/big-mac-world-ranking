<p align="center">
  <img src="assets/readme-banner.svg" alt="Big Mac World Ranking — One iconic burger. A world of opinions." width="1200">
</p>

<h1 align="center">🍔 Big Mac World Ranking</h1>

<p align="center">
  A community tasting tour of Big Macs around the world.<br>
  Real visits. Shared criteria. Every review counts equally.
</p>

<p align="center">
  <a href="#-how-to-contribute">Contribute a review</a> ·
  <a href="#-the-scoring-menu">Scoring criteria</a> ·
  <a href="#-review-index">Review index</a> ·
  <a href=".github/pull_request_template.md">PR template</a>
</p>

---

## 🍟 Fresh out of the kitchen

This project started with a travel habit: visit McDonald's, order a Big Mac, and compare it with previous ones. Now anyone can contribute to an open, collective ranking. The project's creator gets exactly the same voting weight as everyone else.

| Ready to serve | Current status |
| --- | --- |
| 📋 Shared review criteria | Five criteria, scored from 1 to 5 |
| 📍 Restaurant identification | A Google Maps link to the exact location |
| 🤝 Community contributions | One review per pull request, using the [template](.github/pull_request_template.md) |
| 🍔 Review collection | Open for the first contribution — no reviews indexed yet |
| 🏆 Consolidated ranking | Not published yet; aggregation is not automated |

Reviews currently live in the bodies of accepted, merged PRs, with an index in this README. There is no separate review database or website yet.

## 🍔 The order: original Big Mac only

> **The standard local recipe. No extras. No ingredients removed. No special editions.**
>
> This applies to every contribution, including reviews from memory. Differences between standard local recipes are part of the experience.

Each review covers **one Big Mac eaten at one restaurant on one date**. One visit to a single location does not represent an entire country.

Dine-in, takeout, and delivery are all welcome. Label the order type: transport and time before eating can affect the experience and should stay visible in comparisons.

## 📋 The scoring menu

Give each criterion a **whole-number score from 1 to 5**, with a brief explanation of what you observed.

| | Criterion | What to look for |
| --- | --- | --- |
| 👅 | **Flavor and balance** | Do the beef, sauce, cheese, and vegetables work well together? Is there too much or too little of any ingredient? |
| 🥬 | **Texture** | Is the bun soft, the lettuce crisp, and the beef neither dry nor rubbery? |
| 🌡️ | **Temperature** | Did the burger arrive at the temperature you would expect for eating? |
| ✨ | **Perceived freshness** | Do the bun and vegetables seem fresh? Does the burger seem to have sat ready for a while? Describe your perception without assuming kitchen conditions. |
| 🍔 | **Assembly** | Are the ingredients evenly distributed and well proportioned? Is the burger easy to eat? |

### Pick your score

| Score | Meaning | Reference |
| --- | --- | --- |
| **1 / 5** | Very poor | Major problems that seriously hurt the experience. |
| **2 / 5** | Below expectations | Noticeable problems that hurt the experience. |
| **3 / 5** | Good / standard | Meets expectations for a Big Mac. |
| **4 / 5** | Very good | Stands out positively on this criterion. |
| **5 / 5** | Exceptional | A standout experience supported by a concrete explanation. |

**Price, service, and atmosphere stay off the scorecard.** You can describe them separately as context.

## 🧮 From one bite to a world ranking

All five criteria have equal weight:

```text
                Flavor + Texture + Temperature + Freshness + Assembly
Final score  =  ──────────────────────────────────────────────────────
                                          5
```

For example, **4 + 3 + 4 + 3 + 5 = 19 → 3.80 / 5**.

When published, the ranking for a restaurant, city, or country will use the average final score of eligible reviews for that location. Every accepted scored review has equal weight. Calculate using unrounded values, display two decimal places, and treat identical exact averages as ties.

Every published average must show the **number of reviews, number of unique contributors, and date range of visits**. A single visit is an initial sample, not a verdict on a whole country. Reviews from memory do not enter these averages.

## 🤝 How to contribute

### Eat → Review → Open a PR

1. **Try the original.** Order a standard local Big Mac without extras, removed ingredients, or special editions.
2. **Find your restaurant.** Open its specific Google Maps place listing and select **Share → Copy link**. Use the individual restaurant, not a general search or city map.
3. **Add your visit to the [review index](#-review-index).** Fork the repository and edit this README to add one line. You do not need to create a separate data file.
4. **Open a pull request** titled `Review: city, country — YYYY-MM-DD`. Fill out the [PR template](.github/pull_request_template.md) in its description, with one review per PR.
5. **Wait for review.** Maintainers check completeness, consistency with the criteria, and duplicates. We may ask for missing details; agreement with your taste is not required.

### What goes on the receipt?

| Required for a scored review | Optional extras for your story |
| --- | --- |
| Google Maps link to the exact restaurant | Photo |
| Visit date in `YYYY-MM-DD` format | Price and local currency |
| Dine-in, takeout, or delivery | Whether the price is for the burger or a meal |
| Confirmation of the original, unmodified recipe | Approximate time between receiving the order and eating |
| Five scores, each with an explanation | Comments on service and atmosphere |
| Final score and an overall comment | |

The PR author identifies the reviewer, and the Google Maps listing identifies the restaurant and its location. The template does not ask you to repeat your username, country, city, or restaurant address.

Use your own photos or photos you have permission to share, and avoid exposing other people.

## 📍 Review index

**The first stop is yours.** No reviews have been indexed yet.

Add one line using this format, replacing the example values with your visit details:

```text
- City, country — YYYY-MM-DD — @username
```

The PR associated with the index change contains the full review. After the first review is added, remove the empty-state sentence above. Mark memory entries with `(from memory)` so they are distinguishable from scored reviews.

<!-- Add reviews below this line. -->

## 🧾 House rules

- **Your burger, your review.** Review only what you personally ate; do not submit scores on someone else's behalf.
- **One person, one visit, one review.** Do not duplicate reviews or split the same burger into multiple contributions.
- **Come back for seconds.** Repeat visits to the same restaurant are welcome; record each visit's date.
- **Explain the score.** Base it on your observed experience. Disagreement is not a reason to reject a review.
- **Keep it respectful.** Focus comments on the experience.
- **Correct the record.** To fix an accepted review, open a PR referencing the original PR and explain what changed. Update the index if needed. The correction replaces the previous review and does not count as a new visit.

### 🕰️ A Big Mac you remember

Older stories are welcome, even without an exact date or enough detail to assign scores. Select **Review from memory** in the template, share only what you remember, and make uncertainties explicit. The original-recipe rule still applies.

If you cannot identify the exact restaurant, leave the Google Maps link blank and explain the uncertainty. Leave scores blank if you cannot recall enough detail. Do not invent dates or scores to complete the form.

These accounts remain on record but **never count toward ranking averages**.

---

<p align="center"><strong>One iconic burger. A world of opinions.</strong><br>Built by people who always find time for a Big Mac.<br /><sup><sub>This is an independent community project with no affiliation with McDonald's. Big Mac and McDonald's are trademarks of their respective owners.</sub></sup></p>
