import json
from app import app


def run():
    client = app.test_client()

    def show(name, ok, info=''):
        print(f"{name}: {'OK' if ok else 'ERROR'}{(' - '+info) if info else ''}")

    # Root
    r = client.get('/', follow_redirects=False)
    show('GET /', r.status_code in (302, 301))

    # Login page
    r = client.get('/login')
    show('GET /login', r.status_code == 200)

    # Invalid login
    r = client.post('/login', data={'pin': '0000'})
    show('POST /login invalid', r.status_code == 200 and b'Falsche PIN' in r.data)

    # Admin login (1593)
    r = client.post('/login', data={'pin': '1593'}, follow_redirects=True)
    show('POST /login admin 1593 -> /admin', r.status_code == 200 and b'Admin Dashboard' in r.data)

    # Add user (create new test user)
    r = client.post('/admin/add_user', data={
        'name': 'autoTest', 'pin': '9999', 'calendar_id': '', 'role': 'user', 'email': 'a@b.c'
    }, follow_redirects=True)
    show('POST /admin/add_user', r.status_code == 200)

    # Check users.json updated
    try:
        users = json.load(open('users.json'))
        show('users.json contains 9999', '9999' in users)
    except Exception as e:
        show('users.json load', False, str(e))

    # Edit user
    r = client.post('/admin/edit_user/9999', data={'name': 'autoTest2', 'calendar_id': '', 'role': 'user', 'email': 'a@b.c'}, follow_redirects=True)
    show('POST /admin/edit_user', r.status_code == 200)

    # Block user
    r = client.post('/admin/block_user/9999', follow_redirects=True)
    show('POST /admin/block_user', r.status_code == 200)

    # Unblock user
    r = client.post('/admin/unblock_user/9999', follow_redirects=True)
    show('POST /admin/unblock_user', r.status_code == 200)

    # Reset modules
    r = client.post('/admin/reset_modules/9999', follow_redirects=True)
    show('POST /admin/reset_modules', r.status_code == 200)

    # Setup flow for user 1234
    r = client.post('/login', data={'pin': '1234'}, follow_redirects=True)
    ok = r.status_code == 200 and (b'Module speichern' in r.data or b'Setup' in r.data or b'Willkommen' in r.data or b'Dashboard' in r.data)
    show('Login 1234 -> setup/dashboard', ok)

    # Submit setup (toggle some modules)
    r = client.post('/setup', data={'calendar': 'on', 'weather': 'on'}, follow_redirects=True)
    show('POST /setup', r.status_code == 200)

    # Dashboard access
    r = client.get('/dashboard')
    show('GET /dashboard', r.status_code in (200, 302))

    # Zug (may call external API) - allow exceptions
    try:
        r = client.get('/zug')
        show('/zug', r.status_code == 200)
    except Exception as e:
        show('/zug', False, str(e))

    # Abfall (may call external ICS)
    try:
        r = client.get('/abfall')
        show('/abfall', r.status_code == 200)
    except Exception as e:
        show('/abfall', False, str(e))

    # PV
    try:
        r = client.get('/pv')
        show('/pv', r.status_code == 200)
    except Exception as e:
        show('/pv', False, str(e))

    print('\nTests finished')


if __name__ == '__main__':
    run()
