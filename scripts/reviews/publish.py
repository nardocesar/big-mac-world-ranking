"""Publish both ranking pages from a fresh accepted-data snapshot."""
import argparse
import base64
import re
from .github import APIError, create_commit, endpoint, environment, get_file, get_ref
from .intake import feedback
from .model import ValidationError, load_review
from .rankings import outputs, validate_dataset


def remote_reviews(client,repo,sha):
    commit=client.request('GET',endpoint(repo,'/git/commits/'+sha))
    tree=client.request('GET',endpoint(repo,'/git/trees/'+commit['tree']['sha']+'?recursive=1'))
    if tree.get('truncated'):
        raise ValidationError('Repository tree is truncated; refusing to publish a partial ranking.')
    reviews=[]
    for item in tree['tree']:
        path=item['path']
        if not path.startswith('reviews/') or not path.endswith('.md'):
            continue
        if not re.fullmatch(r'reviews/[1-9][0-9]*\.md',path) or item.get('mode')!='100644' or item['type']!='blob':
            raise ValidationError('Accepted reviews must be regular numeric Markdown files directly inside reviews/.')
        blob=client.request('GET',endpoint(repo,'/git/blobs/'+item['sha']))
        if blob.get('encoding')!='base64':
            raise ValidationError('Unexpected review blob encoding.')
        review=load_review(base64.b64decode(blob['content']).decode())
        if path!=f'reviews/{review.source_issue}.md':
            raise ValidationError('Review filename does not match its original source issue.')
        reviews.append(review)
    return validate_dataset(reviews)


def acknowledge(client,repo,reviews):
    for review in reviews:
        for issue in sorted({review.source_issue,review.submission_issue}):
            feedback(client,repo,issue,f'This review has been accepted: https://github.com/{repo}/blob/HEAD/reviews/{review.source_issue}.md\n\nTo change the accepted record, submit the review form as a Correction referencing original issue #{review.source_issue}. Later edits to this issue do not change the ranking.')


def publish_rankings(client,repo,max_attempts=3):
    default=client.request('GET',endpoint(repo))['default_branch']
    for attempt in range(max_attempts):
        snapshot=get_ref(client,repo,default)
        reviews=remote_reviews(client,repo,snapshot)
        changed={name:text for name,text in outputs(reviews).items() if get_file(client,repo,name,snapshot)!=text}
        if not changed:
            # Recheck head before declaring a no-op; a merge may have arrived while reading.
            if get_ref(client,repo,default)!=snapshot:
                continue
            acknowledge(client,repo,reviews)
            return {'outcome':'unchanged'}
        sha=create_commit(client,repo,snapshot,changed,'docs: update community Big Mac rankings')
        try:
            from urllib.parse import quote
            client.request('PATCH',endpoint(repo,'/git/refs/heads/'+quote(default,safe='')),{'sha':sha,'force':False})
        except APIError as exc:
            if exc.status in {409,422}:
                if attempt+1<max_attempts:
                    continue
                raise APIError(exc.status,f'Could not publish after {max_attempts} attempts. Check branch rules or retry the ranking workflow.') from exc
            raise
        acknowledge(client,repo,reviews)
        return {'outcome':'updated','commit':sha}
    raise APIError(409,f'Default branch kept changing across {max_attempts} attempts; retry the ranking workflow.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        client,repo=environment()
        print(publish_rankings(client,repo))
    except (ValueError,APIError) as exc:
        parser.exit(1,f'{exc}\n')

if __name__=='__main__':
    main()
