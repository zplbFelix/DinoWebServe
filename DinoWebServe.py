# -*- coding:utf-8 -*-
"""
DinoWebServe.py
Copyright (c) 2025 zplbFelix
License: GPL-3.0

A lightweight web server implementation using Flask
This program is free software under the GNU General Public License v3.0
"""
import datetime
import os
import logging
from flask import Flask, request, make_response, Response
import colorama
import sys
import subprocess
import html
import ast
import requests
from urllib.parse import urlparse

# Initialize colorama for colored console output
colorama.init()


# ================
# Configuration
# ================

class Config:
    """Server configuration with default values"""
    PORT = 80
    ENCODING = 'utf-8'
    WWW_ROOT = './WWW'
    ERROR_DIR = '/error'
    DIR_LISTING = False
    LOG_DIR = './log'
    LOG_RETENTION_DAYS = None
    CONFIG_DIR = "./config"
    
    # Large file download settings
    LARGE_FILE_THRESHOLD = 50 * 1024 * 1024  # 50MB threshold for streaming
    CHUNK_SIZE = 64 * 1024  # 64KB chunks for streaming

    # File type categories
    HTML_EXTENSIONS = ['html', 'htm', 'pys', 'php', 'pp']
    IMAGE_EXTENSIONS = ['bmp', 'gif', 'jpg', 'png', 'jpeg', 'webp', 'svg', 'ico', 'tif', 'tiff']
    VIDEO_EXTENSIONS = ['mp4', 'webm', 'avi', 'mov', 'wmv', 'flv', 'mkv']
    AUDIO_EXTENSIONS = ['mp3', 'wav', 'ogg', 'aac', 'flac', 'm4a']
    FONT_EXTENSIONS = ['ttf', 'otf', 'woff', 'woff2']
    DOWNLOAD_EXTENSIONS = [
        'exe', 'com', 'zip', 'rar', '7z', 'iso', 'jar', 'pdf', 'doc', 'docx',
        'xls', 'xlsx', 'ppt', 'pptx', 'msi', 'dmg', 'pkg', 'deb', 'rpm'
    ]

    # MIME Type Mapping
    MIME_TYPES = {
        # Images
        'bmp': 'image/bmp',
        'gif': 'image/gif',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'webp': 'image/webp',
        'svg': 'image/svg+xml',
        'ico': 'image/x-icon',
        'tif': 'image/tiff',
        'tiff': 'image/tiff',

        # Videos
        'mp4': 'video/mp4',
        'webm': 'video/webm',
        'avi': 'video/x-msvideo',
        'mov': 'video/quicktime',
        'wmv': 'video/x-ms-wmv',
        'flv': 'video/x-flv',
        'mkv': 'video/x-matroska',

        # Audio
        'mp3': 'audio/mpeg',
        'wav': 'audio/wav',
        'ogg': 'audio/ogg',
        'aac': 'audio/aac',
        'flac': 'audio/flac',
        'm4a': 'audio/mp4',

        # Fonts
        'ttf': 'font/ttf',
        'otf': 'font/otf',
        'woff': 'font/woff',
        'woff2': 'font/woff2',

        # Documents
        'pdf': 'application/pdf',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xls': 'application/vnd.ms-excel',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'ppt': 'application/vnd.ms-powerpoint',
        'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',

        # Archives
        'zip': 'application/zip',
        'rar': 'application/x-rar-compressed',
        '7z': 'application/x-7z-compressed',

        # Other
        'json': 'application/json',
        'xml': 'application/xml',
        'js': 'application/javascript',
        'css': 'text/css',
        'txt': 'text/plain',
        'csv': 'text/csv'
    }

    #Python functions or libraries that are prohibited or allowed to run
    DISABLE_PYTHON_FUNCTIONS = []
    ENABLE_PYTHON_LIBRARIES = ['sys', 'os', 'math', 'datetime', 'time', 'random', 'json',
                               're', 'collections', 'subprocess', 'socket', 'urllib',
                               'csv', 'pickle', 'sqlite3', 'hashlib', 'itertools', 'logging',
                               'secret', 'base64', 'email', 'functools', 'glob', 'html',
                               'string', 'shutil', 'smtplib']

    #PHP related content
    PHP_CGI_PATH = "./PHP/php-cgi"


