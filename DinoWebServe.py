#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
DinoWebServe.py
Copyright (c) 2025 zplbFelix
License: GPL-3.0

A lightweight web server implementation using Flask
This program is free software under the GNU General Public License v3.0
"""
from flask import Flask, request, make_response, Response, send_file
from urllib.parse import urlparse
import subprocess
import functools
import threading
import colorama
import builtins
import datetime
import requests
import tempfile
import logging
import sqlite3
import shutil
import queue
import glob
import html
import sys
import io
import os

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

    # Performance settings
    THREADS = 32  # waitress worker threads
    CONSOLE_LOG = True  # print request logs to console (done in a background thread)
    STATIC_MAX_AGE = 3600  # Cache-Control max-age for static files (HTML always 0)

    # How pys scripts get a per-thread working directory:
    #   'auto'   - Linux: real per-thread cwd via unshare(CLONE_FS) if the system allows it,
    #              otherwise (and on Windows/macOS) patch the common file APIs
    #   'native' - like auto, but warn loudly if the native method is unavailable
    #   'patch'  - always patch the file APIs
    CWD_MODE = 'auto'

    # Large file download settings (kept for compatibility; send_file handles streaming/Range)
    LARGE_FILE_THRESHOLD = 50 * 1024 * 1024  # 50MB threshold for streaming
    CHUNK_SIZE = 64 * 1024  # 64KB chunks for streaming

    # File type categories
    HTML_EXTENSIONS = ['html', 'htm', 'pys']
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

    # Python functions or libraries that are prohibited or allowed to run
    DISABLE_PYTHON_FUNCTIONS = []
    ENABLE_PYTHON_LIBRARIES = ['sys', 'os', 'math', 'datetime', 'time', 'random', 'json',
                               're', 'collections', 'subprocess', 'socket', 'urllib',
                               'csv', 'pickle', 'sqlite3', 'hashlib', 'itertools', 'logging',
                               'secret', 'base64', 'email', 'functools', 'glob', 'html',
                               'string', 'shutil', 'smtplib']


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

# function.py: compiled once at startup, exec'd per request into a fresh scope
function_config = ""
FUNCTION_CODE = None
try:
    config_path = os.path.join(Config.CONFIG_DIR, 'function.py')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as config_file:
            function_config = config_file.read()
        FUNCTION_CODE = compile(function_config, config_path, 'exec')
        print(colorama.Fore.GREEN + 'Function loaded successfully')
    else:
        print(colorama.Fore.YELLOW + 'No Function file found, using defaults')
except Exception as e:
    print(colorama.Fore.RED + f'Error loading Function: {str(e)}')

# Libraries made available to pys scripts: imported once at startup
_LIBS = {}
for _lib_name in Config.ENABLE_PYTHON_LIBRARIES:
    try:
        _LIBS[_lib_name] = __import__(_lib_name)
    except Exception:
        continue

# Initialize Flask app
app = Flask(__name__, static_folder=None)
_http_session = requests.Session()

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
# Per-thread working directory (patches)
# ================
# There is no per-thread cwd on Windows, so instead of os.chdir() (process-wide)
# we patch the common file APIs: while a pys script runs, relative paths are
# resolved against that script's directory, stored in a thread-local variable.
# Threads that are not running pys code (_tls.cwd is None) see no difference.

_tls = threading.local()
_real_getcwd = os.getcwd
_real_chdir = os.chdir
_real_isabs = os.path.isabs
_real_join = os.path.join
_real_abspath = os.path.abspath

# keyword names that carry a path
_PATH_KEYS = ('file', 'path', 'top', 'name', 'src', 'dst', 'database')


def _resolve(p):
    d = getattr(_tls, 'cwd', None)
    if d is None:
        return p
    if isinstance(p, os.PathLike):
        p = os.fspath(p)
    if isinstance(p, str) and not _real_isabs(p):
        return _real_join(d, p)
    return p


def _wrap(fn, n=1, default=None):
    """Wrap fn so that its first n positional args (and common path kwargs) are resolved."""

    @functools.wraps(fn)
    def w(*a, **k):
        if getattr(_tls, 'cwd', None) is not None and k.get('dir_fd') is None:
            a = list(a)
            for i in range(min(n, len(a))):
                a[i] = _resolve(a[i])
            has_kw = False
            for key in _PATH_KEYS:
                if key in k:
                    k[key] = _resolve(k[key])
                    has_kw = True
            if default is not None and not a and not has_kw:
                a.append(_resolve(default))
        return fn(*a, **k)

    return w


def install_cwd_patches():
    # built-in open (pathlib's Path.open goes through io.open as well)
    builtins.open = _wrap(builtins.open)
    io.open = builtins.open

    # os: single-path functions
    for name in ('stat', 'lstat', 'remove', 'unlink', 'mkdir', 'makedirs',
                 'rmdir', 'removedirs', 'chmod', 'utime', 'open'):
        if hasattr(os, name):
            setattr(os, name, _wrap(getattr(os, name)))
    # os.walk() and glob call os.scandir/os.listdir internally, so patching these covers them
    os.listdir = _wrap(os.listdir, default='.')
    os.scandir = _wrap(os.scandir, default='.')

    # os: two-path functions
    for name in ('rename', 'replace'):
        setattr(os, name, _wrap(getattr(os, name), n=2))

    # os.path
    for name in ('exists', 'lexists', 'isfile', 'isdir', 'islink', 'getsize',
                 'getmtime', 'getctime', 'abspath', 'realpath'):
        if hasattr(os.path, name):
            setattr(os.path, name, _wrap(getattr(os.path, name)))

    # getcwd / chdir operate on the thread-local directory while a pys script runs
    def getcwd():
        d = getattr(_tls, 'cwd', None)
        return d if d is not None else _real_getcwd()

    def chdir(p):
        if getattr(_tls, 'cwd', None) is not None:
            _tls.cwd = _real_abspath(_resolve(p))
        else:
            _real_chdir(p)

    os.getcwd = getcwd
    os.chdir = chdir

    # shutil
    for name in ('copy', 'copy2', 'copyfile', 'move', 'copytree'):
        setattr(shutil, name, _wrap(getattr(shutil, name), n=2))
    shutil.rmtree = _wrap(shutil.rmtree)

    # glob
    _real_glob = glob.glob

    @functools.wraps(_real_glob)
    def _glob(pattern, *a, **k):
        d = getattr(_tls, 'cwd', None)
        if d is not None and sys.version_info >= (3, 10) and 'root_dir' not in k \
                and isinstance(pattern, str) and not _real_isabs(pattern):
            k['root_dir'] = d
        return _real_glob(pattern, *a, **k)

    glob.glob = _glob

    # sqlite3
    _real_connect = sqlite3.connect

    @functools.wraps(_real_connect)
    def connect(database, *a, **k):
        if isinstance(database, (str, os.PathLike)):
            s = os.fspath(database)
            if isinstance(s, str) and s != ':memory:' and not s.startswith('file:'):
                database = _resolve(s)
        return _real_connect(database, *a, **k)

    sqlite3.connect = connect

    # subprocess: default cwd (subprocess.run/call/check_output all go through Popen)
    _Popen = subprocess.Popen

    class Popen(_Popen):
        def __init__(self, *a, **k):
            d = getattr(_tls, 'cwd', None)
            if k.get('cwd') is None and d is not None:
                k['cwd'] = d
            super().__init__(*a, **k)

    subprocess.Popen = Popen


# ---- Linux: a real per-thread cwd ----
# On Linux a thread can stop sharing its cwd with the other threads of the process by calling
# unshare(CLONE_FS). After that, os.chdir() in this thread only affects this thread, and *every*
# file API (sqlite3, subprocess, ctypes libraries, ...) sees the right directory, so no API
# patching is needed. Some containers/sandboxes block the syscall (seccomp), so we probe it at
# startup and fall back to the patches above when it does not work.

_CLONE_FS = 0x00000200
_libc = None


def _detect_native_thread_cwd():
    """Return True if per-thread cwd via unshare(CLONE_FS) really works on this system."""
    global _libc
    if not sys.platform.startswith('linux'):
        return False
    try:
        import ctypes
        libc = ctypes.CDLL(None, use_errno=True)
        libc.unshare.argtypes = [ctypes.c_int]
        libc.unshare.restype = ctypes.c_int
    except Exception:
        return False

    try:
        orig = os.getcwd()
    except OSError:
        return False
    probe_dir = tempfile.mkdtemp(prefix='dws-probe-')
    result = {'ok': False}

    def probe():
        try:
            if libc.unshare(_CLONE_FS) != 0:
                return  # blocked (EPERM etc.); do NOT chdir, that would affect the whole process
            os.chdir(probe_dir)
            result['ok'] = True
        except Exception:
            pass

    t = threading.Thread(target=probe, name='cwd-probe')
    t.start()
    t.join()

    try:
        isolated = os.getcwd() == orig  # the chdir in the probe thread must not leak
    except OSError:
        isolated = False
    if not isolated:
        try:
            os.chdir(orig)
        except OSError:
            pass
    try:
        os.rmdir(probe_dir)
    except OSError:
        pass

    if result['ok'] and isolated:
        _libc = libc
        return True
    return False


def _ensure_thread_fs():
    """Give the current thread its own cwd (once per thread). Returns True on success."""
    ok = getattr(_tls, 'fs_unshared', None)
    if ok is None:
        ok = _libc.unshare(_CLONE_FS) == 0
        _tls.fs_unshared = ok
        if ok:
            _tls.base_cwd = os.getcwd()
    return ok


_cwd_mode = str(getattr(Config, 'CWD_MODE', 'auto')).lower()
NATIVE_CWD = False
if _cwd_mode in ('auto', 'native'):
    NATIVE_CWD = _detect_native_thread_cwd()
    if _cwd_mode == 'native' and not NATIVE_CWD:
        print(colorama.Fore.YELLOW + 'CWD_MODE=native requested but unshare(CLONE_FS) is not available here, '
                                     'falling back to patched file APIs' + colorama.Fore.RESET)

if NATIVE_CWD:
    print(colorama.Fore.GREEN + 'pys working directory: native per-thread cwd (unshare CLONE_FS)'
          + colorama.Fore.RESET)
else:
    install_cwd_patches()
    print(colorama.Fore.GREEN + 'pys working directory: patched file APIs' + colorama.Fore.RESET)


def _enter_script_dir(script_dir):
    """Make relative paths resolve against script_dir in the current thread."""
    if not script_dir:
        return
    if NATIVE_CWD:
        if _ensure_thread_fs():
            os.chdir(script_dir)
    else:
        _tls.cwd = script_dir


def _leave_script_dir():
    """Undo _enter_script_dir (always called, even after errors)."""
    if NATIVE_CWD:
        if getattr(_tls, 'fs_unshared', False):
            try:
                os.chdir(_tls.base_cwd)
            except OSError:
                pass
    else:
        _tls.cwd = None


# ================
# Python Interpreter
# ================

def extract_python_tags(html_content):
    """
    Extract <python> tag from HTML, return the format: [("html", ...), ("python", ...), ...]
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
        """Add [html_start, end) to the result"""
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
        results.append(("python",
                        f"echo('<span class=\"python-warning\">Unclosed &lt;python&gt; tag detected (depth={python_depth}), content discarded.</span>')"))
    else:
        flush_html(length)
    return results


