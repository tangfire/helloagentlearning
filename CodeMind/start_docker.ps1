# ==========================================
# Windows 中快速启动 Docker 容器的脚本
# 通过 WSL2 执行
# ==========================================

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "🚀 CodeMind Docker 容器快速启动脚本" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 获取脚本所在目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "📁 项目目录：$ScriptDir" -ForegroundColor Green
Write-Host ""

# 检查是否在 WSL2 中执行
Write-Host "🔧 通过 WSL2 启动 Docker 容器..." -ForegroundColor Yellow
Write-Host ""

# 在 WSL2 中执行启动脚本
wsl bash -c "cd $(wslpath $ScriptDir) && chmod +x start_docker_wsl.sh && ./start_docker_wsl.sh"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✅ 完成！" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "💡 现在可以测试数据库连接：" -ForegroundColor Yellow
Write-Host "   python test_database_connection.py" -ForegroundColor White
Write-Host ""
Write-Host "💡 然后启动 Web 应用：" -ForegroundColor Yellow
Write-Host "   python start_web_app.py" -ForegroundColor White
Write-Host ""