# Try to load custom configuration
if len(sys.argv) > 1:
    Config.CONFIG_DIR = sys.argv[1]
try:
    config_path = os.path.join(Config.CONFIG_DIR, 'config.cfg')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as config_file:
            exec(config_file.read())
        print(colorama.Fore.GREEN + 'Configuration loaded successfully')
    else:
        print(colorama.Fore.YELLOW + 'No config file found, using defaults')
except Exception as e:
    print(colorama.Fore.RED + f'Error loading config: {str(e)}\nUsing default configuration')

try:
    config_path = os.path.join(Config.CONFIG_DIR, 'function.py')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as config_file:
            function_config = config_file.read()
        print(colorama.Fore.GREEN + 'Function loaded successfully')
    else:
        print(colorama.Fore.YELLOW + 'No Function file found, using defaults')
except Exception as e:
    print(colorama.Fore.RED + f'Error loading Function: {str(e)}')

# Initialize Flask app
app = Flask(__name__)

# Suppress Flask logging if possible
try:
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
except:
    print(colorama.Fore.YELLOW + 'Warning: Could not suppress Flask logging')

print(colorama.Fore.RESET)


def get_ip():
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

# ================
# Python Interpreter
# ================

def extract_python_tags(html_content):
    """
    从HTML中提取内容，返回 [("html", ...), ("python", ...), ...] 格式的列表
    """
    def _find_tag_end(html_content, start):
        i = start
        length = len(html_content)
        while i < length:
            c = html_content[i]
            if c == '>':
                return i
            elif c in ('"', "'"):
                quote = c
                i += 1
                while i < length:
                    ch = html_content[i]
                    if ch == quote:
                        break
                    i += 1
            i += 1
        return -1
    def _find_raw_text_end(html_content, i, end_tag):
        length = len(html_content)
        end_tag_len = len(end_tag)
        in_string = False
        string_char = None
        while i < length:
            c = html_content[i]
            if in_string:
                if c == '\\':
                    i += 2
                    continue
                if c == string_char:
                    in_string = False
            else:
                if html_content[i:i + end_tag_len].lower() == end_tag:
                    return i
                if c in ('"', "'", '`'):
                    in_string = True
                    string_char = c
            i += 1
        return -1
    results = []
    i = 0
    length = len(html_content)
    in_comment = False
    in_script = False
    in_style = False
    in_cdata = False
    in_python_tag = False
    python_start = -1
    python_depth = 0
    html_start = 0
    def flush_html(end):
        """将 [html_start, end) 范围内的 HTML 内容追加到结果"""
        nonlocal html_start
        chunk = html_content[html_start:end]
        if chunk:
            results.append(("html", chunk))
        html_start = end
    while i < length:
        if in_cdata:
            if html_content[i:i + 3] == ']]>':
                in_cdata = False
                i += 3
            else:
                i += 1
            continue
        if html_content[i:i + 9] == '<![CDATA[':
            in_cdata = True
            i += 9
            continue
        if in_script:
            end_pos = _find_raw_text_end(html_content, i, '</script>')
            if end_pos == -1:
                break
            in_script = False
            i = end_pos + 9
            continue
        if in_style:
            end_pos = _find_raw_text_end(html_content, i, '</style>')
            if end_pos == -1:
                break
            in_style = False
            i = end_pos + 8
            continue
        if not in_comment and html_content[i:i + 4] == '<!--':
            in_comment = True
            i += 4
            continue
        if in_comment and html_content[i:i + 3] == '-->':
            in_comment = False
            i += 3
            continue
        if in_comment:
            i += 1
            continue
        if not in_script and not in_python_tag and i + 7 <= length:
            tag_check = html_content[i:i + 7].lower()
            if tag_check == '<script' and (
                i + 7 >= length or html_content[i + 7] in ' \t\n\r>/'):
                close = _find_tag_end(html_content, i + 7)
                if close != -1:
                    in_script = True
                    i = close + 1
                else:
                    i += 1
                continue
        if not in_style and not in_python_tag and i + 6 <= length:
            tag_check = html_content[i:i + 6].lower()
            if tag_check == '<style' and (
                i + 6 >= length or html_content[i + 6] in ' \t\n\r>/'):
                close = _find_tag_end(html_content, i + 6)
                if close != -1:
                    in_style = True
                    i = close + 1
                else:
                    i += 1
                continue
        if i + 8 <= length and html_content[i:i + 8].lower() == '<python>':
            if not in_python_tag:
                flush_html(i)
                html_start = i + 8
                in_python_tag = True
                python_start = i + 8
                python_depth = 1
            else:
                python_depth += 1
            i += 8
            continue
        if in_python_tag and i + 9 <= length:
            if html_content[i:i + 9].lower() == '</python>':
                python_depth -= 1
                if python_depth == 0:
                    content = html_content[python_start:i]
                    results.append(("python", content))
                    in_python_tag = False
                    python_start = -1
                    html_start = i + 9
                i += 9
                continue
        i += 1
    if in_python_tag:
        results.append(("python", f'echo("<span class="python-warning">Unclosed <python> tag detected (depth={python_depth}), content discarded.</span>")'))
    else:
        flush_html(length)
    return results

