# github_monitor

## 项目介绍
由于很多猪队友的存在，公司敏感信息通过 GitHub 泄露出去是很常见的。这个项目主要根据关键字与 hosts 生成的关键词，利用 github 提供的 api，监控 git 泄漏，并在检测到信息泄露的时候发送邮件通知。

## 特性
1. 对于泄露有对应的泄漏定级，可作为严重性的参考
2. 简单却完善：利用 api 获取 GitHub 的搜索结果是最简单高效的方式，加上关键词的限定，保证不超过 GitHub 的 api 限制
3. 注释比较详细，可以很快地进行定制
4. 自动组合关键字

## 快速开始
### 依赖
- pip install PyGithub
- pip install jinja2

### 配置
- 在项目文件夹下新建一个 `config.json` 文件，按照 `spider.py` 里的注释配置。config.json 的示例：
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
hosts 中，带 `@` 的说明是邮件类型，在代码中会进行特殊处理，详细处理可见代码

- `spider.py` 中的 `file_url` 可能需要修改

### 运行方式
- crontab 一个小时运行一次 或者直接 python spider.py

## 代码主要逻辑
![代码主要逻辑](https://github.com/Macr0phag3/GithubMonitor/raw/master/pics/pic2.jpg)


## 结果示例
![结果示例](https://github.com/Macr0phag3/GithubMonitor/raw/master/pics/pic1.jpg)

## 一些想法
个人认为，github 监控最难的在于如何判断检索到的数据是否含有泄露的敏感信息，这是一个很难的问题。

对于攻击方来说，一般只是为了利用泄露信息，那么对于 github 泄密的判断，只需要有就行。假如一共 100 条信息，能检测到 10 条也是很有价值的。当然，发现的泄露越多越好，为了达到这一目的，甚至可以上机器学习，提高对敏感信息的判断力。误报率比较低（谁都不想兴冲冲地去看泄露信息结果发现 `password: "********"` :D ）。

**而我这个代码的作用是监控自身公司的泄露。** 对于防守方（公司）检测自身泄露来说，不小心放过一条都意味着很大的风险。换句话说，100 条泄露必须尽可能达到 100% 的检测率，甚至不惜以误报率换取准确率。所以，让代码去判断泄露是很无力的，需要人眼过一遍。那么问题来了，那么多数据，人眼看不过来怎么办呢。

**提高监控关键字的精确性。** 举个例子，假如你的公司域名/ip 为 qq.com/1.1.1.1，那么最好在监控的关键字附上 qq.com/1.1.1.1 这样。类似的方法有很多（自己公司的文件应该有一些特征的。当然肯定有特殊情况，特殊对待吧），目的是减少搜索结果，能提高精确性，降低人的负担。如果你检测的是 `qiniu.com password` 你会发现每一轮都会有大量的数据，所以别用模糊的关键字。

这一方法还解决了 github api 只能拿到前 1000 个搜索结果（不是页面）的问题，搜索结果少意味着更新的数据也不会多，不会超过 1000 的限制。如果你检测的是 `password` 你会发现每轮更新的数据都不止 1000 条，这样会产生漏报（万一就是第 1001 条泄露的呢）。

如果你能理解我上面说的，就没必要自己写 github 的爬虫解析页面，直接调用 api 就好了。

**信任已有，监控增量**，对于攻击者来说，会认为已有的 github 数据存在泄露，需要去淘一遍（当然也有监控增量的）。而对于公司来说，是假设现在 github 没有泄露，然后去监控它的增量，不会淘一遍已有的 github 数据。增量数据包含 2 种：
1. 新增泄露：新 push 的文件
2. 更新泄露：update 的文件

当然，什么都扛不住猪队友呀 :D

## 更新
2019-01-07, 可以免费在 github 上创建私有仓库了。

**强烈建议需要保密的仓库更改为私有**

**强烈建议需要保密的仓库更改为私有**

**强烈建议需要保密的仓库更改为私有**

## License
Copyright © 2018 [Macr0phag3](https://github.com/Macr0phag3).

This project is MIT licensed.

## Others

[![Stargazers over time](https://starchart.cc/Macr0phag3/GithubMonitor.svg)](https://starchart.cc/Macr0phag3/GithubMonitor)
