# IO控制和动画窗口功能升级说明

## 功能概述

本次升级为废弃物AI识别指导投放系统增加了以下重要功能：

### 🆕 新增功能

1. **主界面IO控制开关**
   - 在菜单栏增加IO控制开关
   - 可以实时启用/禁用IO控制功能
   - 状态栏显示IO控制状态

2. **独立动画窗口**
   - 专门的动画显示窗口
   - 支持gif动画播放
   - 增强的粒子特效系统
   - 可调节的动画参数

3. **Gif动画支持**
   - 按垃圾分类显示对应gif动画
   - 自动文件映射和加载
   - 文本替代方案

4. **改进的用户体验**
   - 置顶窗口选项
   - 实时状态监控
   - 丰富的控制面板

## 主要改进

### 1. 主界面功能增强

#### 菜单栏新增项目
- **设置** → **IO控制(&I)**: 可勾选的IO控制开关
- **设置** → **动画窗口(&A)**: 打开动画窗口

#### 状态栏新增显示
- **IO**: 显示IO控制状态（启用/禁用）
- **动画**: 显示动画窗口状态（打开/关闭）

#### 功能集成
- IO控制状态实时更新
- 动画窗口自动显示识别结果
- 配置文件自动保存

### 2. 独立动画窗口

#### 窗口特性
- **尺寸**: 900x700像素
- **布局**: 左侧gif显示，右侧粒子特效
- **控制**: 完整的参数调节面板

#### 主要功能
- **Gif动画播放**: 根据垃圾分类自动播放对应gif
- **粒子特效**: 可调节的粒子系统
- **手动测试**: 四个分类的测试按钮
- **参数控制**: 粒子数量、重力等可调节
- **窗口设置**: 置顶显示、重置功能

### 3. Gif动画系统

#### 文件映射
```
res/gif/
├── recyclable.gif  # 可回收物
├── hazardous.gif   # 有害垃圾
├── wet.gif         # 湿垃圾
├── dry.gif         # 干垃圾
└── default.gif     # 默认动画（可选）
```

#### 技术特性
- **自动加载**: 系统启动时自动扫描gif文件
- **智能适配**: 自动调整gif尺寸适应显示区域
- **错误处理**: 文件不存在时显示文本替代
- **性能优化**: QMovie对象的合理管理

### 4. 粒子特效系统增强

#### 新增特性
- **粒子轨迹**: 显示粒子运动轨迹
- **边界反弹**: 粒子碰撞边界时反弹
- **重力效果**: 可调节的重力参数
- **生命周期**: 粒子透明度渐变效果

#### 可调节参数
- **粒子数量**: 10-100个
- **重力强度**: 0-0.5
- **动画时长**: 5秒循环
- **颜色主题**: 根据垃圾分类自动调整

## 使用方法

### 1. 基本使用流程

1. **启动系统**
   ```bash
   python start_with_io.py
   ```

2. **打开动画窗口**
   - 菜单栏 → 设置 → 动画窗口
   - 或在识别到垃圾时自动弹出

3. **测试动画效果**
   - 使用动画窗口的测试按钮
   - 或进行实际的垃圾识别

4. **调整参数**
   - 使用滑块调节粒子数量和重力
   - 勾选"窗口置顶"保持窗口在最前

### 2. IO控制使用

1. **启用IO控制**
   - 菜单栏 → 设置 → IO控制（勾选）
   - 状态栏显示"IO: 启用"

2. **禁用IO控制**
   - 菜单栏 → 设置 → IO控制（取消勾选）
   - 状态栏显示"IO: 禁用"

3. **状态监控**
   - 通过状态栏实时查看IO状态
   - 日志文件记录详细操作信息

### 3. 自定义Gif动画

1. **准备gif文件**
   - 格式: GIF
   - 尺寸: 建议400x400px
   - 大小: 建议<5MB

2. **放置文件**
   ```
   res/gif/
   ├── recyclable.gif  # 可回收物
   ├── hazardous.gif   # 有害垃圾
   ├── wet.gif         # 湿垃圾
   └── dry.gif         # 干垃圾
   ```

3. **重启应用**
   - 重新启动系统加载新的gif文件
   - 或使用动画窗口的测试功能验证

## 技术实现

### 1. 主窗口集成

#### 新增组件
```python
# 动画窗口
self.animation_window = AnimationWindow(self)

# IO控制开关
self.io_control_action = QAction('IO控制(&I)', self)
self.io_control_action.setCheckable(True)
```

#### 信号处理
```python
# 检测结果处理
def _on_detection_result(self, results):
    if results and self.animation_window:
        first_result = results[0]
        self.animation_window.show_category_animation(first_result.waste_category)
```

