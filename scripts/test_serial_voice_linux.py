#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETV001-485 语音模块 Linux 测试脚本
测试串口: /dev/ttyS4
波特率: 9600
协议: 科星私有协议 (# + 内容)
编码: GB2312
"""

import sys
import time
import argparse

try:
    import serial
except ImportError:
    print("错误: 未安装 pyserial 库")
    print("请运行: pip install pyserial")
    sys.exit(1)

def test_voice(port, baudrate, text):
    print(f"正在打开串口: {port}, 波特率: {baudrate}...")
    try:
        # 初始化串口
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        
        if not ser.is_open:
            ser.open()
            
        print("串口打开成功")
        
        # 准备发送数据
        # 协议格式: # + 文字内容
        content = f"#{text}"
        
        # 编码为 GB2312
        try:
            data = content.encode('gb2312')
        except UnicodeEncodeError:
            print("警告: 包含无法用GB2312编码的字符，尝试使用GB18030")
            data = content.encode('gb18030')
            
        print(f"发送内容: {content}")
        print(f"十六进制: {data.hex().upper()}")
        
        # 发送数据
        bytes_sent = ser.write(data)
        print(f"已发送字节数: {bytes_sent}")
        
        # 等待发送完成
        time.sleep(0.1)
        
        # 关闭串口
        ser.close()
        print("测试完成")
        return True
        
    except serial.SerialException as e:
        print(f"串口错误: {e}")
        print("提示: 请检查串口号是否正确，以及是否有权限访问 (sudo chmod 666 /dev/ttyS4)")
        return False
    except Exception as e:
        print(f"发生未知错误: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='ETV001-485 语音模块测试')
    parser.add_argument('--port', default='/dev/ttyS4', help='串口设备路径 (默认: /dev/ttyS4)')
    parser.add_argument('--baud', type=int, default=9600, help='波特率 (默认: 9600)')
    parser.add_argument('--text', default='你好，语音模块测试成功', help='要播报的文字')
    
    args = parser.parse_args()
    
    test_voice(args.port, args.baud, args.text)