def _dedent_block(text):
    """Remove the indentation of the first non-empty line from every line of the block"""
    lines = text.split("\n")
    first = next((l for l in lines if l.strip()), None)
    if first is None:
        return ""
    g = first[:len(first) - len(first.lstrip(' \t'))]
    if not g:
        return text
    return "\n".join(l[len(g):] if l.startswith(g) else l for l in lines)


# Parsed + compiled pys files, keyed by path and invalidated by mtime
_pys_cache = {}
_pys_cache_lock = threading.Lock()


def load_pys(path):
    """Return [("html", str), ("python", code_object), ...] for a pys file (cached)."""
    mtime = os.stat(path).st_mtime_ns
    cached = _pys_cache.get(path)
    if cached and cached[0] == mtime:
        return cached[1]

    with open(path, 'r', encoding=Config.ENCODING) as f:
        parts = extract_python_tags(f.read())

    compiled = []
    for kind, content in parts:
        if kind == "python":
            try:
                compiled.append(("python", compile(_dedent_block(content), path, 'exec')))
            except SyntaxError as e:
                err = html.escape(f'{e.msg} (line {e.lineno})')
                compiled.append(("html", f'<span class="python-error">{err}</span>'))
        else:
            compiled.append(("html", content))

    with _pys_cache_lock:
        _pys_cache[path] = (mtime, compiled)
    return compiled


