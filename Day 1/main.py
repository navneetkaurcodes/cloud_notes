from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.orm import Session

import models
import schemas
import auth

from database import engine, Base, get_db

app = FastAPI(title="Cloud Notes API")
Base.metadata.create_all(bind=engine)

@app.post("/register")
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):

    existing_user = db.query(models.User).filter(
        models.User.email == user.email
    ).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = auth.hash_password(user.password)

    new_user = models.User(
        name=user.name,
        email=user.email,
        password=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User registered successfully"}

@app.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):

    db_user = db.query(models.User).filter(
        models.User.email == user.email
    ).first()

    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not auth.verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = auth.create_access_token(
        {"sub": db_user.email}
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }

def get_current_user(token: str, db: Session):

    email = auth.verify_token(token)

    if email is None:
        raise HTTPException(status_code=401, detail="Invalid Token")

    user = db.query(models.User).filter(
        models.User.email == email
    ).first()

    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user

@app.post("/notes")
def create_note(
    note: schemas.NoteCreate,
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):

    token = authorization.replace("Bearer ", "")

    user = get_current_user(token, db)

    new_note = models.Note(
        title=note.title,
        content=note.content,
        owner_id=user.id
    )

    db.add(new_note)
    db.commit()
    db.refresh(new_note)

    return new_note

@app.get("/list_notes", response_model=list[schemas.NoteResponse])
def get_notes(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):

    token = authorization.replace("Bearer ", "")

    user = get_current_user(token, db)

    notes = db.query(models.Note).filter(
        models.Note.owner_id == user.id
    ).all()

    return notes

@app.put("/update_notes/{note_id}")
def update_note(
    note_id: int,
    note: schemas.NoteCreate,
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):

    token = authorization.replace("Bearer ", "")

    user = get_current_user(token, db)

    db_note = db.query(models.Note).filter(
        models.Note.id == note_id,
        models.Note.owner_id == user.id
    ).first()

    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")

    db_note.title = note.title
    db_note.content = note.content

    db.commit()
    db.refresh(db_note)

    return db_note

@app.delete("/remove_notes/{note_id}")
def delete_note(
    note_id: int,
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):

    token = authorization.replace("Bearer ", "")

    user = get_current_user(token, db)

    note = db.query(models.Note).filter(
        models.Note.id == note_id,
        models.Note.owner_id == user.id
    ).first()

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    db.delete(note)
    db.commit()

    return {"message": "Note deleted successfully"}