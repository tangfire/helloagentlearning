"""
PostgreSQL 数据库连接管理

使用 SQLAlchemy 提供连接池、事务管理和 ORM 功能
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
import os
from typing import Generator

# 数据库连接配置
DATABASE_CONFIG = {
    "user": os.getenv("POSTGRES_USER", "codemind"),
    "password": os.getenv("POSTGRES_PASSWORD", "codemind2024"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
    "database": os.getenv("POSTGRES_DB", "codemind"),
}

# 构建数据库 URL
DATABASE_URL = f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"

# 创建引擎（带连接池）
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,  # 连接池大小
    max_overflow=40,  # 最大溢出连接数
    pool_pre_ping=True,  # 自动检测失效连接
    pool_recycle=3600,  # 1 小时回收连接
    echo=False,  # 是否打印 SQL 日志
    future=True
)

# 创建会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
    future=True
)

# 声明基类
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话的依赖注入函数
    
    Usage:
        db = next(get_db())
        try:
            # 使用 db
        finally:
            db.close()
    
    或用于 FastAPI:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    获取数据库会话的上下文管理器
    
    Usage:
        with get_db_context() as db:
            # 使用 db
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    初始化数据库 - 创建所有表
    
    注意：生产环境应该使用 Alembic 进行数据库迁移
    """
    try:
        # 检查数据库连接
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print("✅ PostgreSQL 数据库连接成功")
            
        # 创建所有表（仅开发环境使用）
        # Base.metadata.create_all(bind=engine)
        # print("✅ 数据库表已创建")
        
    except Exception as e:
        print(f"❌ 数据库初始化失败：{e}")
        raise


def check_connection():
    """检查数据库连接状态"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"📊 PostgreSQL 版本：{version}")
            return True
    except Exception as e:
        print(f"❌ 数据库连接失败：{e}")
        return False


# ==================== 使用示例 ====================
if __name__ == "__main__":
    print("🔍 测试数据库连接...")
    if check_connection():
        print("✅ 数据库连接正常")
        
        # 测试会话
        with get_db_context() as db:
            # 查询用户数
            from sqlalchemy import text
            result = db.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            print(f"📊 用户总数：{count}")
            
            # 查询工作空间数
            result = db.execute(text("SELECT COUNT(*) FROM workspaces"))
            count = result.scalar()
            print(f"📊 工作空间总数：{count}")
