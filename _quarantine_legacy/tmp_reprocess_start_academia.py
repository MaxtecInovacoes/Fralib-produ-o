import json
import ssl
import urllib.request

ctx = ssl.create_default_context()
base = 'http://localhost:8001'
lead_id = '6ee318c7-bdf9-454a-b206-b90a90e45ec0'
login_data = json.dumps({'email': 'dezigpi@gmail.com', 'password': 'admin123'}).encode()
login_req = urllib.request.Request(base + '/api/auth/login', data=login_data, headers={'Content-Type': 'application/json'}, method='POST')
with urllib.request.urlopen(login_req, context=ctx) as response:
    token = json.loads(response.read())['access_token']
headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
req = urllib.request.Request(base + f'/api/pipeline/reprocessar/{lead_id}', data=json.dumps({}).encode(), headers=headers, method='POST')
with urllib.request.urlopen(req, context=ctx) as response:
    print(response.read().decode())
