from http.cookies import SimpleCookie


def clear_legacy_refresh_cookie(response):
    """过期删除旧版 Path=/ 的 Cookie，保留新版 Path=/api/ 的 Cookie。"""
    legacy = SimpleCookie()
    legacy['refresh_token'] = ''
    cookie = legacy['refresh_token']
    cookie['path'] = '/'
    cookie['max-age'] = 0
    cookie['expires'] = 'Thu, 01 Jan 1970 00:00:00 GMT'
    cookie['samesite'] = 'Lax'
    # 同名 set_cookie/delete_cookie 会互相覆盖；这里另发一条 Set-Cookie。
    response.headers['Set-Cookie'] = cookie.OutputString()
    return response
