from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import io
import requests
import os
from datetime import datetime
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

DATABASE_URL = "sqlite:///./profiles.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, unique=True, index=True)
    company = Column(String)
    inn = Column(String)
    address = Column(String)
    contacts = Column(String)
    logo_path = Column(String)

Base.metadata.create_all(bind=engine)

# --- ШРИФТЫ ---
FONT_REGULAR = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'
possible_paths = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
]
for path in possible_paths:
    if os.path.exists(path):
        try:
            pdfmetrics.registerFont(TTFont('CustomFont', path))
            FONT_REGULAR = 'CustomFont'
            FONT_BOLD = 'CustomFont'
            break
        except: pass

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Бэкенд работает!"}

@app.post("/save-profile")
async def save_profile(
    chat_id: str = Form(...),
    company: str = Form(...),
    inn: str = Form(...),
    address: str = Form(...),
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
        profile.inn = inn
        profile.address = address
        profile.contacts = contacts
        if logo_path: profile.logo_path = logo_path
    else:
        new_profile = Profile(chat_id=chat_id, company=company, inn=inn, address=address, contacts=contacts, logo_path=logo_path)
        db.add(new_profile)
    
    db.commit()
    db.close()
    return {"status": "ok", "message": "Профиль сохранен"}

@app.post("/generate-doc")
async def generate_doc(
    chat_id: str = Form(...),
    service: str = Form(...),
    price: str = Form(...),
    term: str = Form(...),
    template: str = Form("kp")
):
    db = SessionLocal()
    profile = db.query(Profile).filter(Profile.chat_id == chat_id).first()
    db.close()

    if not profile:
        return {"status": "error", "message": "Сначала заполните профиль"}

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # --- РАМКА ---
    c.setStrokeColor(colors.HexColor("#cccccc"))
    c.setLineWidth(1)
    c.rect(40, 40, width - 80, height - 80)

    # --- ШАПКА (РЕКВИЗИТЫ) ---
    if profile.logo_path and os.path.exists(profile.logo_path):
        try:
            img = ImageReader(profile.logo_path)
            c.drawImage(img, 60, height - 120, width=70, height=70, preserveAspectRatio=True, mask='auto')
        except: pass
    
    c.setFillColor(colors.black)
    c.setFont(FONT_BOLD, 20)
    c.drawString(150, height - 80, profile.company)
    
    c.setFont(FONT_REGULAR, 9)
    c.setFillColor(colors.gray)
    c.drawString(150, height - 95, f"ИНН/КПП: {profile.inn}")
    c.drawString(150, height - 110, f"Адрес: {profile.address}")
    c.drawString(150, height - 125, f"Контакты: {profile.contacts}")
    
    c.setStrokeColor(colors.black)
    c.setLineWidth(1.5)
    c.line(60, height - 140, width - 60, height - 140)

    # --- ДАТА ---
    current_date = datetime.now().strftime("%d.%m.%Y")
    c.setFont(FONT_REGULAR, 10)
    c.setFillColor(colors.black)
    c.drawRightString(width - 60, height - 160, f"Дата: {current_date}")

    # --- ТЕЛО ДОКУМЕНТА ---
    if template == "kp":
        c.setFont(FONT_BOLD, 18)
        c.drawCentredString(width / 2, height - 210, "КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ")
        
        c.setFont(FONT_REGULAR, 12)
        c.drawString(60, height - 250, "Наименование услуги:")
        c.drawString(250, height - 250, service)
        
        c.drawString(60, height - 280, "Сроки:")
        c.drawString(250, height - 280, term)
        
        c.setFont(FONT_BOLD, 14)
        c.drawString(60, height - 330, "Стоимость:")
        c.drawString(250, height - 330, price)

    elif template == "smeta":
        c.setFont(FONT_BOLD, 18)
        c.drawCentredString(width / 2, height - 210, "СМЕТА")
        
        table_top = height - 250
        c.setFont(FONT_BOLD, 12)
        c.setFillColor(colors.HexColor("#f0f0f0"))
        c.rect(60, table_top - 25, width - 120, 25, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.drawString(70, table_top - 17, "Наименование работ")
        c.drawRightString(width - 70, table_top - 17, "Стоимость")
        
        c.setStrokeColor(colors.black)
        c.rect(60, table_top - 65, width - 120, 40, fill=0, stroke=1)
        c.setFont(FONT_REGULAR, 12)
        c.drawString(70, table_top - 45, service)
        c.drawRightString(width - 70, table_top - 45, price)

        # Итого
        c.setFont(FONT_BOLD, 14)
        c.drawRightString(width - 180, table_top - 100, "ИТОГО:")
        c.setFont(FONT_BOLD, 16)
        c.drawRightString(width - 70, table_top - 100, price)
        
        c.setFont(FONT_REGULAR, 10)
        c.drawString(60, table_top - 130, f"Сроки: {term}")

    elif template == "dogovor":
        c.setFont(FONT_BOLD, 18)
        c.drawCentredString(width / 2, height - 210, "ДОГОВОР ОКАЗАНИЯ УСЛУГ")
        
        c.setFont(FONT_BOLD, 12)
        c.drawString(60, height - 260, "1. Предмет договора:")
        c.setFont(FONT_REGULAR, 12)
        
        # Текст с отступами
        text_object = c.beginText(60, height - 280)
        text_object.textLine(f"Исполнитель обязуется оказать услугу: {service}")
        text_object.textLine("")
        text_object.textLine(f"Стоимость: {price}")
        text_object.textLine(f"Сроки: {term}")
        c.drawText(text_object)
        
        c.setFont(FONT_BOLD, 12)
        c.drawString(60, height - 360, "2. Подписи сторон:")
        
        c.setFont(FONT_REGULAR, 12)
        c.drawString(60, 150, "Исполнитель: _______________________")
        c.drawRightString(width - 60, 150, "Заказчик: _______________________")

    # --- ПОДВАЛ ---
    c.setFont(FONT_REGULAR, 10)
    c.setFillColor(colors.gray)
    c.drawString(60, 80, "Руководитель _______________________")
    c.drawString(60, 65, "(подпись, расшифровка)")
    c.drawRightString(width - 60, 80, "М.П.")

    c.save()
    buffer.seek(0)

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    files = {'document': ('document.pdf', buffer.getvalue(), 'application/pdf')}
    data = {'chat_id': chat_id, 'caption': 'Ваш документ готов!'}
    try:
        requests.post(url, files=files, data=data)
    except Exception as e:
        print(f"ОШИБКА: {e}")
    buffer.seek(0)
    
    return StreamingResponse(buffer, media_type="application/pdf")
