"""The module contains the implementation of methods for working with the database"""

from typing import List
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy_utils import database_exists, create_database
from db.models_msg_log import Base, User, Chat, Message

class StorageWorker:
    """Database operations"""

    def __init__(self, connection_string: str):
        self.__connection_string = connection_string
        self.__engine = create_engine(self.__connection_string)
        if not database_exists(self.__engine.url):
            create_database(self.__engine.url)
        Base.metadata.create_all(self.__engine)
        session = sessionmaker(autocommit=False, autoflush=False, bind=self.__engine)
        self.__db_session = scoped_session(session)

    def save_message(self, msg: Message):
        """Save message"""
        with self.__db_session() as session:
            session.add(msg)
            session.commit()

    def save_user(self, user: User)-> User:
        """Save user"""
        with self.__db_session() as session:
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    def save_chat(self, chat: Chat)-> Chat:
        """Save chat"""
        with self.__db_session() as session:
            session.add(chat)
            session.commit()
            session.refresh(chat)
            return chat

    def get_messages(self) -> List[Message]:
        """Get list messages"""
        with self.__db_session() as session:
            messages = session.query(Message).all()
            return messages

    def get_user_messages(self, user: User) -> List[Message]:
        """Get list users"""
        with self.__db_session() as session:
            messages = session.query(Message).filter(User.id == user.id).all()
            return messages

    def get_user(self, user_id: str) -> User:
        """Get user"""
        with self.__db_session() as session:
            user = session.get(User, user_id)
            return user

    def get_chat(self, chat_id: str) -> Chat:
        """Get chat"""
        with self.__db_session() as session:
            chat = session.get(Chat, chat_id)
            return chat
