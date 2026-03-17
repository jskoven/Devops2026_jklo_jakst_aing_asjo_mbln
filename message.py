from sqlmodel import Field, SQLModel


class MessageBase(SQLModel):
    text: str = Field(nullable=False)
    pub_date: int


class Message(MessageBase, table=True):
    message_id: int | None = Field(
        default=None, primary_key=True, sa_column_kwargs={"autoincrement": True}
    )
    author_id: int | None = Field(foreign_key="user.user_id", nullable=False)
    flagged: int = Field(default=0)


class MessagePublic(MessageBase):
    message_id: int
    author_id: int
