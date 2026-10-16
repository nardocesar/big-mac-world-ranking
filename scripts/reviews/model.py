"""Canonical review data, validation, and safe readable Markdown."""
from dataclasses import asdict, dataclass
from datetime import date
from fractions import Fraction
import hashlib
import html
import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

CRITERIA = ('Flavor and balance', 'Texture', 'Temperature', 'Perceived freshness', 'Assembly')
ORDER_TYPES = ('Dine-in', 'Takeout', 'Delivery')
CONFIRMATIONS = (
    'I personally ate this Big Mac.',
    'It was the original standard local recipe: no extras, no ingredients removed, and no special edition.',
    'I have permission to share any photos included.',
)

SCHEMA_VERSION = 4
LABEL_PLACEHOLDER = '[street address]'


class ValidationError(ValueError):
    """An actionable submission or dataset error."""


def positive_int(value, field):
    if type(value) is not int or value < 1:
        raise ValidationError(f'{field} must be a positive integer.')
    return value


def normalize_maps_url(url: str) -> str:
    if not isinstance(url, str) or re.search(r'[\s<>\\]', url):
        raise ValidationError('Google Maps link must be a valid HTTPS restaurant link.')
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ValidationError('Google Maps link is invalid.') from exc
    if parsed.scheme != 'https' or parsed.username or parsed.password or port or parsed.fragment:
        raise ValidationError('Google Maps link must use HTTPS without credentials, a port, or a fragment.')
    path = parsed.path.rstrip('/')
    query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
             if not k.startswith('utm_') and k not in {'g_st', 'g_ep', 'entry', 'g_campaignid'}]
    if host in {'maps.app.goo.gl', 'goo.gl'}:
        pattern = r'/[A-Za-z0-9_-]+' if host == 'maps.app.goo.gl' else r'/maps/[A-Za-z0-9_-]+'
        valid = re.fullmatch(pattern, path)
    elif host in {'google.com', 'www.google.com', 'maps.google.com'}:
        valid = path.startswith('/maps/place/') and len(path) > len('/maps/place/')
        valid = valid or (path in {'', '/maps'} and any(k in {'cid', 'ftid', 'query_place_id'} and v for k, v in query))
        host = 'www.google.com'
    else:
        valid = False
    if not valid:
        raise ValidationError('Use the specific restaurant’s Google Maps Share link, not a search or city map.')
    return urlunsplit(('https', host, path, urlencode(query), ''))


def restaurant_label(title: str) -> str | None:
    """Display name from the issue title, e.g. \"McDonald's at 1 Main St, City\"."""
    label = re.sub(r'\s+', ' ', re.sub(r'^\s*\[(?:review|correction)\]', '', title or '', flags=re.I)).strip()[:200].strip()
    return label if label and LABEL_PLACEHOLDER not in label else None


def restaurant_key(url: str) -> str:
    return hashlib.sha256(normalize_maps_url(url).encode()).hexdigest()


def safe_text(value: str) -> str:
    """Render user text as inert text, never HTML or active Markdown links."""
    value = html.escape(value, quote=False)
    return re.sub(r'([\\`*{}\[\]()#+!|_~@])', r'\\\1', value)


def maps_link(url: str) -> str:
    # Angle destinations plus percent encoding prevent Markdown link breakout.
    from urllib.parse import quote
    return quote(normalize_maps_url(url), safe=':/?=&%+,;@!$*~_-')


