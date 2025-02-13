from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import redis
import celery
import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
from models import Base, engine , SessionLocal, Metadata , User
from auth import hash_password, verify_password, create_access_token,get_current_user, get_db
from datetime import timedelta

print("🔹 Creating tables in the database...")
Base.metadata.create_all(bind=engine)
print("✅ Tables created successfully!")
load_dotenv()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ACCESS_TOKEN_EXPIRE_MINUTES=300

app = FastAPI()
Base.metadata.create_all(bind=engine)

celery_app = celery.Celery(
    "tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)

def scrape_metadata(url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.find("title").text if soup.find("title") else ""
            description = soup.find("meta", attrs={"name": "description"})
            description = description["content"] if description else ""
            keywords = soup.find("meta", attrs={"name": "keywords"})
            keywords = keywords["content"] if keywords else ""
            return {"url": url, "title": title, "description": description, "keywords": keywords}
    except Exception as e:
        return {"url": url, "error": str(e)}

@celery_app.task
def scrape_urls_task(urls, user_id):
    print("Celery task started")
    
    results = []
    for url in urls:
        print(f"Scraping: {url}")
        result = scrape_metadata(url)
        print(f"Scraped Data: {result}")
        results.append(result)

    db = SessionLocal()
    print("Connected to DB")

    for result in results:
        if "error" not in result:
            try:
                metadata_obj = Metadata(**result, user_id=user_id)  # Add user_id
                print(f"Inserting into DB: {metadata_obj}")
                db.add(metadata_obj)
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"DB Insert Error: {e}")

    db.close()
    print("Celery task completed")
    return results


@app.post("/signup")
def signup(username: str, password: str, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    hashed_password = hash_password(password)
    new_user = User(username=username, password=hashed_password)
    db.add(new_user)
    db.commit()
    return {"message": "User created successfully"}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": user.username}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/upload")
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    print("Uploading")
    df = pd.read_csv(file.file)
    if "url" not in df.columns:
        raise HTTPException(status_code=400, detail="CSV must contain 'url' column")
    urls = df["url"].dropna().tolist()
    print(f"Scraping URLs: {urls}")  
    task = scrape_urls_task.delay(urls, current_user.user_id)
    print(f"Task queued with ID: {task.id}") 
    return {"task_id": task.id}

@app.get("/status/{task_id}")
def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),  
):
    task_result = celery_app.AsyncResult(task_id)
    return {"status": task_result.status, "result": task_result.result}

@app.get("/results")
def get_results(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  
):
    
    results = db.query(Metadata).filter(Metadata.user_id == current_user.user_id).all()
    return results
