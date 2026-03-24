"""
CodeMind Web 应用启动脚本

快速启动 FastAPI 后端和前端界面
"""

import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def check_dependencies():
    """检查依赖是否已安装"""
    required_packages = ['fastapi', 'uvicorn', 'python-multipart']
    
    print("🔍 检查依赖包...")
    missing = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"⚠️  发现未安装的依赖：{missing}")
        print("📦 正在安装...")
        
        subprocess.check_call([
            sys.executable, 
            '-m', 
            'pip', 
            'install', 
            *missing,
            '--quiet'
        ])
        
        print("✅ 依赖安装完成")
    else:
        print("✅ 所有依赖已就绪")

def start_server():
    """启动 Web 服务器"""
    print("\n" + "=" * 80)
    print("🚀 CodeMind Assistant Web 应用")
    print("=" * 80)
    
    # 检查依赖
    check_dependencies()
    
    # 检查必要文件
    required_files = [
        'web_api.py',
        'codemind_assistant.py',
        'mcp_client.py',
        'static/index.html'
    ]
    
    print("\n📁 检查项目文件...")
    for file in required_files:
        if not Path(file).exists():
            print(f"❌ 缺少必要文件：{file}")
            return False
        print(f"   ✓ {file}")
    
    print("\n🌐 启动 Web 服务器...")
    print("\n访问地址:")
    print("  📱 前端界面：http://localhost:8000")
    print("  📚 API 文档：http://localhost:8000/docs")
    print("  🔍 ReDoc:   http://localhost:8000/redoc")
    print("\n按 Ctrl+C 停止服务器\n")
    
    try:
        # 使用 uvicorn 启动
        import uvicorn
        uvicorn.run(
            "web_api:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level="info"
        )
        return True
        
    except KeyboardInterrupt:
        print("\n\n👋 服务器已停止")
        return True
    except Exception as e:
        print(f"\n❌ 启动失败：{e}")
        return False

def open_browser():
    """在浏览器中打开应用"""
    print("\n⏳ 等待服务器启动...")
    time.sleep(2)
    
    try:
        webbrowser.open('http://localhost:8000')
        print("✅ 已在浏览器中打开应用")
    except Exception as e:
        print(f"⚠️  无法自动打开浏览器：{e}")
        print("   请手动访问：http://localhost:8000")

if __name__ == "__main__":
    success = start_server()
    sys.exit(0 if success else 1)
