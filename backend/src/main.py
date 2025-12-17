from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from models import user_model
from schemas import general_schemas
from db.conn import Base, engine, get_db
from service.auth_service import (
    create_access_token,
    get_current_user,
    hash_password,
    authenticate_user,
    get_user_by_email,
)

app = FastAPI(title="Lumina Backend")

# Create tables on startup (simple dev approach)
Base.metadata.create_all(bind=engine)

@app.post("/auth/signup", response_model=general_schemas.UserRead, status_code=status.HTTP_201_CREATED)
def signup(user_in: general_schemas.UserCreate, db: Session = Depends(get_db)):
    existing = get_user_by_email(db, email=user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists.",
        )

    user = user_model.User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name,
        consent=user_in.consent,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=general_schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    OAuth2PasswordRequestForm expects:
    - username (we treat as email)
    - password
    """
    user = authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/auth/me", response_model=general_schemas.UserRead)
def read_me(current_user: user_model.User = Depends(get_current_user)):
    """Example protected endpoint the web dashboard can call later."""
    return current_user

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app="main:app", host="localhost", port=8080, reload=True)