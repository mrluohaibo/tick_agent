from my_akshare.utils.qg_ip_proxy_tool import QingguoProxyIp


class AkshareConfig:
    _instance = None
    useProxy = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.proxies = None
        return cls._instance

    @classmethod
    def set_proxies(cls, proxies):
        cls().proxies = proxies

    @classmethod
    def get_proxies(cls):
        if AkshareConfig.useProxy:
            proxy_ip_port = QingguoProxyIp().random_proxy_ip_port()
        else:
            proxy_ip_port = None

        proxies = None
        if proxy_ip_port is not None:
            proxies = {
                "http": f"http://{proxy_ip_port}"
            }
        set_proxies(proxies)
        return proxies


config = AkshareConfig()


# 导出 set_proxies 函数
def set_proxies(proxies):
    config.set_proxies(proxies)


def get_proxies():
    return config.get_proxies()


class ProxyContext:
    def __init__(self, proxies):
        self.proxies = proxies
        self.old_proxies = None

    def __enter__(self):
        self.proxies = config.get_proxies()
        config.set_proxies(self.proxies)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        config.set_proxies(None)
        return False  # 不处理异常
