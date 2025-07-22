import os
import dotenv
from pydantic import BaseModel

dotenv.load_dotenv()

class DBConfigSchema(BaseModel):

    host: str
    port: int
    username: str
    pwd: str
    db_name: str
    db_auth_source: str

    @classmethod
    def load(cls):
        data = {
            "host": os.environ["MONGO_HOST"],
            "port": int(os.environ["MONGO_PORT"]),
            "username": os.environ["MONGO_USERNAME"],
            "pwd": os.environ["MONGO_PASSWORD"],
            "db_name": os.environ["MONGO_DB_NAME"],
            "db_auth_source": os.environ["MONGO_AUTH_SOURCE"]
        }
        return cls(**data)