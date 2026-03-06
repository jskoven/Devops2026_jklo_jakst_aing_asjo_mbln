
from sqlmodel import Field, SQLModel

class UserBase(SQLModel):
    username: str = Field(nullable=False)
    email: str = Field(nullable=False)


class User(UserBase,table=True): 
    pw_hash_string: str = Field(nullable=False)
    user_id: int | None = Field(default=None, primary_key=True, sa_column_kwargs={"autoincrement": True})


class UserPublic(UserBase):
    user_id:int 

    
    