def run_python(text, exec_scope=None):
    try:
        content = ''
        if exec_scope is None:
            exec_scope = {'__builtins__': __builtins__}
        elif '__builtins__' not in exec_scope:
            exec_scope['__builtins__'] = __builtins__

        def new_print(*args, sep=' ', end='\n', file=None, flush=False, output=False):
            nonlocal content
            output_file = file if file is not None else sys.stdout
            text = sep.join(str(arg) for arg in args)
            if output:
                output_file.write(text + end)
                if flush:
                    output_file.flush()
            content += text
        def new_echo(text):
            nonlocal content
            content += str(text)

        def ERROR(*args, **kwargs):
            raise NameError('This function has been disabled')

        func_dict = {}
        try:
            exec(function_config)
            tree = ast.parse(function_config)
            func_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            func_dict = ""
            for func in func_names:
                func_dict += f'"{func}": {func}, '
            func_dict = f"{{{func_dict[:-2]}}}"
            func_dict = eval(func_dict)
        except:
            print(colorama.Fore.RED + 'Function execution failed')
        new = {'print': new_print, 'echo': new_echo}
        for func in func_dict:
            new[func] = func_dict[func]

        for i in new:
            if i in Config.DISABLE_PYTHON_FUNCTIONS:
                continue
            exec_scope[i] = new[i]
        for func in Config.DISABLE_PYTHON_FUNCTIONS:
            exec_scope[func] = ERROR
        for i in Config.ENABLE_PYTHON_LIBRARIES:
            try:
                exec_scope[i] = __import__(i)
            except:
                continue

        exec(text, exec_scope)
    except Exception as e:
        error_msg = html.escape(str(e))
        content = f'<span class="python-error">{error_msg}</span>'
    return content, exec_scope  # 同时返回 exec_scope 供下一个块使用


def extract_all_python_tags(html):
    """Extract the content of all <python> tags from HTML and execute"""
    parse = extract_python_tags(html)
    text = ""
    shared_scope = None
    for s in parse:
        if s[0] == "html":
            text += s[1]
        elif s[0] == "python":
            result, shared_scope = run_python(s[1], shared_scope)
            text += result
    return text

