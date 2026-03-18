from sqlalchemy import Column, Integer, BigInteger, String, DateTime, JSON, ForeignKey, SmallInteger
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class WordCategory(Base):
    __tablename__ = "t_word_category"

    category_id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String(20), nullable=False, unique=True)
    create_time = Column(DateTime, default=datetime.utcnow)

    subcategories = relationship("WordSubcategory", back_populates="category")


class WordSubcategory(Base):
    __tablename__ = "t_word_subcategory"

    subcategory_id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("t_word_category.category_id"), nullable=False)
    subcategory_name = Column(String(30), nullable=False, unique=True)
    create_time = Column(DateTime, default=datetime.utcnow)

    category = relationship("WordCategory", back_populates="subcategories")
    words = relationship("Word", back_populates="subcategory")


class Word(Base):
    __tablename__ = "t_word"

    word_id = Column(BigInteger, primary_key=True, autoincrement=True)
    subcategory_id = Column(Integer, ForeignKey("t_word_subcategory.subcategory_id"), nullable=False)
    english = Column(String(50), nullable=False)
    explanation = Column(String(100), nullable=False)
    create_time = Column(DateTime, default=datetime.utcnow)

    subcategory = relationship("WordSubcategory", back_populates="words")


class CambridgeBook(Base):
    __tablename__ = "t_cambridge_book"

    cambridge_id = Column(Integer, primary_key=True, autoincrement=True)
    book_name = Column(String(255), nullable=False, unique=True)
    is_available = Column(SmallInteger, nullable=False, default=1)
    create_time = Column(DateTime, default=datetime.utcnow)

    tests = relationship("CambridgeTest", back_populates="book")


class CambridgeTest(Base):
    __tablename__ = "t_cambridge_test"

    test_id = Column(Integer, primary_key=True, autoincrement=True)
    cambridge_id = Column(Integer, ForeignKey("t_cambridge_book.cambridge_id"), nullable=False)
    test_no = Column(String(5), nullable=False)
    is_available = Column(SmallInteger, nullable=False, default=1)
    create_time = Column(DateTime, default=datetime.utcnow)

    book = relationship("CambridgeBook", back_populates="tests")
    sections = relationship("CambridgeSection", back_populates="test")


class CambridgeSection(Base):
    __tablename__ = "t_cambridge_section"

    section_id = Column(BigInteger, primary_key=True, autoincrement=True)
    test_id = Column(Integer, ForeignKey("t_cambridge_test.test_id"), nullable=False)
    section_no = Column(String(5), nullable=False)
    section_name = Column(String(50), nullable=False)
    audio_path = Column(String(200), nullable=False)
    image_path = Column(String(200), nullable=False)
    answers = Column(JSON, nullable=False)
    create_time = Column(DateTime, default=datetime.utcnow)

    test = relationship("CambridgeTest", back_populates="sections")
    scores = relationship("UserListeningScore", back_populates="section")


class UserListeningScore(Base):
    __tablename__ = "t_user_listening_score"

    score_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    section_id = Column(BigInteger, ForeignKey("t_cambridge_section.section_id"), nullable=False)
    correct_num = Column(Integer, nullable=False)
    total_num = Column(Integer, nullable=False, default=10)
    submit_time = Column(DateTime, default=datetime.utcnow)

    section = relationship("CambridgeSection", back_populates="scores")
