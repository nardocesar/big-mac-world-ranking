import dataclasses
import unittest
from scripts.reviews.forms import parse_submission
from scripts.reviews.model import ValidationError, dump_review, load_review, normalize_maps_url
from tests.support import AUTHOR, body

class ModelTests(unittest.TestCase):
    def test_round_trip_and_inert_user_text(self):
        review = parse_submission(body(**{'Overall experience': '---\n$(touch /tmp/nope)\n[bad](javascript:alert(1))\n<script>bad</script> | @someone'}), AUTHOR, 123, None)
        rendered = dump_review(review)
        self.assertEqual(load_review(rendered), review)
        self.assertNotIn('<script>', rendered)
        self.assertNotIn('[bad](javascript:', rendered)

    def test_rendered_body_cannot_silently_diverge(self):
        rendered = dump_review(parse_submission(body(), AUTHOR, 123, None))
        with self.assertRaises(ValidationError):
            load_review(rendered + '\nA secret second rating\n')

    def test_google_maps_links_only(self):
        for bad in ['http://maps.app.goo.gl/abc', 'https://google.com.evil.test/maps/place/a', 'https://www.google.com/search?q=McDonalds', 'https://www.google.com/maps/search/McDonalds', 'https://user@maps.app.goo.gl/abc', 'https://maps.app.goo.gl:444/abc', 'https://www.google.com/maps/place/a\nhello']:
            with self.subTest(url=bad), self.assertRaises(ValidationError):
                normalize_maps_url(bad)
        self.assertEqual(normalize_maps_url('https://maps.app.goo.gl/AbC?g_st=ic'), 'https://maps.app.goo.gl/AbC')
        self.assertEqual(normalize_maps_url('https://www.google.com/maps/place/McDonalds/?utm_source=x'), 'https://www.google.com/maps/place/McDonalds')

    def test_short_and_full_links_are_not_guessed_equivalent(self):
        a = parse_submission(body(), AUTHOR, 123, None)
        b = parse_submission(body(**{'Google Maps link': 'https://maps.app.goo.gl/AbC'}), AUTHOR, 124, None)
        self.assertNotEqual(a.restaurant_id, b.restaurant_id)
        self.assertEqual(load_review(dump_review(dataclasses.replace(b, restaurant_id=a.restaurant_id, maps_url=a.maps_url))).restaurant_id, a.restaurant_id)
