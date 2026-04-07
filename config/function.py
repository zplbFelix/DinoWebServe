# ======================
# Request Parameters
# ======================

def get(key=None, default=None):
    """
    Retrieve GET query parameters.
    Returns the full dictionary if key is None, otherwise returns the value for the key.
    """
    if key is None:
        return request.args.to_dict()
    return request.args.get(key, default)


def post(key=None, default=None):
    """
    Retrieve POST form data.
    Returns the full dictionary if key is None, otherwise returns the value for the key.
    """
    if key is None:
        return request.form.to_dict()
    return request.form.get(key, default)


def json(key=None, default=None):
    """
    Retrieve JSON request body data.
    Returns the full dictionary if key is None, otherwise returns the value for the key.
    """
    data = request.get_json(silent=True) or {}
    if key is None:
        return data
    return data.get(key, default)


def files(key=None, default=(None, None), default_max_size=(None, None), max_size=None):
    """
    Retrieve uploaded files.
    If a key is provided, returns (file_data, filename) with optional size validation.
    """
    if key is None:
        return request.files
    file = request.files.get(key)
    if not file:
        return default
    data = file.read()
    if max_size and len(data) > max_size:
        return default_max_size
    return data, file.filename


# ======================
# Request Information
# ======================

def method():
    """
    Get the HTTP request method (e.g., GET, POST).
    """
    return request.method


def host():
    """
    Get the request host.
    """
    return request.host


def host_url():
    """
    Get the request host URL.
    """
    return request.host_url


def base_url():
    """
    Get the request base URL (without query strings).
    """
    return request.base_url


def url():
    """
    Get the full request URL.
    """
    return request.url


def full_path():
    """
    Get the full request path including query strings.
    """
    return request.full_path


def root_url():
    """
    Get the root URL of the application.
    """
    return request.root_url


def scheme():
    """
    Get the URL scheme (http or https).
    """
    return request.scheme


def query_string():
    """
    Get the raw query string.
    """
    return request.query_string


def user_agent():
    """
    Get the client's User-Agent string.
    """
    return request.user_agent


def referrer():
    """
    Get the Referrer header.
    """
    return request.referrer


def origin():
    """
    Get the Origin header.
    """
    return request.origin


def accept_languages():
    """
    Get the list of languages the client accepts.
    """
    return request.accept_languages


def accept_mimetypes():
    """
    Get the list of mimetypes the client accepts.
    """
    return request.accept_mimetypes


def get_data():
    """
    Get the raw request body data.
    """
    return request.get_data()


def content_length():
    """
    Get the Content-Length header.
    """
    return request.content_length


def content_type():
    """
    Get the Content-Type header.
    """
    return request.content_type


def mimetype():
    """
    Get the mimetype from the Content-Type header.
    """
    return request.mimetype


def is_json():
    """
    Check if the request contains JSON data.
    """
    return request.is_json


def is_secure():
    """
    Check if the request was made over a secure (HTTPS) connection.
    """
    return request.is_secure


def if_modified_since():
    """
    Get the If-Modified-Since header.
    """
    return request.if_modified_since


def auth_basic():
    """
    Retrieve HTTP Basic Auth credentials.
    Returns (username, password) or (None, None).
    """
    auth = request.authorization
    if auth:
        return auth.username, auth.password
    return None, None


def auth_bearer():
    """
    Retrieve HTTP Bearer Token from the Authorization header.
    Returns the token string or None.
    """
    header = request.headers.get('Authorization')
    if header and header.startswith('Bearer '):
        return header[7:].strip()
    return None


def range_bytes():
    """
    Retrieve HTTP Range request details.
    Returns a list of tuples [(start, end), ...] or None.
    """
    r = request.range
    if r:
        return r.ranges
    return None


def path():
    """
    Get the current request path.
    """
    return request.path


def headers(key=None):
    """
    Retrieve request headers.
    Returns the full dictionary if key is None, otherwise returns the value for the key.
    """
    if key:
        return request.headers.get(key)
    return dict(request.headers)


def cookies(key=None):
    """
    Retrieve request cookies.
    Returns all cookies if key is None, otherwise returns the value for the key.
    """
    if key:
        return request.cookies.get(key)
    return request.cookies


def remote_addr():
    """
    Retrieve the client's real IP address.
    Supports Cloudflare (CF-Connecting-IP) and standard proxy headers (X-Forwarded-For).
    """
    if request.headers.get('CF-Connecting-IP'):
        return request.headers.get('CF-Connecting-IP')

    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')

    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()

    return request.remote_addr

def set_header(key, value):
    if not hasattr(request, 'custom_headers'):
        request.custom_headers = {}
    request.custom_headers[key] = value

def set_content_type(mimetype):
    set_header('Content-Type', mimetype)

# ======================
# File Operations
# ======================

def save_file(key, save_path):
    """
    Save an uploaded file to a specific disk path.
    Returns True if successful, False if the file key is missing.
    """
    file = request.files.get(key)
    if not file:
        return False
    file.save(save_path)
    return True