from dataclasses import replace
import unittest
from scripts.reviews.intake import handle_issue
from scripts.reviews.github import get_file, commit_files
from scripts.reviews.model import load_review, dump_review
from scripts.reviews.check import check_pr
from tests.fake_github import FakeGitHub
from tests.support import AUTHOR, body, correction

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
        raw=correction(**{'Texture score':'5'})
        self.api.issues[125]=self.api.issue(125,raw,{'id':9,'login':'maintainer','type':'User'})
        result=self.submit(125)
        self.assertEqual(result['outcome'],'ready')
        record=load_review(get_file(self.api,'o/r','reviews/123.md','codex/review-123'))
        self.assertEqual((record.author_id,record.source_issue,record.submission_issue),(42,123,125))
        check_pr(self.api,'o/r',result['pr'])
    def test_unauthorized_and_conflicting_corrections_rejected(self):
        result=self.submit(); self.api.merge(result['pr'])
        raw=correction()
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
        self.api.issues[125]=self.api.issue(125,correction(),{'id':8,'login':'stranger','type':'User'})
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
    def test_validation_status_covers_maintainer_reconciliation_commit(self):
        from scripts.reviews.check import check_with_status
        result=self.submit(); branch='codex/review-123'
        review=load_review(get_file(self.api,'o/r','reviews/123.md',branch))
        sha=commit_files(self.api,'o/r',branch,{'reviews/123.md':dump_review(replace(review,restaurant_id='b'*64))},'Reconcile restaurant')
        check_with_status(self.api,'o/r',result['pr'])
        self.assertEqual(self.api.statuses[sha]['state'],'success')
    def test_check_detects_tampered_review_and_fails_its_status(self):
        from scripts.reviews.check import check_with_status
        result=self.submit(); branch='codex/review-123'
        review=load_review(get_file(self.api,'o/r','reviews/123.md',branch))
        sha=commit_files(self.api,'o/r',branch,{'reviews/123.md':dump_review(replace(review,scores={**review.scores,'Texture':1}))},'Unrelated manual change')
        with self.assertRaises(ValueError): check_with_status(self.api,'o/r',result['pr'])
        self.assertEqual(self.api.statuses[sha]['state'],'failure')
    def test_validator_cannot_overwrite_newer_invalid_form_status(self):
        from unittest.mock import patch
        import scripts.reviews.check as checks
        result=self.submit(); original=checks.check_pr
        def interleave(*args):
            review=original(*args)
            self.api.issues[123]['body']=body(**{'Texture score':'6'})
            self.submit()
            return review
        with patch.object(checks,'check_pr',interleave):
            with self.assertRaises(ValueError): checks.check_with_status(self.api,'o/r',result['pr'])
        self.assertEqual(self.api.statuses[self.api.refs['codex/review-123']]['state'],'failure')
    def test_expected_absence_does_not_overwrite_new_branch(self):
        from scripts.reviews.github import APIError
        self.submit(); original=self.api.refs['codex/review-123']
        with self.assertRaises(APIError):
            commit_files(self.api,'o/r','codex/review-123',{'reviews/123.md':'overwritten'},'stale writer',base_sha=self.api.refs['main'],expected_sha=None)
        self.assertEqual(self.api.refs['codex/review-123'],original)
    def test_error_feedback_does_not_activate_untrusted_markdown(self):
        self.api.issues[123]['body']=body(**{'Overall experience':'Fine\n\n### [Click here](https://attacker.example) @maintainer\n\nHello'})
        self.assertEqual(self.submit()['outcome'],'invalid')
        text=self.api.comments[123][0]['body']
        self.assertNotIn('[Click here](https://attacker.example)',text)
        self.assertNotIn(' @maintainer',text)
    def test_new_correction_retains_accepted_grouping_even_if_branch_deleted(self):
        result=self.submit(); branch='codex/review-123'
        record=load_review(get_file(self.api,'o/r','reviews/123.md',branch))
        canonical=replace(record,restaurant_id='c'*64,maps_url='https://maps.app.goo.gl/Canonical')
        commit_files(self.api,'o/r',branch,{'reviews/123.md':dump_review(canonical)},'Reconcile')
        self.api.merge(result['pr']); del self.api.refs[branch]
        self.api.issues[125]=self.api.issue(125,correction(**{'Texture score':'5'}))
        self.assertEqual(self.submit(125)['outcome'],'ready')
        corrected=load_review(get_file(self.api,'o/r','reviews/123.md',branch))
        self.assertEqual((corrected.restaurant_id,corrected.maps_url),('c'*64,'https://maps.app.goo.gl/Canonical'))
    def test_invalid_combined_dataset_cannot_receive_success(self):
        from scripts.reviews.check import check_with_status
        result=self.submit(); branch='codex/review-123'
        record=load_review(get_file(self.api,'o/r','reviews/123.md',branch))
        commit_files(self.api,'o/r',branch,{'reviews/123.md':dump_review(replace(record,maps_url='https://maps.app.goo.gl/Canonical'))},'Reconcile')
        self.api.merge(result['pr'])
        self.api.issues[124]=self.api.issue(124)
        result=self.submit(124)
        self.assertEqual(result['outcome'],'invalid')
        pr=max(self.api.prs)
        with self.assertRaises(ValueError): check_with_status(self.api,'o/r',pr)
        self.assertEqual(self.api.statuses[self.api.refs['codex/review-124']]['state'],'failure')
    def test_nonreview_pr_gets_applicable_required_status(self):
        from scripts.reviews.check import check_with_status
        commit_files(self.api,'o/r','codex/docs',{'README.md':'Documentation'},'Docs',base_sha=self.api.refs['main'])
        pr=self.api.request('POST','/repos/o/r/pulls',{'head':'codex/docs','base':'main','title':'Docs','body':'Docs only'})
        check_with_status(self.api,'o/r',pr['number'])
        self.assertEqual(self.api.statuses[self.api.refs['codex/docs']]['state'],'success')
    def test_lock_resolution_uses_existing_pr_when_correction_target_is_invalid(self):
        from scripts.reviews.intake import resolve_source_issue
        result=self.submit(); self.api.merge(result['pr'])
        self.api.issues[125]=self.api.issue(125,correction())
        self.submit(125)
        self.api.issues[125]['body']=correction('wrong')
        self.assertEqual(resolve_source_issue(self.api,'o/r',125),123)
    def test_competing_correction_cannot_take_over_prepared_branch(self):
        from scripts.reviews.github import APIError
        result=self.submit(); self.api.merge(result['pr']); del self.api.refs['codex/review-123']
        for n in (125,126):
            self.api.issues[n]=self.api.issue(n,correction(**{'Texture score':'5' if n==126 else '1'}))
        request=self.api.request
        raced=False
        def interleave(method,path,data=None):
            nonlocal raced
            if not raced and method=='GET' and '/git/ref/heads/codex%2Freview-123' in path:
                raced=True
                self.submit(126)
                raise APIError(404,'Earlier read saw absent branch')
            return request(method,path,data)
        self.api.request=interleave
        self.assertEqual(self.submit(125)['outcome'],'invalid')
        record=load_review(get_file(self.api,'o/r','reviews/123.md','codex/review-123'))
        self.assertEqual((record.submission_issue,record.scores['Texture']),(126,5))
    def test_title_edit_updates_label_and_stale_title_fails_check(self):
        result=self.submit()
        record=load_review(get_file(self.api,'o/r','reviews/123.md','codex/review-123'))
        self.assertEqual(record.restaurant_label,"McDonald's at 1 Main St, Springfield, IL, USA")
        self.api.issues[123]['title']="[Review] McDonald's at 2 Main St"
        with self.assertRaises(ValueError): check_pr(self.api,'o/r',result['pr'])
        self.submit()
        record=load_review(get_file(self.api,'o/r','reviews/123.md','codex/review-123'))
        self.assertEqual(record.restaurant_label,"McDonald's at 2 Main St")
        check_pr(self.api,'o/r',result['pr'])
    def maintenance_pr(self,user,files):
        commit_files(self.api,'o/r','codex/migrate',files,'Migrate',base_sha=self.api.refs['main'])
        return self.api.request('POST','/repos/o/r/pulls',{'head':'codex/migrate','base':'main','title':'Migrate','body':'Schema migration','user':user})['number']
    def accepted_record(self):
        result=self.submit(); self.api.merge(result['pr'])
        return load_review(get_file(self.api,'o/r','reviews/123.md','main'))
    def test_maintainer_maintenance_pr_with_valid_dataset_gets_success(self):
        from scripts.reviews.check import check_with_status
        record=self.accepted_record()
        pr=self.maintenance_pr({'login':'maintainer','type':'User'},{'reviews/123.md':dump_review(replace(record,restaurant_label='Fixed label')),'README.md':'Docs'})
        check_with_status(self.api,'o/r',pr)
        status=self.api.statuses[self.api.refs['codex/migrate']]
        self.assertEqual(status['state'],'success'); self.assertIn('Maintenance',status['description'])
    def test_maintenance_pr_accepts_newer_schema_it_cannot_parse(self):
        from scripts.reviews.check import check_with_status
        self.accepted_record()
        pr=self.maintenance_pr({'login':'maintainer','type':'User'},{'reviews/123.md':'---\n{"schema_version": 99}\n---\n'})
        check_with_status(self.api,'o/r',pr)
        self.assertEqual(self.api.statuses[self.api.refs['codex/migrate']]['state'],'success')
    def test_maintenance_pr_rejected_for_nonwriter_or_fork(self):
        from scripts.reviews.check import check_with_status
        record=self.accepted_record()
        cases=[({'login':'traveler','type':'User'},dump_review(record),False),
               ({'login':'maintainer','type':'User'},dump_review(record),True)]
        for user,text,fork in cases:
            with self.subTest(user=user['login'],fork=fork):
                self.api.refs.pop('codex/migrate',None)
                for pr in self.api.prs.values():
                    if pr['head']['ref']=='codex/migrate': pr['state']='closed'
                pr=self.maintenance_pr(user,{'reviews/123.md':text,'README.md':'Docs '+str(fork)})
                if fork: self.api.prs[pr]['head']['repo']['full_name']='attacker/r'
                with self.assertRaises(ValueError): check_with_status(self.api,'o/r',pr)
                self.assertEqual(self.api.statuses[self.api.refs['codex/migrate']]['state'],'failure')