def run_python(code, exec_scope=None, script_dir=None):
    """Execute one compiled <python> block. Relative file paths resolve against script_dir."""
    content = ''
    try:
        _enter_script_dir(script_dir)
        if exec_scope is None:
            exec_scope = {
                '__builtins__': __builtins__,
                'request': request,
                'app': app,
                'Config': Config
            }
            if script_dir:
                exec_scope['PYS_DIR'] = script_dir
            if FUNCTION_CODE is not None:
                try:
                    exec(FUNCTION_CODE, exec_scope)
                except Exception as e:
                    print(colorama.Fore.RED + f'Function execution failed: {str(e)}')

        def new_print(*args, sep=' ', end='\n', file=None, flush=False, output=False):
            nonlocal content
            output_file = file if file is not None else sys.stdout
            text_str = sep.join(str(arg) for arg in args)
            if output:
                output_file.write(text_str + end)
                if flush:
                    output_file.flush()
            content += text_str

        def new_echo(text_val):
            nonlocal content
            content += str(text_val)

        def ERROR(*args, **kwargs):
            raise NameError('This function has been disabled')

        exec_scope['print'] = new_print
        exec_scope['echo'] = new_echo

        for func in Config.DISABLE_PYTHON_FUNCTIONS:
            exec_scope[func] = ERROR

        for lib_name, lib in _LIBS.items():
            exec_scope.setdefault(lib_name, lib)

        exec(code, exec_scope)
    except Exception as e:
        error_msg = html.escape(str(e))
        content = f'<span class="python-error">{error_msg}</span>'
    finally:
        _leave_script_dir()  # always restore
    return content, exec_scope  # 同时返回 exec_scope 供下一个块使用


