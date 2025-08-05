#!/bin/bash
set -e

# ByenatOS 安装脚本
# 支持 Linux、macOS 和 Windows (WSL)

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        if command -v apt-get &> /dev/null; then
            DISTRO="debian"
        elif command -v yum &> /dev/null; then
            DISTRO="rhel"
        elif command -v pacman &> /dev/null; then
            DISTRO="arch"
        else
            DISTRO="unknown"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        DISTRO="macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        OS="windows"
        DISTRO="windows"
    else
        log_error "不支持的操作系统: $OSTYPE"
    fi
    
    log_info "检测到操作系统: $OS ($DISTRO)"
}

# 检查依赖
check_dependencies() {
    log_info "检查系统依赖..."
    
    local missing_deps=()
    
    # 检查必需的命令
    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi
    
    if ! command -v git &> /dev/null; then
        missing_deps+=("git")
    fi
    
    if ! command -v docker &> /dev/null; then
        log_warning "Docker未安装，将安装Docker版本"
        INSTALL_MODE="docker"
    else
        log_info "Docker已安装"
    fi
    
    # 检查编译环境 (如果选择源码安装)
    if [[ "$INSTALL_MODE" == "source" ]]; then
        if ! command -v rustc &> /dev/null; then
            missing_deps+=("rust")
        fi
        
        if ! command -v python3 &> /dev/null; then
            missing_deps+=("python3")
        fi
        
        if ! command -v node &> /dev/null; then
            missing_deps+=("nodejs")
        fi
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_warning "缺少以下依赖: ${missing_deps[*]}"
        install_dependencies "${missing_deps[@]}"
    fi
}

# 安装依赖
install_dependencies() {
    local deps=("$@")
    log_info "安装依赖: ${deps[*]}"
    
    case $DISTRO in
        "debian")
            sudo apt-get update
            for dep in "${deps[@]}"; do
                case $dep in
                    "rust")
                        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
                        source ~/.cargo/env
                        ;;
                    "python3")
                        sudo apt-get install -y python3 python3-pip python3-venv
                        ;;
                    "nodejs")
                        curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
                        sudo apt-get install -y nodejs
                        ;;
                    *)
                        sudo apt-get install -y "$dep"
                        ;;
                esac
            done
            ;;
        "rhel")
            for dep in "${deps[@]}"; do
                case $dep in
                    "rust")
                        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
                        source ~/.cargo/env
                        ;;
                    "python3")
                        sudo yum install -y python3 python3-pip
                        ;;
                    "nodejs")
                        curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
                        sudo yum install -y nodejs
                        ;;
                    *)
                        sudo yum install -y "$dep"
                        ;;
                esac
            done
            ;;
        "macos")
            # 检查并安装 Homebrew
            if ! command -v brew &> /dev/null; then
                log_info "安装 Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            
            for dep in "${deps[@]}"; do
                case $dep in
                    "rust")
                        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
                        source ~/.cargo/env
                        ;;
                    "python3")
                        brew install python3
                        ;;
                    "nodejs")
                        brew install node
                        ;;
                    *)
                        brew install "$dep"
                        ;;
                esac
            done
            ;;
        *)
            log_error "不支持的发行版，请手动安装依赖: ${deps[*]}"
            ;;
    esac
}

# Docker安装
install_docker() {
    log_info "使用Docker安装ByenatOS..."
    
    # 下载 docker-compose.yml
    if [[ ! -f "docker-compose.yml" ]]; then
        log_info "下载Docker配置文件..."
        curl -fsSL https://raw.githubusercontent.com/byenatos/byenatos/main/docker-compose.yml -o docker-compose.yml
    fi
    
    # 创建数据目录
    mkdir -p ~/.byenatos/{data,logs,config}
    
    # 启动服务
    log_info "启动ByenatOS服务..."
    docker-compose up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30
    
    # 健康检查
    if curl -f http://localhost:8080/health &> /dev/null; then
        log_success "ByenatOS 已成功安装并运行在 http://localhost:8080"
    else
        log_error "服务启动失败，请检查日志: docker-compose logs"
    fi
}

