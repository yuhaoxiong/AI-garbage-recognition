# GIF显示问题解决方案

## 问题描述
用户反馈：已经将gif图片放在对应文件夹并重命名成正确的文件名，但动画窗口依然显示默认文字而不是gif动画。

## 问题分析

### 1. 原始问题诊断
通过添加详细的日志记录，发现了以下问题：
- **路径问题**：最初使用相对路径，在不同工作目录下可能失效
- **尺寸问题**：gif文件原始尺寸为`QSize(-1, -1)`，导致显示异常
- **文本覆盖**：标签的文本和movie设置冲突

### 2. 解决方案实施

#### 2.1 路径问题修复
```python
# 修改前：使用相对路径
gif_dir = "res/gif"

# 修改后：使用绝对路径
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
gif_dir_path = os.path.join(script_dir, gif_dir)
```

#### 2.2 尺寸处理优化
```python
# 修改前：依赖原始尺寸
original_size = self.current_movie.scaledSize()
self.current_movie.setScaledSize(self.gif_label.size())

# 修改后：使用固定尺寸
label_size = self.gif_label.size()
if label_size.width() > 0 and label_size.height() > 0:
    scaled_size = label_size
else:
    scaled_size = QSize(400, 400)
self.current_movie.setScaledSize(scaled_size)
```

#### 2.3 文本清除机制
```python
# 在播放gif时清除文本
if self.current_movie.state() == QMovie.Running:
    self.gif_label.setText("")  # 清除文本确保gif显示
```

### 3. 当前状态验证

经过修复，测试日志显示：
- ✅ gif文件路径正确
- ✅ 文件存在且格式正确(GIF89a)
- ✅ QMovie创建成功，帧数27
- ✅ 标签尺寸正确(400x400)
- ✅ gif开始播放成功
- ✅ 文本已清除

## 可能的剩余问题

### 1. gif内容问题
**问题**：gif文件可能是透明的或者内容很淡
**解决方案**：
```bash
# 检查gif文件内容
ffmpeg -i res/gif/recyclable.gif -vf "showinfo" -f null -
```

### 2. 运行环境差异
**问题**：测试环境和实际使用环境可能不同
**解决方案**：
- 在实际使用的启动方式中测试
- 检查工作目录是否正确

### 3. 时序问题
**问题**：标签可能在gif加载后被重置
**解决方案**：添加状态检查
```python
def show_default_image(self):
    # 只有在没有播放gif时才显示默认文本
    if not self.current_movie or self.current_movie.state() != QMovie.Running:
        self.gif_label.setText("等待识别结果...")
```

## 推荐的测试步骤

### 1. 基础测试
```bash
# 运行简单的gif测试
python test_gif_display.py

# 运行动画窗口测试
python test_animation_window.py
```

### 2. 完整系统测试
```bash
# 运行完整的主程序
python main.py

# 或者使用IO控制启动
python start_with_io.py
```

### 3. 手动验证
1. 打开动画窗口
2. 手动触发识别结果
3. 观察gif是否正常播放
4. 检查控制台日志输出

## 故障排除

### 如果仍然看到默认文字
1. **检查控制台日志**：寻找错误信息
2. **验证gif文件**：确认文件不是空的或损坏的
3. **检查文件权限**：确保程序有读取权限
4. **重新启动程序**：清除可能的缓存

### 检查命令
```bash
# 查看gif文件信息
ls -la res/gif/

# 检查文件头
hexdump -C res/gif/recyclable.gif | head -2

# 查看文件大小
du -h res/gif/*.gif
```

## 配置确认

确保配置文件正确：
```json
{
  "animation": {
    "enable_animation_window": true,
    "gif_directory": "res/gif"
  }
}
```

## 最终验证

如果问题仍然存在，建议：
1. 重新录制或下载gif文件
2. 使用不同的gif查看器验证文件
3. 检查PySide6版本兼容性
4. 考虑使用其他格式(如MP4)作为备选方案

## 联系信息

如果问题持续存在，请提供：
- 控制台完整日志
- 系统环境信息
- 具体的重现步骤
- gif文件的详细信息 