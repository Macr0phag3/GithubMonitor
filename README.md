# github_monitor

根据关键字与 hosts 生成的关键词，利用 github 提供的 api，监控 git 泄漏。

有对应的泄漏定级。

**注释很详细**

config.json 的示例：
```
{
  "hosts" : [
    "*********.com",
    "*********.com @",
],

"sender_email":{
  "uname":"*********@qq.com",
  "smtp":"smtp.qq.com",
  "port":25,
  "passwd":"*********"
},

"receiver_email":[
  "*********@qq.com",
  "*********@qq.com"
],

"token":"*******************",
"admin_email":"*********@qq.com"
}
```

hosts 中，带 `@` 的说明是邮件类型，在代码中会进行特殊处理，详细解释看代码

## 依赖
- pip install PyGithub
- pip install jinja2

## 运行方式
- crontab 一个小时一次
- python spider.py
- 新建一个 `config.json` 文件，按照 `spider.py` 里的注释配置
- `spider.py` 中的 `file_url` 可能需要修改


## 代码主要逻辑
![代码主要逻辑](https://github.com/Macr0phag3/GithubMonitor/raw/master/pics/pic2.jpg)


## 结果示例
![结果示例](https://github.com/Macr0phag3/GithubMonitor/raw/master/pics/pic1.jpg)
