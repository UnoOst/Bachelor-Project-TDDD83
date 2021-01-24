import os


class Config(object):
    SECRET_KEY = 'supersecretkey'
    #SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://unoos538:WZkJGpKC@localhost:3307/unoos538?charset=utf8mb4' #UNOS URI-rad
    #SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:root@localhost:3306/kandidat?charset=utf8mb4'
    #SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root@localhost/qrave?charset=utf8mb4' #ALLA ANDRAS URI-rad
    SQLALCHEMY_DATABASE_URI = 'sqlite:///app1.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOADED_PHOTOS_DEST = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/images/uploads')
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'qrave.noreply@gmail.com'
    MAIL_PASSWORD = 'Qrave123!'
    QR_CODE_LENGTH = 30

    TEMPLATES_AUTO_RELOAD = True
