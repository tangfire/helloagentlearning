"""
测试 Web API 功能
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """测试健康检查"""
    print("\n🔍 测试健康检查...")
    response = requests.get(f"{BASE_URL}/api/health")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 健康检查通过")
        print(f"   状态：{data['status']}")
        print(f"   助手已初始化：{data['assistant_initialized']}")
        return True
    else:
        print(f"❌ 健康检查失败：{response.status_code}")
        return False

def test_stats():
    """测试统计信息"""
    print("\n📊 测试统计信息...")
    response = requests.get(f"{BASE_URL}/api/stats")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 统计信息获取成功")
        print(f"   加载文档数：{data.get('documents_loaded', 0)}")
        print(f"   创建块数：{data.get('chunks_created', 0)}")
        print(f"   提问次数：{data.get('questions_asked', 0)}")
        return True
    else:
        print(f"❌ 统计信息获取失败：{response.status_code}")
        return False

def test_mcp_status():
    """测试 MCP 状态"""
    print("\n🔌 测试 MCP 状态...")
    response = requests.get(f"{BASE_URL}/api/mcp/status")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ MCP 状态获取成功")
        print(f"   MCP 可用：{data.get('available', False)}")
        print(f"   已连接服务器数：{data.get('connected_servers', 0)}")
        return True
    else:
        print(f"❌ MCP 状态获取失败：{response.status_code}")
        return False

def test_chat():
    """测试智能问答"""
    print("\n💬 测试智能问答...")
    
    question = "CodeMind Assistant 有哪些主要功能？"
    print(f"   问题：{question}")
    
    response = requests.post(
        f"{BASE_URL}/api/chat",
        json={
            "question": question,
            "use_mqe": True,
            "use_hyde": True,
            "use_context": True
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 问答测试成功")
        print(f"   回答长度：{len(data.get('answer', ''))} 字符")
        print(f"   置信度：{data.get('confidence', 0):.2f}")
        print(f"   检索方法：{data.get('retrieval_method', 'unknown')}")
        return True
    else:
        print(f"❌ 问答测试失败：{response.status_code}")
        print(f"   错误：{response.text}")
        return False

def test_task_management():
    """测试任务管理"""
    print("\n✅ 测试任务管理...")
    
    # 创建任务
    task_data = {
        "title": "Web 界面测试任务",
        "description": "这是一个通过 Web API 创建的测试任务",
        "priority": "medium",
        "tags": ["web", "test"]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/tasks/create",
        json=task_data
    )
    
    if response.status_code == 200:
        data = response.json()
        task_id = data.get('task_id')
        print(f"✅ 任务创建成功")
        print(f"   任务 ID: {task_id}")
        
        # 列出任务
        response = requests.get(f"{BASE_URL}/api/tasks/list?status=open&limit=5")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 任务列表获取成功")
            print(f"   总任务数：{data.get('total', 0)}")
            
            if data.get('tasks'):
                print(f"   最新任务：{data['tasks'][0]['title']}")
        
        return True
    else:
        print(f"❌ 任务创建失败：{response.status_code}")
        return False

def test_codebase_explore():
    """测试代码库探索"""
    print("\n🗂️  测试代码库探索...")
    
    response = requests.post(
        f"{BASE_URL}/api/codebase/explore",
        json={
            "command": "dir",
            "save_to_notes": False
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        output = data.get('output', '')
        print(f"✅ 代码库探索成功")
        print(f"   输出行数：{len(output.split(chr(10)))}")
        return True
    else:
        print(f"❌ 代码库探索失败：{response.status_code}")
        return False

def main():
    """运行所有测试"""
    print("=" * 80)
    print("🧪 CodeMind Web API 功能测试")
    print("=" * 80)
    
    tests = [
        ("健康检查", test_health),
        ("统计信息", test_stats),
        ("MCP 状态", test_mcp_status),
        ("代码库探索", test_codebase_explore),
        ("任务管理", test_task_management),
        ("智能问答", test_chat)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ {name} 测试异常：{e}")
            results.append((name, False))
    
    # 汇总结果
    print("\n" + "=" * 80)
    print("📋 测试结果汇总")
    print("=" * 80)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {status} - {name}")
    
    print("\n" + "-" * 80)
    print(f"总计：{passed}/{total} 测试通过 ({passed/total*100:.1f}%)")
    print("=" * 80)
    
    return passed == total

if __name__ == "__main__":
    import sys
    
    # 等待服务器启动
    print("\n⏳ 等待服务器启动...")
    import time
    time.sleep(2)
    
    success = main()
    sys.exit(0 if success else 1)
