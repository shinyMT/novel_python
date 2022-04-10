# -*- coding:utf-8 -*-
# Author:thy


# 引入模块
import os
import sys
import time
from bs4 import BeautifulSoup
import re
import urllib.request, urllib.error
import random
import queue
import threading

# 请求头
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 "
    "Safari/537.36",
    "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; AcooBrowser; .NET CLR 1.1.4322; .NET CLR 2.0.50727)",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0; Acoo Browser; SLCC1; .NET CLR 2.0.50727; Media Center PC 5.0; "
    ".NET CLR 3.0.04506)",
    "Mozilla/4.0 (compatible; MSIE 7.0; AOL 9.5; AOLBuild 4337.35; Windows NT 5.1; .NET CLR 1.1.4322; .NET CLR "
    "2.0.50727)",
    "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Win64; x64; Trident/5.0; .NET CLR 3.5.30729; .NET CLR "
    "3.0.30729; .NET CLR 2.0.50727; Media Center PC 6.0)",
    "Mozilla/5.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0; WOW64; Trident/4.0; SLCC2; .NET CLR 2.0.50727; "
    ".NET CLR 3.5.30729; .NET CLR 3.0.30729; .NET CLR 1.0.3705; .NET CLR 1.1.4322)",
    "Mozilla/4.0 (compatible; MSIE 7.0b; Windows NT 5.2; .NET CLR 1.1.4322; .NET CLR 2.0.50727; InfoPath.2; .NET CLR "
    "3.0.04506.30)",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN) AppleWebKit/523.15 (KHTML, like Gecko, Safari/419.3) Arora/0.3 ("
    "Change: 287 c9dfb30)",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.2pre) Gecko/20070215 K-Ninja/2.1.1",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.9) Gecko/20080705 Firefox/3.0 Kapiko/3.0",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/535.20 (KHTML, like Gecko) Chrome/19.0.1036.7 "
    "Safari/535.20",
    "Opera/9.80 (Macintosh; Intel Mac OS X 10.6.8; U; fr) Presto/2.9.168 Version/11.52",
]

# 创建正则表达式对象
findContent = re.compile(r'<p>(.*?)</p>')
# 定义一个空队列存放待爬取的每个章节的链接
q = queue.Queue()
# 定义一个优先级队列存放顺序的章节链接
priQue = queue.PriorityQueue()
# 定义一个优先级队列存放爬取到的章节内容
contentPriQue = queue.PriorityQueue(maxsize=-1)
# 定义一个存放线程的列表
threadList = []
# 定义一个存放写入线程的列表
writeThreadList = []
# 创建一个锁对象
lockObj = threading.Lock()


# 随机获取请求头，避免因多次访问被拒绝
def createHeader():
    headers = dict()
    headers["User-Agent"] = random.choice(USER_AGENTS)
    headers["Referer"] = "https://www.yushubo.com"
    return headers
    pass


# 获取指定的url的html网页结构
def askUrl(url):
    global html
    # 设置请求链接，url+头部信息
    req = urllib.request.Request(url, headers=createHeader())
    try:
        response = urllib.request.urlopen(req)
        # 读取响应内容
        html = response.read().decode('utf-8')
        # print(html)
        pass
    except urllib.error.URLError as msg:
        # 打印异常状态码和信息
        if hasattr(msg, "code"):
            print(msg.code)
            pass
        if hasattr(msg, "reason"):
            print(msg.reason)
            pass
        pass
    return html
    pass


# 解析网页结构获取数据 --- baseUrl: 不带参数的网页地址
def getData(baseUrl, totalChapter, savePath, novelName):
    # 将获取到的参数 totalChapter 转换为int类型
    totalChapterAsInt = int(totalChapter) + 1
    # 在一开始将书名写入文件
    titleContent = '% ' + novelName + '\n'
    writeToFile(titleContent, savePath, novelName)

    # 循环n次获取全部章节地址
    for n in range(1, totalChapterAsInt):
        # 根据页数, 拼接得到完整的URL地址
        firstUrl = baseUrl + "_" + str(n)
        # 将章节地址放入队列中并设置优先级
        priQue.put((n, firstUrl))
        pass

    # 创建并开启新线程
    for k in range(5):
        thread = GetThread(k)
        thread.start()
        threadList.append(thread)
        pass
    for t in threadList:
        t.join()
        pass

    # 获取完成后最后按顺序写入文件
    writeFileByOrder(savePath, novelName)

    # 拼接保存的地址
    saveNovelPath = savePath + novelName
    # 写入完成后调用外部程序将其转换为epub格式
    cmd = 'pandoc %s -o %s' % (saveNovelPath + '.txt', saveNovelPath + '.epub')
    os.system(cmd)
    pass


