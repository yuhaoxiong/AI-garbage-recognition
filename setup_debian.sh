#!/bin/bash

# 废弃物AI识别指导投放系统 - Debian环境配置脚本
# 适用于 Debian 11/12, Ubuntu 20.04/22.04/24.04 等系统
# 作者: AI智能环保团队
# 版本: 1.0.0

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

log_success() {
    echo -e "${PURPLE}[SUCCESS]${NC} $1"
}

# 检查是否为root用户
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_warn "检测到root用户，建议使用普通用户运行此脚本"
        read -p "是否继续? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# 检测系统版本
detect_system() {
    log_step "检测系统版本..."
    
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
        log_info "检测到系统: $OS $VER"
    else
        log_error "无法检测系统版本"
        exit 1
    fi
    
    # 检查是否为支持的系统
    case $OS in
        "Debian GNU/Linux"|"Ubuntu"|"Raspbian GNU/Linux")
            log_success "系统支持，继续安装..."
            ;;
        *)
            log_warn "未测试的系统: $OS，可能存在兼容性问题"
            read -p "是否继续? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
            ;;
    esac
}

# 更新系统包
update_system() {
    log_step "更新系统包列表..."
    sudo apt update
    
    log_step "升级系统包..."
    sudo apt upgrade -y
    
    log_success "系统更新完成"
}

# 安装基础依赖
install_basic_deps() {
    log_step "安装基础依赖包..."
    
    local basic_packages=(
        "build-essential"
        "cmake"
        "pkg-config"
        "wget"
        "curl"
        "git"
        "unzip"
        "software-properties-common"
        "apt-transport-https"
        "ca-certificates"
        "gnupg"
        "lsb-release"
    )
    
    for package in "${basic_packages[@]}"; do
        log_info "安装 $package..."
        sudo apt install -y "$package"
    done
    
    log_success "基础依赖安装完成"
}

# 安装Python和pip
install_python() {
    log_step "安装Python 3.12和相关工具..."
    
    # 检查Python版本
    if command -v python3.12 &> /dev/null; then
        log_info "Python 3.12 已安装"
    else
        log_info "安装Python 3.12..."
        sudo apt install -y python3.12 python3.12-dev python3.12-venv
    fi
    
    # 安装pip
    if command -v pip3 &> /dev/null; then
        log_info "pip3 已安装"
    else
        log_info "安装pip..."
        sudo apt install -y python3-pip
    fi
    
    # 升级pip
    log_info "升级pip到最新版本..."
    python3.12 -m pip install --upgrade pip
    
    log_success "Python环境安装完成"
}

# 安装OpenCV依赖
install_opencv_deps() {
    log_step "安装OpenCV依赖库..."
    
    local opencv_packages=(
        "libopencv-dev"
        "python3-opencv"
        "libgtk-3-dev"
        "libavcodec-dev"
        "libavformat-dev"
        "libswscale-dev"
        "libv4l-dev"
        "libxvidcore-dev"
        "libx264-dev"
        "libjpeg-dev"
        "libpng-dev"
        "libtiff-dev"
        "gfortran"
        "openexr"
        "libatlas-base-dev"
        "libtbb2"
        "libtbb-dev"
        "libdc1394-22-dev"
        "libopenexr-dev"
        "libgstreamer-plugins-base1.0-dev"
        "libgstreamer1.0-dev"
    )
    
    for package in "${opencv_packages[@]}"; do
        log_info "安装 $package..."
        sudo apt install -y "$package" || log_warn "包 $package 安装失败，跳过..."
    done
    
    log_success "OpenCV依赖安装完成"
}

# 安装Qt6依赖
install_qt6_deps() {
    log_step "安装Qt6依赖库..."
    
    local qt6_packages=(
        "qt6-base-dev"
        "qt6-tools-dev"
        "qt6-tools-dev-tools"
        "libqt6widgets6"
        "libqt6gui6"
        "libqt6core6"
        "libqt6multimedia6"
        "libqt6multimediawidgets6"
        "qml6-module-qtquick"
        "qml6-module-qtquick-controls2"
    )
    
    for package in "${qt6_packages[@]}"; do
        log_info "安装 $package..."
        sudo apt install -y "$package" || log_warn "包 $package 安装失败，跳过..."
    done
    
    log_success "Qt6依赖安装完成"
}

# 安装音频依赖
install_audio_deps() {
    log_step "安装音频处理依赖..."
    
    local audio_packages=(
        "pulseaudio"
        "pulseaudio-utils"
        "alsa-utils"
        "libasound2-dev"
        "libpulse-dev"
        "espeak"
        "espeak-data"
        "libespeak-dev"
        "festival"
        "festvox-kallpc16k"
    )
    
    for package in "${audio_packages[@]}"; do
        log_info "安装 $package..."
        sudo apt install -y "$package" || log_warn "包 $package 安装失败，跳过..."
    done
    
    log_success "音频依赖安装完成"
}

