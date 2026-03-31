from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional
import pymysql
import hashlib
from fastapi import APIRouter
DB_HOST = "124.223.33.28"
DB_PORT = 3306
DB_USER = "cardData"
DB_PASSWORD = "zxN8TNNP4Ghf4Ksb"
DB_NAME = "carddata"
SECRET_KEY = "your-secret-key-for-jwt-2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def get_db_connection():
    """Establish and return MySQL database connection"""
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

# ==================== Pydantic Data Models ====================
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    points: int

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_password_hash(password: str):
    """Hash password with salt for security"""
    salt = "fixed-salt-for-demo-2026"
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

def verify_password(plain_password: str, hashed_password: str):
    """Verify plain password against hashed password"""
    return get_password_hash(plain_password) == hashed_password

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token with expiration"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_by_username(username: str):
    """Retrieve active user by username from t_user table (filter is_delete=0)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM t_user WHERE username = %s AND is_delete = 0", (username,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_by_email(email: str):
    """Check if active user exists by email in t_user table (filter is_delete=0)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM t_user WHERE email = %s AND is_delete = 0", (email,))
    user = cursor.fetchone()
    conn.close()
    return user is not None

def create_new_user(username: str, email: str, hashed_password: str):
    """Create new user in t_user table, match all table columns"""
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = datetime.utcnow()
    
    cursor.execute(
        """
        INSERT INTO t_user 
        (username, email, password, create_time, update_time, is_delete, points) 
        VALUES (%s, %s, %s, %s, %s, 0, 0)
        """,
        (username, email, hashed_password, current_time, current_time)
    )
    # Get auto-generated user_id
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {"id": user_id, "username": username, "email": email, "points": 0}

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_username(token_data.username)
    if user is None:
        raise credentials_exception
    return user

#app = FastAPI(title="Academic English Auth API", version="1.0")
router = APIRouter()
@router.get("/test-db-connection", summary="Test MySQL database connection")
def test_db_connection():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as user_count FROM t_user WHERE is_delete = 0")
        user_count = cursor.fetchone()    
        cursor.execute("SELECT 1 as test_result")
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return {
            "status": "success",
            "message": "Successfully connected to MySQL database",
            "test_query_result": result,
            "active_user_count": user_count["user_count"]
        }
    except Exception as e:
        return {
            "status": "failed",
            "message": f"Failed to connect to MySQL database: {str(e)}",
            "error_type": type(e).__name__
        }

@router.post("/register", response_model=UserResponse, summary="Register new user")
def register(user: UserCreate):
    if len(user.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    if get_user_by_username(user.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    
    if get_user_by_email(user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pwd = get_password_hash(user.password)
    new_user = create_new_user(user.username, user.email, hashed_pwd)
    
    return new_user

@router.post("/login", response_model=Token, summary="User login (get access token)")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=UserResponse, summary="Get current user info")
def read_current_user(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["user_id"],
        "username": current_user["username"],
        "email": current_user["email"],
        "points": current_user.get("points", 0)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
