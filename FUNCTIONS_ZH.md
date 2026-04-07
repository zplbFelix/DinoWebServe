# DinoWebServe 可用 Python 函数技术文档（.pys）

本页详细介绍在 `.pys` 动态页面中可使用的 Python 函数、其行为、返回值、边界情况与示例。

## 概述
- 执行环境由服务器注入，支持有限的内置函数与请求上下文。
- 可通过配置项限制函数与库的可用性：
  - 禁用函数：`DISABLE_PYTHON_FUNCTIONS`
  - 允许库白名单：`ENABLE_PYTHON_LIBRARIES`

## 输出辅助
- `print(*args, sep=' ', end='\n', file=None, flush=False, output=False)`
  - 作用：将内容同时累积到 HTML 输出；当 `output=True` 时，也写入到目标输出流（默认控制台）
  - 返回值：无
  - 注意：用于 `.pys` 中时，最终会把文本拼接到页面 HTML
  - 示例：
    ```html
    <python>
    print("Hello,", "DinoWebServe")
    </python>
    ```

- `echo(text)`
  - 作用：直接将文本拼接到页面 HTML 输出
  - 返回值：无
  - 示例：
    ```html
    <python>
    echo("<p>直接输出一段 HTML</p>")
    </python>
    ```

## 请求参数
- `get(key=None, default=None)`
  - 作用：获取 GET 查询参数；当 `key=None` 时返回完整字典
  - 返回值：`dict` 或 `str`/`None`
  - 示例：
    ```html
    <python>
    all_params = get()              # {'id': '123', ...}
    id = get("id", "0")             # '123' 或默认值 '0'
    </python>
    ```

- `post(key=None, default=None)`
  - 作用：获取 POST 表单数据；当 `key=None` 时返回完整字典
  - 返回值：`dict` 或 `str`/`None`

- `json(key=None, default=None)`
  - 作用：获取 JSON 请求体；无效或空时返回 `{}`（静默解析）
  - 返回值：`dict` 或任意 JSON 值/默认值
  - 注意：`silent=True`，遇到无效 JSON 不抛错，返回空字典

- `files(key=None, default=(None, None), default_max_size=(None, None), max_size=None)`
  - 作用：获取上传文件。如果提供 `key`：
    - 返回 `(data: bytes, filename: str)`；如果不存在返回 `default`
    - 若设置 `max_size` 且超出大小，返回 `default_max_size`
  - 返回值：文件映射或二元组
  - 示例：
    ```html
    <python>
    data, name = files("avatar", default=(None, None), max_size=2*1024*1024)
    if data:
        echo(f"<p>收到文件：{name}，大小 {len(data)} 字节</p>")
    </python>
    ```
  - 注意：`files()` 会读取文件内容；如果需要直接保存到磁盘，请优先使用 `save_file()`。

## 请求信息
- `method()`：返回 HTTP 方法（如 `GET`、`POST`）
- `host()` / `host_url()` / `base_url()` / `url()` / `full_path()` / `root_url()` / `scheme()`
- `query_string()`：原始查询字符串（字节串或字符串）
- `user_agent()` / `referrer()` / `origin()`
- `accept_languages()` / `accept_mimetypes()`
- `get_data()`：原始请求体（字节串）
- `content_length()` / `content_type()` / `mimetype()` / `is_json()` / `is_secure()` / `if_modified_since()`
- `path()`：当前请求路径

示例：
```html
<python>
echo(f"<p>方法：{method()}</p>")
echo(f"<p>完整 URL：{url()}</p>")
echo(f"<p>是否 JSON：{is_json()}</p>")
</python>
```

## 响应控制
- `set_header(key, value)`
  - 作用：设置响应头（Response Header）
  - 示例：
    ```html
    <python>
    set_header("X-Powered-By", "DinoWebServe")
    </python>
    ```

- `set_content_type(mimetype)`
  - 作用：设置响应的 MIME 类型（Content-Type）
  - 示例：
    ```html
    <python>
    set_content_type("application/xml; charset=utf-8")
    echo("<?xml version='1.0' ?><rss>...</rss>")
    </python>
    ```

## 响应控制
- `set_header(key, value)`
  - 作用：设置响应头（Response Header）
  - 示例：
    ```html
    <python>
    set_header("X-Powered-By", "DinoWebServe")
    </python>
    ```

- `set_content_type(mimetype)`
  - 作用：设置响应的 MIME 类型（Content-Type）
  - 示例：
    ```html
    <python>
    set_content_type("application/xml; charset=utf-8")
    echo("<?xml version='1.0' ?><rss>...</rss>")
    </python>
    ```

## 认证与范围请求
- `auth_basic()`：返回 `(username, password)` 或 `(None, None)`
- `auth_bearer()`：从 `Authorization: Bearer xxx` 提取 token，失败返回 `None`
- `range_bytes()`：返回范围请求的列表 `[(start, end), ...]`，或 `None`

## 头与 Cookie
- `headers(key=None)`
  - 作用：获取请求头；当提供 `key` 时返回对应值，否则返回字典
- `cookies(key=None)`
  - 作用：获取 Cookie；当提供 `key` 时返回对应值，否则返回全部 Cookie 映射

## 客户端 IP
- `remote_addr()`
  - 作用：获取客户端真实 IP
  - 优先级：`CF-Connecting-IP` → `X-Forwarded-For`（取首个）→ `request.remote_addr`
  - 示例：
    ```html
    <python>
    echo(f"<p>你的 IP：{remote_addr()}</p>")
    </python>
    ```

## 文件操作
- `save_file(key, save_path)`
  - 作用：将上传文件保存到指定磁盘路径
  - 返回值：`True`（成功）或 `False`（文件键不存在）
  - 示例：
    ```html
    <python>
    ok = save_file("avatar", "D:/uploads/avatar.png")
    echo("<p>保存结果：{}</p>".format("成功" if ok else "失败"))
    </python>
    ```

## 边界与注意事项
- JSON 解析：`json()` 使用静默模式，异常时返回 `{}`，建议对关键字段做默认值处理
- 文件读取与保存：
  - `files()` 会读取文件内容（流被消费）；若仅需保存请直接使用 `save_file()`
  - 建议设置 `max_size` 进行大小校验，避免过大文件导致内存压力
- 安全限制：
  - 某些函数可能被添加到 `DISABLE_PYTHON_FUNCTIONS` 中而不可用
  - 仅允许在 `ENABLE_PYTHON_LIBRARIES` 白名单内的库被导入使用
- 代理与真实 IP：在多层代理环境下，`X-Forwarded-For` 取首个地址；请确保代理链可信

## 参考
- 函数实现与配置：[function.py](./config/function.py)
- 服务器执行环境与注入： [DinoWebServe.py](./DinoWebServe.py)