def serve_pys(path, WWW_ROOT):
    """Run a pys file and build the response"""
    try:
        parts = load_pys(path)
    except OSError:
        return serve_error_page(404, WWW_ROOT)

    script_dir = os.path.dirname(os.path.abspath(path))
    text = []
    shared_scope = None
    for kind, item in parts:
        if kind == "html":
            text.append(item)
        else:
            result, shared_scope = run_python(item, shared_scope, script_dir)
            text.append(result)

    response = make_response("".join(text))
    if hasattr(request, 'custom_headers'):
        for k, v in request.custom_headers.items():
            response.headers[k] = v
    return response


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
    """Serve a file with ETag / 304 / Range support (send_file streams from disk)"""
    try:
        is_html = content_type.startswith('text/html')
        return send_file(
            os.path.abspath(path),
            mimetype=content_type,
            as_attachment=as_attachment,
            download_name=os.path.basename(path),
            conditional=True,
            max_age=0 if is_html else Config.STATIC_MAX_AGE
        )
    except OSError:
        return serve_error_page(404, WWW_ROOT)


# send_file already streams large files, so one function is enough
serve_large_file = serve_file


def _unsafe_path(path):
    """True for request paths that must never reach the file system (.. segments, NUL bytes)"""
    if '\x00' in path:
        return True
    return any(seg == '..' for seg in path.replace('\\', '/').split('/'))


def _is_within(root, target):
    """True if target stays inside root (lexical check, symlinks inside the root are still allowed)"""
    root = os.path.abspath(root)
    target = os.path.abspath(target)
    try:
        return os.path.commonpath([root, target]) == root
    except ValueError:  # e.g. different drives on Windows
        return False


def serve_error_page(status_code, WWW_ROOT):
    """Serve appropriate error page"""
    error_page = os.path.join(WWW_ROOT, Config.ERROR_DIR.strip('/\\'), f'{status_code}.html')
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


# ================
# Logging (asynchronous)
# ================
# Request threads only put a dict on a queue; a background thread does the
# console printing, file writing and old-log cleanup (at most once per day).

_log_queue = queue.Queue()


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


