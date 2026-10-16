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


def restaurant_key(url: str) -> str:
    return hashlib.sha256(normalize_maps_url(url).encode()).hexdigest()


def safe_text(value: str) -> str:
    """Render user text as inert text, never HTML or active Markdown links."""
    value = html.escape(value, quote=True)
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
    kind: str
    restaurant_id: str | None
    maps_url: str | None
    visit_date: str | None
    date_note: str
    order_type: str
    scores: dict[str, int]
    explanations: dict[str, str]
    experience: str
    context: str
    submission_digest: str
    confirmed: bool

    @property
    def final_score(self) -> Fraction | None:
        return Fraction(sum(self.scores.values()), 5) if self.kind == 'scored' else None

    def validate(self):
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValidationError('Unsupported review schema version.')
        for key in ('source_issue', 'submission_issue', 'author_id'):
            positive_int(getattr(self, key), key)
        if self.submission_issue < self.source_issue:
            raise ValidationError('A correction cannot predate the original issue.')
        if not isinstance(self.author_login, str) or not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})', self.author_login):
            raise ValidationError('Reviewer must be a human GitHub account.')
        if self.kind not in {'scored', 'memory'} or self.order_type not in ORDER_TYPES or self.confirmed is not True:
            raise ValidationError('Review type, order type, and recipe confirmations are required.')
        if not isinstance(self.submission_digest, str) or not re.fullmatch(r'[a-f0-9]{64}', self.submission_digest):
            raise ValidationError('Submission digest is required.')
        if self.maps_url is not None:
            if normalize_maps_url(self.maps_url) != self.maps_url:
                raise ValidationError('Store the normalized Google Maps link.')
            if not isinstance(self.restaurant_id, str) or not re.fullmatch(r'[a-f0-9]{64}', self.restaurant_id):
                raise ValidationError('Restaurant ID must be a full SHA-256 identifier.')
        elif self.restaurant_id is not None or self.kind == 'scored':
            raise ValidationError('Scored reviews require a restaurant ID and Google Maps link.')
        if self.visit_date is not None:
            try:
                parsed = date.fromisoformat(self.visit_date)
                if parsed.isoformat() != self.visit_date or parsed > date.today():
                    raise ValueError()
            except (ValueError, TypeError):
                raise ValidationError('Visit date must be a real, nonfuture YYYY-MM-DD date.') from None
        elif self.kind == 'scored':
            raise ValidationError('Visit date is required for scored reviews.')
        if not isinstance(self.scores, dict) or not isinstance(self.explanations, dict):
            raise ValidationError('Scores and explanations must be objects.')
        if self.kind == 'scored':
            if set(self.scores) != set(CRITERIA) or any(type(v) is not int or not 1 <= v <= 5 for v in self.scores.values()):
                raise ValidationError('All five scores must be whole numbers from 1 to 5.')
            if set(self.explanations) != set(CRITERIA):
                raise ValidationError('Each score requires an explanation.')
        elif self.scores or self.explanations:
            raise ValidationError('Memory reviews must not store scores.')
        for value in (self.date_note, self.experience, self.context, *self.explanations.values()):
            if not isinstance(value, str) or len(value) > 12000 or '\x00' in value:
                raise ValidationError('Review text must be text of at most 12,000 characters per field.')
        if not self.experience.strip() or any(not s.strip() for s in self.explanations.values()):
            raise ValidationError('Overall experience and score explanations cannot be blank.')
        return self


def _body(review: Review) -> str:
    place = f'[Google Maps](<{maps_link(review.maps_url)}>)' if review.maps_url else 'Unknown (from memory)'
    lines = [f'# Big Mac review #{review.source_issue}', '', f'Reviewer: [@{review.author_login}](https://github.com/{review.author_login})', '',
             f'Restaurant: {place}', '', f'Visit: {safe_text(review.visit_date or review.date_note or "Unknown")} · {review.order_type}', '',
             f'Type: {review.kind}', '', 'Original standard local recipe confirmed: no extras, removed ingredients, or special edition.', '']
    if review.final_score is not None:
        lines += [f'**Final score: {float(review.final_score):.2f}/5**', '']
        for criterion in CRITERIA:
            lines += [f'## {criterion}: {review.scores[criterion]}/5', '', safe_text(review.explanations[criterion]), '']
    lines += ['## Overall experience', '', safe_text(review.experience), '']
    if review.context:
        lines += ['## Optional context', '', safe_text(review.context), '']
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