### 2. 动画窗口架构

#### 主要组件
- **GifDisplayWidget**: Gif动画显示
- **ParticleEffectWidget**: 粒子特效系统
- **AnimationWindow**: 主窗口容器

#### 关键技术
```python
# Gif播放
self.current_movie = QMovie(gif_path)
self.gif_label.setMovie(self.current_movie)
self.current_movie.start()

# 粒子系统
def update_particles(self):
    for particle in self.particles:
        particle['x'] += particle['vx']
        particle['y'] += particle['vy']
        particle['life'] -= 0.015
```

### 3. 配置管理

#### 新增配置项
```json
{
  "animation": {
    "enable_animation_window": true,
    "animation_window_always_on_top": false,
    "gif_directory": "res/gif"
  }
}
```

#### 配置更新
```python
def _toggle_io_control(self, checked):
    self.config_manager.update_config('system', 'io_control.enable_io_control', checked)
```

## 测试方法

### 1. 动画窗口测试

```bash
# 独立测试动画窗口
python test_animation_window.py
```

功能测试：
- 窗口显示/隐藏
- 四种分类动画播放
- 参数调节效果
- 状态实时更新

### 2. 完整系统测试

```bash
# 完整功能测试
python start_with_io.py
```

测试流程：
1. 启动系统检查动画窗口初始化
2. 菜单栏IO控制开关测试
3. 识别垃圾时动画窗口自动弹出
4. 动画效果和参数调节

### 3. IO控制测试

```bash
# IO控制和动画联合测试
python test_io_animation.py
```

测试内容：
- IO控制工作器状态
- 动画窗口集成效果
- 信号传递正确性

## 配置文件更新

### system_config.json新增项
```json
{
  "io_control": {
    "enable_io_control": true,
    "ir_sensor_pin": 18,
    "detection_delay": 0.5,
    "detection_timeout": 10,
    "debounce_time": 0.1
  },
  "animation": {
    "enable_animations": true,
    "particle_count": 20,
    "animation_duration": 3000,
    "success_animation_duration": 2000,
    "pulse_animation_fps": 20,
    "enable_animation_window": true,
    "animation_window_always_on_top": false,
    "gif_directory": "res/gif"
  }
}
```

## 文件结构

### 新增文件
```
废弃物AI识别指导投放项目/
├── ui/
│   └── animation_window.py          # 独立动画窗口
├── res/
│   └── gif/                         # Gif资源目录
│       ├── README.md                # 资源说明
│       ├── recyclable.gif           # 可回收物动画
│       ├── hazardous.gif            # 有害垃圾动画
│       ├── wet.gif                  # 湿垃圾动画
│       └── dry.gif                  # 干垃圾动画
├── test_animation_window.py         # 动画窗口测试
└── IO控制和动画窗口功能升级说明.md   # 本说明文件
```

### 修改文件
```
├── ui/main_window.py                # 集成动画窗口和IO开关
├── config/system_config.json       # 新增配置项
├── start_with_io.py                # 更新启动说明
└── 其他相关文件...
```

## 注意事项

### 1. 资源管理
- 确保gif文件存在且可读
- 注意gif文件大小影响性能
- 动画窗口会占用额外内存

### 2. 性能考虑
- 粒子数量过多可能影响帧率
- 同时播放多个动画时注意CPU使用
- 长时间运行需要监控内存占用

### 3. 兼容性
- 确保PySide6版本支持QMovie
- 某些gif格式可能不被支持
- 跨平台的文件路径处理

### 4. 用户体验
- 动画窗口可能遮挡主界面
- 建议合理设置窗口位置
- 提供足够的用户控制选项

## 故障排除

### 1. 动画窗口无法打开
- 检查动画配置是否启用
- 确认PySide6库完整性
- 查看日志文件错误信息

### 2. Gif不显示
- 检查gif文件是否存在
- 确认文件路径正确
- 验证gif文件格式

### 3. 粒子效果异常
- 检查QPainter绘制权限
- 确认动画定时器正常
- 验证粒子参数范围

### 4. IO控制开关无效
- 检查配置文件写入权限
- 确认IO控制工作器初始化
- 验证GPIO库安装情况

## 后续扩展

### 1. 功能增强
- 支持更多动画格式（mp4、webp等）
- 添加音效配合动画
- 自定义动画参数保存

### 2. 性能优化
- 动画缓存机制
- GPU加速渲染
- 内存使用优化

### 3. 用户界面
- 动画预览功能
- 拖拽式gif替换
- 动画编辑器集成

---

**版本**: 1.1.0  
**更新日期**: 2024-12-15  
**主要更新**: IO控制开关、独立动画窗口、Gif动画支持 