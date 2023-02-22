# 简介
**SimpleStandardCN 是一个用于分类及搜索下载建筑相关国家和行业标准的开源、免费程序**

# 数据来源？

本应用<b>不是</b>标准信息及电子文件的分发者、制作者或所有者。
所有标准信息及下载均来自程序自动<b>网络实时搜索</b>，
本应用只提供搜索得到的信息<b>本身</b>，
版权、责任等请本软件使用的查询源。
本应用不能保证信息的准确性、真实性、时效性，也不对您的使用负任何责任。

*具体而言*，本程序使用的网络查询源为：
- [工标网](http://www.csres.com)：标准搜索、标准详情信息
- [国家工程建设标准化信息网](http://www.ccsn.org.cn)：标准详情信息、标准下载
- [标准网](https://www.biaozhun.org)：标准详情信息、标准下载（下载需登录)
- [标准库](http://www.bzko.com)：标准下载

# 技术细节
本程序使用 python 语言编写，GUI框架使用 pywebview + 原生JS

# 运行
## Windows
请直接前往 [Releases](https://github.com/RyanHaoo/SimpleStdCN/releases) 页面下载最新的 zip 包，解压后即可运行；

## 代码运行（全平台）
1. 下载安装 Python3.8.x （[官网3.8.10](https://www.python.org/downloads/release/python-3810/)）
2. 下载本程序代码至您的电脑

    a. 方法一：在目标文件夹内执行 `git clone https://github.com/RyanHaoo/SimpleStdCN.git`
    
    b. 方法二：在下图处下载代码压缩包，解压至目标文件夹 ![image](https://user-images.githubusercontent.com/100863534/220602634-e07d3f73-4485-4fcf-b8d8-fa5518a24e65.png)
    
3. 在下载好的代码根目录处创建虚拟环境 `python -m venv venv`
4. 链接至虚拟环境 `. venv/bin/activate`(linux/macOS) 或 `.\venv\Scripts\Activate.ps1`(windows)
5. 安装依赖 `python -m pip install -r requirements.txt`
6. (非Windows) 参照[此处](https://rarfile.readthedocs.io/faq.html#how-can-i-get-it-work-on-linux-macos)手动安装rarfile依赖，否则将无法从"标准库"下载标准
7. 运行程序 `python sscn_gui.py`
