import json
import urllib.parse

# Load settings directly
with open('config/settings.py') as f:
    exec(f.read())

params = {
    'response_type': 'code',
    'client_id': SCHWAB_APP_KEY,
    'redirect_uri': SCHWAB_REDIRECT_URI,
    'scope': 'Trade Account',
    'state': 'xyz'
}
auth_url = 'https://api.schwab.com/public/oauth2/authorize/?' + urllib.parse.urlencode(params)
print('\n👉 COPY THIS URL TO YOUR BROWSER:\n', auth_url)
