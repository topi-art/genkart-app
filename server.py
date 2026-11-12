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

DATABASE_URL = "sqlite:///./profiles_v3.db"
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
    documents_count = Column(Integer, default=0)
    subscription_end_date = Column(DateTime, nullable=True)

Base.metadata.create_all(bind=engine)

FONT_REGULAR = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'
possible_paths = [
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
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
    # (Логика сохранения профиля без изменений)
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
    finally:
        db.close()

@app.post("/generate-doc")
async def generate_doc(
    chat_id: str = Form(...),
    service: str = Form(...),
    price: str = Form(...),
    template: str = Form("kp"),
    # Новые поля
    dogovor_number: str = Form(None),
    dogovor_date: str = Form(None),
    customer_name: str = Form(None),
    customer_inn: str = Form(None),
    customer_address: str = Form(None),
    director_name: str = Form(None),
    smeta_term: str = Form(None),
    smeta_date: str = Form(None)
):
    db = SessionLocal()
    profile = db.query(Profile).filter(Profile.chat_id == chat_id).first()
    
    if not profile:
        db.close()
        return {"status": "error", "message": "Сначала заполните профиль"}

    now = datetime.now()
    has_subscription = profile.subscription_end_date and profile.subscription_end_date > now

    if not has_subscription and profile.documents_count >= 3:
        db.close()
        return {"status": "limit_reached", "message": "Лимит бесплатных документов исчерпан."}

    buffer = io.BytesIO()
    current_date = datetime.now().strftime("%d.%m.%Y")

    if template == "smeta":
        # Используем HTML-шаблон для сметы (передаем smeta_term и smeta_date)
        date_to_use = smeta_date if smeta_date else current_date
        term_to_use = smeta_term if smeta_term else "30"
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{ size: A4; margin: 20mm; }}
                body {{ font-family: Arial, sans-serif; font-size: 10pt; color: #000; margin: 0; }}
                .app-header {{ text-align: right; font-size: 9.5pt; margin-bottom: 20px; }}
                h1 {{ text-align: center; font-size: 13pt; margin-bottom: 15px; }}
                table.smeta {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                table.smeta th, table.smeta td {{ border: 1px solid #000; padding: 6px 8px; }}
                table.smeta th {{ background: #eaeaea; text-align: center; font-weight: bold; }}
                .num {{ text-align: right; white-space: nowrap; }}
                .center {{ text-align: center; }}
                .bold {{ font-weight: bold; }}
                .signs {{ width: 100%; margin-top: 40px; }}
                .signs td {{ width: 50%; vertical-align: top; }}
            </style>
        </head>
        <body>
            <div class="app-header">
                Приложение № 1<br>
                к Договору оказания услуг от {date_to_use} г.
            </div>
            
            <h1>СМЕТА НА ОКАЗАНИЕ УСЛУГ</h1>
            
            <table class="smeta">
                <thead>
                    <tr>
                        <th style="width: 40px;">№</th>
                        <th>Наименование работ / услуг</th>
                        <th style="width: 60px;">Ед. изм.</th>
                        <th style="width: 60px;">Кол-во</th>
                        <th style="width: 110px;">Цена, руб.</th>
                        <th style="width: 120px;">Сумма, руб.</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="center">1</td>
                        <td>{service}</td>
                        <td class="center">усл.</td>
                        <td class="num">1</td>
                        <td class="num">{price}</td>
                        <td class="num">{price}</td>
                    </tr>
                    <tr class="bold">
                        <td colspan="5" class="num">Итого по смете:</td>
                        <td class="num">{price}</td>
                    </tr>
                    <tr class="bold">
                        <td colspan="5" class="num">Всего к оплате:</td>
                        <td class="num">{price}</td>
                    </tr>
                </tbody>
            </table>
            
            <p style="margin-top: 15px;"><strong>Сроки выполнения работ: {term_to_use} дней.</strong></p>
            
            <table class="signs">
                <tr>
                    <td><strong>Исполнитель:</strong><br><br>________________ / {profile.company} /<br>М.П.</td>
                    <td><strong>Заказчик:</strong><br><br>________________ / ________________ /<br>М.П.</td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        pisa_status = pisa.CreatePDF(html_content, dest=buffer)
        if pisa_status.err:
            db.close()
            return {"status": "error", "message": "Ошибка генерации PDF"}

    else:
        # --- REPORTLAB ДЛЯ КП И ДОГОВОРА ---
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Шапка и логотип
        if profile.logo_path and os.path.exists(profile.logo_path):
            try:
                img = ImageReader(profile.logo_path)
                c.drawImage(img, 45, height - 95, width=60, height=60, preserveAspectRatio=True, mask='auto')
            except: pass
        
        c.setFillColor(colors.black)
        c.setFont(FONT_BOLD, 20)
        c.drawString(120, height - 60, profile.company) 
        
        c.setFont(FONT_REGULAR, 9)
        c.setFillColor(colors.gray)
        c.drawString(120, height - 80, f"ИНН/КПП: {profile.inn}")
        c.drawString(120, height - 95, f"Адрес: {profile.address}")
        c.drawString(120, height - 110, f"Контакты: {profile.contacts}")
        
        c.setStrokeColor(colors.black)
        c.setLineWidth(2)
        c.line(40, height - 130, width - 40, height - 130)

        c.setFont(FONT_REGULAR, 10)
        c.setFillColor(colors.black)
        c.drawRightString(width - 50, height - 150, f"Дата: {current_date}")

        if template == "dogovor":
            # --- ДОГОВОР ---
            c.setFont(FONT_BOLD, 16)
            c.drawCentredString(width / 2, height - 190, f"ДОГОВОР ОКАЗАНИЯ УСЛУГ № {dogovor_number}")
            
            c.setFont(FONT_REGULAR, 11)
            c.drawString(60, height - 220, f"г. Москва")
            c.drawRightString(width - 60, height - 220, f"«{dogovor_date}» г.")
            
            # Текст договора
            text_object = c.beginText(60, height - 260)
            text_object.setFont(FONT_REGULAR, 10)
            text_object.textLine(f"{profile.company}, именуемое в дальнейшем «Исполнитель», в лице {director_name}, действующего на основании Устава, с одной стороны, и")
            text_object.textLine(f"{customer_name}, именуемое в дальнейшем «Заказчик», в лице представителя, действующего на основании Устава, с другой стороны, заключили настоящий Договор о нижеследующем:")
            text_object.textLine("")
            text_object.textLine("1. ПРЕДМЕТ ДОГОВОРА")
            text_object.textLine(f"1.1. Исполнитель обязуется оказать услугу: {service}.")
            text_object.textLine(f"1.2. Стоимость услуг составляет: {price} руб.")
            text_object.textLine("")
            text_object.textLine("2. ПОРЯДОК РАСЧЕТОВ")
            text_object.textLine("2.1. Оплата производится в течение 3 банковских дней с момента подписания Акта.")
            text_object.textLine("")
            text_object.textLine("3. ОТВЕТСТВЕННОСТЬ СТОРОН")
            text_object.textLine("3.1. За нарушение сроков оплаты Заказчик уплачивает неустойку 0,1% за каждый день просрочки.")
            text_object.textLine("")
            text_object.textLine("4. ПОДПИСИ СТОРОН")
            c.drawText(text_object)

            c.setFont(FONT_REGULAR, 11)
            c.drawString(60, 150, "Исполнитель: _______________________")
            c.drawRightString(width - 60, 150, "Заказчик: _______________________")

        else:
            # --- КП ---
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
            c.drawString(60, table_top - 45, service)
            c.drawString(width - 150, table_top - 45, price)

            c.setFont(FONT_BOLD, 14)
            c.drawString(width - 350, table_top - 120, "ИТОГО К ОПЛАТЕ:")
            c.setFont(FONT_BOLD, 18)
            c.drawRightString(width - 50, table_top - 120, price)

        c.save()
    
    buffer.seek(0)

    if not has_subscription:
        profile.documents_count += 1
        db.commit()
    
    db.close()

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    files = {'document': ('document.pdf', buffer.getvalue(), 'application/pdf')}
    data = {'chat_id': chat_id, 'caption': 'Ваш документ готов!'}
    try:
        requests.post(url, files=files, data=data)
    except Exception as e:
        print(f"ОШИБКА: {e}")
    buffer.seek(0)
    
    return StreamingResponse(buffer, media_type="application/pdf")
