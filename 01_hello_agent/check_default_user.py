"""
检查数据库中的默认用户
"""
from database.db_connection import get_db_context
from database.dao import UserDAO

def check_default_user():
    """检查默认用户是否存在"""
    with get_db_context() as db:
        user_dao = UserDAO(db)
        
        # 尝试获取默认用户
        default_user = user_dao.get_default_user()
        
        if default_user:
            print(f"✅ 找到默认用户:")
            print(f"   - ID: {default_user.id}")
            print(f"   - 用户名：{default_user.username}")
            print(f"   - 邮箱：{default_user.email}")
            print(f"   - 角色：{default_user.role}")
            return str(default_user.id)
        else:
            print("❌ 未找到默认用户 'admin'")
            
            # 列出所有用户
            users = db.query(user_dao.User).all()
            if users:
                print(f"\n📋 当前数据库中有 {len(users)} 个用户:")
                for user in users:
                    print(f"   - {user.username} (ID: {user.id})")
            else:
                print("📭 数据库中没有任何用户")
            
            return None

if __name__ == "__main__":
    user_id = check_default_user()
    
    if user_id:
        print(f"\n✅ 默认用户 UUID: {user_id}")
    else:
        print("\n❌ 需要先初始化数据库或创建默认用户")
