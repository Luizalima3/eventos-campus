import subprocess
p = subprocess.run(['git', 'credential', 'fill'], input='protocol=https\nhost=github.com\n\n', capture_output=True, text=True)
line = [l for l in p.stdout.split('\n') if l.startswith('password=')][0]
token = line.split('=', 1)[1]

import json, urllib.request
req = urllib.request.Request(
    'https://api.github.com/user/repos',
    data=json.dumps({'name': 'eventos-campus', 'description': 'Sistema de inscricoes para eventos do campus - RAD IFPB', 'private': False}).encode(),
    headers={'Authorization': f'token {token}', 'Accept': 'application/vnd.github+json', 'User-Agent': 'python'},
)
try:
    with urllib.request.urlopen(req) as r:
        d = json.loads(r.read())
        print('REPO_CRIADO:', d['html_url'])
except urllib.error.HTTPError as e:
    print('ERRO:', e.code, e.read().decode()[:300])
