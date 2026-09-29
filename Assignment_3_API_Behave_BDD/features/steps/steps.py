from behave import given, when, then

@given('I am connected to the user management API')
def step_connected(context):
    context.user_client = context.client_factory('user_api')
    context.auth_client = context.client_factory('auth_api')
    context.last_response = None

@given('I have API clients ready')
def step_clients_ready(context):
    context.user_client = context.client_factory('user_api')
    context.auth_client = context.client_factory('auth_api')
    context.last_response = None

@when('I fetch the user with id {uid}')
def step_fetch(context, uid):
    r = context.user_client.get(f'users/{uid}')
    context.last_response = r
    context.last_user = r.json()

@then('the user name should be "{name}"')
def step_name(context, name):
    assert context.last_user.get('name') == name, \
        f"expected name {name!r}, got {context.last_user.get('name')!r}"

@then('the user username should be "{username}"')
def step_username(context, username):
    assert context.last_user.get('username') == username, \
        f"expected username {username!r}, got {context.last_user.get('username')!r}"

@then('the response should contain an email field')
def step_has_email(context):
    assert 'email' in context.last_user, "user payload has no email field"

@when('I create a user with name "{name}" and email "{email}"')
def step_create(context, name, email):
    r = context.user_client.post('users', json_body={'name': name, 'email': email})
    context.last_response = r
    context.created_user = r.json()

@then('the create response should be successful')
def step_create_ok(context):
    assert 200 <= context.last_response.status_code < 300, \
        f"create failed with status {context.last_response.status_code}"

@then('a new user id should be assigned')
def step_created_id(context):
    uid = context.created_user.get('id')
    assert isinstance(uid, int) and uid > 0, f"no id assigned in {context.created_user!r}"
    context.last_created_id = uid

@when('I update user {uid}\'s email to "{email}"')
def step_update(context, uid, email):
    r = context.user_client.put(f'users/{uid}', json_body={'email': email})
    context.last_response = r

@then('the update response should be successful')
def step_update_ok(context):
    assert context.last_response.status_code == 200, \
        f"update failed with status {context.last_response.status_code}"

@when('I delete the user with id {uid}')
def step_delete(context, uid):
    r = context.user_client.delete(f'users/{uid}')
    context.last_response = r

@then('the delete response should be successful')
def step_delete_ok(context):
    assert context.last_response.status_code == 200, \
        f"delete failed with status {context.last_response.status_code}"

@when('I request the bearer endpoint without a token')
def step_bearer_no_token(context):
    context.last_response = context.auth_client.get('bearer')

@when('I request the bearer endpoint with the token "{token}"')
def step_bearer_token(context, token):
    context.last_response = context.auth_client.get(
        'bearer', headers={'Authorization': f'Bearer {token}'})

@when('I request basic auth for user "{user}" with password "{password}"')
def step_basic(context, user, password):
    auth = (user, password) if password == 'secret' else None
    context.last_response = context.auth_client.get(
        f'basic-auth/{user}/{password}', auth=auth)

@then('the request should be rejected with status {code:d}')
def step_rejected(context, code):
    assert context.last_response.status_code == code, \
        f"expected {code}, got {context.last_response.status_code}"

@then('the request should be authenticated')
def step_authenticated(context):
    body = context.last_response.json()
    assert body.get('authenticated') is True, f"not authenticated: {body!r}"

@then('the echoed token should be "{token}"')
def step_echoed_token(context, token):
    assert context.last_response.json().get('token') == token

@then('the authenticated user should be "{user}"')
def step_authed_user(context, user):
    assert context.last_response.json().get('user') == user
