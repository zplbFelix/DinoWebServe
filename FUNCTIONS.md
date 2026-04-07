# DinoWebServe Python Functions Technical Reference (.pys)

This page documents the Python functions available in `.pys` dynamic pages, including behavior, return values, edge cases, and examples.

## Overview
- The execution environment is injected by the server, exposing selected built-ins and request context.
- Function/library availability is controlled via configuration:
  - Disabled functions: `DISABLE_PYTHON_FUNCTIONS`
  - Allowed library whitelist: `ENABLE_PYTHON_LIBRARIES`

## Output Helpers
- `print(*args, sep=' ', end='\n', file=None, flush=False, output=False)`
  - Purpose: Collect text into HTML output; when `output=True`, also write to the target stream (console by default)
  - Returns: None
  - Note: In `.pys`, text is appended to the final page HTML
  - Example:

    ```html
    <python>
    print("Hello,", "DinoWebServe")
    </python>
    ```

- `echo(text)`
  - Purpose: Append text directly into the page HTML output
  - Returns: None
  - Example:

    ```html
    <python>
    echo("<p>Direct HTML output</p>")
    </python>
    ```

## Request Parameters
- `get(key=None, default=None)`
  - Purpose: Retrieve GET query parameters; returns full dict when `key=None`
  - Returns: `dict` or `str`/`None`
  - Example:

    ```html
    <python>
    all_params = get()              # {'id': '123', ...}
    id = get("id", "0")             # '123' or default '0'
    </python>
    ```

- `post(key=None, default=None)`
  - Purpose: Retrieve POST form data; returns full dict when `key=None`
  - Returns: `dict` or `str`/`None`

- `json(key=None, default=None)`
  - Purpose: Retrieve JSON request body; invalid/empty returns `{}` (silent parsing)
  - Returns: `dict` or any JSON value/default
  - Note: `silent=True`; invalid JSON does not raise, returns empty dict

- `files(key=None, default=(None, None), default_max_size=(None, None), max_size=None)`
  - Purpose: Retrieve uploaded file. When `key` is provided:
    - Returns `(data: bytes, filename: str)`; if missing, returns `default`
    - If `max_size` set and exceeded, returns `default_max_size`
  - Returns: file mapping or tuple
  - Example:

    ```html
    <python>
    data, name = files("avatar", default=(None, None), max_size=2*1024*1024)
    if data:
        echo(f"<p>Received file: {name}, size {len(data)} bytes</p>")
    </python>
    ```
  - Note: `files()` reads file content; prefer `save_file()` to write directly to disk.

## Request Information
- `method()` – HTTP method (`GET`, `POST`, etc.)
- `host()` / `host_url()` / `base_url()` / `url()` / `full_path()` / `root_url()` / `scheme()`
- `query_string()` – raw query string (bytes or string)
- `user_agent()` / `referrer()` / `origin()`
- `accept_languages()` / `accept_mimetypes()`
- `get_data()` – raw request body (bytes)
- `content_length()` / `content_type()` / `mimetype()` / `is_json()` / `is_secure()` / `if_modified_since()`
- `path()` – current request path

Example:

```html
<python>
echo(f"<p>Method: {method()}</p>")
echo(f"<p>Full URL: {url()}</p>")
echo(f"<p>Is JSON: {is_json()}</p>")
</python>
```

## Response Control
- `set_header(key, value)`
  - Purpose: Set a response header
  - Example:
    ```html
    <python>
    set_header("X-Powered-By", "DinoWebServe")
    </python>
    ```

- `set_content_type(mimetype)`
  - Purpose: Set the response MIME type (Content-Type)
  - Example:
    ```html
    <python>
    set_content_type("application/xml; charset=utf-8")
    echo("<?xml version='1.0' ?><rss>...</rss>")
    </python>
    ```

## Authentication & Range Requests
- `auth_basic()` – returns `(username, password)` or `(None, None)`
- `auth_bearer()` – extracts token from `Authorization: Bearer xxx`, returns `None` if missing
- `range_bytes()` – returns range list `[(start, end), ...]` or `None`

## Headers & Cookies
- `headers(key=None)`
  - Purpose: Retrieve headers; when `key` provided returns specific value, otherwise dict
- `cookies(key=None)`
  - Purpose: Retrieve cookies; when `key` provided returns specific value, otherwise cookie mapping

## Client IP
- `remote_addr()`
  - Purpose: Get client’s real IP
  - Priority: `CF-Connecting-IP` → `X-Forwarded-For` (first item) → `request.remote_addr`
  - Example:

    ```html
    <python>
    echo(f"<p>Your IP: {remote_addr()}</p>")
    </python>
    ```

## File Operations
- `save_file(key, save_path)`
  - Purpose: Save an uploaded file to a disk path
  - Returns: `True` (success) or `False` (missing file key)
  - Example:

    ```html
    <python>
    ok = save_file("avatar", "D:/uploads/avatar.png")
    echo("<p>Save result: {}</p>".format("Success" if ok else "Failed"))
    </python>
    ```

## Edge Cases & Notes
- JSON parsing: `json()` uses silent mode; invalid JSON returns `{}`. Provide sensible defaults for required fields.
- File reading vs saving:
  - `files()` reads content (consumes stream); use `save_file()` if you only need to save.
  - Set `max_size` to guard against large uploads impacting memory.
- Security restrictions:
  - Functions may be disabled via `DISABLE_PYTHON_FUNCTIONS`
  - Only libraries in `ENABLE_PYTHON_LIBRARIES` can be imported
- Proxies & real IP: In multi-proxy setups, `X-Forwarded-For` uses the first IP; ensure trusted proxy chain.

## References
- Function implementations & configuration: [function.py](./config/function.py)
- Server execution environment & injection: [DinoWebServe.py](./DinoWebServe.py)

