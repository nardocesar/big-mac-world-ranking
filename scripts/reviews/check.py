"""Validate a review PR from trusted code, without executing submitted code."""
import argparse
from dataclasses import replace
from .forms import parse_submission
from .github import APIError, endpoint, environment, get_file, get_ref
from .intake import can_write, submission_marker, set_status
from .model import ValidationError, load_review
from .rankings import load_dataset, remote_reviews, validate_dataset
from pathlib import Path


def check_pr(client,repo,number):
    pr=client.request('GET',endpoint(repo,f'/pulls/{number}'))
    if pr['state']!='open' or pr['head']['repo']['full_name']!=repo:
        raise ValidationError('Review validation requires an open same-repository PR.')
    files=client.list(endpoint(repo,f'/pulls/{number}/files'))
    if len(files)!=1 or files[0].get('status') not in {'added','modified'}:
        raise ValidationError('A review PR must add or modify exactly one review file.')
    path=files[0]['filename']
    import re
    if not re.fullmatch(r'reviews/[1-9][0-9]*\.md',path):
        raise ValidationError('Review PRs must only change their canonical review file.')
    actual=load_review(get_file(client,repo,path,pr['head']['sha']))
    if path!=f'reviews/{actual.source_issue}.md' or submission_marker(actual.submission_issue) not in (pr.get('body') or ''):
        raise ValidationError('Review identity does not match its filename or source PR marker.')
    issue=client.request('GET',endpoint(repo,f'/issues/{actual.submission_issue}'))
    if issue['state']!='open':
        raise ValidationError('The source issue must remain open until the review is accepted.')
    default=client.request('GET',endpoint(repo))['default_branch']
    base = get_ref(client,repo,default)
    accepted_text=get_file(client,repo,path,base)
    accepted=load_review(accepted_text) if accepted_text else None
    if accepted and issue['user']['id']!=accepted.author_id and not can_write(client,repo,issue['user']['login']):
        raise ValidationError('Correction is not authorized by the original reviewer or a maintainer.')
    expected=parse_submission(issue['body'],issue['user'],issue['number'],accepted,issue.get('title') or '')
    expected=replace(expected,restaurant_id=actual.restaurant_id,maps_url=actual.maps_url)
    if actual!=expected:
        raise ValidationError('The review does not match the latest valid issue. Retry intake before merging.')
    dataset = remote_reviews(client, repo, base)
    try:
        validate_dataset([r for r in dataset if r.source_issue != actual.source_issue] + [actual])
    except ValidationError as exc:
        raise ValidationError('This location needs maintainer reconciliation before acceptance: ' + str(exc)) from exc
    return actual



def check_maintenance(client,repo,pr):
    """Accept non-submission review changes (e.g. schema migrations) only from maintainers."""
    if pr['head']['repo']['full_name']!=repo:
        raise ValidationError('Review records can only be changed by form submissions or same-repository maintainer PRs.')
    if not can_write(client,repo,pr['user']['login']):
        raise ValidationError('Only maintainers can change review records outside the review form.')
    # Reads the head commit as data; never executes PR code.
    return remote_reviews(client,repo,pr['head']['sha'])


def check_with_status(client,repo,number):
    pr=client.request('GET',endpoint(repo,f'/pulls/{number}'))
    sha=pr['head']['sha']
    set_status(client,repo,sha,'pending','Validating the current review against its source form.')
    try:
        files=client.list(endpoint(repo,f'/pulls/{number}/files'))
        is_submission = '<!-- big-mac-review issue=' in (pr.get('body') or '')
        is_maintenance = not is_submission and any(f['filename'].startswith('reviews/') for f in files)
        result=check_pr(client,repo,number) if is_submission else None
        if is_maintenance:
            check_maintenance(client,repo,pr)
        if result is not None:
            current_issue = client.request('GET', endpoint(repo, f'/issues/{result.submission_issue}'))
            default = client.request('GET', endpoint(repo))['default_branch']
            accepted_text = get_file(client, repo, f'reviews/{result.source_issue}.md', get_ref(client, repo, default))
            original = load_review(accepted_text) if accepted_text else None
            latest_submission = parse_submission(current_issue['body'], current_issue['user'], current_issue['number'], original, current_issue.get('title') or '')
            if current_issue['state'] != 'open' or latest_submission.submission_digest != result.submission_digest:
                raise ValidationError('Source issue changed during validation; retry intake.')
        latest=client.request('GET',endpoint(repo,f'/pulls/{number}'))
        if latest['head']['sha']!=sha:
            raise ValidationError('PR changed during validation; retry on the current commit.')
    except (ValueError,APIError):
        set_status(client,repo,sha,'failure','Review needs correction; see workflow and source issue.')
        raise
    if result is not None:
        description = 'Review matches the latest valid submission.'
    elif is_maintenance:
        description = 'Maintenance change by a maintainer; full review dataset validated.'
    else:
        description = 'No review records changed; review validation is not applicable.'
    set_status(client,repo,sha,'success',description)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pr',type=int)
    parser.add_argument('--status',action='store_true')
    parser.add_argument('--root',type=Path,default=Path('.'))
    args=parser.parse_args()
    try:
        if args.pr:
            client,repo=environment()
            (check_with_status if args.status else check_pr)(client,repo,args.pr)
        else:
            load_dataset(args.root)
    except (ValueError,OSError) as exc:
        parser.exit(1,f'{exc}\n')
    print('Review validation passed.')

if __name__=='__main__':
    main()
