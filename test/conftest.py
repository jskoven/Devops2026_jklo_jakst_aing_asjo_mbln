from typing import Annotated
import pytest
from fastapi import Depends
from sqlmodel import SQLModel, Session, create_engine

TEST_DB_URL = "postgresql://minitwit:minitwit@db:5432/minitwit"
GUI_URL = "http://minitwit:5001"
engine = create_engine(TEST_DB_URL)


@pytest.fixture(scope="session")
def db_engine():
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(db_session)]
