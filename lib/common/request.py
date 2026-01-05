from gevent import monkey, pool; monkey.patch_all()
from lib.utils.FileUtils import *
import config
import chardet
import time
import random
import urllib3
import requests
import os
import re
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
urllib3.disable_warnings()


class Request:
    def __init__(self, target, port, output, wappalyzer, threads=None):
        self.output = output
        self.wappalyzer = wappalyzer
        self.url_list = self.gen_url_list(target, port)
        self.total = len(self.url_list)
        # 使用自定义线程数或配置文件中的默认值
        self.threads = threads if threads is not None else config.threads
        self.output.config(self.threads, self.total)
        self.output.target(target)
        self.index = 0
        self.alive_path = config.result_save_path.joinpath('%s_alive_results.csv' % str(time.time()).split('.')[0])
        self.brute_path = config.result_save_path.joinpath('%s_brute_results.csv' % str(time.time()).split('.')[0])
        self.alive_result_list = []
        
        # 创建会话，实现连接池和重试机制
        self.session = requests.Session()
        retry_strategy = Retry(
            total=2,  # 总重试次数
            status_forcelist=[429, 500, 502, 503, 504],  # 需要重试的状态码
            allowed_methods=["HEAD", "GET"],  # 允许重试的HTTP方法
            backoff_factor=0.1,  # 重试间隔时间因子（1秒，2秒，4秒...）
            raise_on_status=False
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=100,  # 连接池大小
            pool_maxsize=100       # 每个主机的最大连接数
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.main()

    def get_main_domain(self, domain):
        """
        提取主域名
        :param domain: 完整域名
        :return: 主域名（如 example.com）
        """
        # 移除协议和端口
        domain = re.sub(r'^https?://', '', domain)
        domain = re.sub(r':\d+$', '', domain)
        
        # 处理多级域名，提取主域名
        parts = domain.split('.')
        if len(parts) >= 3:
            # 检查是否为特殊顶级域名（如 .co.uk, .com.cn 等）
            special_tlds = ['co', 'com', 'org', 'net', 'edu', 'gov', 'mil', 'int', 'biz', 'info', 'name', 'pro', 'aero', 'coop', 'museum', 'cn', 'jp', 'au', 'in', 'us', 'de', 'fr', 'ru', 'ca', 'it', 'es']
            # 检查是否为二级顶级域名（如 .com.cn, .net.cn 等）
            two_level_tlds = ['.'.join(parts[-2:]) for parts in [
                ['com', 'cn'], ['net', 'cn'], ['org', 'cn'], ['edu', 'cn'], ['gov', 'cn'],
                ['co', 'uk'], ['org', 'uk'], ['gov', 'uk'], ['ac', 'uk'],
                ['co', 'jp'], ['ne', 'jp'], ['go', 'jp'], ['ac', 'jp'],
                ['com', 'au'], ['net', 'au'], ['org', 'au'],
                ['co', 'in'], ['net', 'in'], ['org', 'in'],
                ['com', 'us'], ['net', 'us'], ['org', 'us'],
                ['com', 'de'], ['net', 'de'], ['org', 'de'],
                ['com', 'fr'], ['net', 'fr'], ['org', 'fr'],
                ['com', 'ru'], ['net', 'ru'], ['org', 'ru'],
                ['com', 'ca'], ['net', 'ca'], ['org', 'ca'],
                ['com', 'it'], ['net', 'it'], ['org', 'it'],
                ['com', 'es'], ['net', 'es'], ['org', 'es']
            ]]
            
            domain_part = '.'.join(parts[-2:])
            if domain_part in two_level_tlds:
                # 例如：subdomain.example.com.cn -> example.com.cn
                main_domain = '.'.join(parts[-3:])
            elif parts[-2] in special_tlds and len(parts) > 3:
                # 例如：subdomain.example.co.uk -> example.co.uk
                main_domain = '.'.join(parts[-3:])
            else:
                # 例如：subdomain.example.com -> example.com
                main_domain = '.'.join(parts[-2:])
        else:
            main_domain = domain
        
        return main_domain
    
    def gen_url_by_port(self, domain, port):
        protocols = ['http://', 'https://']
        if port == 80:
            url = f'http://{domain}'
            return url
        elif port == 443:
            url = f'https://{domain}'
            return url
        else:
            url = []
            for protocol in protocols:
                url.append(f'{protocol}{domain}:{port}')
            return url

    def gen_url_list(self, target, port):
        """
        根据目标文件和端口配置生成URL列表
        :param target: 目标文件路径或单个目标字符串
        :param port: 端口配置（整数、端口组名称或端口列表）
        :return: URL列表
        """
        try:
            # 处理目标输入：可以是文件路径或单个目标字符串
            if os.path.isfile(target):
                with open(target, 'r', encoding='utf-8') as f:
                    domain_list = f.readlines()
            else:
                # 单个目标情况
                domain_list = [target]

            # 获取端口配置
            ports = set()
            if isinstance(port, (set, list, tuple)):
                ports = set(port)
            elif isinstance(port, int):
                if 0 <= port <= 65535:
                    ports = {port}
            elif isinstance(port, str):
                if port in {'default', 'small', 'medium', 'large'}:
                    ports = config.ports.get(port, set())
                else:
                    # 处理单个端口字符串
                    try:
                        port_num = int(port)
                        if 0 <= port_num <= 65535:
                            ports = {port_num}
                    except ValueError:
                        pass
            
            # 默认端口设置
            if not ports:
                ports = {80}

            # 生成URL列表，添加主域名去重
            url_list = []
            processed_combinations = set()  # 用于去重的集合，存储(主域名, 端口)组合
            
            for domain in domain_list:
                domain = domain.strip()
                if not domain:  # 跳过空行
                    continue
                    
                main_domain = self.get_main_domain(domain)
                
                if ':' in domain:
                    # 单个目标指定端口
                    try:
                        domain_part, port_part = domain.split(':', 1)
                        port_num = int(port_part)
                        main_domain_part = self.get_main_domain(domain_part)
                        # 检查是否已经处理过该主域名和端口的组合
                        combination = (main_domain_part, port_num)
                        if combination not in processed_combinations:
                            processed_combinations.add(combination)
                            url = self.gen_url_by_port(domain_part, port_num)
                            if isinstance(url, list):
                                url_list.extend(url)
                            else:
                                url_list.append(url)
                    except (ValueError, IndexError) as e:
                        self.output.debug(f"解析目标{domain}失败: {e}")
                        continue
                else:
                    # 应用端口组
                    for port_num in ports:
                        # 检查是否已经处理过该主域名和端口的组合
                        combination = (main_domain, port_num)
                        if combination not in processed_combinations:
                            processed_combinations.add(combination)
                            url = self.gen_url_by_port(domain, port_num)
                            if isinstance(url, list):
                                url_list.extend(url)
                            else:
                                url_list.append(url)
                    
            return url_list
        except FileNotFoundError as e:
            self.output.error(f"目标文件不存在: {e}")
            return []
        except Exception as e:
            self.output.error(f"生成URL列表失败: {e}")
            return []

    def request(self, url, method='GET'):
        """
        发送HTTP请求并处理响应
        :param url: 请求的URL
        :param method: 请求方法（GET或HEAD）
        :return: 响应对象或None
        """
        try:
            if method.upper() == 'HEAD':
                r = self.session.head(url, timeout=config.timeout, headers=self.get_headers(), 
                                verify=config.verify_ssl, cookies=self.get_cookies(),
                                allow_redirects=config.allow_redirects)
                # HEAD请求只检查状态码，不进行详细分析
                if r.status_code not in config.ignore_status_code:
                    url_info = {
                        'url': url,
                        'title': '',
                        'status': r.status_code,
                        'size': FileUtils.sizeHuman(0).strip(),
                        'application': [],
                        'server': [],
                        'language': [],
                        'frameworks': [],
                        'system': []
                    }
                    # 检查是否已经存在相同URL的结果
                    if not any(item['url'] == url for item in self.alive_result_list):
                        self.output.statusReport(url_info)
                        self.alive_result_list.append(url_info)
            else:
                # 默认使用GET请求
                r = self.session.get(url, timeout=config.timeout, headers=self.get_headers(), 
                           verify=config.verify_ssl, cookies=self.get_cookies(),
                           allow_redirects=config.allow_redirects)
                url_info = self.analysis_response(url, r)
                if url_info:
                    # 检查是否已经存在相同URL的结果
                    if not any(item['url'] == url for item in self.alive_result_list):
                        self.output.statusReport(url_info)
                        self.alive_result_list.append(url_info)
        except requests.exceptions.Timeout:
            self.output.debug(f"请求超时: {url}")
        except requests.exceptions.ConnectionError:
            self.output.debug(f"连接错误: {url}")
            self.output.addConnectionError()
        except requests.exceptions.TooManyRedirects:
            self.output.debug(f"重定向过多: {url}")
        except Exception as e:
            self.output.debug(f"请求失败 {url}: {e}")
        finally:
            self.index += 1
            self.output.lastPath(url, self.index, self.total)
            # 添加请求间隔，避免对目标服务器造成过大压力
            if config.request_delay > 0:
                time.sleep(config.request_delay)
        return None

    def get_headers(self):
        """
        生成伪造请求头
        """
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36',
            'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/68.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:61.0) '
            'Gecko/20100101 Firefox/68.0',
            'Mozilla/5.0 (X11; Linux i586; rv:31.0) Gecko/20100101 Firefox/68.0']
        ua = random.choice(user_agents)
        headers = {
            'Accept': 'text/html,application/xhtml+xml,'
                      'application/xml;q=0.9,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Referer': 'https://www.google.com/',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': ua,
        }
        return headers

    def get_cookies(self):
        cookies = {'rememberMe': 'test'}
        return cookies

    def get_title(self, markup):
        """
        获取标题或页面主要内容
        :param markup: html标签
        :return: 标题或页面主要内容
        """
        try:
            soup = BeautifulSoup(markup, 'lxml')

            title = soup.title
            if title and title.text:
                return title.text.strip()

            h1 = soup.h1
            if h1 and h1.text:
                return h1.text.strip()

            h2 = soup.h2
            if h2 and h2.text:
                return h2.text.strip()

            h3 = soup.h3
            if h3 and h3.text:
                return h3.text.strip()

            desc = soup.find('meta', attrs={'name': 'description'})
            if desc and desc.get('content'):
                return desc['content'].strip()

            word = soup.find('meta', attrs={'name': 'keywords'})
            if word and word.get('content'):
                return word['content'].strip()

            # 获取页面正文前200个字符
            text = soup.get_text(strip=True)
            if len(text) <= 200:
                return text
            return text[:200] + '...'
        except Exception as e:
            self.output.debug(f"获取标题失败: {e}")
            return ''

    def analysis_response(self, url, response):
        """
        分析HTTP响应，提取关键信息
        :param url: 请求的URL
        :param response: HTTP响应对象
        :return: 包含URL信息的字典或None
        """
        try:
            if response.status_code in config.ignore_status_code:
                return None            
            # 改进的编码处理逻辑
            try:
                # 先尝试使用response.text，requests会自动处理
                html = response.text
                # 添加调试信息
                self.output.debug(f"响应头编码: {response.encoding}, 内容长度: {len(html)}")
                self.output.debug(f"响应头: {dict(response.headers)}")
                
                # 验证解码是否正确（检查是否有乱码特征）
                if any(ord(c) > 255 and c != '�' for c in html):
                    # 如果有非ASCII字符且不是替换字符，则解码基本正确
                    pass
                else:
                    # 可能解码有问题，尝试手动检测编码
                    response_content = response.content
                    detected_encoding = chardet.detect(response_content)['encoding']
                    self.output.debug(f"chardet检测到的编码: {detected_encoding}")
                    
                    # 尝试常见的中文编码
                    encodings_to_try = [detected_encoding, response.encoding, 'utf-8', 'gbk', 'gb2312', 'big5', 'utf-16']
                    for encoding in encodings_to_try:
                        if encoding and encoding.lower() != 'none':
                            try:
                                html = response_content.decode(encoding=encoding.strip(), errors='strict')
                                # 验证解码结果
                                if any(ord(c) > 255 for c in html):
                                    self.output.debug(f"使用编码 {encoding} 成功解码中文")
                                    break
                            except (UnicodeDecodeError, LookupError):
                                continue
            except Exception as e:
                self.output.debug(f"获取响应文本失败: {e}")
                # 失败时尝试手动处理
                response_content = response.content
                encoding = response.encoding or chardet.detect(response_content)['encoding'] or 'utf-8'
                try:
                    html = response_content.decode(encoding=encoding, errors='replace')
                except Exception as e2:
                    self.output.debug(f"手动解码也失败: {e2}")
                    html = ""
            
            title = self.get_title(html).strip().replace('\r', '').replace('\n', '')
            status = response.status_code
            size = FileUtils.sizeHuman(len(response.content)).strip()

            # 提取脚本和元数据用于指纹识别
            soup = BeautifulSoup(html, "html.parser")
            scripts = []
            for script in soup.findAll('script', src=True):
                if script.get('src'):
                    scripts.append(script['src'])
            
            meta = {}
            for meta_tag in soup.findAll('meta', attrs=dict(name=True, content=True)):
                if meta_tag.get('name') and meta_tag.get('content'):
                    meta[meta_tag['name'].lower()] = meta_tag['content']
            
            # 执行指纹识别
            detected_apps = self.wappalyzer.analyze(url, html, response.headers, scripts, meta)
            
            # 添加调试信息
            self.output.debug(f"识别到的应用: {detected_apps}")
            
            # 整理识别结果
            application = detected_apps.get('Application', [])
            server = detected_apps.get('Server', [])
            language = detected_apps.get('Language', [])
            frameworks = detected_apps.get('Frameworks', [])
            system = detected_apps.get('System', [])
            
            return {
                'url': url,
                'title': title,
                'status': status,
                'size': size,
                'application': application,
                'server': server,
                'language': language,
                'frameworks': frameworks,
                'system': system
            }
        except Exception as e:
            self.output.debug(f"分析响应失败 {url}: {e}")
            return None

    def main(self):
        gevent_pool = pool.Pool(self.threads)
        while self.url_list:
            tasks = [gevent_pool.spawn(self.request, self.url_list.pop())
                     for i in range(len(self.url_list[:self.threads*10]))]
            for task in tasks:
                task.join()
            del tasks

