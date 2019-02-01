# -*- coding: utf-8 -*-

# running by py3.x
# 2018.11.23 11:07:22 by Tr0y

import json
import random
import time
import traceback

from github import Github  # pip install PyGithub
from jinja2 import Template  # pip install jinja2

import mysqlite
from reporter import Reporter


def GenerateKeywords(hosts):
    '''
    hosts * key
    n*n 种组合的关键字
    其中 host 带 @ 的还要加上 smtp 关键字

    host 的格式为：
        www.baidu.com
        或者
        www.baidu.com @

    参数：
        hosts：列表；监控的域名
    返回值：
        keywords：列表；生成的关键字
    '''

    key = ["password", "passwd", "密码"]
    keywords = []

    for h in hosts:
        if "@" in h:
            h = h.split("@")[0]+" smtp"

        for k in key:
            keywords.append(h+" "+k)

    return keywords


def GenerateHTML(results):
    '''
    利用模板生成报告(results)

    参数：
        results：字典；本轮发现的泄露

    返回值：
        c：字符串；生成的 HTML 源码
    '''

    with open(file_url+"template.html", "r") as fp:
        template = Template(fp.read())
        c = template.render(
            results=results,
        )

    return c


class GithubMonitor:
    '''
    Github 泄露监控
    '''

    def __init__(self, keywords, token):
        '''
        初始化

        参数：
            keywords：列表；要搜索的关键字
            token：字符串；用于授权使用 Github 的 api
        '''

        self.keywords = keywords
        self.token = token

        self.no_update = 0  # 连续旧记录的数量

        self.github = Github(self.token)

    def _analysis_page(self, result, keyword):
        '''
        处理搜索页面

        参数：
            result：实例；搜索页面返回的结果
            keyword：字符串；关键字
        '''

        page_id = 0

        # 0-33 页，每页 30 个结果
        # 对应 github 的 1000 个结果的限制
        while page_id < 34:
            try:
                items = result.get_page(page_id)  # 获取页面的详细记录
                ana_result = self._analysis_result(items, keyword)
                if not ana_result:
                    print("[WARNING] 连续 30 条数据都没有更新")
                    print("[WARNING] 在第{}页退出".format(page_id))
                    break

                elif ana_result is None:
                    print("[WARNING] 搜索页面为空")
                    print("[WARNING] 在第{}页退出".format(page_id))
                    break

            except Exception as e:
                err = str(e)

                # 速度过快会触发 github 的爬虫检测
                if "You have triggered an" in err:
                    sleep_time = random.randint(20, 60)
                    print("[WARNING] Too fast! Sleep for {}s".format(sleep_time))
                    time.sleep(sleep_time)  # sleep 一会
                    continue

                elif "timed out" in err:
                    # 出现 timed out 则重复运行（page_id 不变）
                    print("[WARNING] Read data timed out! Just repeat it")  # 跳过 Not Found
                    continue

                elif "Connection aborted." in err:
                    print("[WARNING] Remote end closed connection without response! Just repeat it")  # Connection aborted 则重复
                    continue

                elif "Unexpected problem" in err:
                    print("[WARNING] Unexpected problem! Just repeat it")
                    continue

                else:
                    # 其他错误则发邮件报告异常
                    err = traceback.format_exc()
                    print("[ERROR] Something went wrong!\n" + err)  # 打印出来，以便在日志中看到
                    r.alert("Github Monitor ERROR: Something went wrong!\n\n"+err, admin_email)
                    raise  # 释放异常，强制停止脚本

            page_id += 1

        print("[INFO] 结束关键字: "+keyword+"\n\n")

    def _analysis_result(self, items, keyword):
        '''
        分析搜索页面
        '''

        result_id = 0

        result_count = len(items)
        if not result_count:  # 结果为空
            return None

        while result_id < result_count:
            item = items[result_id]
            try:
                if all(list([kw in item.decoded_content.decode("utf8") for kw in keyword.split(" ")])):
                    negative = False  # 关键字 不 都存在，疑似误报
                else:
                    negative = True

                url = "https://www.github.com/"+item.repository.full_name+"/blob/master/"+item.path

                update_time = str(int(time.time()))
                record_result = DB.Record(  # 扔给 Record 处理
                    url,
                    item.sha,
                    item.repository.full_name,  # repository
                    item.path,  # filename
                    keyword,
                    update_time,
                    negative,
                )

                if record_result == 3:  # 新泄露
                    self.no_update = 0

                elif record_result == 2:  # 更新泄露
                    self.no_update = 0

                elif record_result == 1:  # 疑似误报
                    self.no_update = 0

                else:  # 旧的数据（一个小时之前爬过）
                    if self.no_update > 30:
                        # 连续 30 条记录都是旧的数据说明后面的数据也是旧的
                        return False

                    self.no_update += 1

            except Exception as e:
                err = str(e)

                # 速度过快触发 github 的爬虫检测就 sleep 一会
                if "You have triggered an" in err:
                    sleep_time = random.randint(20, 60)
                    print("sleep for {}s".format(sleep_time))
                    time.sleep(sleep_time)
                    continue

                elif "timed out" in err:
                    print("timed out")  # timed out 则重复
                    continue

                elif "Unexpected problem" in err:
                    print("[WARNING] Unexpected problem! Just repeat it")
                    continue

                elif "Connection aborted." in err:
                    print("[WARNING] Remote end closed connection without response! Just repeat it")  # Connection aborted 则重复
                    continue

                elif "Not Found" in err:
                    print("File not found. Just pass it")  # 跳过 Not Found

                else:
                    # 出现其他错误的时候扔给 analysis_page() 中的异常检测处理
                    raise

            result_id += 1

        return True

    def search(self):
        '''
        根据关键字搜索 Github 上的代码
        '''

        for keyword in self.keywords:
            result = self.github.search_code(
                keyword,  # 关键字
                sort="indexed",  # 按最新的索引记录排序
                order="desc",  # 最新的索引放在最前面
            )

            self._analysis_page(result, keyword)