def _log_worker():
    last_cleanup_date = None
    try:
        os.makedirs(Config.LOG_DIR, exist_ok=True)
    except OSError:
        pass
    while True:
        entry = _log_queue.get()
        try:
            log_str = str(entry)
            if Config.CONSOLE_LOG:
                print(f"\n{log_str}\n")

            log_date = entry['timestamp'][:10]
            os.makedirs(Config.LOG_DIR, exist_ok=True)
            log_file = os.path.join(Config.LOG_DIR, f'{log_date}.log')
            with open(log_file, 'a', encoding=Config.ENCODING) as f:
                f.write(log_str + '\n')

            # Clean the log only once a day.
            if Config.LOG_RETENTION_DAYS and last_cleanup_date != log_date:
                last_cleanup_date = log_date
                cleanup_old_logs(days=Config.LOG_RETENTION_DAYS)
        except Exception as e:
            try:
                print(colorama.Fore.RED + f'Log error: {e}' + colorama.Fore.RESET)
            except Exception:
                pass


threading.Thread(target=_log_worker, name='log-worker', daemon=True).start()


def log_request():
    """Queue request details for the logging thread"""
    _log_queue.put({
        'timestamp': datetime.datetime.now().isoformat(),
        'ip': get_ip(),
        'method': request.method,
        'path': request.path,
        'url': request.url,
        'user_agent': request.headers.get('User-Agent'),
        'status': getattr(request, 'status_code', 200)
    })


# ================
# Request Handlers
# ================

