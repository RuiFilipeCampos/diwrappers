# Examples 

## non-contextual transient injection

```py

from diwrappers import dependency
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
```

## non-contextual singleton injection

```py
@dependency
@cache
def token() -> p.SecretStr:
    return p.SecretStr("fake_api_token")

@token.inject
def build_http_headers(token: p.SecretStr):
    return {
        "Authorization": f"Bearer {token.get_secret_value()}"
    }
```



## chaining injections
```py
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

```


## chaining dependencies

```py
@dependency
@token.inject
def client(token: p.SecretStr):
    print(token)
    return "client"

@client.inject
def task_using_client(client: str):
    print(client)
```

## framework integration (in this case, FastAPI)

```py
@dependency
def db_token():
    return "fake_db_token"

@app.get("/items/")
@db_token.inject
def read_items(db_token: str):
    return {"message": f"Will connect using to {db_token}"}
```


## testing

### built in context manager for faking constants

```py
with (
    random_int.fake_value(1234) as fake_int,
    token.fake_value("token_for_test_server"),
    api_base_url.fake_value("http://localhost:8000"),
):
    result = get_random_user(name="test_user")
    assert result.user_id == fake_int
```

### construct fake data dynamically

```py
@random_int.faker
def fake_random():
    return random.randint(0, 2)

with fake_random():
    result = get_random_user(name="test_user")
    assert result.user_id in (0, 1, 2)
```


# Soon

## contextual dependency injection (allowing scoped session, scoped request, etc)

## async support
