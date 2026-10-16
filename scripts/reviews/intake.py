"""Turn review issues into review-only PRs, preserving human approval."""
import argparse
from dataclasses import replace
import json
import os
import re
from urllib.parse import urlencode
from .forms import MARKER, original_issue, parse_submission
from .github import APIError, commit_files, endpoint, environment, get_file, get_ref
from .model import ValidationError, dump_review, load_review, positive_int

STATUS = 'review/latest-submission'
COMMENT_MARKER = '<!-- big-mac-review-feedback-v1 -->'


def feedback(client,repo,issue_number,text):
    path=endpoint(repo,f'/issues/{issue_number}/comments')
    body=COMMENT_MARKER+'\n'+text
    comments=client.list(path)
    previous=next((c for c in comments if c.get('user',{}).get('login')=='github-actions[bot]' and c.get('body','').startswith(COMMENT_MARKER)),None)
    if previous:
        if previous['body']!=body:
            client.request('PATCH',endpoint(repo,f'/issues/comments/{previous["id"]}'),{'body':body})
    else:
        client.request('POST',path,{'body':body})


def set_status(client,repo,sha,state,description):
    previous=next((s for s in client.list(endpoint(repo,f'/commits/{sha}/statuses')) if s['context']==STATUS),None)
    data={'state':state,'context':STATUS,'description':description[:140]}
    if not previous or any(previous.get(k)!=v for k,v in data.items()):
        client.request('POST',endpoint(repo,f'/statuses/{sha}'),data)


def can_write(client,repo,login):
    try:
        permission=client.request('GET',endpoint(repo,f'/collaborators/{login}/permission'))
    except APIError as exc:
        if exc.status == 404:
            return False
        raise
    return permission.get('permission') in {'write','maintain','admin'}


def submission_marker(number):
    return f'<!-- big-mac-review issue={number} -->'


def branch_prs(client,repo,branch):
    query=urlencode({'state':'all','head':repo.split('/')[0]+':'+branch,'per_page':100})
    return client.list(endpoint(repo,'/pulls?'+query))


def pending_for_issue(client,repo,number):
    # Also finds an old PR if a submitted correction target was edited or removed.
    prs=client.list(endpoint(repo,'/pulls?state=open&per_page=100'))
    return [p for p in prs if submission_marker(number) in (p.get('body') or '') and p['head']['repo']['full_name']==repo]


