from models import session_model
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from models import user_model
from models import blink_model
from schemas import general_schemas
from db.conn import Base, engine, get_db
from typing import List
from datetime import datetime
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

    
@app.post("/sync/blinks", status_code=status.HTTP_200_OK)
def sync_blinks(
    samples: List[general_schemas.BlinkSampleIn] = Body(...),
    current_user: user_model.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    for sample in samples:
        db.add(
            blink_model.BlinkSample(
                user_id=current_user.id,
                timestamp=sample.timestamp,
                count=sample.count,
                session_id=sample.session_id,
            )
        )
    db.commit()
    return {"status": "ok", "received": len(samples)}



# ========== SESSION ENDPOINTS ==========

@app.post("/sessions", response_model=general_schemas.SessionRead, status_code=status.HTTP_201_CREATED)
def create_session(
    session_in: general_schemas.SessionCreate,
    current_user: user_model.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new tracking session."""
    session = session_model.Session(
        user_id=current_user.id,
        name=session_in.name,
        start_time=session_in.start_time,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@app.get("/sessions", response_model=List[general_schemas.SessionRead])
def list_sessions(
    current_user: user_model.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all sessions for the current user."""
    sessions = db.query(session_model.Session).filter(
        session_model.Session.user_id == current_user.id
    ).order_by(session_model.Session.start_time.desc()).all()
    return sessions


@app.get("/sessions/{session_id}", response_model=general_schemas.SessionWithBlinks)
def get_session(
    session_id: int,
    current_user: user_model.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a session with its blink samples."""
    session = db.query(session_model.Session).filter(
        session_model.Session.id == session_id,
        session_model.Session.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    return session


@app.patch("/sessions/{session_id}", response_model=general_schemas.SessionRead)
def update_session(
    session_id: int,
    session_update: general_schemas.SessionUpdate,
    current_user: user_model.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a session (name, end_time)."""
    session = db.query(session_model.Session).filter(
        session_model.Session.id == session_id,
        session_model.Session.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if session_update.name is not None:
        session.name = session_update.name
    if session_update.end_time is not None:
        session.end_time = session_update.end_time
    
    db.commit()
    db.refresh(session)
    return session


@app.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    current_user: user_model.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a session."""
    session = db.query(session_model.Session).filter(
        session_model.Session.id == session_id,
        session_model.Session.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    db.delete(session)
    db.commit()
    return None


@app.post("/sync/sessions", status_code=status.HTTP_200_OK)
def sync_sessions(
    sessions_data: List[dict] = Body(...),
    current_user: user_model.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sync sessions from local DB. Expects list of {id, name, start_time, end_time}."""
    created_ids = []
    for sess_data in sessions_data:
        session = session_model.Session(
            user_id=current_user.id,
            name=sess_data.get("name"),
            start_time=datetime.fromisoformat(sess_data["start_time"]),
            end_time=datetime.fromisoformat(sess_data["end_time"]) if sess_data.get("end_time") else None,
        )
        db.add(session)
        db.flush()  # Get the ID
        created_ids.append(session.id)
    db.commit()
    return {"status": "ok", "created": len(created_ids), "ids": created_ids}


@app.get("/auth/me", response_model=general_schemas.UserRead)
def read_me(current_user: user_model.User = Depends(get_current_user)):
    """Example protected endpoint the web dashboard can call later."""
    return current_user

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app="main:app", host="localhost", port=8080, reload=True)