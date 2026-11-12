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

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BOT_TOKEN = "9195903180:AAGSvvim9LlwkYhCCNRoFk_e09OQ_Fyh_58" 

# --- АВТОМАТИЧЕСКАЯ ЗАГРУЗКА ШРИФТА ---
FONT_PATH = "DejaVuSans.ttf"
FONT_URL = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"

if not os.path.exists(FONT_PATH):
    try:
        print("Скачиваем шрифт...")
        r = requests.get(FONT_URL, timeout=30)
        with open(FONT_PATH, 'wb') as f:
            f.write(r.content)
        print("Шрифт успешно скачан!")
    except Exception as e:
        print(f"Ошибка скачивания шрифта: {e}")

# Регистрируем шрифт
try:
    pdfmetrics.registerFont(TTFont('DejaVuSans', FONT_PATH))
    FONT_NAME = 'DejaVuSans'
except Exception as e:
    print(f"Ошибка регистрации шрифта: {e}")
    FONT_NAME = 'Helvetica'

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Бэкенд работает!"}

@app.post("/generate-doc")
async def generate_doc(
    logo: UploadFile = File(None),
    company: str = Form(...),
    service: str = Form(...),
    price: str = Form(...),
    term: str = Form(...),
    contacts: str = Form(...),
    template: str = Form("template1"),
    chat_id: str = Form(None)
):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # --- ЛОГИКА ДИЗАЙНА ---
    if template == "template1": # Строгий
        c.setFillColor(colors.black)
        c.setFont(FONT_NAME, 24)
        c.drawString(50, height - 80, company)
        
        c.setStrokeColor(colors.gray)
        c.line(50, height - 90, width - 50, height - 90)
        
        c.setFont(FONT_NAME, 14)
        c.drawString(50, height - 130, "Коммерческое предложение")
        
        c.setFont(FONT_NAME, 12)
        c.drawString(50, height - 170, f"Услуга: {service}")
        c.drawString(50, height - 190, f"Стоимость: {price}")
        c.drawString(50, height - 210, f"Сроки: {term}")
        
        c.setFont(FONT_NAME, 12)
        c.drawString(50, 100, "Контакты:")
        c.drawString(50, 80, contacts)

    elif template == "template2": # Современный
        c.setFillColor(colors.HexColor("#FF2A75"))
        c.rect(0, height - 150, width, 150, fill=1, stroke=0)
        
        c.setFillColor(colors.white)
        c.setFont(FONT_NAME, 28)
        c.drawString(50, height - 90, company)
        
        c.setFillColor(colors.black)
        c.setFont(FONT_NAME, 16)
        c.drawString(50, height - 200, "Предложение услуг")
        
        c.setFont(FONT_NAME, 14)
        c.drawString(50, height - 250, service)
        
        c.setFont(FONT_NAME, 12)
        c.drawString(50, height - 280, f"Инвестиции: {price}")
        c.drawString(50, height - 300, f"Срок реализации: {term}")
        
        c.setFillColor(colors.gray)
        c.setFont(FONT_NAME, 10)
        c.drawString(50, 80, contacts)

    elif template == "template3": # Смета
        c.setFillColor(colors.black)
        c.setFont(FONT_NAME, 20)
        c.drawString(50, height - 80, "СМЕТА")
        
        c.setFont(FONT_NAME, 12)
        c.drawString(50, height - 110, f"Исполнитель: {company}")
        
        c.setStrokeColor(colors.black)
        c.line(50, height - 150, width - 50, height - 150)
        c.line(50, height - 180, width - 50, height - 180)
        
        c.setFont(FONT_NAME, 12)
        c.drawString(50, height - 170, "Наименование работ")
        c.drawString(width - 200, height - 170, "Стоимость")
        
        c.setFont(FONT_NAME, 12)
        c.drawString(50, height - 210, service)
        c.drawString(width - 200, height - 210, price)
        
        c.line(50, height - 230, width - 50, height - 230)
        
        c.setFont(FONT_NAME, 14)
        c.drawString(width - 200, height - 260, f"Итого: {price}")
        
        c.setFont(FONT_NAME, 10)
        c.drawString(50, 80, f"Сроки: {term} | Контакты: {contacts}")

    # --- ДОБАВЛЯЕМ ЛОГОТИП ---
    if logo:
        try:
            logo_data = await logo.read()
            img = ImageReader(io.BytesIO(logo_data))
            c.drawImage(img, width - 150, height - 120, width=100, height=100, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f"Ошибка логотипа: {e}")

    c.save()
    buffer.seek(0)

    # --- ОТПРАВКА В TELEGRAM ---
    if chat_id:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
        files = {'document': ('offer.pdf', buffer.getvalue(), 'application/pdf')}
        data = {'chat_id': chat_id, 'caption': 'Ваш документ готов!'}
        try:
            requests.post(url, files=files, data=data)
        except Exception as e:
            print(f"ОШИБКА: {e}")
        buffer.seek(0)
    
    return StreamingResponse(buffer, media_type="application/pdf")
