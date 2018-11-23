# -*- coding: utf-8 -*-

import sqlite3
import time


class mysqlite:
    def __init__(self, dbname, tablename):
        self.dbname = dbname
        self.conn = sqlite3.connect(self.dbname)
        self.tablename = tablename
        self.Create()

    def Create(self):  #
        '''
        创建数据库
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

    def Record(self, url, sha, repository, filename, keyword, update_time, negative):
        result = self.Select(
            '''SELECT url, sha, update_time FROM {tablename} where url='{url}'; '''.format(
                url=url,
                tablename=self.tablename
            ))

        if result:  # 已存在
            if result[0][1] != sha:  # 文件 sha 发生变化
                if negative:
                    level = 1
                else:
                    level = 2

                # 旧的 update_time 作为更新后的 last_record_time
                self.Update(url, sha, repository, filename, keyword, level, update_time, result[0][2])
            else:
                level = 0
        else:
            if negative:
                level = 1
            else:
                level = 3

            self.Insert(url, sha, repository, filename, keyword, level, update_time)

        return level

    def Select(self, sql):
        '''
        查询

        默认查询所有 column
        '''

        result = self.conn.execute(sql)
        self.conn.commit()
        rows = result.fetchall()
        return rows

    def Insert(self, url, sha, repository, filename, keyword, level, update_time):
        '''
        插入数据

        column 顺序与参数顺序一致
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

    def Update(self, url, sha, repository, filename, keyword, level, update_time, last_record_time):
        '''
        更新数据
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

    def get_hour(self):
        '''
        返回上个小时的时间戳

        假如现在是 2018.11.21 19:44:02， 那么返回 '1542794400'
        即 2018.11.21 18:00:00 的时间戳
        '''

        return str(int(
            time.mktime(
                time.strptime(
                    time.strftime("%Y-%m-%d %H"), "%Y-%m-%d %H")
            )
        )-3600)

    def Get_Data(self, keyword, level):
        result = self.Select('''SELECT * FROM {tablename} where keyword='{keyword}' and update_time>='{update_time}' and level={level};
        '''.format(
            tablename=self.tablename,
            keyword=keyword,
            level=level,
            update_time=self.get_hour(),
        ))

        for i, r in enumerate(result):
            result[i] = list(result[i])  # tuple 转 list
            result[i][-1] = r[-1] if r[-1] == "∞" else time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(  # 时间戳转成可读性的时间
                    int(r[-1])
                )
            )
        return result
