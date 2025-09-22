# 废弃物AI识别指导投放系统

## 🎉 最新优化和改进 (v1.1.0)

### ✨ 新增功能
- **🚀 智能启动器**: 新增用户友好的图形化启动器 (`launcher.py`)，提供系统检查和启动选项
- **🛡️ 错误恢复系统**: 全面的错误处理和自动恢复机制，提高系统稳定性
- **⚙️ 增强配置管理**: 重构配置管理器，支持配置验证、备份和恢复
- **🔄 降级机制**: 智能降级和备用模式，确保系统在异常情况下仍能运行

### 🔧 问题修复
- **✅ 导入错误处理**: 修复所有模块导入问题，添加安全导入和降级机制
- **✅ 主窗口稳定性**: 解决主窗口创建和显示问题，添加备用界面
- **✅ 配置文件健壮性**: 增强配置文件的错误处理和自动修复能力
- **✅ 资源管理优化**: 改进内存和资源管理，减少内存泄漏

### 🎨 用户体验改进
- **📱 响应式界面**: 优化界面布局，支持不同窗口大小
- **🎯 启动选项**: 多种启动模式选择（完整、简化、调试、安全）
- **📊 系统检查**: 启动前自动检查系统状态和依赖
- **💡 智能提示**: 详细的错误信息和解决建议

### 🏗️ 架构优化
- **🔌 模块化设计**: 改进模块间的耦合，增强系统的可维护性
- **🛠️ 错误恢复**: 分层错误处理，从模块级到系统级的全面覆盖
- **📝 日志增强**: 更详细的日志记录和错误追踪
- **🔍 调试支持**: 增强的调试功能和诊断工具

### 📁 文件结构优化
- **📚 文档整合**: 将所有说明文档移至 `docs/` 目录
- **🧹 代码清理**: 删除所有测试文件和冗余代码
- **📋 统一管理**: 整合项目文档，提供完整的使用指南

## 🚀 快速启动

### 推荐启动方式

```bash
# 使用图形化启动器（推荐）
python launcher.py

# 或直接启动主程序
python main.py

# 简化模式启动
python simple_main.py
```

## 系统概述

废弃物AI识别指导投放系统是一个基于计算机视觉和人工智能技术的智能垃圾分类指导系统。系统通过实时摄像头监控、AI图像识别、红外传感器IO控制和动画特效，为用户提供准确的垃圾分类指导和投放建议。

## 🚀 最新功能

### v1.0.0 - IO控制和动画功能版本

- **🔍 AI智能识别**：基于RKNN深度学习模型的实时垃圾识别
- **📡 红外传感器IO控制**：智能触发机制，只在检测到用户时进行识别
- **🎬 动画特效系统**：丰富的视觉反馈，包括粒子特效、脉冲动画、成功标记
- **🔊 语音指导功能**：中文语音播报分类结果和投放指导
- **📱 响应式界面**：三栏布局，自适应窗口大小调整

## 功能特性

### 核心功能
- **实时AI检测**：支持多种垃圾类型的实时识别
- **分类指导**：提供详细的垃圾分类说明和投放指导
- **语音播报**：中文语音合成技术，实时播报识别结果
- **用户界面**：现代化的图形界面，支持触摸和鼠标操作

### 新增功能
- **IO控制系统**：
  - 红外传感器监控用户接近
  - 智能触发AI检测，节省计算资源
  - 防抖处理，避免误触发
  - 超时保护，防止长时间占用
  - 模拟模式，便于开发和测试

- **动画系统**：
  - 等待动画：提示用户放置物品
  - 检测动画：显示AI检测过程
  - 成功动画：粒子特效+勾选标记
  - 错误动画：错误提示和重试引导
  - 响应式设计：适应不同屏幕尺寸

- **运动检测系统**：
  - 基于背景减除的运动检测
  - 大模型API集成识别
  - 实时可视化测试界面
  - 参数实时调节和优化
  - 检测结果统计分析

### 垃圾分类支持
- **可回收物**：塑料瓶、纸张、金属等
- **有害垃圾**：电池、药品、化学品等
- **湿垃圾**：食物残渣、果皮、菜叶等
- **干垃圾**：其他不可回收的垃圾

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     主界面 (MainWindow)                      │
├─────────────┬─────────────────┬─────────────────────────────┤
│  摄像头显示   │    动画播放区域    │       指导界面              │
│ (Camera)    │  (Animation)    │    (Guidance)              │
└─────────────┴─────────────────┴─────────────────────────────┘
       │              │                     │
       ▼              ▼                     ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────────────────────┐
│  检测工作器   │ │  动画组件    │ │       指导组件               │
│ (Detection) │ │ (Animation) │ │     (Guidance)             │
└─────────────┘ └─────────────┘ └─────────────────────────────┘
       │              │                     │
       ▼              ▼                     ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────────────────────┐
│ IO控制工作器 │ │  粒子系统    │ │       语音合成               │
│ (IO Control)│ │ (Particles) │ │    (Voice Guide)           │
└─────────────┘ └─────────────┘ └─────────────────────────────┘
       │
       ▼
