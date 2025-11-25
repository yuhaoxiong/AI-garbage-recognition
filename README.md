# 废弃物AI识别指导投放系统

面向线下投放点的智能垃圾分类指导系统。通过摄像头取流、运动检测与（可选）AI识别，实时给出分类结果、动画引导与语音提示。

## ✨ 功能特点

- 🎥 实时摄像头取流与显示（平滑、低延迟）
- 🏃 运动检测触发拍照与识别（可独立于本地模型）
- 🤖 AI识别接入（可选：本地RKNN或云端API）
- 🎨 动态状态面板（等待/检测/识别中/成功）
- 🔊 语音播报（欢迎语、检测提示、分类指导）
- 🗣️ 语音助手（可选：唤醒词“小蔚/小蔚小蔚” + 大模型问答）
- ⚙️ 图形化参数配置（摄像头/运动检测/API/动画/音频等）

## 🚀 快速开始

### 环境要求
- Python 3.10+（建议 3.12）
- Windows 10/11 或 Linux
- USB 摄像头

### 安装
```bash
pip install -r requirements.txt
```

### 启动
```bash
# 直接启动主程序（推荐）
python main.py

# 可选：使用启动器（图形化检查与一键启动）
python launcher.py
```

## 🏗️ 架构与模块

```
ui/                  # 界面
  ├─ main_window.py  # 主窗口（摄像头 + 动态状态）
  ├─ dynamic_status_widget.py  # 状态面板
  ├─ guidance_widget.py        # 结果与指导（备用展示）
  ├─ animation_window.py       # 叠加动画窗口（可选）
worker/              # 工作线程
  ├─ waste_detection_worker.py       # 摄像头取流与基础检测
  ├─ motion_detection_worker.py      # 运动检测 + API识别流程
  └─ io_control_worker.py            # 红外/IO 触发
utils/               # 工具与服务
  ├─ config_manager.py, api_client.py, voice_* 等
config/              # JSON 配置
res/gif/             # 动画资源
```

状态流简述：等待 → 检测到物体 → 识别中 → 成功/失败 → 恢复等待

## ⚙️ 配置概览

`config/system_config.json` 关键字段示例：

```json
{
  "camera": {"device_id": 0, "width": 1280, "height": 720, "fps": 30},
  "motion_detection": {"motion_threshold": 800, "min_contour_area": 1500, "detection_cooldown": 15.0},
  "io_control": {"enable_io_control": true, "ir_sensor_pin": 18, "detection_delay": 0.5, "detection_timeout": 10, "debounce_time": 0.1},
  "animation": {"enable_animations": true, "pulse_animation_fps": 20},
  "ui": {"window_title": "废弃物AI识别指导投放系统", "fullscreen": false, "window_size": {"width": 1200, "height": 800}, "theme": "modern"},
  "audio": {"enable_voice": true, "voice_language": "zh", "volume": 0.8, "speech_rate": 150},
  "api": {"base_url": "https://api.example.com", "api_key": "", "timeout": 30}
}
```

`config/waste_classification.json` 维护分类的颜色、图标与投放指导文本。

## 🧭 使用流程

1) 启动程序后进入“等待检测”。
2) 画面出现物体运动时触发“检测到物体”。
3) 自动拍照并进入“识别中”（本地或API）。
4) 识别成功后显示结果、投放指导并播报语音。

### 语音助手（可选）

1. 在 `config/system_config.json` 中开启：
   ```json
   "voice_assistant": { "enable_voice_assistant": true }
   ```
2. 在菜单“设置”中可切换“语音助手”，唤醒词默认为“小蔚”或“小蔚小蔚”。
3. 在“参数配置”对话框新增“🗣️ 语音助手”与“🤖 LLM”页签，可设置ASR/模型/密钥等。
4. 依赖：Windows/Linux 需 `speechrecognition`；Linux 可选 `vosk` 离线识别。

## 🛠️ 常见问题

- 摄像头无法打开：检查设备占用，调整 `camera.device_id`。
- 识别延迟较高：降低分辨率/帧率，或改用运动检测+API方案。
- 动画不显示：确认 `animation.enable_animations` 为 true。
- 无语音：安装可选依赖 `pyttsx3` 与 `pygame`，并开启 `audio.enable_voice`。

## 📈 性能建议

- 低配设备：降低分辨率与FPS、减少动画、增大检测冷却时间。
- 高配设备：开启更高分辨率、提高FPS、启用多线程与GPU（如使用RKNN）。

## 📚 深入文档

- docs/系统文档.md（总体说明）
- docs/运动检测功能说明.md（算法与参数）
- docs/IO控制和动画功能说明.md（红外与动画）
- docs/参数配置界面说明.md（图形化参数配置）

---

版权归项目所有。欢迎用于教学与实验，商用请先沟通授权。