@dataclass(frozen=True)
class Review:
    schema_version: int
    source_issue: int
    submission_issue: int
    author_id: int
    author_login: str
    author_login_issue: int
    restaurant_id: str
    maps_url: str
    input_maps_url: str
    restaurant_label: str | None
    visit_date: str
    order_type: str
    scores: dict[str, int]
    experience: str
    submission_digest: str
    confirmed: bool

    @property
    def final_score(self) -> Fraction:
        return Fraction(sum(self.scores.values()), 5)

    def validate(self):
        if type(self.schema_version) is not int or self.schema_version != SCHEMA_VERSION:
            raise ValidationError('Unsupported review schema version.')
        for key in ('source_issue', 'submission_issue', 'author_id', 'author_login_issue'):
            positive_int(getattr(self, key), key)
        if not self.source_issue <= self.author_login_issue <= self.submission_issue:
            raise ValidationError("Reviewer login observation must belong to this review’s history.")
        if self.submission_issue < self.source_issue:
            raise ValidationError('A correction cannot predate the original issue.')
        if not isinstance(self.author_login, str) or not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})', self.author_login):
            raise ValidationError('Reviewer must be a human GitHub account.')
        if self.order_type not in ORDER_TYPES or self.confirmed is not True:
            raise ValidationError('Order type and recipe confirmations are required.')
        if not isinstance(self.submission_digest, str) or not re.fullmatch(r'[a-f0-9]{64}', self.submission_digest):
            raise ValidationError('Submission digest is required.')
        for url in (self.maps_url, self.input_maps_url):
            if normalize_maps_url(url) != url:
                raise ValidationError('Store normalized Google Maps links.')
        if not isinstance(self.restaurant_id, str) or not re.fullmatch(r'[a-f0-9]{64}', self.restaurant_id):
            raise ValidationError('Restaurant ID must be a full SHA-256 identifier.')
        if self.restaurant_label is not None and (not isinstance(self.restaurant_label, str) or not self.restaurant_label.strip()
                                                  or len(self.restaurant_label) > 200 or re.search(r'[\x00-\x1f]', self.restaurant_label)):
            raise ValidationError('Restaurant label must be a single line of at most 200 characters.')
        try:
            parsed = date.fromisoformat(self.visit_date)
            if parsed.isoformat() != self.visit_date or parsed > date.today():
                raise ValueError()
        except (ValueError, TypeError):
            raise ValidationError('Visit date must be a real, nonfuture YYYY-MM-DD date.') from None
        if not isinstance(self.scores, dict) or set(self.scores) != set(CRITERIA) or any(type(v) is not int or not 1 <= v <= 5 for v in self.scores.values()):
            raise ValidationError('All five scores must be whole numbers from 1 to 5.')
        if not isinstance(self.experience, str) or len(self.experience) > 12000 or '\x00' in self.experience:
            raise ValidationError('Overall experience must be text of at most 12,000 characters.')
        return self


def _body(review: Review) -> str:
    name = safe_text(review.restaurant_label) if review.restaurant_label else 'Google Maps'
    lines = [f'# Big Mac review #{review.source_issue}', '', f'Reviewer: [@{review.author_login}](https://github.com/{review.author_login})', '',
             f'Restaurant: [{name}](<{maps_link(review.maps_url)}>)', '', f'Visit: {review.visit_date} · {review.order_type}', '',
             'Original standard local recipe confirmed: no extras, removed ingredients, or special edition.', '',
             f'**Final score: {float(review.final_score):.2f}/5**', '']
    lines += [f'- {criterion}: {review.scores[criterion]}/5' for criterion in CRITERIA] + ['']
    if review.experience.strip():
        lines += ['## Overall experience', '', safe_text(review.experience), '']
    return '\n'.join(lines).rstrip() + '\n'


def dump_review(review: Review) -> str:
    review.validate()
    metadata = json.dumps(asdict(review), ensure_ascii=True, indent=2, sort_keys=True)
    for char in '<>&[]':
        metadata = metadata.replace(char, f'\\u{ord(char):04x}')
    return f'---\n{metadata}\n---\n\n{_body(review)}'


def load_review(text: str) -> Review:
    if not isinstance(text, str) or len(text) > 150000 or not text.startswith('---\n'):
        raise ValidationError('Review must have JSON-compatible front matter.')
    try:
        metadata, _ = text[4:].split('\n---\n', 1)
        review = Review(**json.loads(metadata)).validate()
    except (ValueError, TypeError, KeyError) as exc:
        raise ValidationError(f'Invalid review metadata: {exc}') from exc
    if dump_review(review) != text:
        raise ValidationError('Review body must match its canonical metadata. Re-render after editing metadata.')
    return review


def rerender(path):
    """Regenerate the readable body after a deliberate metadata-only edit."""
    text = path.read_text()
    if not text.startswith('---\n'):
        raise ValidationError('Review must start with JSON-compatible front matter.')
    try:
        metadata, _ = text[4:].split('\n---\n',1)
        review = Review(**json.loads(metadata)).validate()
    except (ValueError,TypeError) as exc:
        raise ValidationError(f'Invalid review metadata: {exc}') from exc
    path.write_text(dump_review(review))


if __name__ == '__main__':
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description='Re-render a review after editing its metadata.')
    parser.add_argument('--render',type=Path,required=True)
    args = parser.parse_args()
    try:
        rerender(args.render)
    except (ValueError,OSError) as exc:
        parser.exit(1,f'{exc}\n')
