import os
import shutil
import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, Form, Request, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_
from jose import JWTError, jwt
from pydantic import BaseModel

import models, database, auth

models.Base.metadata.create_all(bind=database.engine)
app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

os.makedirs("storage", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/raw", StaticFiles(directory="storage"), name="raw")
templates = Jinja2Templates(directory="templates")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        username: str = payload.get("sub")
        if username is None: raise HTTPException(status_code=401)
    except JWTError:
        raise HTTPException(status_code=401)
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None: raise HTTPException(status_code=401)
    return user


# --- MODELS ---
class FileOut(BaseModel):
    id: int
    filename: str
    extension: str
    size: int
    created_at: str
    updated_at: str  # <--- НОВЕ ПОЛЕ
    uploader: str
    editor: str
    access_type: str
    storage_name: str


class ShareRequest(BaseModel):
    filename: str
    target_user: str
    level: str


class UpdateContentRequest(BaseModel):
    storage_name: str
    content: str


# --- ROUTES ---

@app.post("/register")
def register(username: str = Form(...), password: str = Form(...), db: Session = Depends(database.get_db)):
    if db.query(models.User).filter(models.User.username == username).first():
        raise HTTPException(status_code=400, detail="User exists")
    user = models.User(username=username, hashed_password=auth.get_password_hash(password))
    db.add(user)
    db.commit()
    return {"status": "created"}


@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect credentials")
    token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/files", response_model=List[FileOut])
def list_files(user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    files = db.query(models.File).outerjoin(models.Permission).filter(
        or_(models.File.owner_id == user.id, models.Permission.user_id == user.id)
    ).all()

    result = []
    for f in files:
        access = "owner"
        if f.owner_id != user.id:
            perm = next((p for p in f.permissions if p.user_id == user.id), None)
            access = perm.access_level if perm else "read"

        result.append({
            "id": f.id,
            "filename": f.display_name,
            "extension": f.extension,
            "size": f.size,
            "created_at": f.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": f.updated_at.strftime("%Y-%m-%d %H:%M:%S"),  # <--- НОВЕ
            "uploader": f.uploader_name,
            "editor": f.editor_name,
            "access_type": access,
            "storage_name": f.storage_name
        })
    return result


@app.post("/upload")
def upload(file: UploadFile, user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    # 1. Спочатку шукаємо, чи є такий файл У МЕНЕ (власник)
    existing_my = db.query(models.File).filter(
        models.File.display_name == file.filename,
        models.File.owner_id == user.id
    ).first()

    # 2. Якщо немає, шукаємо, чи є такий файл, РОЗШАРЕНИЙ мені з правом WRITE
    existing_shared = None
    if not existing_my:
        existing_shared = db.query(models.File).join(models.Permission).filter(
            models.File.display_name == file.filename,
            models.Permission.user_id == user.id,
            models.Permission.access_level == "write"
        ).first()

    # Вибираємо, що будемо оновлювати (пріоритет: мій файл -> розшарений)
    target_file = existing_my or existing_shared

    target_storage_name = ""

    if target_file:
        # ОНОВЛЕННЯ ІСНУЮЧОГО
        target_storage_name = target_file.storage_name
        target_file.editor_name = user.username
        target_file.updated_at = datetime.now()
        # file.size оновиться нижче
    else:
        # СТВОРЕННЯ НОВОГО (навіть якщо ім'я зайняте кимось іншим - це буде мій файл)
        target_storage_name = f"{uuid.uuid4()}_{file.filename}"
        new_file = models.File(
            display_name=file.filename,
            extension=os.path.splitext(file.filename)[1].lower(),
            size=0,
            storage_name=target_storage_name,
            uploader_name=user.username,
            editor_name=user.username,
            owner_id=user.id
        )
        db.add(new_file)

    # Фізичний запис файлу (Синхронний, бо функція def, не async)
    path = os.path.join("storage", target_storage_name)
    try:
        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Оновлюємо розмір після запису
        if target_file:
            target_file.size = os.path.getsize(path)
        else:
            new_file.size = os.path.getsize(path)

    except Exception as e:
        print(f"Error writing file: {e}")
        raise HTTPException(500, "Failed to write file")

    db.commit()
    return {"status": "ok"}

@app.delete("/delete/{storage_name}")
def delete_file(storage_name: str, user: models.User = Depends(get_current_user),
                db: Session = Depends(database.get_db)):
    file = db.query(models.File).filter(models.File.storage_name == storage_name).first()
    if not file: raise HTTPException(404, "Not found")

    # 1. Якщо Власник -> Видаляємо повністю
    if file.owner_id == user.id:
        try:
            path = os.path.join("storage", file.storage_name)
            if os.path.exists(path): os.remove(path)
        except:
            pass
        db.delete(file)
        db.commit()
        return {"status": "deleted_completely"}

    # 2. Якщо Гість -> Видаляємо тільки право доступу (прибираємо зі списку)
    else:
        perm = db.query(models.Permission).filter_by(file_id=file.id, user_id=user.id).first()
        if perm:
            db.delete(perm)
            db.commit()
            return {"status": "removed_permission"}
        else:
            raise HTTPException(403, "Cannot delete file (not owner and no permission found)")


@app.post("/share")
def share(req: ShareRequest, user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    file = db.query(models.File).filter_by(display_name=req.filename, owner_id=user.id).first()
    if not file: raise HTTPException(404, "File not found or not owner")

    target = db.query(models.User).filter_by(username=req.target_user).first()
    if not target: raise HTTPException(404, "User not found")

    existing_perm = db.query(models.Permission).filter_by(file_id=file.id, user_id=target.id).first()
    if existing_perm:
        existing_perm.access_level = req.level
    else:
        db.add(models.Permission(user_id=target.id, file_id=file.id, access_level=req.level))

    db.commit()
    return {"status": "shared"}


# --- НОВИЙ ЕНДПОІНТ: Оновлення тексту ---
@app.post("/update_content")
def update_content(req: UpdateContentRequest, user: models.User = Depends(get_current_user),
                   db: Session = Depends(database.get_db)):
    file = db.query(models.File).filter(models.File.storage_name == req.storage_name).first()
    if not file: raise HTTPException(404, "Not found")

    # Перевірка прав (Owner або Write)
    has_access = False
    if file.owner_id == user.id:
        has_access = True
    else:
        perm = db.query(models.Permission).filter_by(file_id=file.id, user_id=user.id).first()
        if perm and perm.access_level == "write": has_access = True

    if not has_access: raise HTTPException(403, "Read only access")

    # Зберігаємо файл
    path = os.path.join("storage", file.storage_name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(req.content)

    # Оновлюємо метадані
    file.editor_name = user.username
    file.updated_at = datetime.now()
    file.size = os.path.getsize(path)

    db.commit()
    return {"status": "updated"}


@app.get("/")
def serve_web(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)