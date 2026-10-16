from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from scripts.reviews.forms import parse_submission
from scripts.reviews.model import ValidationError, dump_review
from scripts.reviews.rankings import load_dataset, render_contributors, render_restaurants, generate
from tests.support import AUTHOR, NO_SCORES, body


def review(issue=123, author=AUTHOR, **fields):
    return parse_submission(body(**fields), author, issue, None)

class RankingTests(unittest.TestCase):
    def test_empty_states(self):
        self.assertIn('No accepted reviews yet', render_contributors([]))
        self.assertIn('No scored restaurant reviews yet', render_restaurants([]))

    def test_memory_counts_for_contributors_only_and_bot_not_credited(self):
        reviews = [review(), review(124, **{'Contribution type': 'Review from memory', **NO_SCORES})]
        page = render_contributors(reviews)
        self.assertIn('| 1 | [@traveler](https://github.com/traveler) | 2 | 1 | 1 |', page)
        restaurants = render_restaurants(reviews)
        self.assertIn('| 3.80 | 1 | 1 | 2025-01-02', restaurants)
        self.assertNotIn('github-actions', page)
        self.assertIn('reviews/123.md', restaurants)
        self.assertNotIn('reviews/124.md', restaurants)

    def test_competition_ties_and_deterministic_order(self):
        a = review()
        b = review(124, {'login': 'other', 'id': 9, 'type': 'User'}, **{'Google Maps link': 'https://maps.app.goo.gl/Bbb'})
        page = render_restaurants([a,b])
        self.assertEqual(page.count('| 1 | ['), 2)
        self.assertEqual(page, render_restaurants([b,a]))
        self.assertEqual(render_contributors([a,b]), render_contributors([b,a]))

    def test_account_rename_merges_by_id_and_uses_latest_login(self):
        old = review()
        renamed = review(125, {'login':'new-name','id':42,'type':'User'})
        text = render_contributors([renamed,old])
        self.assertIn('[@new-name]', text)
        self.assertNotIn('[@traveler]', text)
        self.assertIn('| 2 | 2 | 0 |', text)

    def test_exact_averages_do_not_tie_just_because_display_rounds(self):
        a = review()
        b = review(124, **{'Google Maps link': 'https://maps.app.goo.gl/Bbb'})
        group_a = [replace(a, source_issue=i, submission_issue=i, author_login_issue=i) for i in range(1, 101)]
        group_b = [replace(b, source_issue=i, submission_issue=i, author_login_issue=i) for i in range(101, 201)]
        group_b[-1] = replace(group_b[-1], scores={**b.scores, 'Texture': 4})
        page = render_restaurants(group_a + group_b)
        self.assertEqual(page.count('| 3.80 | 100 |'), 2)
        self.assertIn('| 2 |', page)

    def test_duplicate_identity_filename_and_restaurant_conflicts_rejected(self):
        a = review()
        with TemporaryDirectory() as tmp:
            root = Path(tmp); (root/'reviews').mkdir()
            (root/'reviews/124.md').write_text(dump_review(a))
            with self.assertRaises(ValidationError): load_dataset(root)
        with self.assertRaises(ValidationError):
            render_restaurants([a,replace(a,source_issue=124,submission_issue=124,maps_url='https://maps.app.goo.gl/Other')])
        with self.assertRaises(ValidationError):
            render_contributors([a,a])

    def test_rebuild_corrections_deletion_and_validation_before_writes(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); (root/'reviews').mkdir()
            path = root/'reviews/123.md'
            path.write_text(dump_review(review()))
            generate(root)
            first = (root/'RESTAURANTS.md').read_text()
            self.assertFalse(generate(root))
            path.write_text(dump_review(replace(review(),submission_issue=130,kind='memory',scores={})))
            generate(root)
            self.assertIn('No scored', (root/'RESTAURANTS.md').read_text())
            self.assertIn('| 1 | 0 | 1 |', (root/'CONTRIBUTORS.md').read_text())
            before = (root/'CONTRIBUTORS.md').read_bytes()
            path.write_text('invalid')
            with self.assertRaises(ValidationError): generate(root)
            self.assertEqual(before, (root/'CONTRIBUTORS.md').read_bytes())
            path.unlink(); generate(root)
            self.assertIn('No accepted', (root/'CONTRIBUTORS.md').read_text())
            self.assertNotEqual(first, (root/'RESTAURANTS.md').read_text())
    def test_maintainer_correction_does_not_revive_obsolete_login(self):
        old=review()
        renamed=review(124,{'login':'new-name','id':42,'type':'User'})
        corrected=parse_submission(body(**{'Contribution type':'Correction','Original review issue number':'123','Corrected review type':'Scored review'}),{'id':9,'login':'maintainer','type':'User'},125,old)
        self.assertIn('[@new-name]',render_contributors([corrected,renamed]))
