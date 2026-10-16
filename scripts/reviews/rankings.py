"""Rebuild both public ranking pages from accepted Markdown records."""
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
import argparse
import re
from .model import Review, ValidationError, load_review, maps_link

FOOTER = '\n---\nGenerated from accepted files in `reviews/`. Do not edit this page manually.\nRebuild with `python -m scripts.reviews.rankings`. [How to contribute](README.md#-how-to-contribute).\n'


def validate_dataset(reviews: list[Review]) -> list[Review]:
    seen, submissions, places = set(), set(), {}
    for review in reviews:
        review.validate()
        if review.source_issue in seen or review.submission_issue in submissions:
            raise ValidationError('Duplicate original review or latest submission issue in dataset.')
        seen.add(review.source_issue)
        submissions.add(review.submission_issue)
        if review.restaurant_id:
            if review.restaurant_id in places and places[review.restaurant_id] != review.maps_url:
                raise ValidationError('Reviews for the same restaurant ID must use one canonical Google Maps URL.')
            places[review.restaurant_id] = review.maps_url
    return reviews


def load_dataset(root: Path) -> list[Review]:
    reviews = []
    for path in sorted((root/'reviews').glob('*.md')):
        if path.is_symlink() or not re.fullmatch(r'[1-9][0-9]*\.md', path.name):
            raise ValidationError(f'Unexpected review path: {path.name}.')
        review = load_review(path.read_text())
        if path.stem != str(review.source_issue):
            raise ValidationError(f'{path.name} does not match its original issue number.')
        reviews.append(review)
    return validate_dataset(reviews)


def source_links(reviews: list[Review]) -> str:
    return ', '.join(f'[#{r.source_issue}](reviews/{r.source_issue}.md)' for r in sorted(reviews,key=lambda r:r.source_issue))


def render_contributors(reviews: list[Review]) -> str:
    validate_dataset(reviews)
    lines = ['# 🍟 Top contributors', '', 'Every accepted review counts once, including reviews from memory. Corrections replace a review and never add a contribution. Equal totals share a position.', '']
    groups = defaultdict(list)
    for review in reviews:
        groups[review.author_id].append(review)
    if not groups:
        lines += ['No accepted reviews yet. [Be the first to contribute](README.md#-how-to-contribute).', '']
    else:
        lines += ['| Rank | Contributor | Total reviews | Scored | From memory | Reviews |', '| --- | --- | --- | --- | --- | --- |']
        previous, rank = None, 0
        for index, (_, group) in enumerate(sorted(groups.items(),key=lambda item:(-len(item[1]),item[0])),1):
            total = len(group)
            if total != previous:
                rank = index
            previous = total
            latest = max(group,key=lambda r:(r.submission_issue,r.author_login.lower()))
            scored = sum(r.kind == 'scored' for r in group)
            lines.append(f'| {rank} | [@{latest.author_login}](https://github.com/{latest.author_login}) | {total} | {scored} | {total-scored} | {source_links(group)} |')
        lines.append('')
    return '\n'.join(lines) + FOOTER


def render_restaurants(reviews: list[Review]) -> str:
    validate_dataset(reviews)
    lines = ['# 🍔 Best McDonald’s restaurants', '', 'Ranked by the exact average of accepted scored Big Mac reviews. Every review and each of the five criteria have equal weight. Scores display two decimal places; only equal exact averages share a rank.', '', 'A single review is an initial sample, not a verdict. Memory reviews are excluded. Dine-in, takeout, and delivery details remain in the linked reviews. Restaurants are grouped by a maintainer-reviewed location ID; different Maps links may need reconciliation.', '']
    groups = defaultdict(list)
    for review in reviews:
        if review.kind == 'scored':
            groups[review.restaurant_id].append(review)
    if not groups:
        lines += ['No scored restaurant reviews yet. [Add the first stop](README.md#-how-to-contribute).', '']
    else:
        averages = {key: sum((r.final_score for r in group),Fraction()) / len(group) for key,group in groups.items()}
        lines += ['| Rank | Restaurant · Google Maps | Average / 5 | Reviews | Contributors | First visit | Last visit | Source reviews |', '| --- | --- | --- | --- | --- | --- | --- | --- |']
        previous, rank = None, 0
        for index, (key, group) in enumerate(sorted(groups.items(),key=lambda item:(-averages[item[0]],item[0])),1):
            average = averages[key]
            if average != previous:
                rank = index
            previous = average
            dates = [r.visit_date for r in group]
            label = f'Location {key[:12]}'
            lines.append(f'| {rank} | [{label}](<{maps_link(group[0].maps_url)}>) | {float(average):.2f} | {len(group)} | {len({r.author_id for r in group})} | {min(dates)} | {max(dates)} | {source_links(group)} |')
        lines.append('')
    return '\n'.join(lines) + FOOTER


def outputs(reviews: list[Review]) -> dict[str, str]:
    return {'CONTRIBUTORS.md':render_contributors(reviews), 'RESTAURANTS.md':render_restaurants(reviews)}


def generate(root: Path, check: bool = False) -> bool:
    rendered = outputs(load_dataset(root))
    changed = {name:text for name,text in rendered.items() if not (root/name).exists() or (root/name).read_text() != text}
    if not check:
        for name,text in changed.items():
            (root/name).write_text(text)
    return bool(changed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path('.'))
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args()
    try:
        changed = generate(args.root,args.check)
    except (ValidationError,OSError) as exc:
        parser.exit(1, f'{exc}\n')
    if args.check and changed:
        parser.exit(1,'Generated ranking files are out of date.\n')
    print('Rankings changed.' if changed else 'Rankings are up to date.')

if __name__ == '__main__':
    main()
