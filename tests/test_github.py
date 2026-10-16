import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlsplit, parse_qs
from scripts.reviews.github import APIError, GitHubClient

class GitHubTests(unittest.TestCase):
    def test_pagination_reads_past_first_hundred(self):
        def response(req,timeout):
            data=list(range(100)) if parse_qs(urlsplit(req.full_url).query)['page']==['1'] else [100]
            return io.BytesIO(json.dumps(data).encode())
        with patch('scripts.reviews.github.urlopen',response):
            self.assertEqual(len(GitHubClient('test').list('/repos/o/r/pulls?state=all')),101)
    def test_api_error_does_not_expose_token(self):
        with patch('scripts.reviews.github.urlopen',side_effect=HTTPError('https://api.github.com',403,'Forbidden',{},io.BytesIO(b'{"message":"Permission denied"}'))):
            with self.assertRaises(APIError) as caught:
                GitHubClient('private-token').request('GET','/repos/o/r')
            self.assertEqual(caught.exception.status,403)
            self.assertNotIn('private-token',str(caught.exception))
