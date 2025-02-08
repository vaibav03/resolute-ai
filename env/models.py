from sqlalchemy import Column, Integer, String, Text, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Ensure DATABASE_URL is set
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:dv3523DV@localhost:5432/resolute")

# Print DATABASE_URL to debug
print(f"🔹 DATABASE_URL: {DATABASE_URL}")


engine = create_engine(DATABASE_URL)
connection = engine.connect()
print("✅ Connection successful!")
connection.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    
    user_metadata = relationship("Metadata", back_populates="user")


class Metadata(Base):
    __tablename__ = "metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), index=True)
    url = Column(String, index=True)
    title = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    keywords = Column(Text, nullable=True)
    
    user = relationship("User", back_populates="user_metadata")