# 解析网页结构
def analysisHTML(url):
    # 得到网页结构
    html = askUrl(url)
    soup = BeautifulSoup(html, "html.parser")

    return soup
    pass


# 获取当前章节的页数
def getPageNum(url):
    soup = analysisHTML(url)
    # 根据源码找到[article-title]的h1
    title = soup.select('h1[class="article-title"]')[0].string
    try:
        num = str(title).split('/')[1].split(')')[0]
        pass
    except IndexError as e:
        num = 1
        # print('当前章节只有一页 ', e)
        pass

    return num
    pass


# 将内容写入文件
def writeToFile(content, savePath, novelName):
    # 拼接目标地址
    targetSavePath = savePath + novelName + '.txt'
    # with自带close效果
    with open(targetSavePath, 'a+', encoding='utf-8') as f:
        f.write(content)
        pass
    pass


# 获取时间函数
def getTime():
    currentTime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    return currentTime
    pass


# 创建一个线程类用于获取章节内容
class GetThread(threading.Thread):

    def __init__(self, threadId):
        threading.Thread.__init__(self)
        self.threadId = threadId
        pass

    # 设置线程任务
    def run(self):
        # 获取锁对象
        # lockObj.acquire()
        # 获取队列中的所有地址
        while not priQue.empty():
            urlData = priQue.get()
            firstUrl = urlData[1]
            # 获取当前章节的章节序号
            index = int(str(firstUrl).split('_')[2])

            # 定义一个变量存放章节内容
            fileContent = ""
            # 获取页数
            pageNum = getPageNum(firstUrl)
            # 向内容中添加标题
            fileContent += "# 第" + str(index) + "章\n"

            for j in range(1, int(pageNum) + 1):
                detailUrl = firstUrl + "_" + str(j) + ".html"
                soup = analysisHTML(detailUrl)
                # 根据源码找到[article-con]的div
                for item in soup.select('div[class="article-con"]'):
                    # 将HTML节点转换为字符串
                    page = str(item)
                    # 获取字符串中所有p标签的内容组成一个数组
                    content = re.findall(findContent, page)
                    for sentence in content:
                        # 去除多余字符和p标签得到正常内容
                        single = str(sentence).replace('\u3000', '').replace('<p>', '\n\n')
                        # 向内容中添加章节具体内容
                        fileContent += single
                        pass
                    pass
                pass

            # 向内容中添加换行符以开启下一章节
            fileContent += '\n\n'

            # 将获取到的章节内容按照章节优先级放入队列中
            contentPriQue.put((index, fileContent))
            pass
        pass

    pass


# 按顺序将内容写入文件的方法
def writeFileByOrder(savePath, novelName):
    # 获取锁
    lockObj.acquire()
    # 获取队列池中所有的内容
    while not contentPriQue.empty():
        data = contentPriQue.get()
        index = data[0]
        content = data[1]
        writeToFile(content, savePath, novelName)
        print('第 ', index, ' 章获取完毕')
        pass
    # 释放锁
    lockObj.release()
    pass


# 主函数
def main(totalChapterNum, savePath, novelUrl, novelName):
    # 不带参数值的url
    # 第一章地址：https://www.yushubo.com/read_99857_1.html
    # 最后一章地址：https://www.yushubo.com/read_99857_115.html
    # 将传递来的url进行切割
    splitList = novelUrl.split('_')
    novelBaseUrl = splitList[0] + "_" + splitList[1]
    # baseUrl = "https://www.yushubo.com/read_99857"
    baseUrl = novelBaseUrl
    # 爬取网页结构并解析数据
    getData(baseUrl, totalChapterNum, savePath, novelName)

    pass


if __name__ == '__main__':
    args = []
    # sys.argv用于获取url传递的参数, 因为argv[0]代表程序名，因此参数从1开始取
    for i in range(1, len(sys.argv)):
        args.append((sys.argv[i]))
        pass
    totalNum = args[0]
    targetPath = args[1]
    bookUrl = args[2]
    bookName = args[3]
    # print("获取的总章节数为：" + str(totalNum) + ", 保存的目录为：" + str(targetPath))

    main(totalChapterNum=totalNum, savePath=targetPath, novelUrl=bookUrl, novelName=bookName)
    # main(8)
    pass
