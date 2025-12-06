import os

class Config:
    """Cấu hình chung cho Flask app"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-this-in-production'
    
    # Database Configuration
    USE_SQLITE = os.environ.get('USE_SQLITE', 'true').lower() == 'true'
    
    if USE_SQLITE:
        # SQLite - Không cần cài đặt gì, dùng file local
        SQLALCHEMY_DATABASE_URI = 'sqlite:///vrp_system.db'
    else:
        # MySQL Database Configuration
        MYSQL_HOST = os.environ.get('MYSQL_HOST') or 'localhost'
        MYSQL_PORT = int(os.environ.get('MYSQL_PORT') or 3306)
        MYSQL_USER = os.environ.get('MYSQL_USER') or 'root'
        MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
        MYSQL_DB = os.environ.get('MYSQL_DB') or 'vrp_system'
        
        # Xử lý trường hợp password rỗng
        if MYSQL_PASSWORD:
            SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4'
        else:
            SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{MYSQL_USER}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Set to True for SQL debugging
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'connect_args': {
            'charset': 'utf8mb4'
        }
    }
    
    # Upload Configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Session Configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # Pagination
    ITEMS_PER_PAGE = 20
    
    # OR-Tools Configuration
    VEHICLE_CAPACITY = 100  # Sức chứa mặc định của xe
    MAX_VEHICLES = 10  # Số xe tối đa
    DEPOT_INDEX = 0  # Index của kho (DEPOT)
    
class DevelopmentConfig(Config):
    """Cấu hình cho môi trường development"""
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    """Cấu hình cho môi trường production"""
    DEBUG = False
    
class TestingConfig(Config):
    """Cấu hình cho môi trường testing"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Dictionary để chọn config theo môi trường
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
