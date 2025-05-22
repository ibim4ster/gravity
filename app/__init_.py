from flask import Flask
from app.extensions import db, login_manager
from app.config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Inicializar extensiones
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Registrar blueprints
    from app.routes.auth import auth as auth_bp
    from app.routes.main import main as main_bp
    from app.routes.admin import admin as admin_bp
    from app.routes.licenses import licenses as licenses_bp
    from app.routes.search import search as search_bp
    from app.routes.user import user as user_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(licenses_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(user_bp)
    
    # Crear tablas en la base de datos
    with app.app_context():
        db.create_all()
    
    return app