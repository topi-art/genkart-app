from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import io
import os
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from xhtml2pdf import pisa

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BOT_TOKEN = "9195903180:AAGSvvim9LlwkYhCCNRoFk_e09OQ_Fyh_58" 

# База данных
DATABASE_URL = "sqlite:///./profiles_final.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, unique=True, index=True)
    company = Column(String, default="ООО Ваша компания")
    inn = Column(String, default="0000000000")
    address = Column(String, default="г. Москва")
    contacts = Column(String, default="+7 (999) 999-99-99")

Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Бэкенд работает!"}

# Эндпоинт для загрузки профиля при входе
@app.get("/get-profile")
async def get_profile(chat_id: str):
    db = SessionLocal()
    profile = db.query(Profile).filter(Profile.chat_id == chat_id).first()
    db.close()
    if profile:
        return {
            "status": "ok", 
            "company": profile.company, 
            "inn": profile.inn, 
            "address": profile.address, 
            "contacts": profile.contacts
        }
    return {"status": "not_found"}

# Эндпоинт для сохранения профиля
@app.post("/save-profile")
async def save_profile(
    chat_id: str = Form(...),
    company: str = Form(...),
    inn: str = Form(...),
    address: str = Form(...),
    contacts: str = Form(...)
):
    db = SessionLocal()
    try:
        profile = db.query(Profile).filter(Profile.chat_id == chat_id).first()
        if profile:
            profile.company = company
            profile.inn = inn
            profile.address = address
            profile.contacts = contacts
        else:
            new_profile = Profile(chat_id=chat_id, company=company, inn=inn, address=address, contacts=contacts)
            db.add(new_profile)
        db.commit()
        return {"status": "ok", "message": "Профиль сохранен"}
    except Exception as e:
        print(f"ОШИБКА БД: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@app.post("/generate-doc")
async def generate_doc(
    template: str = Form("kp"),
    company: str = Form("ООО Ваша компания"),
    inn: str = Form("0000000000"),
    address: str = Form("г. Москва"),
    contacts: str = Form("+7 (999) 999-99-99"),
    services_json: str = Form("[]"),
    term: str = Form("30"),
    dogovor_number: str = Form("Б/Н"),
    dogovor_date: str = Form(""),
    customer_name: str = Form("ООО Заказчик"),
    customer_inn: str = Form("1111111111"),
    customer_address: str = Form("г. Москва"),
    director_name: str = Form("Иванов И.И."),
    smeta_date: str = Form("")
):
    services = json.loads(services_json)
    total_price = sum(float(s['price']) * int(s['qty']) for s in services)
    current_date = datetime.now().strftime("%d.%m.%Y")
    date_to_use = dogovor_date if dogovor_date else current_date
    smeta_date_to_use = smeta_date if smeta_date else current_date
    
    buffer = io.BytesIO()

    # ... (Здесь должен быть весь блок генерации PDF, который я присылал в прошлом сообщении, 
    # начиная с "if template == 'kp':" и заканчивая "pisa.CreatePDF(html, dest=buffer)") ...

    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf")
