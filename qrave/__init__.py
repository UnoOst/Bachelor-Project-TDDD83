from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class
from flask_admin import Admin
from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class
from .config import Config

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'users.login'
login_manager.login_message_category = 'info'
mail = Mail()
photos = UploadSet()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object('qrave.config.Config')

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    from .adminPages.admin import create_admin
    admin = create_admin()
    admin.init_app(app)

    from .users.routes import users
    from .main.routes import main
    from .errors.handlers import errors
    from .hostAdmin.routes import host_blueprint
    from .hostAdmin.payments import payment_blueprint
    from .adminPages.routes import admin
    app.register_blueprint(users)
    app.register_blueprint(main)
    app.register_blueprint(errors)
    app.register_blueprint(host_blueprint)
    app.register_blueprint(payment_blueprint)
    app.register_blueprint(admin)

    photos = UploadSet('photos', IMAGES)
    configure_uploads(app, photos)
    patch_request_class(app)

    from .flask_helpers import helper
    app.cli.add_command(helper)

    return app


