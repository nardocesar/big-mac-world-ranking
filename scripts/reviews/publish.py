"""Publish both ranking pages from a fresh accepted-data snapshot."""
import argparse
from .github import APIError, create_commit, endpoint, environment, get_file, get_ref
from .intake import feedback, set_status
from .rankings import outputs, remote_reviews


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
        # This trusted commit changes only derived pages, and its complete source dataset passed validation.
        set_status(client,repo,sha,'success','Only generated rankings changed; accepted review data validated.')
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
