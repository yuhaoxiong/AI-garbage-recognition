#!/bin/bash
# -*- coding: utf-8 -*-
"""
Linux TTS引擎安装脚本 - 废弃物AI识别指导投放系统
自动安装和配置Linux系统下的高质量中文TTS引擎
"""

set -e

# 颜色输出函数
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 检查是否为root用户
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_warn "建议不要以root用户运行此脚本"
        read -p "是否继续? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# 检测Linux发行版
detect_distro() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        DISTRO=$ID
        VERSION=$VERSION_ID
    else
        log_error "无法检测Linux发行版"
        exit 1
    fi
    
    log_info "检测到系统: $PRETTY_NAME"
}

# 更新包管理器
update_package_manager() {
    log_step "更新包管理器..."
    
    case $DISTRO in
        ubuntu|debian)
            sudo apt-get update
            ;;
        fedora)
            sudo dnf update
            ;;
        centos|rhel)
            sudo yum update
            ;;
        arch)
            sudo pacman -Sy
            ;;
        *)
            log_warn "未知的发行版，跳过包管理器更新"
            ;;
    esac
}

# 安装基础依赖
install_base_dependencies() {
    log_step "安装基础依赖..."
    
    case $DISTRO in
        ubuntu|debian)
            sudo apt-get install -y python3 python3-pip python3-venv \
                build-essential portaudio19-dev python3-dev \
                alsa-utils pulseaudio
            ;;
        fedora)
            sudo dnf install -y python3 python3-pip python3-venv \
                gcc gcc-c++ portaudio-devel python3-devel \
                alsa-utils pulseaudio
            ;;
        centos|rhel)
            sudo yum install -y python3 python3-pip python3-venv \
                gcc gcc-c++ portaudio-devel python3-devel \
                alsa-utils pulseaudio
            ;;
        arch)
            sudo pacman -S --noconfirm python python-pip \
                base-devel portaudio alsa-utils pulseaudio
            ;;
        *)
            log_error "不支持的发行版: $DISTRO"
            exit 1
            ;;
    esac
}

# 安装Edge-TTS
install_edge_tts() {
    log_step "安装Edge-TTS (微软高质量TTS)..."
    
    pip3 install --user edge-tts
    
    # 测试Edge-TTS
    if command -v edge-tts >/dev/null 2>&1; then
        log_info "Edge-TTS安装成功"
        
        # 创建测试音频
        log_info "测试Edge-TTS中文语音..."
        edge-tts --voice zh-CN-XiaoxiaoNeural --text "这是Edge-TTS中文语音测试" --write-media test_edge_tts.mp3
        
        if [[ -f test_edge_tts.mp3 ]]; then
            log_info "Edge-TTS测试文件生成成功: test_edge_tts.mp3"
            # 尝试播放测试音频
            if command -v mpg123 >/dev/null 2>&1; then
                mpg123 test_edge_tts.mp3
            elif command -v ffplay >/dev/null 2>&1; then
                ffplay -nodisp -autoexit test_edge_tts.mp3
            else
                log_warn "没有找到音频播放器，无法播放测试文件"
            fi
            rm -f test_edge_tts.mp3
        fi
    else
        log_error "Edge-TTS安装失败"
    fi
}

# 安装espeak-ng
install_espeak_ng() {
    log_step "安装espeak-ng (改进版espeak)..."
    
    case $DISTRO in
        ubuntu|debian)
            sudo apt-get install -y espeak-ng espeak-ng-data
            ;;
        fedora)
            sudo dnf install -y espeak-ng
            ;;
        centos|rhel)
            # CentOS/RHEL可能需要EPEL仓库
            if ! rpm -q epel-release >/dev/null 2>&1; then
                sudo yum install -y epel-release
            fi
            sudo yum install -y espeak-ng
            ;;
        arch)
            sudo pacman -S --noconfirm espeak-ng
            ;;
        *)
            log_warn "尝试从源码编译espeak-ng..."
            install_espeak_ng_from_source
            return
            ;;
    esac
    
    # 测试espeak-ng
    if command -v espeak-ng >/dev/null 2>&1; then
        log_info "espeak-ng安装成功"
        
        # 测试中文语音
        log_info "测试espeak-ng中文语音..."
        espeak-ng -v zh "这是espeak-ng中文语音测试"
        
        # 检查中文语音包
        if espeak-ng --voices=zh | grep -q zh; then
            log_info "espeak-ng中文语音包已安装"
        else
            log_warn "espeak-ng中文语音包可能未正确安装"
        fi
    else
        log_error "espeak-ng安装失败"
    fi
}

# 从源码编译espeak-ng
install_espeak_ng_from_source() {
    log_step "从源码编译espeak-ng..."
    
    # 安装编译依赖
    case $DISTRO in
        ubuntu|debian)
            sudo apt-get install -y autotools-dev automake libtool pkg-config
            ;;
        fedora)
            sudo dnf install -y autoconf automake libtool pkgconfig
            ;;
        centos|rhel)
            sudo yum install -y autoconf automake libtool pkgconfig
            ;;
        arch)
            sudo pacman -S --noconfirm autoconf automake libtool pkgconf
            ;;
    esac
    
    # 下载和编译
    cd /tmp
    git clone https://github.com/espeak-ng/espeak-ng.git
    cd espeak-ng
    ./autogen.sh
    ./configure --prefix=/usr/local
    make
    sudo make install
    
    # 更新库路径
    sudo ldconfig
    
    cd - && rm -rf /tmp/espeak-ng
}