# ================
# PHP Interpreter
# ================


def run_php(filepath, WWW_ROOT):
    filepath = filepath.replace('\\','/')
    filename = filepath.split('/')[-1]
    env = {
        'GATEWAY_INTERFACE': 'CGI/1.1',
        'SERVER_SOFTWARE': 'Flask/DinoWebServe',
        'SERVER_NAME': request.host.split(':')[0],
        'SERVER_PORT': str(request.host.split(':')[1] if ':' in request.host else '80'),
        'SERVER_PROTOCOL': request.environ.get('SERVER_PROTOCOL', 'HTTP/1.1'),
        'REQUEST_URI': request.full_path,
        'REMOTE_ADDR': get_ip(),
        'REMOTE_HOST': get_ip(),
        'SCRIPT_NAME': request.path,
        'SCRIPT_FILENAME': os.path.abspath(filepath),
        'DOCUMENT_ROOT': os.path.abspath(WWW_ROOT),
        'REQUEST_METHOD': request.method,
        'QUERY_STRING': request.query_string.decode('utf-8'),
        'CONTENT_TYPE': request.headers.get('Content-Type', ''),
        'REDIRECT_STATUS': '0', 
        'HTTP_USER_AGENT': request.headers.get('User-Agent', ''),
        'HTTP_ACCEPT': request.headers.get('Accept', ''),
        'HTTP_ACCEPT_LANGUAGE': request.headers.get('Accept-Language', ''),
        'HTTP_ACCEPT_ENCODING': request.headers.get('Accept-Encoding', ''),
        'HTTP_CONNECTION': request.headers.get('Connection', ''),
        'HTTP_HOST': request.headers.get('Host', ''),
        'PATH_INFO': filename,
        **os.environ
    }
    stdin_data = None
    if request.method in ['POST', 'PUT', 'PATCH']:
        content_type = request.content_type
        if 'application/x-www-form-urlencoded' in content_type:
            stdin_data = request.get_data()
        elif 'multipart/form-data' in content_type:
            stdin_data = request.get_data()
        elif 'application/json' in content_type:
            stdin_data = request.get_data()
        else:
            stdin_data = request.get_data()
        env['CONTENT_LENGTH'] = str(len(stdin_data)) if stdin_data else '0'
    app.logger.debug(f"PHP Request: {env}")
    app.logger.debug(f"POST Data: {stdin_data}")
    try:
        result = subprocess.run(
            [Config.PHP_CGI_PATH],
            env=env,
            input=stdin_data if stdin_data else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10
        )

        app.logger.debug(f"PHP Exit Code: {result.returncode}")
        app.logger.debug(f"PHP Output: {result.stdout[:200]}")
        app.logger.debug(f"PHP Error: {result.stderr[:200]}")

        if result.returncode != 0:
            error_msg = result.stderr.decode('utf-8', 'ignore') or "Unknown PHP error"
            return f"PHP Execution Error (Code {result.returncode}): {error_msg}", 500

        output = result.stdout

        if b'\r\n\r\n' in output:
            headers, body = output.split(b'\r\n\r\n', 1)
        else:
            headers = b''
            body = output
        response = Response(body)

        if headers:
            for line in headers.split(b'\r\n'):
                if b':' in line:
                    key, value = line.split(b':', 1)
                    if key.strip().decode().lower() not in ['status', 'connection']:
                        response.headers[key.strip().decode()] = value.strip().decode()

        if 'Content-Type' not in response.headers:
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
        
        return response, body.decode()

    except Exception as e:
        app.logger.error(f"Server Error: {str(e)}")
        return f"Server Error: {str(e)}", 500


# ================
# pp File
# ================

def run_pp(file_path, WWW_ROOT):
    html = run_php(file_path, WWW_ROOT)[1]
    return extract_all_python_tags(html)

# ================
# Helper Functions
# ================

