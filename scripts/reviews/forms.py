"""Parse GitHub Issue Form Markdown; never trust author fields from the body."""
from datetime import date
import hashlib
import json
import re
from .model import CRITERIA, SCHEMA_VERSION, restaurant_label, CONFIRMATIONS, Review, ValidationError, normalize_maps_url, restaurant_key, positive_int

MARKER = 'Original standard local recipe'
ORIGINAL = 'Original review issue number'
_REVIEW = ('Google Maps link', 'Visit date', 'Order type') + tuple(f'{criterion} score' for criterion in CRITERIA) + ('Overall experience', 'Confirmations')
# Field order of the two Issue Forms: review.yml and correction.yml.
REVIEW_FIELDS = ('Big Mac recipe',) + _REVIEW
CORRECTION_FIELDS = ('Big Mac recipe', ORIGINAL) + _REVIEW
FIELDS = frozenset(CORRECTION_FIELDS)


def sections(body: str) -> dict[str, str]:
    if not isinstance(body, str) or len(body) > 60000:
        raise ValidationError('Submission is missing or too long.')
    headings = list(re.finditer(r'^### (.+)\s*$', body, re.M))
    result = {}
    for i, match in enumerate(headings):
        name = match.group(1).strip()
        if name not in FIELDS or name in result:
            raise ValidationError(f'Unknown or duplicate form heading: {name}. Keep the generated form headings unchanged.')
        value = body[match.end():headings[i + 1].start() if i + 1 < len(headings) else len(body)].strip()
        result[name] = '' if value == '_No response_' else value
    if result.get('Big Mac recipe') != MARKER:
        raise ValidationError('Use the Submit a review form linked in the README.')
    return result


def original_issue(body: str) -> int | None:
    """The corrected review's issue number for the Correct a review form, else None."""
    fields = sections(body)
    if ORIGINAL not in fields:
        return None
    number = fields[ORIGINAL].lstrip('#').strip()
    if not re.fullmatch(r'[1-9][0-9]*', number):
        raise ValidationError('Original review issue number is required for a correction.')
    return int(number)


def parse_submission(body: str, author: dict, issue_number: int, existing: Review | None = None, title: str = '') -> Review:
    fields = sections(body)
    positive_int(issue_number, 'Issue number')
    positive_int(author.get('id'), 'Reviewer account ID')
    if author.get('type') != 'User':
        raise ValidationError('Review submissions must come from a human GitHub account.')
    target = original_issue(body)
    correction = target is not None
    if correction and (existing is None or target != existing.source_issue):
        raise ValidationError('The original accepted review could not be found.')
    if not correction and existing is not None:
        raise ValidationError('Use the Correct a review form to update an accepted review.')
    checked = re.findall(r'^- \[[xX]\] (.+)$', fields.get('Confirmations', ''), re.M)
    if any(item not in checked for item in CONFIRMATIONS):
        raise ValidationError('Check all confirmations: personal consumption, original recipe, and photo permission.')
    maps = fields.get('Google Maps link', '')
    if not maps:
        raise ValidationError('Google Maps link is required.')
    maps = normalize_maps_url(maps)
    raw_date = fields.get('Visit date', '')
    try:
        visit_date = date.fromisoformat(raw_date).isoformat()
        if visit_date != raw_date:
            raise ValueError()
    except ValueError:
        raise ValidationError('Visit date must use YYYY-MM-DD.') from None
    scores = {}
    for criterion in CRITERIA:
        score = fields.get(f'{criterion} score', '')
        if not re.fullmatch('[1-5]', score):
            raise ValidationError(f'{criterion} score must be a whole number from 1 to 5.')
        scores[criterion] = int(score)
    digest = hashlib.sha256(json.dumps([body, title, author['id'], author['login'], issue_number], ensure_ascii=True).encode()).hexdigest()
    review = Review(SCHEMA_VERSION, target if correction else issue_number, issue_number,
                    existing.author_id if correction else author['id'],
                    existing.author_login if correction and author['id'] != existing.author_id else author['login'],
                    existing.author_login_issue if correction and author['id'] != existing.author_id else issue_number,
                    restaurant_key(maps), maps, maps, restaurant_label(title), visit_date,
                    fields.get('Order type', ''), scores, fields.get('Overall experience', ''), digest, True)
    return review.validate()
