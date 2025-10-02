from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
APP_SCHEMA = "public"
db = SQLAlchemy(metadata=MetaData(schema=APP_SCHEMA))