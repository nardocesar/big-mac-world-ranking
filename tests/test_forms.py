import unittest
from scripts.reviews.forms import parse_submission
from scripts.reviews.model import ValidationError
from tests.support import AUTHOR, body

class FormTests(unittest.TestCase):
    def test_scored_review_uses_real_author_and_computes_score(self):
        review = parse_submission(body(), AUTHOR, 123, None)
        self.assertEqual((review.author_id, review.author_login, review.source_issue), (42, 'traveler', 123))
        self.assertEqual(str(review.final_score), '19/5')

    def test_memory_allows_unknown_place_date_and_scores(self):
        review = parse_submission(body(**{'Contribution type': 'Review from memory', 'Google Maps link': '_No response_', 'Visit date': 'Around 2010', 'Texture score': 'I forget'}), AUTHOR, 124, None)
        self.assertEqual(review.kind, 'memory')
        self.assertIsNone(review.visit_date)
        self.assertIsNone(review.restaurant_id)
        self.assertIsNone(review.final_score)
        self.assertIn('Around 2010', review.date_note)

    def test_invalid_scored_values_fail_with_field_feedback(self):
        for key, value in [('Visit date', '2035-01-01'), ('Visit date', '2025-02-30'), ('Texture score', '2.5'), ('Texture score', '6'), ('Texture explanation', '_No response_'), ('Google Maps link', 'https://evil.example/maps'), ('Confirmations', '- [ ] I personally ate this Big Mac.')]:
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
        new = parse_submission(body(**{'Contribution type': 'Correction', 'Original review issue number': '123', 'Corrected review type': 'Review from memory'}), {'id': 9, 'login': 'maintainer', 'type': 'User'}, 125, old)
        self.assertEqual((new.source_issue, new.submission_issue, new.author_id, new.kind), (123, 125, 42, 'memory'))

    def test_unmarked_and_injected_fields_are_rejected(self):
        for raw in [body().replace('big-mac-review-v1', 'other'), body(**{'Overall experience': 'Hello\n\n### Author\n\nadmin'})]:
            with self.assertRaises(ValidationError):
                parse_submission(raw, AUTHOR, 123, None)