# 安装Festival
install_festival() {
    log_step "安装Festival语音合成系统..."
    
    case $DISTRO in
        ubuntu|debian)
            sudo apt-get install -y festival festvox-kallpc16k festvox-kdlpc16k
            ;;
        fedora)
            sudo dnf install -y festival festival-devel
            ;;
        centos|rhel)
            if ! rpm -q epel-release >/dev/null 2>&1; then
                sudo yum install -y epel-release
            fi
            sudo yum install -y festival
            ;;
        arch)
            sudo pacman -S --noconfirm festival festival-english
            ;;
        *)
            log_warn "不支持的发行版，跳过Festival安装"
            return
            ;;
    esac
    
    # 测试Festival
    if command -v festival >/dev/null 2>&1; then
        log_info "Festival安装成功"
        
        # 测试语音合成
        log_info "测试Festival语音..."
        echo "This is Festival TTS test" | festival --tts
    else
        log_error "Festival安装失败"
    fi
}

# 安装Ekho
install_ekho() {
    log_step "安装Ekho中文语音合成引擎..."
    
    case $DISTRO in
        ubuntu|debian)
            # 检查是否有ekho包
            if apt-cache search ekho | grep -q ekho; then
                sudo apt-get install -y ekho
            else
                log_warn "包管理器中没有ekho，尝试从源码编译..."
                install_ekho_from_source
            fi
            ;;
        fedora)
            if dnf search ekho | grep -q ekho; then
                sudo dnf install -y ekho
            else
                install_ekho_from_source
            fi
            ;;
        *)
            install_ekho_from_source
            ;;
    esac
    
    # 测试Ekho
    if command -v ekho >/dev/null 2>&1; then
        log_info "Ekho安装成功"
        
        # 测试中文语音
        log_info "测试Ekho中文语音..."
        ekho "这是余音中文语音测试"
    else
        log_warn "Ekho安装失败或不可用"
    fi
}

# 从源码编译Ekho
install_ekho_from_source() {
    log_step "从源码编译Ekho..."
    
    # 安装编译依赖
    case $DISTRO in
        ubuntu|debian)
            sudo apt-get install -y libsndfile1-dev libpulse-dev \
                libncurses5-dev libvorbis-dev
            ;;
        fedora)
            sudo dnf install -y libsndfile-devel pulseaudio-libs-devel \
                ncurses-devel libvorbis-devel
            ;;
        centos|rhel)
            sudo yum install -y libsndfile-devel pulseaudio-libs-devel \
                ncurses-devel libvorbis-devel
            ;;
        arch)
            sudo pacman -S --noconfirm libsndfile libpulse ncurses libvorbis
            ;;
    esac
    
    # 下载和编译
    cd /tmp
    git clone https://github.com/hgneng/ekho.git
    cd ekho
    ./configure
    make
    sudo make install
    
    # 更新库路径
    sudo ldconfig
    
    cd - && rm -rf /tmp/ekho
}

# 安装音频播放工具
install_audio_tools() {
    log_step "安装音频播放工具..."
    
    case $DISTRO in
        ubuntu|debian)
            sudo apt-get install -y mpg123 ffmpeg sox
            ;;
        fedora)
            sudo dnf install -y mpg123 ffmpeg sox
            ;;
        centos|rhel)
            # 可能需要RPM Fusion仓库
            sudo yum install -y mpg123 sox
            ;;
        arch)
            sudo pacman -S --noconfirm mpg123 ffmpeg sox
            ;;
    esac
}

# 配置音频系统
configure_audio() {
    log_step "配置音频系统..."
    
    # 确保用户在audio组中
    if ! groups $USER | grep -q audio; then
        sudo usermod -a -G audio $USER
        log_info "已将用户添加到audio组，需要重新登录生效"
    fi
    
    # 启动PulseAudio (如果未运行)
    if ! pgrep -x pulseaudio >/dev/null; then
        pulseaudio --start
        log_info "已启动PulseAudio"
    fi
    
    # 测试音频输出
    log_info "测试音频输出..."
    speaker-test -t sine -f 1000 -l 1 -s 1 || log_warn "音频测试失败，请检查音频设备"
}

# 安装Python依赖
install_python_dependencies() {
    log_step "安装Python TTS依赖..."
    
    # 升级pip
    pip3 install --user --upgrade pip
    
    # 安装TTS相关包
    pip3 install --user \
        pyttsx3 \
        pygame \
        edge-tts \
        requests \
        numpy
    
    log_info "Python TTS依赖安装完成"
}

