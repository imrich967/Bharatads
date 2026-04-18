
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.get("/")
def home():
    return {"message": "BharatAds Server Live hai! 🇮🇳"}

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

from fastapi.responses import HTMLResponse
import pathlib

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    html = pathlib.Path("dashboard.html").read_text()
    return html