# 安装GPIO依赖（仅树莓派）
install_gpio_deps() {
    log_step "检查是否为树莓派系统..."
    
    if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null || [[ "$OS" == "Raspbian GNU/Linux" ]]; then
        log_info "检测到树莓派系统，安装GPIO依赖..."
        
        local gpio_packages=(
            "python3-rpi.gpio"
            "python3-gpiozero"
            "rpi.gpio-common"
        )
        
        for package in "${gpio_packages[@]}"; do
            log_info "安装 $package..."
            sudo apt install -y "$package" || log_warn "包 $package 安装失败，跳过..."
        done
        
        log_success "GPIO依赖安装完成"
    else
        log_info "非树莓派系统，跳过GPIO依赖安装"
    fi
}

# 创建Python虚拟环境
create_venv() {
    log_step "创建Python虚拟环境..."
    
    local venv_dir="venv"
    
    if [[ -d "$venv_dir" ]]; then
        log_warn "虚拟环境已存在，是否重新创建? (y/N)"
        read -p "> " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$venv_dir"
        else
            log_info "跳过虚拟环境创建"
            return
        fi
    fi
    
    python3.12 -m venv "$venv_dir"
    log_success "虚拟环境创建完成"
    
    log_info "激活虚拟环境并升级pip..."
    source "$venv_dir/bin/activate"
    pip install --upgrade pip
    
    log_success "虚拟环境配置完成"
}

# 安装Python依赖包
install_python_deps() {
    log_step "安装Python依赖包..."
    
    if [[ ! -f "requirements.txt" ]]; then
        log_error "未找到requirements.txt文件"
        return 1
    fi
    
    # 激活虚拟环境
    if [[ -d "venv" ]]; then
        source venv/bin/activate
        log_info "已激活虚拟环境"
    fi
    
    log_info "安装requirements.txt中的依赖..."
    pip install -r requirements.txt
    
    log_success "Python依赖包安装完成"
}

# 配置摄像头权限
setup_camera_permissions() {
    log_step "配置摄像头权限..."
    
    # 将用户添加到video组
    sudo usermod -a -G video "$USER"
    
    # 创建udev规则
    sudo tee /etc/udev/rules.d/99-camera.rules > /dev/null <<EOF
# USB摄像头权限配置
SUBSYSTEM=="video4linux", GROUP="video", MODE="0664"
SUBSYSTEM=="usb", ATTRS{idVendor}=="*", ATTRS{idProduct}=="*", GROUP="video", MODE="0664"
EOF
    
    # 重新加载udev规则
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    
    log_success "摄像头权限配置完成"
}

# 创建桌面快捷方式
create_desktop_shortcut() {
    log_step "创建桌面快捷方式..."
    
    local desktop_file="$HOME/Desktop/废弃物AI识别系统.desktop"
    local current_dir=$(pwd)
    
    cat > "$desktop_file" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=废弃物AI识别指导投放系统
Comment=基于AI技术的智能垃圾分类指导系统
Exec=bash -c "cd '$current_dir' && source venv/bin/activate && python main.py"
Icon=$current_dir/res/icon.png
Terminal=false
Categories=Utility;Science;
StartupNotify=true
EOF
    
    chmod +x "$desktop_file"
    
    log_success "桌面快捷方式创建完成"
}

# 主函数
main() {
    echo -e "${CYAN}"
    echo "=================================================="
    echo "    废弃物AI识别指导投放系统 - 环境配置脚本"
    echo "=================================================="
    echo -e "${NC}"
    
    check_root
    detect_system
    
    log_step "开始安装依赖环境..."
    
    update_system
    install_basic_deps
    install_python
    install_opencv_deps
    install_qt6_deps
    install_audio_deps
    install_gpio_deps
    
    # 如果在项目目录中，则创建虚拟环境并安装Python依赖
    if [[ -f "requirements.txt" ]]; then
        create_venv
        install_python_deps
        setup_camera_permissions
        create_desktop_shortcut
    else
        log_warn "未在项目目录中运行，跳过Python依赖安装"
        log_info "请在项目根目录中运行此脚本以完成完整配置"
    fi
    
    echo -e "${GREEN}"
    echo "=================================================="
    echo "           环境配置完成！"
    echo "=================================================="
    echo -e "${NC}"
    
    log_success "所有依赖已安装完成"
    log_info "请重新登录或重启系统以使权限配置生效"
    
    if [[ -d "venv" ]]; then
        echo -e "${YELLOW}使用方法:${NC}"
        echo "1. 激活虚拟环境: source venv/bin/activate"
        echo "2. 运行程序: python main.py"
        echo "3. 或者直接双击桌面快捷方式"
    fi
}

# 运行主函数
main "$@"
