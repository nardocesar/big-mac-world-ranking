from dataclasses import replace
import unittest
from scripts.reviews.intake import handle_issue
from scripts.reviews.github import get_file, commit_files
from scripts.reviews.model import load_review, dump_review
from scripts.reviews.check import check_pr
from tests.fake_github import FakeGitHub
from tests.support import AUTHOR, body

class IntakeTests(unittest.TestCase):
    def setUp(self): self.api=FakeGitHub()
    def submit(self,n=123,**kwargs): return handle_issue(self.api,'o/r',n,**kwargs)
    def test_valid_submission_creates_one_review_pr_and_credits_human(self):
        result=self.submit(); self.assertEqual(result['outcome'],'ready')
        self.assertEqual(len(self.api.prs),1)
        record=load_review(get_file(self.api,'o/r','reviews/123.md','codex/review-123'))
        self.assertEqual((record.author_login,record.author_id),('traveler',42))
        check_pr(self.api,'o/r',result['pr'])
        writes=len(self.api.mutations); self.submit()
        self.assertEqual(writes,len(self.api.mutations))
    def test_valid_edit_updates_existing_pr(self):
        self.submit(); self.api.issues[123]['body']=body(**{'Texture score':'5'})
        self.submit()
        self.assertEqual(len(self.api.prs),1)
        record=load_review(get_file(self.api,'o/r','reviews/123.md','codex/review-123'))
        self.assertEqual(str(record.final_score),'21/5')
    def test_invalid_edit_fails_status_and_check_of_stale_pr(self):
        result=self.submit(); self.api.issues[123]['body']=body(**{'Texture score':'6'})
        self.assertEqual(self.submit()['outcome'],'invalid')
        sha=self.api.refs['codex/review-123']
        self.assertEqual(self.api.statuses[sha]['state'],'failure')
        with self.assertRaises(ValueError): check_pr(self.api,'o/r',result['pr'])
    def test_invalid_first_submission_and_unrelated_issue_make_no_pr(self):
        self.api.issues[123]['body']=body(**{'Texture score':'0'})
        self.assertEqual(self.submit()['outcome'],'invalid'); self.assertFalse(self.api.prs)
        self.api.issues[123]['body']='Please add a website.'
        self.assertEqual(self.submit()['outcome'],'ignored')
    def test_merge_then_issue_edit_does_not_change_accepted_record(self):
        result=self.submit(); self.api.merge(result['pr'])
        before=self.api.refs['main']; self.api.issues[123]['body']=body(**{'Texture score':'1'})
        self.assertEqual(self.submit()['outcome'],'accepted')
        self.assertEqual(self.api.refs['main'],before)
        self.assertEqual(len(self.api.prs),1)
    def test_rejected_pr_needs_explicit_retry(self):
        result=self.submit(); self.api.prs[result['pr']]['state']='closed'
        self.assertEqual(self.submit()['outcome'],'rejected')
        self.assertEqual(self.submit(retry=True)['outcome'],'ready')
        self.assertEqual(len(self.api.prs),1)
    def test_closing_issue_closes_pending_pr(self):
        result=self.submit(); self.api.issues[123]['state']='closed'
        self.assertEqual(self.submit()['outcome'],'closed')
        self.assertEqual(self.api.prs[result['pr']]['state'],'closed')
    def test_correction_replaces_review_without_stealing_author(self):
        result=self.submit(); self.api.merge(result['pr'])
        raw=body(**{'Contribution type':'Correction','Original review issue number':'123','Corrected review type':'Scored review','Texture score':'5'})
        self.api.issues[125]=self.api.issue(125,raw,{'id':9,'login':'maintainer','type':'User'})
        result=self.submit(125)
        self.assertEqual(result['outcome'],'ready')
        record=load_review(get_file(self.api,'o/r','reviews/123.md','codex/review-123'))
        self.assertEqual((record.author_id,record.source_issue,record.submission_issue),(42,123,125))
        check_pr(self.api,'o/r',result['pr'])
    def test_unauthorized_and_conflicting_corrections_rejected(self):
        result=self.submit(); self.api.merge(result['pr'])
        raw=body(**{'Contribution type':'Correction','Original review issue number':'123','Corrected review type':'Scored review'})
        self.api.issues[125]=self.api.issue(125,raw,{'id':8,'login':'stranger','type':'User'})
        self.assertEqual(self.submit(125)['outcome'],'invalid')
        self.api.issues[125]['user']=AUTHOR.copy(); self.submit(125)
        self.api.issues[126]=self.api.issue(126,raw)
        self.assertEqual(self.submit(126)['outcome'],'invalid')
    def test_reconciliation_survives_edit_only_when_input_location_unchanged(self):
        self.submit(); branch='codex/review-123'
        review=load_review(get_file(self.api,'o/r','reviews/123.md',branch))
        changed=replace(review,restaurant_id='a'*64,maps_url='https://maps.app.goo.gl/Canonical')
        commit_files(self.api,'o/r',branch,{'reviews/123.md':dump_review(changed)},'Reconcile restaurant')
        self.api.issues[123]['body']=body(**{'Texture score':'5'}); result=self.submit()
        self.assertEqual(load_review(get_file(self.api,'o/r','reviews/123.md',branch)).restaurant_id,'a'*64)
        check_pr(self.api,'o/r',result['pr'])
        self.api.issues[123]['body']=body(**{'Google Maps link':'https://maps.app.goo.gl/NewPlace'})
        self.submit()
        self.assertNotEqual(load_review(get_file(self.api,'o/r','reviews/123.md',branch)).restaurant_id,'a'*64)
    def test_dry_run_never_mutates(self):
        result=self.submit(dry_run=True)
        self.assertEqual(result['outcome'],'would-create')
        self.assertEqual(self.api.mutations,[])
    def test_noncollaborator_correction_gets_actionable_error(self):
        from scripts.reviews.github import APIError
        result=self.submit(); self.api.merge(result['pr'])
        self.api.issues[125]=self.api.issue(125,body(**{'Contribution type':'Correction','Original review issue number':'123','Corrected review type':'Scored review'}),{'id':8,'login':'stranger','type':'User'})
        request=self.api.request
        def missing_permission(method,path,data=None):
            if '/collaborators/stranger/' in path: raise APIError(404,'not collaborator')
            return request(method,path,data)
        self.api.request=missing_permission
        self.assertEqual(self.submit(125)['outcome'],'invalid')
    def test_branch_conflict_does_not_overwrite_another_commit(self):
        self.submit(); self.api.issues[123]['body']=body(**{'Texture score':'5'})
        self.api.conflict_once=True
        self.assertEqual(self.submit()['outcome'],'invalid')
        self.assertEqual(self.api.refs['codex/review-123'],'concurrent')
        self.assertEqual(self.submit(retry=True)['outcome'],'ready')
    def test_retry_recovers_file_commit_before_failed_pr_creation(self):
        from scripts.reviews.github import APIError
        request=self.api.request
        def unavailable(method,path,data=None):
            if method=='POST' and path.endswith('/pulls'): raise APIError(503,'temporary outage')
            return request(method,path,data)
        self.api.request=unavailable
        with self.assertRaises(APIError): self.submit()
        self.api.request=request
        self.assertEqual(self.submit()['outcome'],'ready')
        self.assertEqual(len(self.api.prs),1)
    def test_form_changes_mid_run_fail_closed(self):
        request=self.api.request
        def change_after_pr(method,path,data=None):
            result=request(method,path,data)
            if method=='POST' and path.endswith('/pulls'):
                self.api.issues[123]['body']=body(**{'Texture score':'1'})
            return result
        self.api.request=change_after_pr
        self.assertEqual(self.submit()['outcome'],'invalid')
        sha=self.api.refs['codex/review-123']
        self.assertEqual(self.api.statuses[sha]['state'],'failure')