# 创建测试脚本
create_test_script() {
    log_step "创建TTS测试脚本..."
    
    cat > test_tts_engines.py << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TTS引擎测试脚本
"""

import subprocess
import sys
import time

def test_edge_tts():
    """测试Edge-TTS"""
    print("测试Edge-TTS...")
    try:
        import edge_tts
        import asyncio
        
        async def test():
            communicate = edge_tts.Communicate("这是Edge-TTS中文测试", "zh-CN-XiaoxiaoNeural")
            await communicate.save("test_edge.mp3")
        
        asyncio.run(test())
        print("✓ Edge-TTS测试成功")
        return True
    except Exception as e:
        print(f"✗ Edge-TTS测试失败: {e}")
        return False

def test_espeak_ng():
    """测试espeak-ng"""
    print("测试espeak-ng...")
    try:
        subprocess.run(['espeak-ng', '-v', 'zh', '这是espeak-ng中文测试'], 
                      check=True, timeout=10)
        print("✓ espeak-ng测试成功")
        return True
    except Exception as e:
        print(f"✗ espeak-ng测试失败: {e}")
        return False

def test_festival():
    """测试Festival"""
    print("测试Festival...")
    try:
        process = subprocess.Popen(['festival', '--tts'], 
                                 stdin=subprocess.PIPE, 
                                 text=True)
        process.communicate(input="This is Festival TTS test")
        print("✓ Festival测试成功")
        return True
    except Exception as e:
        print(f"✗ Festival测试失败: {e}")
        return False

def test_ekho():
    """测试Ekho"""
    print("测试Ekho...")
    try:
        subprocess.run(['ekho', '这是余音中文测试'], 
                      check=True, timeout=10)
        print("✓ Ekho测试成功")
        return True
    except Exception as e:
        print(f"✗ Ekho测试失败: {e}")
        return False

def test_pyttsx3():
    """测试pyttsx3"""
    print("测试pyttsx3...")
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.say("这是pyttsx3中文测试")
        engine.runAndWait()
        print("✓ pyttsx3测试成功")
        return True
    except Exception as e:
        print(f"✗ pyttsx3测试失败: {e}")
        return False

if __name__ == "__main__":
    print("开始TTS引擎测试...\n")
    
    tests = [
        ("Edge-TTS", test_edge_tts),
        ("espeak-ng", test_espeak_ng),
        ("Festival", test_festival),
        ("Ekho", test_ekho),
        ("pyttsx3", test_pyttsx3),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n{'='*40}")
        success = test_func()
        results.append((name, success))
        time.sleep(1)
    
    print(f"\n{'='*40}")
    print("测试结果汇总:")
    for name, success in results:
        status = "✓ 可用" if success else "✗ 不可用"
        print(f"  {name:15} {status}")
    
    available_count = sum(1 for _, success in results if success)
    print(f"\n可用引擎数量: {available_count}/{len(tests)}")
    
    if available_count == 0:
        print("\n⚠️  没有可用的TTS引擎，请检查安装")
        sys.exit(1)
    else:
        print("\n🎉 至少有一个TTS引擎可用")
EOF
    
    chmod +x test_tts_engines.py
    log_info "测试脚本已创建: test_tts_engines.py"
}

# 主安装流程
main() {
    log_info "开始安装Linux TTS引擎..."
    
    check_root
    detect_distro
    
    # 询问用户要安装哪些引擎
    echo
    echo "请选择要安装的TTS引擎 (可多选):"
    echo "1) Edge-TTS (推荐 - 微软高质量TTS)"
    echo "2) espeak-ng (改进版espeak)"
    echo "3) Festival (传统TTS引擎)"
    echo "4) Ekho (专门的中文TTS)"
    echo "5) 全部安装"
    echo
    
    read -p "请输入选择 (例: 1,2,4 或 5): " choices
    
    # 解析选择
    install_edge=false
    install_espeak=false
    install_festival=false
    install_ekho=false
    
    if [[ "$choices" == *"5"* ]]; then
        install_edge=true
        install_espeak=true
        install_festival=true
        install_ekho=true
    else
        [[ "$choices" == *"1"* ]] && install_edge=true
        [[ "$choices" == *"2"* ]] && install_espeak=true
        [[ "$choices" == *"3"* ]] && install_festival=true
        [[ "$choices" == *"4"* ]] && install_ekho=true
    fi
    
    # 开始安装
    update_package_manager
    install_base_dependencies
    install_audio_tools
    configure_audio
    install_python_dependencies
    
    # 安装选定的TTS引擎
    $install_edge && install_edge_tts
    $install_espeak && install_espeak_ng
    $install_festival && install_festival
    $install_ekho && install_ekho
    
    # 创建测试脚本
    create_test_script
    
    echo
    log_info "安装完成！"
    log_info "运行 'python3 test_tts_engines.py' 来测试所有TTS引擎"
    echo
    log_info "推荐的TTS引擎优先级 (按质量排序):"
    log_info "1. Edge-TTS - 最高质量，需要网络连接"
    log_info "2. Ekho - 专为中文设计，离线工作"
    log_info "3. espeak-ng - 改进的espeak，支持多语言"
    log_info "4. Festival - 传统选择，主要支持英文"
    
    if groups $USER | grep -q audio; then
        log_info "请重新登录以使音频组权限生效"
    fi
}

# 运行主函数
main "$@"

