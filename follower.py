from sqlmodel import Field, SQLModel


class Follower(SQLModel, table=True):
    who_id: int = Field(primary_key=True)
    whom_id: int = Field(primary_key=True)