def get_file_extension(path):
    """Extract file extension from path in lowercase"""
    return path.split('.')[-1].lower() if '.' in path else ''


def is_allowed_file(path, extensions):
    """Check if file exists and has allowed extension"""
    ext = get_file_extension(path)
    return os.path.isfile(path) and ext in extensions


def serve_file(path, content_type, WWW_ROOT, as_attachment=False):
    """Serve file with proper Content-Type header"""
    try:
        with open(path, 'rb') as f:
            content = f.read()
    except IOError:
        return serve_error_page(404, WWW_ROOT)

    response = make_response(content)
    response.headers['Content-Type'] = content_type
    if as_attachment:
        filename = os.path.basename(path)
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def serve_large_file(path, content_type, WWW_ROOT, as_attachment=False):
    """Serve large files using streaming to avoid memory issues"""
    try:
        # Get file size for Content-Length header
        file_size = os.path.getsize(path)
        
        # Check if we should use streaming based on file size
        if file_size < Config.LARGE_FILE_THRESHOLD:
            # For smaller files, use the regular function
            return serve_file(path, content_type, WWW_ROOT, as_attachment)
        
        # For large files, use streaming
        def generate():
            with open(path, 'rb') as f:
                while True:
                    chunk = f.read(Config.CHUNK_SIZE)
                    if not chunk:
                        break
                    yield chunk
        
        response = Response(
            generate(),
            mimetype=content_type,
            direct_passthrough=True
        )
        
        # Set headers
        response.headers['Content-Length'] = file_size
        response.headers['Accept-Ranges'] = 'bytes'
        
        if as_attachment:
            filename = os.path.basename(path)
            response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except IOError:
        return serve_error_page(404, WWW_ROOT)


def serve_error_page(status_code, WWW_ROOT):
    """Serve appropriate error page"""
    error_page = (WWW_ROOT+os.path.join(Config.ERROR_DIR.replace('\\','/'), f'{status_code}.html')).replace('\\','/')
    print(error_page)
    if os.path.exists(error_page):
        with open(error_page, 'r', encoding=Config.ENCODING) as f:
            return f.read(), status_code
    return f"Error {status_code}", status_code


