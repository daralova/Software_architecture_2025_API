from app.db.database import Base, engine
from app.db import models  # noqa: F401

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Таблицы созданы")