# 源码安装
install_from_source() {
    log_info "从源码安装ByenatOS..."
    
    # 克隆代码库
    if [[ ! -d "byenatos" ]]; then
        log_info "克隆代码库..."
        git clone https://github.com/byenatos/byenatos.git
        cd byenatos
    else
        cd byenatos
        git pull origin main
    fi
    
    # 设置开发环境
    log_info "设置开发环境..."
    ./Tools/DevEnvironment/DevSetup.sh
    
    # 构建项目
    log_info "构建项目..."
    ./Scripts/build.sh
    
    # 运行测试
    log_info "运行测试..."
    ./Scripts/test.sh
    
    # 安装服务
    log_info "安装系统服务..."
    sudo ./Scripts/install_service.sh
    
    log_success "ByenatOS 已从源码安装完成"
}

# 预编译二进制安装
install_binary() {
    log_info "安装预编译二进制文件..."
    
    # 检测架构
    ARCH=$(uname -m)
    case $ARCH in
        "x86_64")
            ARCH="x64"
            ;;
        "aarch64" | "arm64")
            ARCH="arm64"
            ;;
        *)
            log_error "不支持的架构: $ARCH"
            ;;
    esac
    
    # 下载最新版本
    LATEST_VERSION=$(curl -s https://api.github.com/repos/byenatos/byenatos/releases/latest | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/')
    DOWNLOAD_URL="https://github.com/byenatos/byenatos/releases/download/${LATEST_VERSION}/byenatos-${OS}-${ARCH}.tar.gz"
    
    log_info "下载 ByenatOS ${LATEST_VERSION} for ${OS}-${ARCH}..."
    curl -fsSL "$DOWNLOAD_URL" -o byenatos.tar.gz
    
    # 解压安装
    log_info "安装到 /opt/byenatos..."
    sudo mkdir -p /opt/byenatos
    sudo tar -xzf byenatos.tar.gz -C /opt/byenatos --strip-components=1
    
    # 创建符号链接
    sudo ln -sf /opt/byenatos/bin/byenatos /usr/local/bin/byenatos
    
    # 创建配置目录
    mkdir -p ~/.byenatos/{data,logs,config}
    
    # 安装系统服务
    sudo /opt/byenatos/scripts/install_service.sh
    
    # 清理
    rm byenatos.tar.gz
    
    log_success "ByenatOS 已安装完成"
}

# 主安装流程
main() {
    log_info "开始安装 ByenatOS..."
    
    # 检测操作系统
    detect_os
    
    # 询问安装方式
    if [[ -z "$INSTALL_MODE" ]]; then
        echo
        echo "请选择安装方式:"
        echo "1) Docker (推荐，快速部署)"
        echo "2) 预编译二进制 (生产环境)"
        echo "3) 源码编译 (开发者)"
        echo
        read -p "请输入选择 (1-3): " choice
        
        case $choice in
            1)
                INSTALL_MODE="docker"
                ;;
            2)
                INSTALL_MODE="binary"
                ;;
            3)
                INSTALL_MODE="source"
                ;;
            *)
                log_error "无效选择"
                ;;
        esac
    fi
    
    # 检查依赖
    check_dependencies
    
    # 执行安装
    case $INSTALL_MODE in
        "docker")
            install_docker
            ;;
        "binary")
            install_binary
            ;;
        "source")
            install_from_source
            ;;
    esac
    
    # 显示后续步骤
    echo
    log_success "安装完成！"
    echo
    echo "后续步骤:"
    echo "1. 访问管理面板: http://localhost:8082"
    echo "2. 查看API文档: http://localhost:8080/docs"
    echo "3. 阅读开发者指南: https://docs.byenatos.org"
    echo
    echo "获取帮助:"
    echo "- GitHub: https://github.com/byenatos/byenatos"
    echo "- 社区: https://community.byenatos.org"
    echo "- 文档: https://docs.byenatos.org"
}

# 脚本入口
main "$@"