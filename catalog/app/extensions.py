import sys
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

if 'app.extensions' in sys.modules:
    from app.extensions import db, migrate
elif 'iam.app.extensions' in sys.modules:
    from iam.app.extensions import db, migrate
else:
    db = SQLAlchemy()
    migrate = Migrate()