def handle_issue(client,repo,issue_number,retry=False,dry_run=False):
    positive_int(issue_number,'Issue number')
    issue=client.request('GET',endpoint(repo,f'/issues/{issue_number}'))
    if 'pull_request' in issue:
        return {'outcome':'ignored'}
    raw=issue.get('body') or ''
    pending=pending_for_issue(client,repo,issue_number)
    is_form=bool(re.search(r'^### Form version\s*\n\s*'+re.escape(MARKER)+r'\s*(?:\n|$)',raw,re.M))
    if not is_form and not pending:
        return {'outcome':'ignored'}
    existing_pr=pending[0] if pending else None
    metadata=client.request('GET',endpoint(repo))
    default=metadata['default_branch']
    base=get_ref(client,repo,default)
    def fail(message):
        if not dry_run:
            if existing_pr:
                current=client.request('GET',endpoint(repo,f'/pulls/{existing_pr["number"]}'))
                set_status(client,repo,current['head']['sha'],'failure','Submission needs correction; see source issue.')
            # Error messages contain field names, not untrusted field values.
            feedback(client,repo,issue_number,'Please update this review form:\n\n'+message)
        return {'outcome':'invalid','error':message}
    try:
        target=original_issue(raw) if is_form else None
        source=target or issue_number
        accepted_text=get_file(client,repo,f'reviews/{source}.md',base)
        accepted=load_review(accepted_text) if accepted_text else None
        if accepted and (not target or accepted.submission_issue==issue_number):
            if not dry_run:
                feedback(client,repo,issue_number,'This review has been accepted. Later issue edits do not change the record. To update it, submit the review form as a Correction referencing original issue #'+str(source)+'.')
            return {'outcome':'accepted'}
        if existing_pr and existing_pr['head']['ref']!='codex/review-'+str(source):
            raise ValidationError('Do not change the original review target after a PR has been created. Ask a maintainer to close the old submission first.')
        branch='codex/review-'+str(source)
        prs=branch_prs(client,repo,branch)
        matching=sorted((p for p in prs if submission_marker(issue_number) in (p.get('body') or '')),key=lambda p:p['number'],reverse=True)
        prior=matching[0] if matching else None
        existing_pr=existing_pr or (prior if prior and prior['state']=='open' else None)
        if issue['state']=='closed':
            if not dry_run and existing_pr:
                set_status(client,repo,existing_pr['head']['sha'],'failure','Source issue is closed.')
                client.request('PATCH',endpoint(repo,f'/pulls/{existing_pr["number"]}'),{'state':'closed'})
                feedback(client,repo,issue_number,'The pending review PR was closed because this submission was closed. A maintainer can retry it manually.')
            return {'outcome':'closed'}
        if prior and prior['state']=='closed' and not prior.get('merged_at') and not retry:
            return {'outcome':'rejected'}
        if target:
            if not accepted:
                raise ValidationError('Original review issue must identify an accepted review.')
            if issue['user']['id']!=accepted.author_id and not can_write(client,repo,issue['user']['login']):
                raise ValidationError('Only the original reviewer or a repository maintainer can correct this review.')
        review=parse_submission(raw,issue['user'],issue_number,accepted if target else None)
        for pr in prs:
            if pr['state']=='open' and submission_marker(issue_number) not in (pr.get('body') or ''):
                raise ValidationError('This review already has another pending correction. Resolve that PR before submitting another.')
        branch_sha=get_ref(client,repo,branch)
        previous_text=get_file(client,repo,f'reviews/{source}.md',branch_sha) if branch_sha else None
        previous=load_review(previous_text) if previous_text else None
        if previous and previous.submission_issue not in {issue_number,accepted.submission_issue if accepted else issue_number}:
            # An atomic ref update can reserve the branch before its PR is created.
            if not any(p.get('merged_at') and submission_marker(previous.submission_issue) in (p.get('body') or '') for p in prs):
                raise ValidationError('Another correction is reserving this review branch. Ask a maintainer to finish or close it.')
        if previous and previous.submission_issue==issue_number and previous.input_maps_url==review.input_maps_url:
            review=replace(review,restaurant_id=previous.restaurant_id,maps_url=previous.maps_url)
        rendered=dump_review(review)
        if dry_run:
            return {'outcome':'would-update' if prior else 'would-create','path':f'reviews/{source}.md','content':rendered}
        if rendered!=previous_text:
            try:
                branch_sha=commit_files(client,repo,branch,{f'reviews/{source}.md':rendered},f'Record Big Mac review from issue #{issue_number}',base_sha=base,expected_sha=branch_sha)
            except APIError as exc:
                if exc.status in {409,422}:
                    raise ValidationError('The review branch changed concurrently. Ask a maintainer to retry this submission.') from exc
                raise
        if prior and prior['state']=='closed':
            prior=client.request('PATCH',endpoint(repo,f'/pulls/{prior["number"]}'),{'state':'open'})
        if not prior:
            prior=client.request('POST',endpoint(repo,'/pulls'),{
                'head':branch,'base':default,'title':f'Review: Big Mac visit #{source}',
                'body':submission_marker(issue_number)+f'\n\nReview submitted by @{review.author_login}.\n\nCloses #{issue_number}\n\nThe record is `reviews/{source}.md`. Check the scores, original-recipe confirmation, and whether this location should reuse an existing restaurant ID and canonical Maps URL. Human review is required.'})
        # Check freshness before success; if the issue changed mid-run, fail closed.
        latest=client.request('GET',endpoint(repo,f'/issues/{issue_number}'))
        if latest.get('body')!=raw or latest['state']!='open':
            existing_pr=prior
            return fail('The form changed during processing. A maintainer can retry the latest version.')
        set_status(client,repo,branch_sha,'success','Review matches the latest valid submission.')
        feedback(client,repo,issue_number,f'Your review PR is ready for maintainer review: {prior["html_url"]}\n\nEdit this form to update the pending review. Acceptance happens only after a maintainer merges the PR.')
        return {'outcome':'ready','pr':prior['number']}
    except ValidationError as exc:
        return fail(str(exc))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--issue',type=int,required=True)
    parser.add_argument('--retry',action='store_true')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    try:
        client,repo=environment()
        if args.retry and not can_write(client,repo,os.environ.get('GITHUB_ACTOR','')):
            raise ValidationError('Only maintainers can request a retry.')
        result=handle_issue(client,repo,args.issue,args.retry,args.dry_run)
        print(json.dumps(result,indent=2))
        if result['outcome']=='invalid':
            parser.exit(1)
    except (APIError,ValueError) as exc:
        parser.exit(1,f'{exc}\n')

if __name__=='__main__':
    main()
