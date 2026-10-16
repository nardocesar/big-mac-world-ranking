import unittest
from scripts.reviews.forms import parse_submission
from scripts.reviews.model import ValidationError
from tests.support import AUTHOR, NO_SCORES, TITLE, body

class FormTests(unittest.TestCase):
    def test_scored_review_uses_real_author_and_computes_score(self):
        review = parse_submission(body(), AUTHOR, 123, None)
        self.assertEqual((review.author_id, review.author_login, review.source_issue), (42, 'traveler', 123))
        self.assertEqual(str(review.final_score), '19/5')

    def test_memory_allows_unknown_place_date_and_scores(self):
        review = parse_submission(body(**{'Contribution type': 'Review from memory', 'Google Maps link': '_No response_', 'Visit date': 'Around 2010', **NO_SCORES}), AUTHOR, 124, None)
        self.assertEqual(review.kind, 'memory')
        self.assertIsNone(review.visit_date)
        self.assertIsNone(review.restaurant_id)
        self.assertIsNone(review.final_score)
        self.assertIn('Around 2010', review.date_note)

    def test_invalid_scored_values_fail_with_field_feedback(self):
        for key, value in [('Visit date', '2035-01-01'), ('Visit date', '2025-02-30'), ('Texture score', '2.5'), ('Texture score', '6'), ('Google Maps link', 'https://evil.example/maps'), ('Confirmations', '- [ ] I personally ate this Big Mac.')]:
            with self.subTest(key=key, value=value), self.assertRaises(ValidationError):
                parse_submission(body(**{key: value}), AUTHOR, 123, None)

    def test_duplicate_headings_fail_instead_of_overwriting(self):
        with self.assertRaises(ValidationError):
            parse_submission(body() + '\n\n### Texture score\n\n5', AUTHOR, 123, None)

    def test_bot_cannot_be_the_reviewer(self):
        with self.assertRaises(ValidationError):
            parse_submission(body(), {'id': 1, 'login': 'bot[bot]', 'type': 'Bot'}, 123, None)

    def test_correction_preserves_identity_and_changes_effective_type(self):
        old = parse_submission(body(), AUTHOR, 123, None)
        new = parse_submission(body(**{'Contribution type': 'Correction', 'Original review issue number': '123', 'Corrected review type': 'Review from memory', **NO_SCORES}), {'id': 9, 'login': 'maintainer', 'type': 'User'}, 125, old)
        self.assertEqual((new.source_issue, new.submission_issue, new.author_id, new.kind), (123, 125, 42, 'memory'))

    def test_unmarked_and_injected_fields_are_rejected(self):
        for raw in [body().replace('Original standard local recipe', 'Special edition'), body(**{'Overall experience': 'Hello\n\n### Author\n\nadmin'})]:
            with self.assertRaises(ValidationError):
                parse_submission(raw, AUTHOR, 123, None)
    def test_reviewer_correction_refreshes_login_without_changing_numeric_identity(self):
        old=parse_submission(body(),AUTHOR,123,None)
        new=parse_submission(body(**{'Contribution type':'Correction','Original review issue number':'123','Corrected review type':'Scored review'}),{'id':42,'login':'new-name','type':'User'},125,old)
        self.assertEqual((new.author_id,new.author_login),(42,'new-name'))

    def test_memory_with_scores_is_rejected_instead_of_silently_dropping_them(self):
        with self.assertRaisesRegex(ValidationError, 'New scored review'):
            parse_submission(body(**{'Contribution type': 'Review from memory'}), AUTHOR, 124, None)

    def test_overall_experience_is_optional(self):
        review = parse_submission(body(**{'Overall experience': '_No response_'}), AUTHOR, 123, None)
        self.assertEqual(review.experience, '')

    def test_removed_fields_are_no_longer_accepted(self):
        for heading in ('Texture explanation', 'Optional context'):
            with self.subTest(heading=heading), self.assertRaises(ValidationError):
                parse_submission(body() + f'\n\n### {heading}\n\nText', AUTHOR, 123, None)

    def test_restaurant_label_comes_from_issue_title(self):
        review = parse_submission(body(), AUTHOR, 123, None, TITLE)
        self.assertEqual(review.restaurant_label, "McDonald's at 1 Main St, Springfield, IL, USA")

    def test_placeholder_or_blank_title_has_no_label(self):
        for title in ('', '[Review] ', "[Review] McDonald's at [street address], [city], [state], [country]"):
            with self.subTest(title=title):
                self.assertIsNone(parse_submission(body(), AUTHOR, 123, None, title).restaurant_label)

    def test_title_is_part_of_submission_digest(self):
        a = parse_submission(body(), AUTHOR, 123, None, TITLE)
        b = parse_submission(body(), AUTHOR, 123, None, TITLE + ' (2)')
        self.assertNotEqual(a.submission_digest, b.submission_digest)
