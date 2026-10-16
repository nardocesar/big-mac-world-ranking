"""Small GitHub REST boundary. All user content stays JSON data."""
import base64
import json
import os
import re
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urlsplit, parse_qsl
from urllib.request import Request, urlopen

class APIError(RuntimeError):
    def __init__(self, status, message):
        self.status = status
        super().__init__(f'GitHub API {status}: {message}')

class GitHubClient:
    def __init__(self, token: str):
        self.token = token

    def request(self, method: str, path: str, data=None):
        if not path.startswith('/repos/'):
            raise ValueError('Only repository-scoped GitHub API paths are supported.')
        payload = json.dumps(data).encode() if data is not None else None
        request = Request('https://api.github.com' + path, data=payload, method=method,
                          headers={'Authorization':f'Bearer {self.token}','Accept':'application/vnd.github+json',
                                   'X-GitHub-Api-Version':'2022-11-28','User-Agent':'big-mac-world-ranking','Content-Type':'application/json'})
        try:
            with urlopen(request,timeout=30) as response:
                content = response.read()
                return json.loads(content) if content else None
        except HTTPError as exc:
            try:
                message = json.loads(exc.read()).get('message','request failed')
            except (ValueError,AttributeError):
                message = 'request failed'
            finally:
                exc.close()
            raise APIError(exc.code,message) from None

    def list(self, path: str) -> list:
        parsed = urlsplit(path)
        query = dict(parse_qsl(parsed.query))
        results = []
        for page in range(1,1001):
            query.update(per_page=100,page=page)
            batch = self.request('GET',parsed.path+'?'+urlencode(query))
            if not isinstance(batch,list):
                raise APIError(500,'Expected paginated array.')
            results.extend(batch)
            if len(batch)<100:
                return results
        raise APIError(500,'Pagination exceeded safety limit; no partial result was used.')


def environment():
    repo = os.environ.get('GITHUB_REPOSITORY','')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo):
        raise ValueError('GITHUB_REPOSITORY must be owner/repository.')
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if not token:
        raise ValueError('GH_TOKEN or GITHUB_TOKEN is required.')
    return GitHubClient(token), repo


def endpoint(repo, suffix=''):
    return '/repos/'+repo+suffix


def get_ref(client,repo,branch):
    try:
        return client.request('GET',endpoint(repo,'/git/ref/heads/'+quote(branch,safe='')))['object']['sha']
    except APIError as exc:
        if exc.status==404:
            return None
        raise


def get_file(client,repo,path,ref):
    try:
        result=client.request('GET',endpoint(repo,'/contents/'+quote(path,safe='/')+'?'+urlencode({'ref':ref})))
    except APIError as exc:
        if exc.status==404:
            return None
        raise
    if result.get('type')!='file' or result.get('encoding')!='base64':
        raise ValueError('Expected a regular UTF-8 text file smaller than 1 MB.')
    return base64.b64decode(result['content']).decode('utf-8')


def create_commit(client,repo,parent_sha,files,message,extra_parent=None,tree_base=None):
    commit=client.request('GET',endpoint(repo,'/git/commits/'+(tree_base or parent_sha)))
    tree=client.request('POST',endpoint(repo,'/git/trees'),{
        'base_tree':commit['tree']['sha'],
        'tree':[{'path':path,'mode':'100644','type':'blob','content':content} for path,content in sorted(files.items())]})
    parents=[parent_sha]
    if extra_parent and extra_parent!=parent_sha:
        parents.append(extra_parent)
    return client.request('POST',endpoint(repo,'/git/commits'),{'message':message,'tree':tree['sha'],'parents':parents})['sha']


_NO_EXPECTATION = object()

def commit_files(client,repo,branch,files,message,*,base_sha=None,expected_sha=_NO_EXPECTATION):
    current=get_ref(client,repo,branch)
    if expected_sha is not _NO_EXPECTATION and current!=expected_sha:
        raise APIError(409,'The submission branch changed; retry after checking the existing PR.')
    parent=current or base_sha
    if not parent:
        raise ValueError('A base commit is required to create a branch.')
    sha=create_commit(client,repo,parent,files,message,extra_parent=base_sha,tree_base=base_sha)
    if current:
        client.request('PATCH',endpoint(repo,'/git/refs/heads/'+quote(branch,safe='')),{'sha':sha,'force':False})
    else:
        client.request('POST',endpoint(repo,'/git/refs'),{'ref':'refs/heads/'+branch,'sha':sha})
    return sha
