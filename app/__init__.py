from flask import Flask


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'dev-secret-key-cambiar-en-produccion'

    # Registrar blueprints
    from app.routes.main import main_bp
    from app.routes.productos import productos_bp
    from app.routes.facturas import facturas_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(productos_bp, url_prefix='/productos')
    app.register_blueprint(facturas_bp, url_prefix='/facturas')

    return app