def forward_request(url, path, query_string):
    url = f"{Config.WWW_ROOT[url]}/{path}"
    if query_string:
        url += f"?{query_string.decode()}"
    real_ip = get_ip()
    # -------- Header processing --------
    headers = dict(request.headers)
    # repair Host
    headers["Host"] = urlparse(url).netloc
    # prevent gzip differences
    headers.pop("Accept-Encoding", None)
    # covers all IP-related header
    headers["X-Real-IP"] = real_ip
    headers["X-Forwarded-For"] = real_ip
    headers["X-Forwarded-Proto"] = request.scheme
    # -------- forward request --------
    resp = _http_session.request(
        method=request.method,
        url=url,
        headers=headers,
        data=request.stream,
        cookies=request.cookies,
        stream=True,
        allow_redirects=False
    )

    # -------- response --------
    def generate():
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                yield chunk

    # -------- Header processing --------
    excluded_headers = {
        'connection',
        'keep-alive',
        'proxy-authenticate',
        'proxy-authorization',
        'te',
        'trailers',
        'transfer-encoding',
        'upgrade',
        'content-length',
        'content-encoding',
        'server',
        'x-powered-by'
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


@app.before_request
def before_request():
    """Log all requests"""
    log_request()


@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS'])
def serve(path):
    """Main request handler"""
    if _unsafe_path(path):
        return "404", 404
    if isinstance(Config.WWW_ROOT, dict):
        if str(request.host) in Config.WWW_ROOT:
            if Config.WWW_ROOT[str(request.host)].startswith("http"):
                return forward_request(str(request.host), path, request.query_string)
            else:
                WWW_ROOT = Config.WWW_ROOT[str(request.host)]
        elif "ELSE" in Config.WWW_ROOT:
            if Config.WWW_ROOT["ELSE"].startswith("http"):
                return forward_request(str(request.host), path, request.query_string)
            else:
                WWW_ROOT = Config.WWW_ROOT["ELSE"]
        else:
            return "<!DOCTYPE html> <html> <head> <title>404 Not Found</title> <style> body { background-color: #fff; color: #000; font-family: Arial, sans-serif; text-align: center; margin-top: 10%; } h1 { font-size: 2em; margin-bottom: 0.5em; } p { color: #555; } </style> </head> <body> <h1>404 Not Found</h1> <p>DinoWebServe</p> </body> </html>", 404
    else:
        WWW_ROOT = Config.WWW_ROOT

    WWW_ROOT = os.path.normpath(WWW_ROOT)
    fs_path = os.path.join(WWW_ROOT, path)
    if not _is_within(WWW_ROOT, fs_path):  # e.g. an absolute path like /etc/passwd
        return "404", 404

    # Try dynamic extension mapping (e.g., access rss.xml -> rss.xml.pys)
    if not os.path.exists(fs_path):
        for dynamic_ext in ['pys']:
            if os.path.isfile(fs_path + '.' + dynamic_ext):
                fs_path = fs_path + '.' + dynamic_ext
                break

    # Try wildcard mapping (e.g., access post/abc -> post.{}.pys)
    if not os.path.exists(fs_path):
        try:
            # We look for a file that matches the prefix and has {}
            parts = path.replace('\\', '/').split('/')
            for i in range(len(parts) + 1):
                dir_rel = "/".join(parts[:i])
                full_dir = os.path.join(WWW_ROOT, dir_rel)
                if not os.path.isdir(full_dir):
                    break

                match_name = "/".join(parts[i:])
                if not match_name:
                    continue

                for item in os.listdir(full_dir):
                    if '{}.' in item:
                        prefix, rest = item.split('{}.', 1)
                        # Remove trailing dot for flexible prefix matching
                        clean_prefix = prefix.rstrip('.')
                        ext = get_file_extension(item).lower()
                        if ext in Config.HTML_EXTENSIONS and match_name.startswith(clean_prefix):
                            fs_path = os.path.join(full_dir, item)
                            break
                if os.path.isfile(fs_path):
                    break
        except:
            pass

    if os.path.isdir(fs_path):
        # Check for index files
        found_index_path = None
        found_index_ext = None

        # 1. Try standard index files first (exact matches like index.pys)
        for ext in Config.HTML_EXTENSIONS:
            test_path = os.path.join(fs_path, 'index.' + ext)
            if os.path.isfile(test_path):
                found_index_path = test_path
                found_index_ext = ext
                break

        # 2. Try extended index files (index.*.pys)
        if not found_index_path:
            try:
                candidates = []
                for item in os.listdir(fs_path):
                    if item.startswith('index.') and os.path.isfile(os.path.join(fs_path, item)):
                        ext = get_file_extension(item).lower()
                        if ext in Config.HTML_EXTENSIONS:
                            candidates.append((item, ext))
                if candidates:
                    # Sort candidates to ensure deterministic behavior (shortest first)
                    candidates.sort(key=lambda x: (len(x[0]), x[0]))
                    best_name, best_ext = candidates[0]
                    found_index_path = os.path.join(fs_path, best_name)
                    found_index_ext = best_ext
            except Exception as e:
                app.logger.error(f"Error listing directory for index files: {e}")

        if found_index_path:
            if found_index_ext == 'pys':
                return serve_pys(found_index_path, WWW_ROOT)
            return serve_file(found_index_path, 'text/html', WWW_ROOT=WWW_ROOT)
        # Generate directory listing if no index file found
        return generate_directory_listing(fs_path, '/' + path, WWW_ROOT)

    # Handle file requests
    if os.path.isfile(fs_path):
        ext = get_file_extension(fs_path).lower()
        # HTML files
        if ext in Config.HTML_EXTENSIONS:
            if ext == 'pys':
                return serve_pys(fs_path, WWW_ROOT)
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
            return serve_large_file(fs_path, Config.MIME_TYPES.get(ext, 'application/octet-stream'), as_attachment=True,
                                    WWW_ROOT=WWW_ROOT)

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
    try:
        try:
            from waitress import serve as waitress_serve

            waitress_serve(app, host='0.0.0.0', port=Config.PORT,
                           threads=Config.THREADS, ident='DinoWebServe')
        except ImportError:
            print(colorama.Fore.YELLOW + 'waitress not installed (pip install waitress), '
                                         'falling back to the Flask development server'
                  + colorama.Fore.RESET)
            app.run(host='0.0.0.0', port=Config.PORT, threaded=True)
    except PermissionError:
        if os.name == 'posix' and Config.PORT < 1024:
            print(colorama.Fore.RED + f'Permission denied for port {Config.PORT}: ports below 1024 need root on Linux.\n'
                                      '  - use a port >= 1024 (and proxy with nginx / Cloudflare), or\n'
                                      '  - run: sudo setcap cap_net_bind_service=+ep "$(readlink -f "$(which python3)")", or\n'
                                      '  - run: sudo sysctl net.ipv4.ip_unprivileged_port_start=80'
                  + colorama.Fore.RESET)
            sys.exit(1)
        raise