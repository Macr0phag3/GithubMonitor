# -*- coding: utf-8 -*-
# running by py3.x

import time
import json
import random
import mysqlite
import traceback

from reporter import Reporter
from github import Github  # pip install PyGithub
from jinja2 import Template  # pip install jinja2


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

            self.analysis_page(result, keyword)

    def analysis_page(self, result, keyword):
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
                ana_result = self.analysis_result(items, keyword)
                if ana_result == False:
                    print("[WARNING] 连续 30 条数据都没有更新")
                    print("[WARNING] 在第{}页退出".format(page_id))
                    break

                elif ana_result == None:
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

                elif "Read timed out" in err:
                    # 出现 timed out 则重复运行（page_id 不变）
                    print("[WARNING] Read data timed out! Just repeat it")  # 跳过 Not Found
                    continue

                else:
                    # 其他错误则发邮件报告异常
                    err = traceback.format_exc()
                    print("[EEEOR] Something went wrong!\n" + err)  # 打印出来，以便在日志中看到
                    r.alert("Github Monitor EEEOR: Something went wrong!\n\n"+err, admin_email)
                    raise  # 释放异常，强制停止脚本

            page_id += 1

        print("[INFO] 结束关键字: "+keyword+"\n\n")

    def analysis_result(self, items, keyword):
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

                elif "Read timed out" in err:
                    print("timed out")  # timed out 则重复
                    continue

                elif "Not Found" in err:
                    print("File not found. Just pass it")  # 跳过 Not Found

                else:
                    # 出现其他错误的时候扔给 analysis_page() 中的异常检测处理
                    raise

            result_id += 1

        return True


# --------------------- 可能需要修改 ----------------------
file_url = "./"
DB = mysqlite.mysqlite(file_url+"github", "leak")
# -------------------------------------------------------

with open(file_url+"config.json", "r") as fp:
    config = json.load(fp)

hosts = config["hosts"]

admin_email = config["admin_email"]

token = config["token"]
r = Reporter(
    config["sender_email"]["uname"],
    config["sender_email"]["smtp"],
    config["sender_email"]["port"],
    config["sender_email"]["uname"],
    config["sender_email"]["passwd"]
)

keywords = GenerateKeywords(hosts)

Monitor = GithubMonitor(keywords, token)
results = Monitor.search()

send_flag = 0  # 为 0 时说明 3 个 level 均为空
results = {}
for keyword in keywords:
    results[keyword] = []
    empty = True
    for level in range(3, 0, -1):
        result = DB.Get_Date(keyword, level)
        if result:
            send_flag = 1
            results[keyword].append(result)
            empty = False
        else:
            results[keyword].append([(None, )*7+("∞",)])

    if empty:  # 不汇报无泄漏的关键字
        results.pop(keyword)

DB.conn.close()

if send_flag:
    c = GenerateHTML(results)

    for email_addr in config["receiver_email"]:
        r.alert(c, email_addr)

    with open(file_url+"result.html", 'w') as fp:
        fp.write(c)
