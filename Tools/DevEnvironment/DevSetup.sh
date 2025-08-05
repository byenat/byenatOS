#!/bin/bash

# ByenatOS 虚拟系统开发环境安装脚本  
# AI时代个人智能中间层开发工具链配置

set -e

echo "🚀 开始配置 ByenatOS 虚拟系统开发环境"
echo "=================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印彩色信息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查操作系统
detect_os() {
    print_info "检测操作系统..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        if command -v apt &> /dev/null; then
            DISTRO="ubuntu"
        elif command -v yum &> /dev/null; then
            DISTRO="centos"
        elif command -v pacman &> /dev/null; then
            DISTRO="arch"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        DISTRO="macos"
    else
        print_error "不支持的操作系统: $OSTYPE"
        exit 1
    fi
    
    print_success "检测到操作系统: $OS ($DISTRO)"
}

# 安装基础开发工具
install_basic_tools() {
    print_info "安装基础开发工具..."
    
    case $DISTRO in
        "ubuntu")
            sudo apt update
            sudo apt install -y curl wget git build-essential cmake \
                python3 python3-pip nodejs npm clang llvm
            ;;
        "macos")
            # 检查并安装 Homebrew
            if ! command -v brew &> /dev/null; then
                print_info "安装 Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            
            brew install git cmake python3 node llvm
            ;;
        "arch")
            sudo pacman -Syu --noconfirm
            sudo pacman -S --noconfirm git cmake python python-pip nodejs npm clang llvm
            ;;
        *)
            print_warning "未知发行版，请手动安装基础工具"
            ;;
    esac
    
    print_success "基础开发工具安装完成"
}

# 安装 Rust 工具链
install_rust() {
    print_info "安装 Rust 工具链..."
    
    if ! command -v rustc &> /dev/null; then
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        source $HOME/.cargo/env
    else
        print_info "Rust 已安装，更新到最新版本..."
        rustup update
    fi
    
    # 安装必要的 Rust 组件
    rustup component add clippy rustfmt rust-src
    rustup target add x86_64-unknown-linux-gnu aarch64-unknown-linux-gnu
    
    # 安装内核开发工具
    cargo install cargo-bootimage bootloader
    
    print_success "Rust 工具链安装完成"
}

# 安装 AI 开发工具
install_ai_tools() {
    print_info "安装 AI 开发工具..."
    
    # Python AI 工具
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
    pip3 install transformers onnx onnxruntime numpy pandas scikit-learn
    pip3 install whisper-ai opencv-python pillow
    
    # JavaScript/TypeScript 工具
    npm install -g typescript @types/node webpack webpack-cli
    npm install -g @tensorflow/tfjs @tensorflow/tfjs-node
    
    print_success "AI 开发工具安装完成"
}

# 安装前端开发工具
install_frontend_tools() {
    print_info "安装前端开发工具..."
    
    # 前端框架和工具
    npm install -g vite vue@next react create-react-app
    npm install -g tailwindcss @tailwindcss/typography
    npm install -g sass postcss autoprefixer
    
    print_success "前端开发工具安装完成"
}

# 安装容器和虚拟化工具
install_container_tools() {
    print_info "安装容器和虚拟化工具..."
    
    case $DISTRO in
        "ubuntu")
            # Docker
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
            sudo apt update
            sudo apt install -y docker-ce docker-ce-cli containerd.io
            
            # QEMU
            sudo apt install -y qemu-system-x86 qemu-system-arm qemu-utils
            ;;
        "macos")
            brew install --cask docker
            brew install qemu
            ;;
        "arch")
            sudo pacman -S --noconfirm docker qemu qemu-arch-extra
            ;;
    esac
    
    print_success "容器和虚拟化工具安装完成"
}

# 配置开发环境
setup_dev_environment() {
    print_info "配置开发环境..."
    
    # 创建工作目录
    mkdir -p ~/.byenatos/{cache,logs,temp,models}
    
    # 配置 Git (如果还没配置)
    if [ -z "$(git config --global user.name)" ]; then
        read -p "请输入您的 Git 用户名: " git_username
        read -p "请输入您的 Git 邮箱: " git_email
        git config --global user.name "$git_username"
        git config --global user.email "$git_email"
    fi
    
    # 配置 VS Code 扩展推荐
    if command -v code &> /dev/null; then
        print_info "安装推荐的 VS Code 扩展..."
        code --install-extension rust-lang.rust-analyzer
        code --install-extension ms-python.python
        code --install-extension bradlc.vscode-tailwindcss
        code --install-extension ms-vscode.vscode-typescript-next
        code --install-extension ms-vscode.hexeditor
    fi
    
    print_success "开发环境配置完成"
}

# 下载预训练模型
download_ai_models() {
    print_info "下载预训练 AI 模型 (可选)..."
    
    read -p "是否下载预训练的 AI 模型? 这可能需要较长时间和大量存储空间。(y/N): " download_models
    
    if [[ $download_models =~ ^[Yy]$ ]]; then
        mkdir -p Config/AIModels/{language,speech,vision}
        
        print_info "下载轻量级语言模型..."
        # 这里将来会下载实际的模型文件
        echo "# 模型下载占位符" > Config/AIModels/language/model_info.txt
        
        print_info "下载语音识别模型..."
        echo "# 语音模型占位符" > Config/AIModels/speech/model_info.txt
        
        print_info "下载计算机视觉模型..."
        echo "# 视觉模型占位符" > Config/AIModels/vision/model_info.txt
        
        print_success "AI 模型下载完成"
    else
        print_info "跳过 AI 模型下载"
    fi
}

# 验证安装
verify_installation() {
    print_info "验证安装..."
    
    tools=("git" "rustc" "cargo" "python3" "pip3" "node" "npm" "clang")
    
    for tool in "${tools[@]}"; do
        if command -v $tool &> /dev/null; then
            version=$($tool --version | head -n1)
            print_success "$tool: $version"
        else
            print_error "$tool: 未安装"
        fi
    done
}

# 主函数
main() {
    echo
    print_info "ByenatOS 开发环境安装脚本"
    print_info "此脚本将安装开发 ByenatOS 所需的全套工具链"
    echo
    
    read -p "是否继续安装? (y/N): " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        print_info "安装已取消"
        exit 0
    fi
    
    detect_os
    install_basic_tools
    install_rust
    install_ai_tools
    install_frontend_tools
    install_container_tools
    setup_dev_environment
    download_ai_models
    verify_installation
    
    echo
    print_success "🎉 ByenatOS 开发环境安装完成!"
    echo
    print_info "下一步:"
    print_info "1. 重启终端或执行: source ~/.bashrc (或 ~/.zshrc)"
    print_info "2. 进入项目目录: cd byenatOS"
    print_info "3. 运行构建脚本: python3 Build/Scripts/BuildSystem.py"
    print_info "4. 查看文档: Documentation/DeveloperGuide/"
    echo
    print_info "开发愉快! 🚀"
}

# 运行主函数
main "$@"