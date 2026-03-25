import urllib.parse
import config.settings as s
params = {
    'response_type': 'code',
    'client_id': s.SCHWAB_APP_KEY,
    'redirect_uri': s.SCHWAB_REDIRECT_URI,
    'scope': 'Trade Account',
    'state': 'quant'
}
url = "https://api.schwab.com/v1/oauth/authorize?" + urllib.parse.urlencode(params)
print(f"\n🔑 AUTHENTICATION REQUIRED\n1. Open: {url}\n2. Login & Authorize\n3. Copy the 'code=' from the redirect URL.")
