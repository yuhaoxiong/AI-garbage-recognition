# UI缩放问题修复说明

## 问题概述

用户反馈UI缩放窗口后显示不全的问题，主要表现为：
- 窗口缩小后内容溢出或被裁剪
- 组件尺寸不能动态适应窗口大小
- 分割器比例在小窗口中不合适
- 字体和图标大小不响应缩放

## 修复内容

### 1. 主窗口优化 (main_window.py)

#### 添加窗口最小尺寸限制
```python
# 设置窗口最小尺寸，防止缩放过小导致显示问题
self.setMinimumSize(800, 600)
```

#### 改进分割器管理
- 为摄像头和指导界面组件设置最小宽度
- 添加动态拉伸因子
- 响应窗口大小变化自动调整比例

```python
self.camera_widget.setMinimumWidth(300)
self.guidance_widget.setMinimumWidth(400)
self.splitter.setStretchFactor(0, 2)  # 左侧拉伸因子
self.splitter.setStretchFactor(1, 3)  # 右侧拉伸因子
```

#### 新增响应式resize事件处理
```python
def resizeEvent(self, event):
    """动态调整分割器比例"""
    window_width = self.width()
    
    if window_width < 900:
        # 小窗口：35% vs 65%
        self.splitter.setSizes([window_width * 0.35, window_width * 0.65])
    elif window_width < 1200:
        # 中等窗口：40% vs 60%
        self.splitter.setSizes([window_width * 0.4, window_width * 0.6])
    else:
        # 大窗口：45% vs 55%
        self.splitter.setSizes([window_width * 0.45, window_width * 0.55])
```

### 2. 摄像头组件优化

#### 响应式视频显示区域
- 将最小尺寸从640x480改为320x240，减少空间占用
- 添加拉伸因子，让视频区域能够动态适应
- 改进图像缩放逻辑，增加最小显示尺寸保护

```python
self.video_label.setMinimumSize(320, 240)  # 更小的最小尺寸
layout.addWidget(self.video_label, 1)      # 添加拉伸因子
```

#### 智能图像缩放
```python
min_size = min(label_size.width(), label_size.height())
if min_size < 200:  # 显示区域太小时的保护机制
    scaled_pixmap = pixmap.scaled(200, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
```

### 3. 指导界面组件优化 (guidance_widget.py)

#### CategoryCard响应式设计
- 图标尺寸从固定60x60改为弹性40-80像素范围
- 所有字体大小适度减小，适应小窗口显示
- 设置卡片最小尺寸160x120，确保基本可读性

```python
# 响应式图标
icon_label.setMinimumSize(40, 40)
icon_label.setMaximumSize(80, 80)

# 优化字体大小
title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))  # 从18减到14
desc_label.setFont(QFont("Microsoft YaHei", 9))              # 从10减到9
guidance_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))  # 从12减到10
```

#### 文本换行支持
- 为标题和描述添加`setWordWrap(True)`
- 确保长文本能够正确换行显示

### 4. 全局字体优化

- 主标题从20px减小到16px
- 按钮和状态栏保持合适的字体大小
- 确保所有文本在小窗口中仍然可读

## 使用建议

### 最佳窗口尺寸
- **最小推荐尺寸**：800x600（系统强制最小值）
- **理想尺寸**：1024x768或以上
- **全屏模式**：按F11切换，ESC退出

### 窗口缩放建议
1. **小屏幕设备**（<900px宽）：系统自动减少摄像头区域比例
2. **中等屏幕**（900-1200px）：平衡显示，40%摄像头+60%指导
3. **大屏幕**（>1200px）：给摄像头更多显示空间

### 分割器操作
- 拖动分割器手柄可手动调整左右区域比例
- 系统会在窗口大小变化时自动重新调整
- 每个区域都有最小宽度保护，防止过度压缩

## 测试验证

### 测试场景
1. **窗口缩放测试**：从最大化缩小到最小尺寸
2. **分割器测试**：拖动分割器到各种比例
3. **全屏测试**：F11全屏模式下的显示效果
4. **不同分辨率测试**：在不同屏幕分辨率下的适应性

### 预期效果
- ✅ 窗口可以缩放到800x600最小尺寸
- ✅ 所有文本和图标在最小窗口中仍然可读
- ✅ 摄像头画面自动适应显示区域
- ✅ 分类卡片在小空间中正确排列
- ✅ 分割器比例自动优化

## 技术要点

### 响应式设计原则
1. **最小尺寸保护**：防止组件缩放过小导致不可用
2. **动态比例调整**：根据窗口大小自动调整布局比例
3. **文本换行支持**：确保长文本能够正确显示
4. **智能缩放**：图像和图标有合理的缩放范围

### Qt布局管理
- 使用拉伸因子(stretch factor)控制组件缩放行为
- 通过最小/最大尺寸限制防止过度缩放
- 利用QSplitter的动态调整能力
- resizeEvent事件处理实现自动布局优化

## 故障排除

### 如果仍然出现显示问题：

1. **检查屏幕DPI设置**：高DPI屏幕可能需要额外的缩放设置
2. **更新Qt版本**：确保使用兼容的PySide6版本
3. **重启应用程序**：让新的尺寸设置生效
4. **检查系统资源**：确保有足够内存进行界面渲染

### 性能优化建议
- 在小窗口中，摄像头帧率可能会自动降低以提高性能
- 大量文本换行可能影响渲染性能，建议合理控制文本长度
- 频繁的窗口大小调整可能触发多次布局计算

## 更新记录

- **2025-07-14**: 完成UI缩放问题修复
  - 添加窗口最小尺寸限制
  - 优化分割器动态比例调整
  - 改进摄像头组件响应式设计
  - 优化分类卡片和字体大小
  - 添加响应式resize事件处理 