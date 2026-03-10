from taosws import Connection

# 测试连接参数 - 使用DSN格式
dsn = "taos://root:Luohb123456@192.168.99.108:6030/stock_tick_info"

print("尝试连接TDengine...")
print(f"DSN: {dsn}")
try:
    # 使用DSN字符串连接
    conn = Connection(dsn)
    print("连接成功!")

    # 尝试简单查询
    result = conn.query("SELECT NOW()")
    print(f"查询结果: {result}")

    conn.close()
except Exception as e:
    print(f"连接失败: {e}")
    import traceback
    traceback.print_exc()