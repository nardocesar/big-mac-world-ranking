"""In-memory REST boundary for lifecycle tests; no network or public writes."""
import base64
from copy import deepcopy
from urllib.parse import urlsplit, parse_qs, unquote
from scripts.reviews.github import APIError
from tests.support import AUTHOR, TITLE, body

class FakeGitHub:
    def __init__(self):
        self.issues = {123:self.issue(123)}
        self.prs = {}
        self.comments = {}
        self.statuses = {}
        self.permissions = {'maintainer':'admin', 'traveler':'read'}
        self.refs = {'main':'base'}
        self.commits = {'base':{'sha':'base','tree':{'sha':'tree-base'},'parents':[]}}
        self.trees = {'tree-base':{}}
        self.blobs = {}
        self.mutations = []
        self.n = 0
        self.conflict_once = False

    @staticmethod
    def issue(n, raw=None, user=None):
        return {'number':n,'title':TITLE,'body':raw if raw is not None else body(),'state':'open','user':deepcopy(user or AUTHOR),'html_url':f'https://github.com/o/r/issues/{n}'}

    def list(self,path):
        return self.request('GET',path)

    def request(self,method,path,data=None):
        parsed=urlsplit(path); route=unquote(parsed.path).removeprefix('/repos/o/r'); query=parse_qs(parsed.query)
        if method != 'GET': self.mutations.append((method,path,deepcopy(data)))
        self.n += 1
        if route == '' and method == 'GET': return {'default_branch':'main','owner':{'login':'o'}}
        if route.startswith('/collaborators/'):
            login=route.split('/')[2]; return {'permission':self.permissions.get(login,'read')}
        if route.startswith('/issues/') and not route.startswith('/issues/comments/'):
            parts=route.split('/'); n=int(parts[2])
            if len(parts)==3:
                if method=='PATCH': self.issues[n].update(data)
                return deepcopy(self.issues[n])
            if parts[3]=='comments':
                if method=='GET': return deepcopy(self.comments.get(n,[]))
                item={'id':self.n,'body':data['body'],'user':{'login':'github-actions[bot]','type':'Bot'}}
                self.comments.setdefault(n,[]).append(item); return deepcopy(item)
        if route.startswith('/issues/comments/'):
            id_=int(route.split('/')[-1])
            for comments in self.comments.values():
                for comment in comments:
                    if comment['id']==id_: comment.update(data); return deepcopy(comment)
        if route == '/pulls':
            if method=='POST':
                if any(p['state']=='open' and p['head']['ref']==data['head'] for p in self.prs.values()):
                    raise APIError(422,'A pull request already exists for this branch')
                n=1000+len(self.prs); pr={'number':n,'state':'open','merged_at':None,'merged':False,'title':data['title'],'body':data['body'],'head':{'ref':data['head'],'sha':self.refs[data['head']],'repo':{'full_name':'o/r'}},'base':{'ref':data['base']},'html_url':f'https://github.com/o/r/pull/{n}','user':deepcopy(data.get('user',{'login':'github-actions[bot]','type':'Bot'}))}
                self.prs[n]=pr; return deepcopy(pr)
            prs=list(self.prs.values())
            if 'head' in query: prs=[p for p in prs if p['head']['ref']==query['head'][0].split(':',1)[1]]
            if query.get('state',['all'])[0]!='all': prs=[p for p in prs if p['state']==query['state'][0]]
            return deepcopy(prs)
        if route.startswith('/pulls/'):
            parts=route.split('/'); pr=self.prs[int(parts[2])]
            pr['head']['sha']=self.refs[pr['head']['ref']]
            if len(parts)==4 and parts[3]=='files':
                files=self.trees[self.commits[pr['head']['sha']]['tree']['sha']]
                base=self.trees[self.commits[self.refs['main']]['tree']['sha']]
                return [{'filename':p,'status':'modified' if p in base else 'added'} for p in files if files.get(p)!=base.get(p)]
            if method=='PATCH': pr.update(data)
            return deepcopy(pr)
        if route.startswith('/commits/') and route.endswith('/statuses'):
            sha=route.split('/')[2]; return [self.statuses[sha]] if sha in self.statuses else []
        if route.startswith('/statuses/'):
            sha=route.split('/')[-1]; self.statuses[sha]=deepcopy(data); return deepcopy(data)
        if route.startswith('/git/ref/heads/'):
            branch=route.removeprefix('/git/ref/heads/')
            if branch not in self.refs: raise APIError(404,'not found')
            return {'object':{'sha':self.refs[branch]}}
        if route=='/git/refs' and method=='POST':
            branch=data['ref'].removeprefix('refs/heads/')
            if branch in self.refs: raise APIError(422,'exists')
            self.refs[branch]=data['sha']; return {'object':{'sha':data['sha']}}
        if route.startswith('/git/refs/heads/') and method=='PATCH':
            branch=route.removeprefix('/git/refs/heads/')
            if self.conflict_once:
                self.conflict_once=False
                old=self.refs[branch]; new='concurrent'
                self.commits[new]={'sha':new,'tree':deepcopy(self.commits[old]['tree']),'parents':[{'sha':old}]}
                self.refs[branch]=new
                raise APIError(422,'not fast forward')
            if data['force'] or self.commits[data['sha']]['parents'][0]['sha']!=self.refs[branch]: raise APIError(422,'not fast forward')
            self.refs[branch]=data['sha']; return {'object':{'sha':data['sha']}}
        if route=='/git/trees' and method=='POST':
            sha=f'tree-{self.n}'; tree=deepcopy(self.trees[data['base_tree']])
            for item in data['tree']:
                blob=f'blob-{self.n}-{item["path"].replace(chr(47),chr(45))}'; self.blobs[blob]=item['content']; tree[item['path']]=blob
            self.trees[sha]=tree; return {'sha':sha}
        if route.startswith('/git/trees/'):
            sha=route.split('/')[-1]
            return {'truncated':False,'tree':[{'path':p,'type':'blob','mode':'100644','sha':blob} for p,blob in self.trees[sha].items()]}
        if route=='/git/commits' and method=='POST':
            sha=f'commit-{self.n}'; result={'sha':sha,'tree':{'sha':data['tree']},'parents':[{'sha':p} for p in data['parents']]}
            self.commits[sha]=result; return deepcopy(result)
        if route.startswith('/git/commits/'):
            return deepcopy(self.commits[route.split('/')[-1]])
        if route.startswith('/git/blobs/'):
            text=self.blobs[route.split('/')[-1]]
            return {'encoding':'base64','content':base64.b64encode(text.encode()).decode()}
        if route.startswith('/contents/'):
            p=route.removeprefix('/contents/'); ref=query.get('ref',['main'])[0]; sha=self.refs.get(ref,ref)
            tree=self.trees[self.commits[sha]['tree']['sha']]
            if p not in tree: raise APIError(404,'missing')
            blob=tree[p]; return {'encoding':'base64','content':base64.b64encode(self.blobs[blob].encode()).decode(),'sha':blob,'type':'file'}
        raise AssertionError((method,route,data))

    def merge(self,pr_number):
        pr=self.prs[pr_number]; self.refs['main']=self.refs[pr['head']['ref']]
        pr.update(state='closed',merged=True,merged_at='2026-10-16T00:00:00Z')