┌─────────────┐
│ 红外传感器   │
│ (IR Sensor) │
└─────────────┘
```

## 技术栈

- **界面框架**：PySide6 (Qt6)
- **图像处理**：OpenCV
- **AI推理**：RKNN Toolkit Lite
- **语音合成**：PyTTSx3
- **硬件控制**：RPi.GPIO (树莓派)
- **配置管理**：JSON
- **日志系统**：Python logging

## 系统要求

### 硬件要求
- **处理器**：ARM Cortex-A72 或更高 (推荐树莓派4B)
- **内存**：4GB RAM 或更高
- **存储**：16GB 或更高的SD卡
- **摄像头**：USB摄像头或CSI摄像头
- **传感器**：红外传感器 (可选)
- **显示器**：支持1024x768分辨率或更高

### 软件要求
- **操作系统**：
  - Ubuntu 20.04+ (推荐)
  - Raspberry Pi OS Bullseye+
  - Windows 10+ (开发测试)
- **Python**：3.8 或更高版本
- **其他依赖**：见 requirements.txt

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd 废弃物AI识别指导投放项目

# 安装依赖
pip install -r requirements.txt

# 创建必要目录
mkdir -p logs data models
```

### 2. 硬件连接 (可选)

如果要使用IO控制功能，需要连接红外传感器：

```
红外传感器连接：
- VCC → 3.3V (Pin 1)
- GND → GND (Pin 6)
- OUT → GPIO 18 (Pin 12)
```

### 3. 配置系统

编辑 `config/system_config.json`：

```json
{
  "io_control": {
    "enable_io_control": true,        // 启用IO控制
    "ir_sensor_pin": 18,              // GPIO引脚号
    "detection_delay": 0.5,           // 检测延迟
    "detection_timeout": 10,          // 检测超时
    "debounce_time": 0.1             // 防抖时间
  },
  "animation": {
    "enable_animations": true,        // 启用动画
    "particle_count": 20,             // 粒子数量
    "animation_duration": 3000,       // 动画持续时间
    "pulse_animation_fps": 20         // 脉冲动画帧率
  }
}
```

### 4. 启动系统

```bash
# 方法1：使用完整功能启动脚本
python start_with_io.py

# 方法2：使用原始启动脚本
python main.py

# 方法3：使用简化启动脚本
python simple_main.py
```

### 5. 功能测试

```bash
# 测试IO控制和动画功能
python test_io_animation.py

# 测试系统核心功能
python test_system.py
```

## 使用说明

### 正常使用流程

1. **系统启动**
   - 启动应用程序
   - 系统自动初始化各个组件
   - 显示启动画面和功能状态

2. **用户交互**
   - 用户接近红外传感器（如果启用IO控制）
   - 系统播放等待动画，提示用户放置物品
   - 延迟0.5秒后开始AI检测

3. **AI检测**
   - 摄像头捕获图像
   - AI模型进行实时识别
   - 播放检测动画显示处理过程

4. **结果显示**
   - 识别成功：播放成功动画，显示分类结果
   - 识别失败：播放错误动画，显示错误信息
   - 语音播报分类结果和投放指导

5. **用户离开**
   - 红外信号消失
   - 系统停止检测，重置动画状态

### 界面说明

- **左侧区域**：实时摄像头显示，包含FPS和分辨率信息
- **中间区域**：动画播放区域，显示各种视觉反馈
- **右侧区域**：垃圾分类指导界面，显示分类卡片和检测结果

### 快捷键

- **F11**：全屏/窗口模式切换
- **Ctrl+Q**：退出程序
- **Esc**：退出全屏模式

## 配置说明

### 系统配置 (system_config.json)

```json
{
  "camera": {
    "device_id": 0,                   // 摄像头设备ID
    "resolution": {
      "width": 1280,
      "height": 720
    },
    "fps": 30,                        // 目标帧率
    "auto_focus": true,               // 自动对焦
    "exposure": -1                    // 曝光值 (-1为自动)
  },
  "ai_detection": {
    "model_path": "models/waste_detection.rknn",
    "input_size": 640,                // 模型输入尺寸
    "confidence_threshold": 0.6,      // 置信度阈值
    "nms_threshold": 0.45,            // NMS阈值
    "max_detections": 10,             // 最大检测数量
    "detection_interval": 0.1,        // 检测间隔
    "use_gpu": false                  // 是否使用GPU
  },
  "io_control": {
    "enable_io_control": true,        // 启用IO控制
    "ir_sensor_pin": 18,              // 红外传感器GPIO引脚
    "detection_delay": 0.5,           // 检测延迟时间(秒)
    "detection_timeout": 10,          // 检测超时时间(秒)
    "debounce_time": 0.1              // 防抖时间(秒)
  },
  "animation": {
    "enable_animations": true,        // 启用动画
    "particle_count": 20,             // 粒子特效数量
    "animation_duration": 3000,       // 动画持续时间(毫秒)
    "success_animation_duration": 2000, // 成功动画持续时间(毫秒)
    "pulse_animation_fps": 20         // 脉冲动画帧率
  },
  "ui": {
    "window_title": "废弃物AI识别指导投放系统",
    "fullscreen": false,              // 启动时全屏
    "window_size": {
      "width": 1024,
      "height": 768
    },
    "theme": "modern",                // 界面主题
    "language": "zh_CN",              // 语言
    "auto_hide_guidance": true,       // 自动隐藏指导
    "guidance_display_time": 5000     // 指导显示时间(毫秒)
  },
  "audio": {
    "enable_voice": true,             // 启用语音
    "voice_language": "zh",           // 语音语言
    "volume": 0.8,                    // 音量
    "speech_rate": 150                // 语音速度
  }
}
```

