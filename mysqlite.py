# -*- coding: utf-8 -*-

# 2018.11.23 11:07:22 by Tr0y

import sqlite3
import time


def _get_hour():
    '''
    返回上个小时的时间戳
    假如现在是 2018.11.21 19:44:02， 那么返回 '1542794400'
    即 2018.11.21 18:00:00 的时间戳

    返回值：
        字符串；上个小时的时间戳
    '''

    return str(int(
        time.mktime(
            time.strptime(
                time.strftime("%Y-%m-%d %H"), "%Y-%m-%d %H")
        )
    )-3600)


class MySqlite:
    def __init__(self, dbname, tablename):
        '''
        初始化

        参数：
            dbname：字符串；数据库名
            tablename：字符串；表名
        '''

        self.dbname = dbname
        self.tablename = tablename

        self.conn = sqlite3.connect(self.dbname)

        self._create()

    def _create(self):  #
        '''
        若数据库不存在，则创建数据库
        '''

        query = """create table IF NOT EXISTS {tablename}(
            url VARCHAR(100),
            sha VARCHAR(40),
            repository VARCHAR(100),
            keyword VARCHAR(100),
            filename VARCHAR(100),
            level VARCHAR(5),
            update_time VARCHAR(10),
            last_record_time VARCHAR(10),
            PRIMARY KEY (url, sha)
        );""".format(tablename=self.tablename)  # 不存在才新建
        self.conn.execute(query)
        self.conn.commit()

    def _select(self, sql):
        '''
        查询

        参数：
            sql：字符串；查询的语句

        返回值：
            rows：2 维列表；查询的结果
        '''

        result = self.conn.execute(sql)
        self.conn.commit()
        rows = result.fetchall()
        return rows  # [(, ... ,), (, ... ,)]

    def _insert(self, url, sha, repository, filename, keyword, level, update_time):
        '''
        插入数据
        column 顺序与参数顺序一致
        **插入的数据类型均为字符串**

        参数：
            url：        字符串；代码文件的 url
            sha：        字符串；代码文件的 sha
            repository： 字符串；代码文件的仓库
            filename：   字符串；代码文件的文件名
            keyword：    字符串；代码文件命中的关键字
            level：      整数；  泄露级别
            update_time：字符串；数据库中此记录被更新的时间
        '''

        data = '''INSERT INTO {tablename}(url, sha, repository, keyword, filename, level, update_time, last_record_time) VALUES('{url}','{sha}','{repository}','{keyword}','{filename}','{level}','{update_time}', '∞');
        '''.format(
            tablename=self.tablename,
            url=url,
            sha=sha,
            repository=repository,
            keyword=keyword,
            filename=filename,
            level=level,
            update_time=update_time
        )

        self.conn.execute(data)
        self.conn.commit()

    def _update(self, url, sha, repository, filename, keyword, level, update_time, last_record_time):
        '''
        更新数据

        参数：
            url：             字符串；代码文件的 url
            sha：             字符串；代码文件的 sha
            repository：      字符串；代码文件的仓库
            filename：        字符串；代码文件的文件名
            keyword：         字符串；代码文件命中的关键字
            level：           整数；  泄露级别
            update_time：     字符串；数据库中此记录被更新的时间
            last_record_time：字符串；数据库中此记录上一次被更新的时间
        '''

        data = '''UPDATE {tablename} SET url='{url}', sha='{sha}', repository='{repository}', keyword='{keyword}', filename='{filename}', level='{level}', update_time='{update_time}', last_record_time='{last_record_time}' where url='{url}';
        '''.format(
            tablename=self.tablename,
            url=url,
            sha=sha,
            repository=repository,
            keyword=keyword,
            filename=filename,
            level=level,
            update_time=update_time,
            last_record_time=last_record_time
        )

        self.conn.execute(data)
        self.conn.commit()

    def Record(self, url, sha, repository, filename, keyword, update_time, negative):
        '''
        根据数据库情况，判断新数据记录方式

        参数：
            url：        字符串；代码文件的 url
            sha：        字符串；代码文件的 sha
            repository： 字符串；代码文件的仓库
            filename：   字符串；代码文件的文件名
            keyword：    字符串；代码文件命中的关键字
            update_time：字符串；数据库中此记录被更新的时间
            negative：   布尔值；是否为误报

        返回值
            level：整数；泄露级别
        '''

        result = self._select(
            '''SELECT url, sha, update_time FROM {tablename} where url='{url}'; '''.format(
                url=url,
                tablename=self.tablename
            ))  # 查询是否存在此 url 的记录

        if result:  # 已存在
            if result[0][1] != sha:  # 文件 sha 发生变化
                if negative:
                    level = 1
                else:
                    level = 2

                # 旧的 update_time 作为新的 last_record_time
                self._update(url, sha, repository, filename, keyword, level, update_time, result[0][2])
            else:
                level = 0
        else:
            if negative:
                level = 1
            else:
                level = 3

            self._insert(url, sha, repository, filename, keyword, level, update_time)

        return level

    def Get_Data(self, keyword, level):
        '''
        获取上一轮的泄露记录

        参数：
            keyword：字符串；关键字
            level：字符串；泄露级别

        返回值：
            result：2 维列表；泄露记录
        '''

        last_hour_time = _get_hour()
        result = self._select('''SELECT * FROM {tablename} where keyword='{keyword}' and update_time>='{last_hour_time}' and update_time<'{now_hour_time}' and level={level};
        '''.format(
            tablename=self.tablename,
            keyword=keyword,
            level=level,
            last_hour_time=last_hour_time,
            now_hour_time=last_hour_time+3600  # 加个小于当前小时的限制，防止此轮刚更新就报告
        ))

        for i, r in enumerate(result):
            result[i] = list(result[i])  # tuple 转 list
            result[i][-1] = r[-1] if r[-1] == "∞" else time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(  # 时间戳转成可读性的时间
                    int(r[-1])
                )
            )

        return result
