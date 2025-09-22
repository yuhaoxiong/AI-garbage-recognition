# Gif动画资源说明

## 目录结构

此目录用于存放垃圾分类对应的gif动画文件。

## 文件命名规则

请按照以下命名规则放置gif文件：

- `recyclable.gif` - 可回收物动画
- `hazardous.gif` - 有害垃圾动画
- `wet.gif` - 湿垃圾动画
- `dry.gif` - 干垃圾动画
- `default.gif` - 默认动画（可选）

## 文件要求

- **格式**: GIF格式
- **尺寸**: 建议400x400像素或以下
- **大小**: 建议每个文件不超过5MB
- **时长**: 建议2-5秒循环动画
- **帧率**: 建议15-25fps

## 使用方法

1. 将对应的gif文件复制到此目录
2. 确保文件名称正确
3. 重启应用程序或刷新动画窗口

## 示例动画建议

### 可回收物 (recyclable.gif)
- 回收符号旋转
- 塑料瓶变形回收
- 纸张折叠动画
- 蓝色主题

### 有害垃圾 (hazardous.gif)
- 警告符号闪烁
- 电池放电动画
- 危险品标识
- 红色主题

### 湿垃圾 (wet.gif)
- 食物残渣分解
- 植物生长动画
- 堆肥过程
- 棕色/绿色主题

### 干垃圾 (dry.gif)
- 垃圾桶装填
- 焚烧处理动画
- 填埋场景
- 灰色主题

## 注意事项

1. 确保gif文件可以正常播放
2. 避免过于复杂的动画影响性能
3. 保持动画循环播放的连贯性
4. 如果gif文件不存在，系统会显示文本替代

## 获取动画资源

可以从以下渠道获取或制作gif动画：

1. **在线资源**
   - 免费图标网站（如flaticon、iconfinder）
   - 动画资源网站（如Giphy、LottieFiles）

2. **自制动画**
   - 使用After Effects + Lottie
   - 使用Figma动画功能
   - 使用在线gif制作工具

3. **AI生成**
   - 使用AI动画生成工具
   - 提供文字描述生成动画

## 技术实现

动画显示使用PySide6的QMovie类：

```python
self.current_movie = QMovie(gif_path)
self.gif_label.setMovie(self.current_movie)
self.current_movie.start()
``` 