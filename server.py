from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import io
import requests
import os
from datetime import datetime, timedelta
from textwrap import wrap
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

DATABASE_URL = "sqlite:///./profiles_v2.db"
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

# --- ПОИСК КРАСИВЫХ ШРИФТОВ (С ЗАСЕЧКАМИ И БЕЗ) ---
FONT_REGULAR = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'
possible_paths = [
    # Шрифты без засечек (для заголовков)
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    # Шрифты с засечками (для текста, как Times New Roman)
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
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
    try:
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
        return {"status": "ok", "message": "Профиль сохранен"}
    except Exception as e:
        print(f"ОШИБКА БД: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@app.post("/generate-doc")
async def generate_doc(
    chat_id: str = Form(...),
    service: str = Form(...),
    price: str = Form(...),
    term: str = Form(...),
    template: str = Form("kp"),
    payment: str = Form("prepay")
):
    db = SessionLocal()
    profile = db.query(Profile).filter(Profile.chat_id == chat_id).first()
    db.close()

    if not profile:
        return {"status": "error", "message": "Сначала заполните профиль"}

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # --- ВОДЯНОЙ ЗНАК ---
    if profile.logo_path and os.path.exists(profile.logo_path):
        try:
            c.saveState()
            c.setFillAlpha(0.05)
            img = ImageReader(profile.logo_path)
            c.drawImage(img, width/2 - 200, height/2 - 200, width=400, height=400, preserveAspectRatio=True, mask='auto')
            c.restoreState()
        except: pass

    # --- РАМКА ---
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.rect(30, 30, width - 60, height - 60)
    c.setLineWidth(0.5)
    c.rect(35, 35, width - 70, height - 70)

    # --- ШАПКА ---
    if profile.logo_path and os.path.exists(profile.logo_path):
        try:
            img = ImageReader(profile.logo_path)
            c.drawImage(img, 50, height - 110, width=80, height=80, preserveAspectRatio=True, mask='auto')
        except: pass
    
    c.setFillColor(colors.black)
    c.setFont(FONT_BOLD, 20)
    c.drawString(150, height - 70, profile.company)
    
    c.setFont(FONT_REGULAR, 9)
    c.setFillColor(colors.gray)
    c.drawString(150, height - 90, f"ИНН/КПП: {profile.inn}")
    c.drawString(150, height - 105, f"Адрес: {profile.address}")
    c.drawString(150, height - 120, f"Контакты: {profile.contacts}")
    
    c.setStrokeColor(colors.black)
    c.setLineWidth(2)
    c.line(40, height - 130, width - 40, height - 130)

    current_date = datetime.now().strftime("%d.%m.%Y")
    c.setFont(FONT_REGULAR, 10)
    c.setFillColor(colors.black)
    c.drawRightString(width - 50, height - 150, f"Дата: {current_date}")

    # --- ОПРЕДЕЛЯЕМ ТЕКСТ УСЛОВИЙ ОПЛАТЫ ---
    if payment == "prepay":
        payment_text = "100% предоплата"
    elif payment == "half":
        payment_text = "50% предоплата, 50% по факту"
    else:
        payment_text = "100% постоплата"

    # --- ТЕЛО ---
    if template == "kp":
        c.setFont(FONT_BOLD, 16)
        c.drawCentredString(width / 2, height - 190, "КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ")
        
        table_top = height - 230
        c.setFont(FONT_BOLD, 12)
        c.setFillColor(colors.HexColor("#f0f0f0"))
        c.rect(50, table_top - 25, width - 100, 25, fill=1, stroke=1)
        c.setFillColor(colors.black)
        c.drawString(60, table_top - 17, "Наименование услуги")
        c.drawString(width - 150, table_top - 17, "Стоимость")
        
        c.rect(50, table_top - 80, width - 100, 55, fill=0, stroke=1)
        c.setFont(FONT_REGULAR, 12)
        
        text_object = c.beginText(60, table_top - 45)
        text_object.setFont(FONT_REGULAR, 12)
        if len(service) > 40:
            text_object.textLine(service[:40])
            text_object.textLine(service[40:])
        else:
            text_object.textLine(service)
        c.drawText(text_object)

        c.setFont(FONT_BOLD, 14)
        c.drawString(width - 150, table_top - 45, price)

        c.setFont(FONT_BOLD, 14)
        c.drawString(width - 350, table_top - 120, "ИТОГО К ОПЛАТЕ:")
        c.setFont(FONT_BOLD, 18)
        c.drawRightString(width - 50, table_top - 120, price)

        if term.isdigit():
            delivery_date = (datetime.now() + timedelta(days=int(term))).strftime("%d.%m.%Y")
            term_text = f"{term} дней (до {delivery_date})"
        else:
            term_text = term

        c.setFont(FONT_REGULAR, 12)
        c.drawString(60, table_top - 160, f"Сроки оказания услуг: {term_text}")
        
        # --- УСЛОВИЯ ДЛЯ КП ---
        c.setFont(FONT_BOLD, 12)
        c.drawString(60, table_top - 220, "УСЛОВИЯ ПРЕДЛОЖЕНИЯ:")
        
        conditions_kp = [
            "1. Настоящее коммерческое предложение (КП) действительно в течение 14 (четырнадцати) календарных дней с даты его формирования.",
            f"2. Порядок оплаты: {payment_text} от общей стоимости в течение 3 (трех) банковских дней с момента выставления счета.",
            "3. Гарантия на выполняемые работы (поставляемый товар) составляет 12 месяцев с момента подписания закрывающих документов.",
            "4. Указанные цены носят информационный характер. Настоящее КП не является публичной офертой в соответствии со ст. 437 ГК РФ."
        ]
        
        y_pos = table_top - 240
        for cond in conditions_kp:
            lines = wrap(cond, width=85) 
            for line in lines:
                c.setFont(FONT_REGULAR, 9)
                c.drawString(60, y_pos, line)
                y_pos -= 12
            y_pos -= 8

    elif template == "smeta":
        c.setFont(FONT_BOLD, 16)
        c.drawCentredString(width / 2, height - 190, "СМЕТА")
        
        table_top = height - 230
        c.setFont(FONT_BOLD, 12)
        c.setFillColor(colors.HexColor("#f0f0f0"))
        c.rect(50, table_top - 25, width - 100, 25, fill=1, stroke=1)
        c.setFillColor(colors.black)
        c.drawString(60, table_top - 17, "№")
        c.drawString(90, table_top - 17, "Наименование работ")
        c.drawString(width - 150, table_top - 17, "Стоимость")
        
        c.rect(50, table_top - 80, width - 100, 55, fill=0, stroke=1)
        c.line(80, table_top - 80, 80, table_top - 25)
        
        c.setFont(FONT_REGULAR, 12)
        c.drawString(65, table_top - 45, "1")
        c.drawString(90, table_top - 45, service)
        c.drawString(width - 150, table_top - 45, price)

        c.setFont(FONT_BOLD, 14)
        c.drawString(width - 350, table_top - 120, "ИТОГО:")
        c.setFont(FONT_BOLD, 18)
        c.drawRightString(width - 50, table_top - 120, price)

        if term.isdigit():
            delivery_date = (datetime.now() + timedelta(days=int(term))).strftime("%d.%m.%Y")
            term_text = f"{term} дней (до {delivery_date})"
        else:
            term_text = term

        c.setFont(FONT_REGULAR, 12)
        c.drawString(60, table_top - 160, f"Сроки: {term_text}")

        # --- ПРИМЕЧАНИЯ ДЛЯ СМЕТЫ ---
        c.setFont(FONT_BOLD, 12)
        c.drawString(60, table_top - 220, "ПРИМЕЧАНИЯ К СМЕТЕ:")
        
        conditions_smeta = [
            "1. Настоящая Смета является неотъемлемой частью Договора (Приложение № 1) и действительна только при наличии подписей обеих Сторон.",
            "2. Расчет является предварительным. Итоговая стоимость может быть скорректирована при изменении объема работ более чем на 10%.",
            "3. Транспортные расходы и доставка: рассчитываются отдельно по тарифам транспортной компании и оплачиваются Заказчиком.",
            "4. В стоимость сметы не включены дополнительные работы, не указанные в перечне выше."
        ]
        
        y_pos = table_top - 240
        for cond in conditions_smeta:
            lines = wrap(cond, width=85) 
            for line in lines:
                c.setFont(FONT_REGULAR, 9)
                c.drawString(60, y_pos, line)
                y_pos -= 12
            y_pos -= 8

    elif template == "dogovor":
        c.setFont(FONT_BOLD, 16)
        c.drawCentredString(width / 2, height - 190, "ДОГОВОР ОКАЗАНИЯ УСЛУГ")
        
        c.setFont(FONT_BOLD, 12)
        c.drawString(60, height - 230, "1. Предмет договора:")
        
        c.setFont(FONT_REGULAR, 11)
        text_object = c.beginText(80, height - 250)
        text_object.textLine(f"Исполнитель обязуется оказать услугу: {service}.")
        text_object.textLine(f"Стоимость услуг составляет: {price}.")
        text_object.textLine(f"Порядок оплаты: {payment_text}.")
        
        if term.isdigit():
            delivery_date = (datetime.now() + timedelta(days=int(term))).strftime("%d.%m.%Y")
            term_text = f"{term} календарных дней (до {delivery_date})"
        else:
            term_text = term
        text_object.textLine(f"Сроки оказания услуг: {term_text}.")
        c.drawText(text_object)

        # --- ЗАКЛЮЧИТЕЛЬНЫЕ ПОЛОЖЕНИЯ ДЛЯ ДОГОВОРА ---
        c.setFont(FONT_BOLD, 12)
        c.drawString(60, height - 340, "ЗАКЛЮЧИТЕЛЬНЫЕ ПОЛОЖЕНИЯ И ОТВЕТСТВЕННОСТЬ СТОРОН:")
        
        conditions_dogovor = [
            "1. Настоящий Договор вступает в силу с момента его подписания обеими Сторонами и действует до полного исполнения обязательств.",
            "2. Приемка результатов работ оформляется двусторонним Актом. Заказчик обязан подписать Акт в течение 3 рабочих дней или направить мотивированный отказ.",
            "3. За нарушение сроков оплаты Заказчик уплачивает неустойку 0,1% от суммы задолженности за каждый день просрочки, но не более 10%.",
            "4. За нарушение сроков исполнения обязательств Исполнитель уплачивает неустойку 0,1% от стоимости неисполненной части, но не более 10%.",
            "5. Все споры решаются путем переговоров, а при недостижении согласия — в Арбитражном суде по месту нахождения Истца."
        ]
        
        y_pos = height - 360
        for cond in conditions_dogovor:
            lines = wrap(cond, width=85) 
            for line in lines:
                c.setFont(FONT_REGULAR, 9)
                c.drawString(60, y_pos, line)
                y_pos -= 12
            y_pos -= 8

        c.setFont(FONT_BOLD, 12)
        c.drawString(60, height - 520, "Подписи сторон:")
        c.setFont(FONT_REGULAR, 11)
        c.drawString(60, 150, "Исполнитель: _______________________")
        c.drawRightString(width - 60, 150, "Заказчик: _______________________")

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
