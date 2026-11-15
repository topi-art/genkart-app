from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import io, json, requests
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from xhtml2pdf import pisa
from num2words import num2words

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ТОЛЬКО НОВЫЙ ТОКЕН
BOT_TOKEN = "9065574882:AAEiC01s-YC1ADejERPNLcZSdEJS7qCZe_I" 
MY_CHAT_ID = "1124115675"

def decline_fio(fio):
    if not fio: return ""
    words = fio.split()
    res = []
    for word in words:
        if word.endswith("."): res.append(word)
        elif word.endswith("а"): res.append(word[:-1] + "ы")
        elif word.endswith("я"): res.append(word[:-1] + "и")
        elif word.endswith("на") or word.endswith("ва"): res.append(word + "ой")
        else: res.append(word + "а")
    return " ".join(res)

def get_signature_fio(fio):
    parts = fio.split()
    if len(parts) >= 2: return f"{parts[1]} {parts[0]}"
    return fio

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
    director = Column(String, default="Иванов И.И.")

Base.metadata.create_all(bind=engine)

CSS_STYLES = """
@page { size: a4; margin: 20mm 15mm 20mm 30mm; }
body { font-family: "Helvetica", sans-serif; font-size: 11pt; line-height: 1.35; text-align: justify; color: #000; text-indent: 1.25cm; }
h1.title { text-align: center; font-size: 14pt; font-weight: bold; margin-bottom: 20px; text-transform: uppercase; text-indent: 0; }
.meta { width: 100%; margin-bottom: 20px; text-indent: 0; }
.meta td { border: none; padding: 0; }
table { width: 100%; border-collapse: collapse; margin-top: 15px; text-indent: 0; }
th, td { border: 1px solid #000; padding: 6px; text-align: left; }
.header-info { margin-bottom: 20px; font-size: 10pt; text-align: left; text-indent: 0; }
.signature-block { margin-top: 30px; text-indent: 0; }
"""

def format_money(val):
    return f"{val:,.2f}".replace(',', ' ').replace('.', ',')

def num2words_rub(num):
    try:
        rub = int(num)
        kop = int(round((num - rub) * 100))
        rub_str = num2words(rub, lang='ru').capitalize()
        return f"{rub_str} рублей {kop:02d} копеек"
    except:
        return f"{format_money(num)} рублей"

def get_header_html(company, inn, address, contacts):
    return f"<div class='header-info'><strong>{company}</strong><br>ИНН: {inn}<br>Адрес: {address}<br>Тел: {contacts}</div>"

@app.get("/")
def read_root(): 
    return FileResponse("index.html")

@app.get("/get-profile")
async def get_profile(chat_id: str):
    db = SessionLocal()
    profile = db.query(Profile).filter(Profile.chat_id == chat_id).first()
    db.close()
    if profile:
        return {"status": "ok", "company": profile.company, "inn": profile.inn, "address": profile.address, "contacts": profile.contacts}
    return {"status": "not_found"}

@app.post("/save-profile")
async def save_profile(
    chat_id: str = Form(...), company: str = Form(""), inn: str = Form(""), address: str = Form(""), contacts: str = Form("")
):
    db = SessionLocal()
    try:
        profile = db.query(Profile).filter(Profile.chat_id == chat_id).first()
        if profile:
            profile.company, profile.inn, profile.address, profile.contacts = company, inn, address, contacts
        else:
            db.add(Profile(chat_id=chat_id, company=company, inn=inn, address=address, contacts=contacts))
        db.commit()
        return {"status": "ok"}
    except Exception as e: return {"status": "error", "message": str(e)}
    finally: db.close()

@app.post("/generate-doc")
async def generate_doc(
    template: str = Form("kp"), company: str = Form(""), inn: str = Form(""), 
    address: str = Form(""), contacts: str = Form(""), director: str = Form(""),
    services_json: str = Form("[]"), term: str = Form(""), dogovor_number: str = Form(""), 
    customer_name: str = Form(""), customer_inn: str = Form(""), chat_id: str = Form(None)
):
    try:
        services = json.loads(services_json)
        total_price = sum(float(s['price']) * int(s['qty']) for s in services)
        date_to_use = datetime.now().strftime("%d.%m.%Y")
        buffer = io.BytesIO()
        
        header_html = get_header_html(company, inn, address, contacts)

        if template == "kp":
            rows = "".join([f"<tr><td style='text-align:center;'>{i+1}</td><td>{s['name']}</td><td style='text-align:center;'>{s.get('unit', 'усл.')}</td><td style='text-align:center;'>{term}</td><td style='text-align:right;'>{format_money(float(s['price'])*int(s['qty']))} руб.</td></tr>" for i, s in enumerate(services)])
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            {header_html}
            <table class="meta"><tr><td style="text-align:right;">Исх. № {dogovor_number} от {date_to_use} г.</td></tr></table>
            <h1 class="title">Коммерческое предложение<br>на оказание услуг</h1>
            <table><tr><th style="text-align:center; width: 5%;">№</th><th style="width: 50%;">Наименование услуги</th><th style="text-align:center; width: 10%;">Ед.</th><th style="text-align:center; width: 15%;">Срок</th><th style="text-align:right; width: 20%;">Стоимость</th></tr>{rows}</table>
            <p style="text-align:right; margin-top: 10px; text-indent: 0;"><strong>Итого: {format_money(total_price)} руб.</strong></p>
            </body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        elif template == "smeta":
            rows = "".join([f"<tr><td style='text-align:center;'>{i+1}</td><td>{s['name']}</td><td style='text-align:center;'>{s.get('unit', 'усл.')}</td><td style='text-align:center;'>{s['qty']}</td><td style='text-align:right;'>{format_money(float(s['price']))}</td><td style='text-align:right;'>{format_money(float(s['price'])*int(s['qty']))}</td></tr>" for i, s in enumerate(services)])
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            <h1 class="title">Смета</h1>
            <table><tr><th>№</th><th>Наименование</th><th>Ед.</th><th>Кол-во</th><th>Цена</th><th>Сумма</th></tr>{rows}</table>
            </body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        else:
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            <h1 class="title">{template.upper()}</h1>
            <p>Общая сумма: {format_money(total_price)} руб.</p>
            </body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        buffer.seek(0)

        # Отправляем ТОЛЬКО через нового бота на твой ID
        target_chat_id = chat_id if chat_id else MY_CHAT_ID
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
        files = {'document': (f'{template}.pdf', buffer.getvalue(), 'application/pdf')}
        data = {'chat_id': target_chat_id, 'caption': 'Ваш документ готов! 📄'}
        requests.post(url, files=files, data=data)
            
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