### 垃圾分类配置 (waste_classification.json)

```json
{
  "waste_categories": {
    "可回收物": {
      "color": "#0080ff",
      "icon": "♻️",
      "description": "可以回收利用的垃圾",
      "guidance": "请清洗干净后投放到蓝色可回收物垃圾桶"
    },
    "有害垃圾": {
      "color": "#ff0000",
      "icon": "☠️",
      "description": "对人体健康或环境有害的垃圾",
      "guidance": "请投放到红色有害垃圾桶"
    },
    "湿垃圾": {
      "color": "#8B4513",
      "icon": "🥬",
      "description": "易腐的生物质垃圾",
      "guidance": "请投放到棕色湿垃圾桶"
    },
    "干垃圾": {
      "color": "#808080",
      "icon": "🗑️",
      "description": "除有害垃圾、可回收物、湿垃圾以外的垃圾",
      "guidance": "请投放到黑色干垃圾桶"
    }
  },
  "ai_model": {
    "classes": [
      "plastic_bottle", "paper", "battery", "food_waste", "other"
    ],
    "class_mapping": {
      "plastic_bottle": "可回收物",
      "paper": "可回收物",
      "battery": "有害垃圾",
      "food_waste": "湿垃圾",
      "other": "干垃圾"
    }
  }
}
```

## 开发指南

### 目录结构

```
废弃物AI识别指导投放项目/
├── config/                 # 配置文件
│   ├── system_config.json
│   └── waste_classification.json
├── ui/                     # 界面模块
│   ├── main_window.py
│   ├── guidance_widget.py
│   └── animation_widget.py
├── worker/                 # 后台工作器
│   ├── waste_detection_worker.py
│   └── io_control_worker.py
├── utils/                  # 工具模块
│   ├── config_manager.py
│   ├── voice_guide.py
│   └── image_utils.py
├── models/                 # AI模型文件
├── data/                   # 数据文件
├── logs/                   # 日志文件
├── res/                    # 资源文件
├── main.py                 # 主启动脚本
├── start_with_io.py        # IO控制启动脚本
├── simple_main.py          # 简化启动脚本
├── test_io_animation.py    # IO动画测试
├── test_system.py          # 系统测试
└── requirements.txt        # 依赖列表
```

### 添加新功能

1. **添加新的垃圾分类**
   - 编辑 `waste_classification.json`
   - 添加新的分类和映射关系
   - 更新AI模型以支持新类别

2. **自定义动画效果**
   - 在 `AnimationWidget` 中添加新的动画类
   - 实现绘制和更新逻辑
   - 添加控制接口

3. **扩展传感器支持**
   - 修改 `IOControlWorker` 硬件接口
   - 添加新的传感器配置
   - 实现信号处理逻辑

### 调试和测试

```bash
# 启用调试模式
export DEBUG=1
python main.py

# 查看日志
tail -f logs/waste_detection.log

# 运行测试套件
python test_system.py
python test_io_animation.py

# 运行运动检测测试界面
python test_motion_detection.py

# 在主程序中使用运动检测测试
# → 设置菜单 → 运动检测测试界面
# → 检测菜单 → 显示运动检测结果
```

## 故障排除

### 常见问题

1. **摄像头无法打开**
   - 检查设备连接
   - 确认设备ID配置正确
   - 检查权限设置

2. **AI模型加载失败**
   - 确认模型文件存在
   - 检查RKNN库安装
   - 验证模型格式

3. **IO控制不工作**
   - 检查GPIO库安装
   - 确认硬件连接
   - 验证引脚配置

4. **动画不显示**
   - 检查动画配置
   - 确认PySide6版本
   - 查看错误日志

5. **语音播报失败**
   - 检查音频设备
   - 确认语音库安装
   - 验证语音配置

### 性能优化

1. **提高检测速度**
   - 降低输入图像分辨率
   - 调整检测间隔
   - 使用GPU加速

2. **减少资源占用**
   - 关闭不必要的动画
   - 降低动画帧率
   - 优化内存使用

3. **提高识别准确度**
   - 改善光照条件
   - 调整置信度阈值
   - 使用更好的模型

## 运动检测功能说明

## GIF显示问题解决方案

## 主界面布局优化说明

## IO控制和动画窗口功能升级说明

## IO控制和动画功能说明

## UI缩放问题修复说明

## 问题分析与解决方案

## 启动说明 