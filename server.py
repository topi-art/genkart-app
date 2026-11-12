from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
import io
import os
import json
import requests
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer
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

# --- БАЗА ДАННЫХ ---
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

# --- ЭНДПОИНТЫ ---
@app.get("/")
def read_root():
    return {"status": "ok", "message": "Бэкенд работает!"}

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
        return {"status": "ok", "message": "Сохранено"}
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
    smeta_date: str = Form(""),
    chat_id: str = Form(None)
):
    try:
        print(f"=== НАЧАЛО ГЕНЕРАЦИИ. Шаблон: {template}, chat_id: {chat_id} ===")
        
        services = json.loads(services_json)
        total_price = sum(float(s['price']) * int(s['qty']) for s in services)
        current_date = datetime.now().strftime("%d.%m.%Y")
        date_to_use = dogovor_date if dogovor_date else current_date
        smeta_date_to_use = smeta_date if smeta_date else current_date
        buffer = io.BytesIO()

        # --- ГЕНЕРАЦИЯ КП ---
        if template == "kp":
            rows = ""
            for i, s in enumerate(services):
                amount = float(s['price']) * int(s['qty'])
                rows += f"<tr><td>{i+1}</td><td>{s['name']}</td><td>{term} дн.</td><td style='text-align:right;'>{amount:.2f}</td></tr>"
            html = f"""<html><head><style>body{{font-family:'Times New Roman',serif;font-size:11pt;}}table{{width:100%;border-collapse:collapse;}}th,td{{border:1px solid #000;padding:8px;}}.title{{text-align:center;font-size:14pt;font-weight:bold;margin:20px 0;}}.header{{border-bottom:1px solid #000;padding-bottom:10px;margin-bottom:20px;}}</style></head><body>
            <div class="header"><strong>{company}</strong><br>ИНН {inn}<br>{address}<br>Тел: {contacts}</div>
            <div class="title">КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ</div>
            <p>Предлагаем вам следующие услуги:</p>
            <table><tr><th>№</th><th>Услуга</th><th>Срок</th><th>Стоимость</th></tr>{rows}</table>
            <p style="text-align:right;"><strong>Итого: {total_price:.2f} руб.</strong> (НДС не облагается)</p>
            <p><strong>Условия:</strong><br>1. КП действительно 14 дней.<br>2. Оплата 100% постоплата.</p><br>
            <p>Директор {company} _______________ / {director_name} /</p></body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        # --- ГЕНЕРАЦИЯ СМЕТЫ ---
        elif template == "smeta":
            rows = ""
            for i, s in enumerate(services):
                amount = float(s['price']) * int(s['qty'])
                rows += f"<tr><td>{i+1}</td><td>{s['name']}</td><td>усл.</td><td>{s['qty']}</td><td>{s['price']}</td><td>{amount:.2f}</td></tr>"
            html = f"""<html><head><style>body{{font-family:Arial,sans-serif;font-size:10pt;}}table{{width:100%;border-collapse:collapse;}}th,td{{border:1px solid #000;padding:6px;}}th{{background:#eee;}}</style></head><body>
            <div style="text-align:right;margin-bottom:20px;">Приложение № 1 к Договору № {dogovor_number} от {smeta_date_to_use}</div>
            <h1 style="text-align:center;font-size:13pt;">СМЕТА НА ОКАЗАНИЕ УСЛУГ</h1>
            <table><tr><th>№</th><th>Наименование</th><th>Ед.</th><th>Кол-во</th><th>Цена</th><th>Сумма</th></tr>{rows}
            <tr><td colspan="5" style="text-align:right;font-weight:bold;">Всего к оплате:</td><td style="font-weight:bold;">{total_price:.2f}</td></tr></table>
            <p style="margin-top:20px;"><strong>Всего наименований {len(services)}, на сумму {total_price:.2f} рублей.</strong></p><br><br>
            <table style="border:none;"><tr><td style="border:none;">Исполнитель: ______________ / {director_name} /<br>М.П.</td><td style="border:none;">Заказчик: ______________ / {customer_name} /<br>М.П.</td></tr></table></body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        # --- ГЕНЕРАЦИЯ ДОГОВОРА ---
        elif template == "dogovor":
            html = f"""<html><head><style>body{{font-family:'Times New Roman',serif;font-size:11pt;line-height:1.35;}}.title{{text-align:center;font-size:14pt;font-weight:bold;margin-bottom:20px;}}.meta{{display:flex;justify-content:space-between;}}</style></head><body>
            <div class="title">ДОГОВОР ОКАЗАНИЯ УСЛУГ № {dogovor_number}</div>
            <div class="meta"><span>г. Москва</span><span>«{date_to_use}» г.</span></div>
            <p>{company}, в лице {director_name}, с одной стороны, и {customer_name} (ИНН: {customer_inn}, адрес: {customer_address}), с другой стороны, заключили Договор:</p>
            <p><strong>1. ПРЕДМЕТ ДОГОВОРА</strong><br>1.1. Исполнитель обязуется оказать услуги согласно Смете.</p>
            <p><strong>2. СТОИМОСТЬ И ПОРЯДОК РАСЧЕТОВ</strong><br>2.1. Общая стоимость Услуг составляет {total_price:.2f} руб.</p>
            <p><strong>3. ОТВЕТСТВЕННОСТЬ СТОРОН</strong><br>3.1. За нарушение сроков оплаты неустойка 0,1%.</p>
            <p><strong>4. ЗАКЛЮЧИТЕЛЬНЫЕ ПОЛОЖЕНИЯ</strong><br>4.1. Договор действует до полного исполнения.</p><br><br>
            <table style="border:none;width:100%;"><tr><td style="border:none;width:50%;"><strong>ИСПОЛНИТЕЛЬ:</strong><br>{company}<br>ИНН: {inn}<br><br>______________ / {director_name} /</td><td style="border:none;width:50%;"><strong>ЗАКАЗЧИК:</strong><br>{customer_name}<br>ИНН: {customer_inn}<br><br>______________ / ФИО /</td></tr></table></body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        print("=== PDF УСПЕШНО СГЕНЕРИРОВАН В ПАМЯТИ ===")
        buffer.seek(0)

        # --- ОТПРАВКА В TELEGRAM ---
        if chat_id:
            print(f"=== ПОПЫТКА ОТПРАВКИ В TELEGRAM ДЛЯ CHAT_ID: {chat_id} ===")
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            files = {'document': ('document.pdf', buffer.getvalue(), 'application/pdf')}
            data = {'chat_id': chat_id, 'caption': 'Ваш документ готов!'}
            try:
                response = requests.post(url, files=files, data=data)
                print(f"=== ОТВЕТ ОТ TELEGRAM API: {response.status_code} ===")
                print(f"=== ТЕКСТ ОТВЕТА: {response.text} ===")
            except Exception as e:
                print(f"=== КРИТИЧЕСКАЯ ОШИБКА ОТПРАВКИ В ТГ: {e} ===")
                return JSONResponse(status_code=500, content={"status": "error", "message": f"Ошибка ТГ: {str(e)}"})
        else:
            print("=== CHAT_ID ОТСУТСТВУЕТ, ОТПРАВКА В ТГ ПРОПУЩЕНА ===")

        buffer.seek(0)
        return StreamingResponse(buffer, media_type="application/pdf")

    except Exception as e:
        print(f"=== ОШИБКА ПРИ ГЕНЕРАЦИИ ДОКУМЕНТА: {e} ===")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
