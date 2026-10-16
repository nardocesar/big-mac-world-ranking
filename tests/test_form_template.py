import re
import unittest
from pathlib import Path
from scripts.reviews.forms import CORRECTION_FIELDS, REVIEW_FIELDS
from scripts.reviews.model import CRITERIA

TEMPLATES = Path(__file__).resolve().parent.parent / '.github/ISSUE_TEMPLATE'
PLACEHOLDER = "McDonald\'s at [street address], [city], [state], [country]"


def labels(text):
    return tuple(re.findall(r'^    label: (.+)$', text, re.M))


def field(text, label):
    return text.split(f'label: {label}', 1)[1].split('- type:', 1)[0]


class FormTemplateTests(unittest.TestCase):
    def setUp(self):
        self.review = (TEMPLATES / 'review.yml').read_text()
        self.correction = (TEMPLATES / 'correction.yml').read_text()

    def test_titles_suggest_restaurant_address(self):
        self.assertIn(f'title: "[Review] {PLACEHOLDER}"', self.review)
        self.assertIn(f'title: "[Correction] {PLACEHOLDER}"', self.correction)

    def test_field_labels_match_parser(self):
        self.assertEqual(labels(self.review), REVIEW_FIELDS)
        self.assertEqual(labels(self.correction), CORRECTION_FIELDS)

    def test_review_fields_are_required_except_overall_experience(self):
        for text in (self.review, self.correction):
            for label in ('Google Maps link', 'Visit date', 'Order type', *(f'{c} score' for c in CRITERIA)):
                self.assertIn('required: true', field(text, label))
            self.assertNotIn('required: true', field(text, 'Overall experience'))
        self.assertIn('required: true', field(self.correction, 'Original review issue number'))

    def test_scores_are_selects_from_one_to_five(self):
        for text in (self.review, self.correction):
            for criterion in CRITERIA:
                block = text.split(f'- type: dropdown\n  id: {criterion.lower().replace(" ", "_")}_score', 1)
                self.assertEqual(len(block), 2, criterion)
                self.assertIn("options:\n    - '1'\n    - '2'\n    - '3'\n    - '4'\n    - '5'", block[1].split('- type:', 1)[0])

    def test_removed_fields_are_gone(self):
        for text in (self.review, self.correction):
            for removed in ('explanation', 'optional context', 'memory', 'contribution type', 'corrected review type'):
                self.assertNotIn(removed, text.lower())
