# RemoteVP-Npc


## 项目介绍

注意：由于项目主要针对工业设备远程编程需求而开发，项目仅仅支持Windows平台、Python3.5， Python3.6。

本项目是基于开源项目 [FreeIOE](https://) 边缘计算框架和 [冬笋云](https://cloud.thingsroot.com) 的一个工业设备（PLC、触摸屏，现场设备等）的远程编程应用。

本项目针对自身业务特点，在IOT网关中一直了 FreeIOE 边缘计算框架，并开发了 FreeIOE 应用 FreeIOE_Vnet_Npc, 并使用冬笋云提供的API对远程的IOT网关进行管理和配置。

本项目使用 [Nps](https://github.com/ehang-io/nps) 搭建隧道代理服务。

本项目还是使用到的其他开源项目如下：

* [Nps](https://github.com/ehang-io/nps) - 一款轻量级、高性能、功能强大的内网穿透代理服务器……
* [Tinc](https://github.com/gsliepen/tinc) - tinc is a Virtual Private Network (VPN) daemon that uses tunnelling and encryption to create a secure private network between hosts on the Internet……

## 功能描述
* 自动获取冬笋云用户名下网关
* 自动检测网关是否具备远程编程功能并自动修复。
* 前后端分离，前后端自由定制。
* restapi & mqtt-ws 接口

#### 虚拟网络
* 点对点虚拟交换机。
* 检测目标IP的延迟。
* 可测试本机和网关创建的虚拟网络的带宽。

#### 虚拟串口
* 点对点虚拟串口。
* 支持动态波特率，自动适配编程软件。
* 支持实时查看串口报文。

## 如何安装

* Windows 7 ~ Windows 10 平台安装 Python3.6

* 下载本项目代码到本地 git clone https://github.com/viccom/RemoteVP-Npc

* 到本项目目录下运行 pip install -r requirements.txt

## 编译为 Windows 二进制文件

1. requirements.txt 已经自动安装 pyinstaller。

2. 先通过 pyinstaller.exe --hiddenimport apps.vnet.app --uac-admin main.py 获得main.spec文件
编辑main.spec文件，hiddenimports=更改为如下内容：

    hiddenimports=['idna', 'apps.common.app', 'apps.vnet.app', 'apps.vserial.app', 'pkg_resources.py2_warn', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan.auto', 'uvicorn.lifespan', 'uvicorn.lifespan.on', 'uvicorn.logging'],

3. 再次运行 pyinstaller.exe -F main.spec 即可获得可用的二进制文件。
