import re
import unittest
from pathlib import Path
from scripts.reviews.forms import FIELDS

TEMPLATE = Path(__file__).resolve().parent.parent / '.github/ISSUE_TEMPLATE/review.yml'


class FormTemplateTests(unittest.TestCase):
    def setUp(self):
        self.text = TEMPLATE.read_text()

    def test_title_suggests_restaurant_address(self):
        self.assertIn('title: "[Review] McDonald\'s at [street address], [city], [state], [country]"', self.text)

    def test_field_labels_match_parser(self):
        labels = re.findall(r'^    label: (.+)$', self.text, re.M)
        self.assertEqual(tuple(labels), FIELDS)

    def test_removed_fields_and_required_experience_are_gone(self):
        self.assertNotIn('explanation', self.text.lower())
        self.assertNotIn('Optional context', self.text)
        experience = self.text.split('label: Overall experience', 1)[1].split('- type:', 1)[0]
        self.assertNotIn('required: true', experience)
