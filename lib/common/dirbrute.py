import requests
import urllib3
import rules
import config
from concurrent.futures import ThreadPoolExecutor
from lib.utils.FileUtils import *
from lib.utils.tools import *
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
urllib3.disable_warnings()


class Dirbrute:
    def __init__(self, target, output, brute_result_list):
        """
        初始化目录扫描器
        :param target: 目标URL
        :param output: 输出对象
        :param brute_result_list: 用于存储扫描结果的列表
        """
        self.target = target
        self.output = output
        self.output.bruteTarget(target)
        self.all_rules = []
        self.brute_result_list = brute_result_list
        self.total_rules = 0
        self.scanned_rules = 0
        
        # 创建会话，实现连接池和重试机制
        self.session = requests.Session()
        retry_strategy = Retry(
            total=1,  # 目录扫描重试次数较少
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET"],
            backoff_factor=0.1,
            raise_on_status=False
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=50,
            pool_maxsize=50
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def format_url(self, path):
        url = self.target
        if url.endswith('/'):
            url = url.strip('/')
        if not path.startswith('/'):
            path = '/' + path
        return url + path

    def init_rules(self):
        """
        初始化扫描规则
        """
        config_file_rules = rules.common_rules.get('config_file', [])
        shell_scripts_rules = rules.common_rules.get('shell_scripts', [])
        editor_rules = rules.common_rules.get('editor', [])
        spring_rules = rules.common_rules.get('spring', [])
        web_app_rules = rules.common_rules.get('web_app', [])
        test_page_rules = rules.common_rules.get('test_page', [])
        other_rules = rules.common_rules.get('other', [])
        
        # 合并所有规则
        self.all_rules = []
        self.all_rules.extend(config_file_rules)
        self.all_rules.extend(shell_scripts_rules)
        self.all_rules.extend(editor_rules)
        self.all_rules.extend(spring_rules)
        self.all_rules.extend(web_app_rules)
        self.all_rules.extend(test_page_rules)
        self.all_rules.extend(other_rules)
        
        # 去重，避免重复扫描相同路径
        unique_paths = {}
        unique_rules = []
        for rule in self.all_rules:
            path = rule.get('path')
            if path and path not in unique_paths:
                unique_paths[path] = True
                unique_rules.append(rule)
        
        self.all_rules = unique_rules
        self.total_rules = len(self.all_rules)
        self.output.info(f"Loaded {self.total_rules} directory brute force rules")

    def compare_rule(self, rule, response_status, response_html, response_content_type):
        """
        比较响应与规则是否匹配
        :param rule: 规则字典
        :param response_status: 响应状态码
        :param response_html: 响应HTML内容
        :param response_content_type: 响应内容类型
        :return: 是否匹配
        """
        # 检查状态码
        expected_status = rule.get('status')
        if expected_status:
            rule_status = [200, 206, expected_status]
            if response_status not in rule_status:
                return False
        
        # 检查标签
        expected_tag = rule.get('tag')
        if expected_tag and expected_tag not in response_html:
            return False
        
        # 检查内容类型排除
        expected_type_no = rule.get('type_no')
        if expected_type_no and expected_type_no in response_content_type:
            return False
        
        # 检查内容类型包含
        expected_type = rule.get('type')
        if expected_type and expected_type not in response_content_type:
            return False
        
        return True

    def brute(self, rule):
        """
        执行目录扫描
        :param rule: 规则字典
        :return: 结果或异常
        """
        # 获取路径并格式化URL
        path = rule.get('path')
        if not path:
            return
            
        url = self.format_url(path)
        
        # 准备请求头
        user_agent = 'Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36'
        headers = {
            'User-Agent': user_agent,
            'Connection': 'Keep-Alive',
            'Range': 'bytes=0-102400'  # 只请求前100KB以提高效率
        }
        
        try:
            # 发送请求
            method = 'HEAD' if config.use_head_request else 'GET'
            if method == 'HEAD':
                r = self.session.head(url, headers=headers, verify=config.verify_ssl, 
                                timeout=config.timeout, allow_redirects=False)
                # HEAD请求获取的内容有限
                response_html = ""
                content_length = r.headers.get('Content-Length', 0)
                size = FileUtils.sizeHuman(int(content_length))
            else:
                r = self.session.get(url, headers=headers, verify=config.verify_ssl, 
                               timeout=config.timeout, allow_redirects=False)
                response_html = r.text
                size = FileUtils.sizeHuman(len(r.text))
                
            # 获取响应信息
            response_status = r.status_code
            response_content_type = r.headers.get('Content-Type', '')
            
            url_info = {'url': url, 'status': response_status, 'size': size.strip()}
            
            # 检查黑名单规则，如果匹配则跳过
            blacklist_match = False
            for black_rule in rules.black_rules:
                if self.compare_rule(black_rule, response_status, response_html, response_content_type):
                    blacklist_match = True
                    break
            
            if not blacklist_match:
                # 检查白名单规则
                for white_rule in rules.white_rules:
                    if self.compare_rule(white_rule, response_status, response_html, response_content_type):
                        # 检查是否已经存在相同URL的结果
                        if not any(item['url'] == url for item in self.brute_result_list):
                            self.output.statusReport(url_info)
                            self.brute_result_list.append(url_info)
                
                # 检查是否匹配规则
                if self.compare_rule(rule, response_status, response_html, response_content_type):
                    # 检查是否已经存在相同URL的结果
                    if not any(item['url'] == url for item in self.brute_result_list):
                        self.brute_result_list.append(url_info)
                        self.output.statusReport(url_info)
                        return [url, rule]
                
        except requests.exceptions.Timeout:
            self.output.debug(f"Timeout: {url}")
        except requests.exceptions.ConnectionError:
            self.output.debug(f"Connection error: {url}")
        except requests.exceptions.TooManyRedirects:
            self.output.debug(f"Too many redirects: {url}")
        except Exception as e:
            self.output.debug(f"Error {url}: {e}")
        finally:
            self.scanned_rules += 1
            # 显示扫描进度
            if self.total_rules > 0:
                progress = (self.scanned_rules / self.total_rules) * 100
                if self.scanned_rules % 10 == 0:  # 每扫描10个规则更新一次进度
                    self.output.info(f"Directory brute force progress: {self.scanned_rules}/{self.total_rules} ({progress:.1f}%)", end='\r')
            # 添加请求间隔，避免对目标服务器造成过大压力
            if hasattr(config, 'request_delay') and config.request_delay > 0:
                import time
                time.sleep(config.request_delay)
        return [url, rule]

    def run(self):
        """
        运行目录扫描
        """
        self.init_rules()
        if not self.all_rules:
            self.output.error("No directory brute force rules loaded")
            return
            
        # 使用全局配置的线程数
        thread_count = config.thread_count if hasattr(config, 'thread_count') else 30
        
        self.output.info(f"Starting directory brute force with {thread_count} threads")
        
        # 执行扫描
        with ThreadPoolExecutor(max_workers=thread_count) as pool:
            pool.map(self.brute, self.all_rules)
        
        # 完成扫描
        self.output.info(f"Directory brute force completed: {self.scanned_rules}/{self.total_rules} rules scanned")
        self.output.info(f"Found {len(self.brute_result_list)} valid directories/paths")
