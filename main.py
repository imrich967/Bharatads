
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from pydantic import BaseModel
import random
import pathlib

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = "bharatads-secret-2024"
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

engine = create_engine("sqlite:///bharatads.db", connect_args={"check_same_thread": False})
Base = declarative_base()
Session = sessionmaker(bind=engine)

class Ad(Base):
    __tablename__ = "ads"
    id = Column(Integer, primary_key=True)
    advertiser = Column(String)
    image_url = Column(String)
    click_url = Column(String)
    niche = Column(String)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    cpm = Column(Float, default=10.0)

class Publisher(Base):
    __tablename__ = "publishers"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    website = Column(String)
    earnings = Column(Float, default=0.0)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    password = Column(String)
    role = Column(String)

Base.metadata.create_all(engine)

db = Session()
if db.query(Ad).count() == 0:
    db.add_all([
        Ad(advertiser="Flipkart", image_url="https://example.com/flipkart.jpg",
           click_url="https://flipkart.com", niche="shopping", cpm=15.0),
        Ad(advertiser="Byjus", image_url="https://example.com/byjus.jpg",
           click_url="https://byjus.com", niche="education", cpm=12.0),
        Ad(advertiser="Zomato", image_url="https://example.com/zomato.jpg",
           click_url="https://zomato.com", niche="food", cpm=10.0),
    ])
    db.add_all([
        Publisher(name="Hindi Blog", website="hindinews.com"),
        Publisher(name="Tamil Site", website="tamilnews.com"),
    ])
    db.commit()
db.close()

class SignupData(BaseModel):
    username: str
    email: str
    password: str
    role: str

@app.get("/")
def home():
    return {"message": "BharatAds Server Live hai!"}

@app.post("/signup")
def signup(data: SignupData):
    db = Session()
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        db.close()
        raise HTTPException(status_code=400, detail="Username already exists!")
    hashed = pwd_context.hash(data.password)
    user = User(username=data.username, email=data.email, password=hashed, role=data.role)
    db.add(user)
    db.commit()
    db.close()
    return {"message": f"Welcome to BharatAds, {data.username}!"}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = Session()
    user = db.query(User).filter(User.username == form_data.username).first()
    db.close()
    if not user or not pwd_context.verify(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="Wrong username ya password!")
    token = jwt.encode(
        {"sub": user.username, "role": user.role,
         "exp": datetime.utcnow() + timedelta(hours=24)},
        SECRET_KEY, algorithm=ALGORITHM
    )
    return {"access_token": token, "token_type": "bearer", "role": user.role}

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"username": payload.get("sub"), "role": payload.get("role")}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token!")

@app.get("/me")
def get_me(user=Depends(get_current_user)):
    return user

@app.get("/get-ad")
def get_ad(niche: str = "general", publisher_id: int = 1):
    db = Session()
    matched = db.query(Ad).filter(Ad.niche == niche).all()
    if not matched:
        matched = db.query(Ad).all()
    ad = random.choice(matched)
    ad.impressions += 1
    publisher = db.query(Publisher).filter(Publisher.id == publisher_id).first()
    if publisher:
        publisher.earnings += ad.cpm / 1000
    db.commit()
    result = {
        "id": ad.id,
        "advertiser": ad.advertiser,
        "image_url": ad.image_url,
        "click_url": ad.click_url,
        "niche": ad.niche,
        "impressions": ad.impressions
    }
    db.close()
    return JSONResponse(content=result)

@app.get("/click/{ad_id}")
def track_click(ad_id: int):
    db = Session()
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if ad:
        ad.clicks += 1
        db.commit()
    total = ad.clicks
    db.close()
    return {"status": "tracked", "total_clicks": total}

@app.get("/publisher/{publisher_id}/earnings")
def get_earnings(publisher_id: int):
    db = Session()
    publisher = db.query(Publisher).filter(Publisher.id == publisher_id).first()
    if not publisher:
        return JSONResponse(content={"error": "Publisher nahi mila"})
    result = {
        "publisher": publisher.name,
        "website": publisher.website,
        "total_earnings": round(publisher.earnings, 4)
    }
    db.close()
    return JSONResponse(content=result)

@app.get("/stats")
def get_stats():
    db = Session()
    ads = db.query(Ad).all()
    result = []
    for ad in ads:
        result.append({
            "advertiser": ad.advertiser,
            "impressions": ad.impressions,
            "clicks": ad.clicks,
            "ctr": round((ad.clicks / ad.impressions * 100), 2) if ad.impressions > 0 else 0
        })
    db.close()
    return JSONResponse(content=result)

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    try:
        html = pathlib.Path("dashboard.html").read_text()
        return html
    except:
        return "<h1>Dashboard loading...</h1>"

from pydantic import BaseModel

class PaymentRequest(BaseModel):
    publisher_id: int
    upi_id: str

@app.post("/request-payment")
def request_payment(data: PaymentRequest, user=Depends(get_current_user)):
    db = Session()
    publisher = db.query(Publisher).filter(Publisher.id == data.publisher_id).first()
    
    if not publisher:
        db.close()
        raise HTTPException(status_code=404, detail="Publisher nahi mila!")
    
    if publisher.earnings < 100:
        db.close()
        return {
            "status": "error",
            "message": f"Minimum ₹100 chahiye! Abhi ₹{publisher.earnings} hai!"
        }
    
    amount = publisher.earnings
    publisher.earnings = 0
    db.commit()
    db.close()
    
    return {
        "status": "success",
        "message": f"₹{amount} payment process ho raha hai!",
        "upi_id": data.upi_id,
        "amount": amount,
        "publisher": publisher.name
    }

@app.get("/payment-history/{publisher_id}")
def payment_history(publisher_id: int):
    db = Session()
    publisher = db.query(Publisher).filter(Publisher.id == publisher_id).first()
    if not publisher:
        db.close()
        return {"error": "Publisher nahi mila!"}
    result = {
        "publisher": publisher.name,
        "current_earnings": round(publisher.earnings, 4),
        "minimum_payout": "₹100",
        "upi_ready": publisher.earnings >= 100
    }
    db.close()
    return result

from pydantic import BaseModel

class PaymentRequest(BaseModel):
    publisher_id: int
    upi_id: str

@app.post("/request-payment")
def request_payment(data: PaymentRequest, user=Depends(get_current_user)):
    db = Session()
    publisher = db.query(Publisher).filter(Publisher.id == data.publisher_id).first()
    
    if not publisher:
        db.close()
        raise HTTPException(status_code=404, detail="Publisher nahi mila!")
    
    if publisher.earnings < 100:
        db.close()
        return {
            "status": "error",
            "message": f"Minimum ₹100 chahiye! Abhi ₹{publisher.earnings} hai!"
        }
    
    amount = publisher.earnings
    publisher.earnings = 0
    db.commit()
    db.close()
    
    return {
        "status": "success",
        "message": f"₹{amount} payment process ho raha hai!",
        "upi_id": data.upi_id,
        "amount": amount,
        "publisher": publisher.name
    }

@app.get("/payment-history/{publisher_id}")
def payment_history(publisher_id: int):
    db = Session()
    publisher = db.query(Publisher).filter(Publisher.id == publisher_id).first()
    if not publisher:
        db.close()
        return {"error": "Publisher nahi mila!"}
    result = {
        "publisher": publisher.name,
        "current_earnings": round(publisher.earnings, 4),
        "minimum_payout": "₹100",
        "upi_ready": publisher.earnings >= 100
    }
    db.close()
    return result
