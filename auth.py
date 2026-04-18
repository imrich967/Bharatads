
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from pydantic import BaseModel

SECRET_KEY = "bharatads-secret-key-2024"
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    password = Column(String)
    role = Column(String)  # advertiser ya publisher

Base.metadata.create_all(engine)

# Signup
class SignupData(BaseModel):
    username: str
    email: str
    password: str
    role: str

@app.post("/signup")
def signup(data: SignupData):
    db = Session()
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists!")
    
    hashed = pwd_context.hash(data.password)
    user = User(
        username=data.username,
        email=data.email,
        password=hashed,
        role=data.role
    )
    db.add(user)
    db.commit()
    db.close()
    return {"message": f"Welcome to BharatAds, {data.username}!"}

# Login
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

# Current user
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")
        return {"username": username, "role": role}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token!")

@app.get("/me")
def get_me(user = Depends(get_current_user)):
    return user
