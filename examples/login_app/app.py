import getpass

from flask import Flask, request

from nectar.hiveconnect import HiveConnect

app = Flask(__name__)


c = HiveConnect(client_id="nectarflower", scope="login,vote,custom_json", get_refresh_token=False)
# replace test with our wallet password
wallet_password = getpass.getpass("Wallet-Password:")
c.hive.wallet.unlock(wallet_password)


@app.route("/")
def index():
    """
    Render a link to start the HiveConnect OAuth login flow.
    
    Generates a HiveConnect login URL that redirects to the app's /welcome endpoint and returns a simple HTML anchor users can click to begin authentication.
    
    Returns:
        str: An HTML string with an anchor linking to the HiveConnect login URL.
    """
    login_url = c.get_login_url(
        "http://localhost:5000/welcome",
    )
    return "<a href='%s'>Login with HiveConnect</a>" % login_url


@app.route("/welcome")
def welcome():
    """
    Handle the post-login callback: obtain the user's access token and username, store the token in the Hive wallet under the user's public name, and return a simple welcome message.
    
    This route reads parameters from the incoming request:
    - If `c.get_refresh_token` is truthy, exchanges the provided `code` for tokens via `c.get_access_token(code)` and uses the returned `access_token` and `username`.
    - Otherwise, it uses `access_token` and `username` query parameters; if `username` is missing it sets the current access token on the client and queries the authenticated account with `c.me()`.
    
    Side effects:
    - Removes any existing wallet entry for the resolved username and then saves the new access token with `c.hive.wallet.addToken(name, access_token)`.
    
    Returns:
        A plain HTML string welcoming the user, e.g. "Welcome <strong>{name}</strong>!".
    """
    access_token = request.args.get("access_token", None)
    name = request.args.get("username", None)
    if c.get_refresh_token:
        code = request.args.get("code")
        refresh_token = c.get_access_token(code)
        access_token = refresh_token["access_token"]
        name = refresh_token["username"]
    elif name is None:
        c.set_access_token(access_token)
        name = c.me()["name"]

    if name in c.hive.wallet.getPublicNames():
        c.hive.wallet.removeTokenFromPublicName(name)
    c.hive.wallet.addToken(name, access_token)
    return "Welcome <strong>%s</strong>!" % name
