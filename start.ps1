# PowerShell 启动脚本 - 企业诊断报告平台
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "🏢 企业 RAG 知识库与 PPT 诊断报告生成平台" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python 环境
Write-Host "📋 检查 Python 环境..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ 未找到 Python 环境，请先安装 Python 3.8+" -ForegroundColor Red
    exit 1
}

# 检查虚拟环境
if (Test-Path ".venv") {
    Write-Host "✅ 检测到虚拟环境" -ForegroundColor Green
    Write-Host "💡 提示：使用 .venv\Scripts\Activate.ps1 激活虚拟环境" -ForegroundColor Cyan
} else {
    Write-Host "⚠️  未检测到虚拟环境" -ForegroundColor Yellow
    Write-Host "💡 建议：创建虚拟环境 python -m venv .venv" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "📋 可用功能" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. 数据库迁移（首次使用）" -ForegroundColor White
Write-Host "  2. 安装依赖" -ForegroundColor White
Write-Host "  3. 启动 Web 服务" -ForegroundColor White
Write-Host "  4. 查看 API 文档" -ForegroundColor White
Write-Host "  5. 退出" -ForegroundColor White
Write-Host ""

$choice = Read-Host "请选择操作 (1-5)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "============================================" -ForegroundColor Cyan
        Write-Host "🔧 执行数据库迁移" -ForegroundColor Cyan
        Write-Host "============================================" -ForegroundColor Cyan
        
        if (Test-Path "CodeMind\migrate_database.py") {
            python CodeMind/migrate_database.py
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host ""
                Write-Host "🎉 数据库迁移完成！" -ForegroundColor Green
                Write-Host "💡 现在可以选择选项 3 启动服务" -ForegroundColor Cyan
            } else {
                Write-Host ""
                Write-Host "❌ 数据库迁移失败，请检查错误信息" -ForegroundColor Red
            }
        } else {
            Write-Host "❌ 未找到迁移脚本" -ForegroundColor Red
        }
        
        Write-Host ""
        Read-Host "按回车键返回"
        & $PSCommandPath
    }
    
    "2" {
        Write-Host ""
        Write-Host "============================================" -ForegroundColor Cyan
        Write-Host "📦 安装依赖" -ForegroundColor Cyan
        Write-Host "============================================" -ForegroundColor Cyan
        
        if (Test-Path "requirements.txt") {
            pip install -r requirements.txt
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host ""
                Write-Host "✅ 依赖安装完成！" -ForegroundColor Green
            } else {
                Write-Host ""
                Write-Host "❌ 依赖安装失败" -ForegroundColor Red
            }
        } else {
            Write-Host "❌ 未找到 requirements.txt" -ForegroundColor Red
        }
        
        Write-Host ""
        Read-Host "按回车键返回"
        & $PSCommandPath
    }
    
    "3" {
        Write-Host ""
        Write-Host "============================================" -ForegroundColor Cyan
        Write-Host "🚀 启动 Web 服务" -ForegroundColor Cyan
        Write-Host "============================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "访问地址:" -ForegroundColor Yellow
        Write-Host "  📱 原有界面：http://localhost:8000" -ForegroundColor Cyan
        Write-Host "  🏢 企业诊断平台：http://localhost:8000/enterprise" -ForegroundColor Cyan
        Write-Host "  📚 API 文档：http://localhost:8000/docs" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "按 Ctrl+C 停止服务" -ForegroundColor Yellow
        Write-Host ""
        
        # 启动服务
        Set-Location CodeMind\web_app
        uvicorn web_api:app --host 0.0.0.0 --port 8000 --reload
        
        Set-Location ..\..
    }
    
    "4" {
        Write-Host ""
        Write-Host "============================================" -ForegroundColor Cyan
        Write-Host "📚 API 文档" -ForegroundColor Cyan
        Write-Host "============================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "正在打开浏览器..." -ForegroundColor Yellow
        Start-Process "http://localhost:8000/docs"
        
        Write-Host ""
        Write-Host "💡 提示：请先启动服务（选项 3）再访问文档" -ForegroundColor Cyan
        Write-Host ""
        Read-Host "按回车键返回"
        & $PSCommandPath
    }
    
    "5" {
        Write-Host ""
        Write-Host "👋 再见！" -ForegroundColor Cyan
        exit 0
    }
    
    default {
        Write-Host ""
        Write-Host "❌ 无效的选择，请输入 1-5" -ForegroundColor Red
        Write-Host ""
        Read-Host "按回车键返回"
        & $PSCommandPath
    }
}