def generate_directory_listing(path, url_path, WWW_ROOT):
    """Generate HTML directory listing"""
    if not Config.DIR_LISTING:
        return serve_error_page(403, WWW_ROOT)

    items = []
    parent_dir = os.path.dirname(url_path.rstrip('/'))

    # Add parent directory link
    if parent_dir != url_path:
        items.append('<li><a href="../">Parent Directory</a></li>')

    # Add directory contents
    try:
        for item in sorted(os.listdir(path)):
            item_path = os.path.join(path, item)
            item_url = os.path.join(url_path, item)

            if os.path.isdir(item_path):
                items.append(f'<li><a href="{item_url}/">{item}/</a></li>')
            else:
                items.append(f'<li><a href="{item_url}">{item}</a></li>')
    except OSError:
        return serve_error_page(403, WWW_ROOT)

    listing = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Index of {url_path}</title>
    <style>
        body {{ font-family: sans-serif; line-height: 1.5; }}
        ul {{ list-style-type: none; padding-left: 20px; }}
        a {{ text-decoration: none; color: #0366d6; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>Index of {url_path}</h1>
    <ul>
        {"".join(items)}
    </ul>
</body>
</html>
"""
    return listing

def cleanup_old_logs(days=3):
    """Delete log files older than `days` days"""
    now = datetime.datetime.now()
    cutoff = now - datetime.timedelta(days=days)
    if os.path.exists(Config.LOG_DIR):
        for filename in os.listdir(Config.LOG_DIR):
            file_path = os.path.join(Config.LOG_DIR, filename)
            try:
                log_date_str = filename.replace(".log", "")
                log_date = datetime.datetime.strptime(log_date_str, "%Y-%m-%d")
                if log_date < cutoff:
                    os.remove(file_path)
                    print(f"Deleted old log: {file_path}")
            except Exception as e:
                print(f"Skipping {filename}: {e}")

def log_request():
    """Log request details to file and console"""
    if not os.path.exists(Config.LOG_DIR):
        os.makedirs(Config.LOG_DIR)

    log_date = datetime.datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(Config.LOG_DIR, f'{log_date}.log')

    log_entry = {
        'timestamp': datetime.datetime.now().isoformat(),
        'ip': get_ip(),
        'method': request.method,
        'path': request.path,
        'url': request.url,
        'user_agent': request.headers.get('User-Agent'),
        'status': getattr(request, 'status_code', 200)
    }

    log_str = str(log_entry)
    print(f"\n{log_str}\n")

    with open(log_file, 'a', encoding=Config.ENCODING) as f:
        f.write(log_str + '\n')

    # 每次写日志时顺便清理旧日志
    if Config.LOG_RETENTION_DAYS:
        cleanup_old_logs(days=Config.LOG_RETENTION_DAYS)


# ================
# Request Handlers
# ================

@app.before_request
def before_request():
    """Log all requests"""
    log_request()


@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS'])
def serve(path):
    """Main request handler"""
    if path.startswith(".."):
        return "404", 404
    if isinstance(Config.WWW_ROOT, dict):
        if str(request.host) in Config.WWW_ROOT:
            if Config.WWW_ROOT[str(request.host)].startswith("http"):
                url = f"{Config.WWW_ROOT[str(request.host)]}/{path}"
                real_ip = get_ip()
                # -------- 请求头处理 --------
                headers = dict(request.headers)
                # 强制修复 Host
                headers["Host"] = urlparse(url).netloc
                # 防 gzip 差异（关键）
                headers.pop("Accept-Encoding", None)
                # 覆盖所有客户端可伪造 IP 头
                headers["X-Real-IP"] = real_ip
                headers["X-Forwarded-For"] = real_ip
                headers["X-Forwarded-Proto"] = request.scheme
                # -------- 请求转发 --------
                resp = requests.request(
                    method=request.method,
                    url=url,
                    headers=headers,
                    data=request.stream,
                    cookies=request.cookies,
                    stream=True,
                    allow_redirects=False
                )

                # -------- 响应体（流式）--------
                def generate():
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            yield chunk

                # -------- 响应头处理 --------
                excluded_headers = {
                    "content-encoding",
                    "content-length",
                    "transfer-encoding",
                    "connection",
                }
                response_headers = [
                    (k, v) for k, v in resp.headers.items()
                    if k.lower() not in excluded_headers
                ]
                return Response(
                    generate(),
                    status=resp.status_code,
                    headers=response_headers
                )
            else:
                WWW_ROOT = Config.WWW_ROOT[str(request.host)]
        elif "ELSE" in Config.WWW_ROOT:
            WWW_ROOT = Config.WWW_ROOT["ELSE"]
        else:
            return "<!DOCTYPE html> <html> <head> <title>404 Not Found</title> <style> body { background-color: #fff; color: #000; font-family: Arial, sans-serif; text-align: center; margin-top: 10%; } h1 { font-size: 2em; margin-bottom: 0.5em; } p { color: #555; } </style> </head> <body> <h1>404 Not Found</h1> <p>DinoWebServe</p> </body> </html>", 404
    else:
        WWW_ROOT = Config.WWW_ROOT
    WWW_ROOT = WWW_ROOT.replace('/','\\')
    fs_path = os.path.join(WWW_ROOT, path)
    if os.path.isdir(fs_path):
        # Check for index files
        for index_file in Config.HTML_EXTENSIONS:
            index_path = os.path.join(fs_path, 'index.'+index_file)
            if os.path.exists(index_path):
                if index_file == 'pys':
                    with open(index_path, 'r', encoding=Config.ENCODING) as f:
                        html_content = f.read()
                    return extract_all_python_tags(html_content)
                if index_file == 'php':
                    return run_php(index_path, WWW_ROOT)[1]
                if index_file == 'pp':
                    return run_pp(index_path, WWW_ROOT)
                return serve_file(index_path, 'text/html', WWW_ROOT=WWW_ROOT)
        # Generate directory listing if no index file found
        return generate_directory_listing(fs_path, '/' + path, WWW_ROOT)

    # Handle file requests
    if os.path.isfile(fs_path):
        ext = get_file_extension(fs_path).lower()
        # HTML files
        if ext in Config.HTML_EXTENSIONS:
            if ext == 'pys':
                with open(fs_path, 'r', encoding=Config.ENCODING) as f:
                    html_content = f.read()
                return extract_all_python_tags(html_content)
            if ext == 'php':
                return run_php(fs_path, WWW_ROOT)[1]
            if ext == 'pp':
                return run_pp(fs_path, WWW_ROOT)
            return serve_file(fs_path, 'text/html', WWW_ROOT=WWW_ROOT)

        # Images
        elif ext in Config.IMAGE_EXTENSIONS:
            return serve_large_file(fs_path, Config.MIME_TYPES.get(ext, 'image/' + ext), WWW_ROOT=WWW_ROOT)

        # Videos
        elif ext in Config.VIDEO_EXTENSIONS:
            return serve_large_file(fs_path, Config.MIME_TYPES.get(ext, 'video/' + ext), WWW_ROOT=WWW_ROOT)

        # Audio
        elif ext in Config.AUDIO_EXTENSIONS:
            return serve_large_file(fs_path, Config.MIME_TYPES.get(ext, 'audio/' + ext), WWW_ROOT=WWW_ROOT)

        # Fonts
        elif ext in Config.FONT_EXTENSIONS:
            return serve_large_file(fs_path, Config.MIME_TYPES.get(ext, 'application/octet-stream'), WWW_ROOT=WWW_ROOT)

        # Downloadable files
        elif ext in Config.DOWNLOAD_EXTENSIONS:
            return serve_large_file(fs_path, Config.MIME_TYPES.get(ext, 'application/octet-stream'), as_attachment=True, WWW_ROOT=WWW_ROOT)

        # Other files
        else:
            # Try to determine MIME type or fall back to octet-stream
            mime_type = Config.MIME_TYPES.get(ext, 'application/octet-stream')
            return serve_large_file(fs_path, mime_type, WWW_ROOT=WWW_ROOT)

    # File not found
    return serve_error_page(404, WWW_ROOT)

for code in [400, 401, 403, 404, 405, 406, 408, 409, 410,
             411, 412, 413, 414, 415, 416, 417, 418, 422,
             423, 424, 428, 429, 431, 451, 500, 501, 502,
             503, 504, 505]:
    @app.errorhandler(code)
    def generic_error(e, status_code=code):
        if isinstance(Config.WWW_ROOT, dict):
            if str(request.host) in Config.WWW_ROOT:
                WWW_ROOT = Config.WWW_ROOT[str(request.host)]
            elif "ELSE" in Config.WWW_ROOT:
                WWW_ROOT = Config.WWW_ROOT["ELSE"]
            else:
                return "<!DOCTYPE html> <html> <head> <title>404 Not Found</title> <style> body { background-color: #fff; color: #000; font-family: Arial, sans-serif; text-align: center; margin-top: 10%; } h1 { font-size: 2em; margin-bottom: 0.5em; } p { color: #555; } </style> </head> <body> <h1>404 Not Found</h1> <p>DinoWebServe</p> </body> </html>", 404
        else:
            WWW_ROOT = Config.WWW_ROOT
        return serve_error_page(status_code, WWW_ROOT)

# ================
# Main Execution
# ================

if __name__ == "__main__":
    print(f"Starting server on port {Config.PORT}")
    app.run(host='0.0.0.0', port=Config.PORT)


