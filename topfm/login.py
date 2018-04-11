import asyncio
import webbrowser
from aiohttp import web
from aioauth_client import FacebookClient

FB_APP_ID = "861396037290610"
FB_APP_SECRET = "93e96cff6e14f348f8f93d9f4f06ebb7"


async def facebookLogin():
    host, port = "127.0.0.1", 5088
    endpoint = "/oauth/facebook"

    app = web.Application()
    app.router.add_route('GET', endpoint, _oauth)

    loop = asyncio.get_event_loop()

    server_coro = loop.create_server(app.make_handler(), host, port)
    server = asyncio.ensure_future(server_coro)

    def _shutdown(fut):
        assert fut.done()
        server_coro.close()
        server.cancel()

    app.access_tok_future = asyncio.Future()
    app.access_tok_future.add_done_callback(_shutdown)

    # Give server a chance to start
    await asyncio.sleep(.5)
    webbrowser.open_new(f"http://{host:s}:{port:d}{endpoint:s}")

    await asyncio.wait_for(app.access_tok_future, 45)
    return app.access_tok_future.result()


async def _oauth(request):
    params = {"client_id": FB_APP_ID,
              "client_secret": FB_APP_SECRET,
              "scope": "publish_actions"}
    client = FacebookClient(**params)
    client.params["redirect_uri"] = f"http://{request.host}{request.path}"

    # Check if is not redirect from provider
    if client.shared_key not in request.query:
        # Redirect client to provider
        return web.HTTPFound(client.get_authorize_url())

    access_token = (await client.get_access_token(request.query["code"]))[1]
    user, user_info = await client.user_info()
    access_token["user"] = user_info

    text = f"""
    <html>
    <head><title>Authenticated</title></head>
    <body>
    TopFM login to Facebook (as {user.username}) successful.
    It is safe to close this page.
    </body>
    </html>
    """
    if not request.app.access_tok_future.cancelled():
        request.app.access_tok_future.set_result(access_token)
    return web.Response(text=text, content_type='text/html')
