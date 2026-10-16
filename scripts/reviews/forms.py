"""Parse GitHub Issue Form Markdown; never trust author fields from the body."""
from dataclasses import replace
from datetime import date
import hashlib
import json
import re
from .model import CRITERIA, CONFIRMATIONS, Review, ValidationError, normalize_maps_url, restaurant_key, positive_int

MARKER = 'big-mac-review-v1'
BASE_FIELDS = ('Form version', 'Contribution type', 'Original review issue number', 'Corrected review type', 'Google Maps link', 'Visit date', 'Order type')
FIELDS = BASE_FIELDS + tuple(x for criterion in CRITERIA for x in (f'{criterion} score', f'{criterion} explanation')) + ('Overall experience', 'Optional context', 'Confirmations')


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
    if result.get('Form version') != MARKER:
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


def parse_submission(body: str, author: dict, issue_number: int, existing: Review | None = None) -> Review:
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
    scores, explanations = {}, {}
    if kind == 'scored':
        for criterion in CRITERIA:
            score = fields.get(f'{criterion} score', '')
            if not re.fullmatch('[1-5]', score):
                raise ValidationError(f'{criterion} score must be a whole number from 1 to 5.')
            scores[criterion] = int(score)
            explanations[criterion] = fields.get(f'{criterion} explanation', '')
    digest = hashlib.sha256(json.dumps([body, author['id'], author['login'], issue_number], ensure_ascii=True).encode()).hexdigest()
    review = Review(1, target if correction else issue_number, issue_number,
                    existing.author_id if correction else author['id'], existing.author_login if correction else author['login'],
                    kind, restaurant_key(maps) if maps else None, maps, maps, visit_date,
                    raw_date if visit_date is None else '', fields.get('Order type', ''), scores, explanations,
                    fields.get('Overall experience', ''), fields.get('Optional context', ''), digest, True)
    return review.validate()
