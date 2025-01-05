```py


from diwrappers import dependency

# NOTE: EXAMPLES 


# NOTE: non-contextual transient injection

import random

@dependency
def random_int():
    return random.randint(1, 10)


@random_int.inject
def throw_coin(random_int: int) -> t.Literal["heads", "tails"]:
    if random_int <= 5:
        return "heads"
    else:
        return "tails"


# NOTE: non-contextual singleton injection

@dependency
@cache
def token() -> p.SecretStr:
    return p.SecretStr("fake_api_token")

@token.inject
def build_http_headers(token: p.SecretStr):
    return {
        "Authorization": f"Bearer {token.get_secret_value()}"
    }


# chaining injections

import requests
class User(p.BaseModel):
    user_id: int
    name: str

@dependency
@cache
def api_base_url():
    return p.HttpUrl("http://base-url-of-your-app")

@random_int.inject
@token.inject
@api_base_url.inject
def get_random_user(
    # injections
    base_url: p.HttpUrl,
    token: p.SecretStr,
    random_int: int,

    # call signature
    name: str
):

    response = requests.get(
        url= base_url.unicode_string() + "/user",
        json={
            "user_id": random_int,
            "name": name
        },
        headers={
            "authorization": f"Bearer {token.get_secret_value()}"
        }
    )
    response.raise_for_status()
    return p.TypeAdapter(User).validate_json(response.text)


# NOTE: testing

with (
    random_int.fake_value(1234) as fake_int,
    token.fake_value("token_for_test_server"),
    api_base_url.fake_value("http://localhost:8000"),
):
    result = get_random_user(name="test_user")
    assert result.user_id == fake_int

@random_int.faker
def fake_random():
    return random.randint(0, 2)

with fake_random():
    result = get_random_user(name="test_user")
    assert result.user_id in (0, 1, 2)


# chaining dependencies

@dependency
@token.inject
def client(token: p.SecretStr):
    print(token)
    return "client"

@client.inject
def task_using_client(client: str):
    print(client)


# NOTE: framework integration (in this case, FastAPI)

@dependency
def db_token():
    return "fake_db_token"

@app.get("/items/")
@db_token.inject
def read_items(db_token: str):
    return {"message": f"Will connect using to {db_token}"}
```