# --------------------- 可能需要修改 ----------------------
file_url = "./"
DB = mysqlite.MySqlite(file_url+"github", "leak")
# -------------------------------------------------------

# 读取配置
# 将配置放在单独的 json 文件中
# 再设置 .gitgnore 防止泄露
with open(file_url+"config.json", "r") as fp:
    config = json.load(fp)

hosts = config["hosts"]  # 监控的 host

admin_email = config["admin_email"]  # 管理员邮箱（报错的时候通知）

token = config["token"]  # Github token
r = Reporter(
    config["sender_email"]["uname"],
    config["sender_email"]["smtp"],
    config["sender_email"]["port"],
    config["sender_email"]["uname"],
    config["sender_email"]["passwd"]
)

keywords = GenerateKeywords(hosts)

Monitor = GithubMonitor(keywords, token)
Monitor.search()

send_flag = 0
results = {}
for keyword in keywords:
    results[keyword] = []
    empty = True
    for level in range(3, 0, -1):
        result = DB.Get_Data(keyword, level)  # 获取上一轮的泄漏记录
        if result:
            send_flag = 1
            results[keyword].append(result)
            empty = False
        else:
            results[keyword].append([(None, )*7+("∞",)])

    if empty:  # 不汇报无泄漏的关键字
        results.pop(keyword)

DB.conn.close()

if send_flag:  # 为 0 时说明 所有关键字都无泄漏
    print("[Info] Send email")
    c = GenerateHTML(results)

    for email_addr in config["receiver_email"]:
        r.alert(c, email_addr)

    with open(file_url+"result.html", 'w') as fp:
        fp.write(c)
else:
    print("[Info] Nothing to do")

'''
results 示例：

{'qiniu 密码': [('www.github.com/nicoson/CNR-Video-Audit/blob/master/README.md',
   '0f00caf3b2bc2828428b568148b1939bdce5f6c6',
   'nicoson/CNR-Video-Audit',
   'qiniu 密码',
   'README.md',
   '3',
   '1542811078',
   '∞'),

  ('www.github.com/Macr0phag3/github_monitor/blob/master/template.html',
   'e7e35a1fd081e31675a2644fbe91d56356f5e74d',
   'Macr0phag3/github_monitor',
   'qiniu 密码',
   'template.html',
   '3',
   '1542811744',
   '∞'),

  ('www.github.com/Macr0phag3/github_monitor/blob/master/spider.py',
   '2b3fd456e58eb5dc0ee6d72b98a9494f7dda9423',
   'Macr0phag3/github_monitor',
   'qiniu 密码',
   'spider.py',
   '2',
   '1542811745',
   '∞'),

  ('www.github.com/shuaizhupeiqi/shuaizhupeiqi.github.io/blob/master/page/2/index.html',
   '413fc90095643fa9e0acc0e5bdb8a6d7c116fc3a',
   'shuaizhupeiqi/shuaizhupeiqi.github.io',
   'qiniu 密码',
   'page/2/index.html',
   '2',
   '1542811520',
   '∞')]}
'''
