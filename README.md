# WebAliveScan_plus

WebAliveScan 是一个高效的Web存活扫描工具，用于快速检测目标网站的存活状态、端口开放情况，并识别网站的应用技术栈。

## 安装
```bash
pip3 install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

## 功能特性

### 核心功能
- ✅ 批量网站存活检测
- ✅ 多端口扫描支持
- ✅ 自定义并发线程数
- ✅ 快速目录扫描
- ✅ 应用指纹识别
- ✅ 结果导出为CSV

### 最新优化
- 🚀 **连接池与会话管理**：提高并发扫描效率
- 🛡️ **智能重试机制**：自动重试失败请求，增强稳定性
- 📊 **扫描进度条**：直观显示扫描进度
- 🌐 **中文编码支持**：完美解决中文标题乱码问题
- 🎨 **优化输出样式**：更清晰的扫描结果展示
- 🔍 **多级域名处理**：智能提取主域名，避免重复扫描
- 📝 **修复编码错误**：解决CSV文件保存时的编码问题
-  ⚡ **优化线程设置**：降低默认线程数，提高稳定性
- 🎯 **启用HEAD请求**：默认使用HEAD请求，提高扫描效率
- 🚦 **扫描速度控制**：添加请求间隔，避免对目标服务器造成过大压力
- 📋 **结果去重功能**：确保每个URL只出现在结果中一次
- 📖 **完善规则加载**：修复测试页面规则未加载问题
- 🛑 **黑名单规则支持**：可以过滤不需要的扫描结果
- 📄 **异常日志记录**：详细记录扫描过程中的异常信息

## 使用帮助

### 基本使用
```bash
# 扫描指定目标文件中的网站，使用默认端口
python3 webscan.py --target target.txt --port default

# 使用大端口集合扫描
python3 webscan.py --target target.txt --port large
```

### 自定义线程数
```bash
# 使用20个线程进行扫描
python3 webscan.py --target target.txt --port default --threads 20
```

### 自定义端口
```bash
# 使用指定端口扫描
python3 webscan.py --target target.txt --port 80,443,8080
```

### 单个目标自定义端口
```bash
python3 webscan.py --target target.txt --port 80

target.txt内容示例：
# 扫描--port指定的80端口
www.google.com

# 扫描www.baidu.com的443端口（覆盖--port参数）
www.baidu.com:443
```

### 快速目录扫描
```bash
# 启用快速目录扫描功能
python3 webscan.py --target target.txt --port 80 --brute True

# 目录扫描规则可在rules.py中配置
```

## 配置说明

### config.py配置选项
```python
# 忽略指定的HTTP状态码
ignore_status_code = [400]

# 默认线程数量（已优化为更合理的100）
threads = 100

# 目录扫描线程数
thread_count = 30

# 超时时间（秒）
timeout = 10

# 忽略SSL证书验证
verify_ssl = False

# 是否使用HEAD请求提高效率（已默认启用）
use_head_request = True

# 请求间隔（秒），用于控制扫描速度
request_delay = 0.1

# 日志配置
log_level = 'DEBUG'  # 日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL
log_path = 'scan.log'  # 日志文件路径
```

## 端口集合说明

工具内置了多种端口集合，方便快速选择：
- `default`：{80} - 默认Web端口
- `small`：{80, 443, 8000, 8080, 8443} - 精选常用端口
- `medium`：{80, 81, 443, 591, 2082, 2087, 2095, 2096, 3000, 8000, 8001, 8008, 8080, 8083, 8443, 8834, 8888} - 中等规模端口集合
- `large`：包含50+常用Web端口 - 全面端口集合

## 扫描结果示例

```
[█████████████████████████████████████████████░░░░░] 90% (73/81)
[17:48:49] URL[http://geniuneoverseas.taobao.com] Status[200] Size[4KB] Title[首页-瑞妈代购铺-淘宝网] Server[Tengine]
```

## 版本历史

- v1.0：初始版本，基本存活扫描功能
- v1.1：增加忽略指定HTTP状态码功能
- v1.2：增加单个目标自定义端口功能
- v1.3：增加快速目录扫描功能
- v1.4：增加简单的指纹识别、修改输出样式
- v1.5：优化中文编码支持、添加连接池和重试机制
- v1.6：增加扫描进度条、优化整体性能
- v1.7：
  - 修复CSV文件保存时的编码错误
  - 优化多级域名处理，智能提取主域名
  - 降低默认线程数，提高稳定性
  - 启用HEAD请求默认设置
  - 添加扫描速度控制
  - 实现结果去重功能
  - 修复测试页面规则未加载问题
  - 添加黑名单规则支持
  - 实现异常日志记录功能

**注意**：原作者已停止更新，最新版采用Golang编写。项目地址：https://github.com/broken5/bscan
