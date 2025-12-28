
import requests
from my_akshare.utils.context import config


class request_proxy_class(requests.Session):
    def __init__(self, base_url=None, default_headers=None):
        super().__init__()
        self.base_url = base_url or ""
        self.session = requests.Session()
        if default_headers:
            self.headers.update(default_headers)

    def request(self, method, url, *args, **kwargs):
        # 自动拼接 base_url（如果 url 是相对路径）
        if not url.startswith(('http://', 'https://')):
            url = self.base_url.rstrip('/') + '/' + url.lstrip('/')

        # 可选：打印日志
        print(f"Sending {method.upper()} to {url}")
        kwargs['proxies'] = config.get_proxies()
        # 调用父类的 request 方法
        return super().request(method, url, *args, **kwargs)


request_proxy = request_proxy_class(

        default_headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"}
    )