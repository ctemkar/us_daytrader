from flask import Flask, request
import config.settings as s
import requests
import json
import base64

app = Flask(__name__)

@app.route('/')
def handle_code():
    code = request.args.get('code')
    if code:
        token_url = "https://api.schwab.com/v1/oauth/token"
        auth_str = f"{s.SCHWAB_APP_KEY}:{s.SCHWAB_APP_SECRET}"
        headers = {
            'Authorization': f"Basic {base64.b64encode(auth_str.encode()).decode()}",
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': s.SCHWAB_REDIRECT_URI
        }
        res = requests.post(token_url, headers=headers, data=data)
        if res.status_code == 200:
            with open(s.SCHWAB_TOKEN_PATH, 'w') as f:
                json.dump(res.json(), f)
            return "✅ SUCCESS: Token saved to schwab_token.json. You can close this and start the engine!"
        else:
            return f"❌ ERROR: {res.text}"
    return "Waiting for code..."

if __name__ == '__main__':
    app.run(port=5000)
