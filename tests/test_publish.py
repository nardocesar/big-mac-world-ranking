import unittest
from scripts.reviews.publish import publish_rankings
from scripts.reviews.github import APIError, get_file, commit_files
from scripts.reviews.intake import handle_issue
from tests.fake_github import FakeGitHub

class PublishTests(unittest.TestCase):
    def setUp(self): self.api=FakeGitHub()
    def test_two_pages_in_one_commit_and_noop_repeat(self):
        before=self.api.refs['main']
        result=publish_rankings(self.api,'o/r')
        self.assertEqual(result['outcome'],'updated')
        self.assertNotEqual(self.api.refs['main'],before)
        self.assertIn('No accepted',get_file(self.api,'o/r','CONTRIBUTORS.md','main'))
        self.assertIn('No scored',get_file(self.api,'o/r','RESTAURANTS.md','main'))
        before=self.api.refs['main']; writes=len(self.api.mutations)
        self.assertEqual(publish_rankings(self.api,'o/r')['outcome'],'unchanged')
        self.assertEqual(before,self.api.refs['main'])
        self.assertEqual(writes,len(self.api.mutations))
    def test_after_merge_ranks_human_and_acknowledges_source(self):
        result=handle_issue(self.api,'o/r',123); self.api.merge(result['pr'])
        publish_rankings(self.api,'o/r')
        self.assertIn('[@traveler]',get_file(self.api,'o/r','CONTRIBUTORS.md','main'))
        self.assertIn('3.80',get_file(self.api,'o/r','RESTAURANTS.md','main'))
        self.assertIn('accepted',self.api.comments[123][0]['body'])
    def test_concurrent_merge_reloads_dataset_without_overwrite(self):
        self.api.conflict_once=True
        self.assertEqual(publish_rankings(self.api,'o/r')['outcome'],'updated')
        final=self.api.commits[self.api.refs['main']]
        self.assertEqual(final['parents'][0]['sha'],'concurrent')
    def test_invalid_dataset_publishes_neither_page(self):
        commit_files(self.api,'o/r','main',{'reviews/123.md':'invalid'},'bad record')
        before=self.api.refs['main']; writes=len(self.api.mutations)
        with self.assertRaises(ValueError): publish_rankings(self.api,'o/r')
        self.assertEqual(before,self.api.refs['main'])
        self.assertEqual(writes,len(self.api.mutations))
    def test_permission_error_is_not_silently_ignored(self):
        request=self.api.request
        def forbidden(method,path,data=None):
            if method=='PATCH' and '/git/refs/' in path: raise APIError(403,'protected branch')
            return request(method,path,data)
        self.api.request=forbidden
        with self.assertRaisesRegex(APIError,'protected branch'): publish_rankings(self.api,'o/r')
    def test_conflicts_stop_after_three_attempts(self):
        request=self.api.request
        def conflicting(method,path,data=None):
            if method=='PATCH' and '/git/refs/' in path: raise APIError(409,'conflict')
            return request(method,path,data)
        self.api.request=conflicting
        with self.assertRaisesRegex(APIError,'3 attempts'): publish_rankings(self.api,'o/r')
