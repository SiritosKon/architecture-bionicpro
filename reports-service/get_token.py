import base64, hashlib, os, re, sys, urllib.parse, urllib.request, http.cookiejar

KC = "http://localhost:8080"
REALM = "reports-realm"
CLIENT = "reports-frontend"
REDIRECT = "http://localhost:3000/callback"
user = sys.argv[1] if len(sys.argv) > 1 else "prothetic1"
pwd = sys.argv[2] if len(sys.argv) > 2 else "prothetic123"

verifier = base64.urlsafe_b64encode(os.urandom(40)).rstrip(b"=").decode()
challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

auth = f"{KC}/realms/{REALM}/protocol/openid-connect/auth?" + urllib.parse.urlencode({
    "client_id": CLIENT, "response_type": "code", "scope": "openid",
    "redirect_uri": REDIRECT, "code_challenge": challenge, "code_challenge_method": "S256",
})
html = opener.open(auth).read().decode()
action = re.search(r'action="([^"]+)"', html).group(1).replace("&amp;", "&")

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a): return None
op2 = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), NoRedirect)
data = urllib.parse.urlencode({"username": user, "password": pwd}).encode()
try:
    op2.open(action, data)
    print("ERROR: expected redirect", file=sys.stderr); sys.exit(1)
except urllib.error.HTTPError as e:
    loc = e.headers.get("Location")
code = urllib.parse.parse_qs(urllib.parse.urlparse(loc).query)["code"][0]

tok = urllib.request.urlopen(f"{KC}/realms/{REALM}/protocol/openid-connect/token",
    urllib.parse.urlencode({
        "grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT,
        "client_id": CLIENT, "code_verifier": verifier,
    }).encode()).read().decode()
import json
print(json.loads(tok)["access_token"])
