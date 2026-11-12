from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import io
import requests
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import declarative_base, sessionmaker

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BOT_TOKEN = "9195903180:AAGSvvim9LlwkYhCCNRoFk_e09OQ_Fyh_58" 

# --- НАСТРОЙКА БАЗЫ ДАННЫХ ---
DATABASE_URL = "sqlite:///./profiles.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, unique=True, index=True)
    company = Column(String)
    contacts = Column(String)
    logo_path = Column(String)

Base.metadata.create_all(bind=engine)

# --- ПОИСК СИСТЕМНОГО ШРИФТА ---
FONT_NAME = 'Helvetica'
possible_paths = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
]
for path in possible_paths:
    if os.path.exists(path):
        try:
            pdfmetrics.registerFont(TTFont('CustomFont', path))
            FONT_NAME = 'CustomFont'
            break
        except: pass

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Бэкенд работает!"}

# --- ЭНДПОИНТ ДЛЯ СОХРАНЕНИЯ ПРОФИЛЯ ---
@app.post("/save-profile")
async def save_profile(
    chat_id: str = Form(...),
    company: str = Form(...),
    contacts: str = Form(...),
    logo: UploadFile = File(None)
):
    db = SessionLocal()
    profile = db.query(Profile).filter(Profile.chat_id == chat_id).first()
    
    logo_path = ""
    if logo:
        logo_path = f"logo_{chat_id}.png"
        logo_data = await logo.read()
        with open(logo_path, "wb") as f:
            f.write(logo_data)
    
    if profile:
        profile.company = company
        profile.contacts = contacts
        if logo_path: profile.logo_path = logo_path
    else:
        new_profile = Profile(chat_id=chat_id, company=company, contacts=contacts, logo_path=logo_path)
        db.add(new_profile)
    
    db.commit()
    db.close()
    return {"status": "ok", "message": "Профиль сохранен"}

# --- ЭНДПОИНТ ДЛЯ ГЕНЕРАЦИИ ДОКУМЕНТА ---
@app.post("/generate-doc")
async def generate_doc(
    chat_id: str = Form(...),
    service: str = Form(...),
    price: str = Form(...),
    term: str = Form(...),
    template: str = Form("template1")
):
    db = SessionLocal()
    profile = db.query(Profile).filter(Profile.chat_id == chat_id).first()
    db.close()

    if not profile:
        return {"status": "error", "message": "Сначала заполните профиль"}

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # --- 1. РАМКА БЛАНКА ---
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.rect(30, 30, width - 60, height - 60)
    c.setLineWidth(0.5)
    c.rect(35, 35, width - 70, height - 70)

    # --- 2. ШАПКА ---
    if profile.logo_path and os.path.exists(profile.logo_path):
        try:
            img = ImageReader(profile.logo_path)
            c.drawImage(img, 50, height - 110, width=80, height=80, preserveAspectRatio=True, mask='auto')
        except: pass
    
    c.setFillColor(colors.black)
    c.setFont(FONT_NAME, 20)
    c.drawString(150, height - 70, profile.company)
    
    c.setFont(FONT_NAME, 9)
    c.drawString(150, height - 90, profile.contacts)
    
    c.setLineWidth(2)
    c.line(40, height - 120, width - 40, height - 120)

    # --- 3. ЗАГОЛОВОК ---
    c.setFont(FONT_NAME, 16)
    c.drawCentredString(width / 2, height - 160, "КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ")
    
    c.setFont(FONT_NAME, 10)
    c.drawString(50, height - 190, f"Дата: {term}")

    # --- 4. ТАБЛИЦА ---
    table_top = height - 230
    c.setFont(FONT_NAME, 12)
    
    c.setFillColor(colors.HexColor("#f0f0f0"))
    c.rect(50, table_top - 25, width - 100, 25, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.drawString(60, table_top - 17, "Наименование услуги")
    c.drawString(width - 200, table_top - 17, "Стоимость")
    
    c.rect(50, table_top - 80, width - 100, 55, fill=0, stroke=1)
    c.setFont(FONT_NAME, 12)
    
    text_object = c.beginText(60, table_top - 45)
    text_object.setFont(FONT_NAME, 12)
    if len(service) > 40:
        text_object.textLine(service[:40])
        text_object.textLine(service[40:])
    else:
        text_object.textLine(service)
    c.drawText(text_object)

    c.setFont(FONT_NAME, 14)
    c.drawString(width - 190, table_top - 45, price)

    # --- 5. ИТОГО ---
    c.setFont(FONT_NAME, 14)
    c.drawString(width - 250, table_top - 120, "ИТОГО К ОПЛАТЕ:")
    c.setFont(FONT_NAME, 18)
    c.drawString(width - 150, table_top - 120, price)

    # --- 6. ПОДВАЛ ---
    c.setFont(FONT_NAME, 10)
    c.drawString(50, 80, "Руководитель _______________________")
    c.drawString(50, 60, "(подпись, расшифровка)")
    c.drawString(width - 200, 80, "М.П.")

    c.save()
    buffer.seek(0)

    # --- ОТПРАВКА В TELEGRAM ---
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    files = {'document': ('offer.pdf', buffer.getvalue(), 'application/pdf')}
    data = {'chat_id': chat_id, 'caption': 'Ваш документ готов!'}
    try:
        requests.post(url, files=files, data=data)
    except Exception as e:
        print(f"ОШИБКА: {e}")
    buffer.seek(0)
    
    return StreamingResponse(buffer, media_type="application/pdf")
