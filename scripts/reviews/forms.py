"""Parse GitHub Issue Form Markdown; never trust author fields from the body."""
from dataclasses import replace
from datetime import date
import hashlib
import json
import re
from .model import CRITERIA, SCHEMA_VERSION, restaurant_label, CONFIRMATIONS, Review, ValidationError, normalize_maps_url, restaurant_key, positive_int

MARKER = 'Original standard local recipe'
BASE_FIELDS = ('Big Mac recipe', 'Contribution type', 'Original review issue number', 'Corrected review type', 'Google Maps link', 'Visit date', 'Order type')
FIELDS = BASE_FIELDS + tuple(f'{criterion} score' for criterion in CRITERIA) + ('Overall experience', 'Confirmations')


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
    fields = sections(body)
    if fields.get('Contribution type') != 'Correction':
        return None
    number = fields.get('Original review issue number', '').lstrip('#').strip()
    if not re.fullmatch(r'[1-9][0-9]*', number):
        raise ValidationError('Original review issue number is required for a correction.')
    return int(number)


def parse_submission(body: str, author: dict, issue_number: int, existing: Review | None = None, title: str = '') -> Review:
    fields = sections(body)
    positive_int(issue_number, 'Issue number')
    positive_int(author.get('id'), 'Reviewer account ID')
    if author.get('type') != 'User':
        raise ValidationError('Review submissions must come from a human GitHub account.')
    selected = fields.get('Contribution type')
    correction = selected == 'Correction'
    target = original_issue(body)
    if correction and (existing is None or target != existing.source_issue):
        raise ValidationError('The original accepted review could not be found.')
    if not correction and existing is not None:
        raise ValidationError('Use Correction to update an accepted review.')
    kind = fields.get('Corrected review type') if correction else selected
    kinds = {'New scored review': 'scored', 'Scored review': 'scored', 'Review from memory': 'memory'}
    if kind not in kinds:
        raise ValidationError('Select scored review or review from memory (also for corrections).')
    kind = kinds[kind]
    checked = re.findall(r'^- \[[xX]\] (.+)$', fields.get('Confirmations', ''), re.M)
    if any(item not in checked for item in CONFIRMATIONS):
        raise ValidationError('Check all confirmations: personal consumption, original recipe, and photo permission.')
    maps = fields.get('Google Maps link', '')
    maps = normalize_maps_url(maps) if maps else None
    raw_date = fields.get('Visit date', '')
    try:
        visit_date = date.fromisoformat(raw_date).isoformat()
        if visit_date != raw_date:
            raise ValueError()
    except ValueError:
        if kind == 'scored':
            raise ValidationError('Visit date must use YYYY-MM-DD for a scored review.') from None
        visit_date = None
    # GitHub renders an unselected optional dropdown as "None".
    raw_scores = {c: fields.get(f'{c} score', '') for c in CRITERIA}
    filled = {c: v for c, v in raw_scores.items() if v not in {'', 'None'}}
    scores = {}
    if kind == 'scored':
        for criterion in CRITERIA:
            score = raw_scores[criterion]
            if not re.fullmatch('[1-5]', score):
                raise ValidationError(f'{criterion} score must be a whole number from 1 to 5.')
            scores[criterion] = int(score)
    elif filled:
        raise ValidationError('You selected Review from memory but filled in scores. Memory reviews never count toward restaurant averages: select New scored review (or Scored review for a correction) to rank this visit, or clear the scores.')
    digest = hashlib.sha256(json.dumps([body, title, author['id'], author['login'], issue_number], ensure_ascii=True).encode()).hexdigest()
    review = Review(SCHEMA_VERSION, target if correction else issue_number, issue_number,
                    existing.author_id if correction else author['id'],
                    existing.author_login if correction and author['id'] != existing.author_id else author['login'],
                    existing.author_login_issue if correction and author['id'] != existing.author_id else issue_number,
                    kind, restaurant_key(maps) if maps else None, maps, maps, restaurant_label(title), visit_date,
                    raw_date if visit_date is None else '', fields.get('Order type', ''), scores,
                    fields.get('Overall experience', ''), digest, True)
    return review.validate()
