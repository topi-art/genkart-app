from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import io
import requests
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

DATABASE_URL = "sqlite:///./profiles_v6.db"
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
    template: str = Form("kp"),
    services_json: str = Form("[]"),
    term: str = Form("30"),
    dogovor_number: str = Form("Б/Н"),
    dogovor_date: str = Form(""),
    customer_name: str = Form(""),
    customer_inn: str = Form(""),
    customer_address: str = Form(""),
    director_name: str = Form(""),
    smeta_date: str = Form("")
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

    services = json.loads(services_json)
    total_price = sum(float(s['price']) * int(s['qty']) for s in services)
    
    buffer = io.BytesIO()
    current_date = datetime.now().strftime("%d.%m.%Y")
    date_to_use = dogovor_date if dogovor_date else current_date
    smeta_date_to_use = smeta_date if smeta_date else current_date

    # --- ГЕНЕРАЦИЯ КП ---
    if template == "kp":
        rows_html = ""
        for i, s in enumerate(services):
            amount = float(s['price']) * int(s['qty'])
            rows_html += f"<tr><td>{i+1}</td><td>{s['name']}</td><td>{term} дней</td><td class='right'>{amount:.2f}</td></tr>"

        html_content = f"""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{ size: A4; margin: 20mm; }}
                body {{ font-family: "Times New Roman", serif; font-size: 11pt; line-height: 1.35; }}
                .header {{ text-align: left; border-bottom: 1px solid #000; padding-bottom: 10px; margin-bottom: 20px; }}
                .title {{ text-align: center; font-weight: bold; font-size: 14pt; margin: 20px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                table, th, td {{ border: 1px solid #000; padding: 8px; }}
                .right {{ text-align: right; }}
            </style>
        </head>
        <body>
            <div class="header">
                <strong>{profile.company}</strong><br>
                ИНН {profile.inn}<br>
                Адрес: {profile.address}<br>
                Тел.: {profile.contacts}
            </div>
            <div style="text-align: right;">Исх. № ___ от {current_date} г.</div>
            <div class="title">КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ<br>на оказание услуг</div>
            <p>Компания {profile.company} предлагает вам следующие услуги:</p>
            <table>
                <tr><th>№</th><th>Наименование услуги</th><th>Срок</th><th>Стоимость, руб.</th></tr>
                {rows_html}
            </table>
            <p class="right"><strong>Итого к оплате: {total_price:.2f} руб.</strong> (НДС не облагается, УСН)</p>
            
            <p><strong>Условия сотрудничества:</strong></p>
            <ol>
                <li>КП действительно в течение 14 календарных дней.</li>
                <li>Порядок оплаты: 100% постоплата в течение 3 банковских дней.</li>
                <li>Гарантия на работы 12 месяцев.</li>
            </ol>
            <br>
            <p>С уважением,<br>Генеральный директор {profile.company} _______________ / {director_name} /</p>
        </body>
        </html>
        """
        pisa.CreatePDF(html_content, dest=buffer)

    # --- ГЕНЕРАЦИЯ СМЕТЫ ---
    elif template == "smeta":
        rows_html = ""
        for i, s in enumerate(services):
            amount = float(s['price']) * int(s['qty'])
            rows_html += f"<tr><td>{i+1}</td><td>{s['name']}</td><td>усл.</td><td class='num'>{s['qty']}</td><td class='num'>{s['price']}</td><td class='num'>{amount:.2f}</td></tr>"

        html_content = f"""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{ size: A4; margin: 20mm; }}
                body {{ font-family: Arial, sans-serif; font-size: 10pt; }}
                .app-header {{ text-align: right; margin-bottom: 20px; }}
                h1 {{ text-align: center; font-size: 13pt; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                th, td {{ border: 1px solid #000; padding: 6px; }}
                th {{ background: #eaeaea; text-align: center; }}
                .num {{ text-align: right; }}
                .bold {{ font-weight: bold; }}
                .signs {{ width: 100%; margin-top: 40px; }}
            </style>
        </head>
        <body>
            <div class="app-header">Приложение № 1<br>к Договору № {dogovor_number} от {smeta_date_to_use} г.</div>
            <h1>СМЕТА НА ОКАЗАНИЕ УСЛУГ</h1>
            <table>
                <tr><th>№</th><th>Наименование</th><th>Ед.</th><th>Кол-во</th><th>Цена, руб.</th><th>Сумма, руб.</th></tr>
                {rows_html}
                <tr class="bold"><td colspan="5" class="num">Всего к оплате:</td><td class="num">{total_price:.2f}</td></tr>
            </table>
            <p style="margin-top: 15px;"><strong>Всего наименований {len(services)}, на сумму {total_price:.2f} рублей.</strong></p>
            <table class="signs">
                <tr>
                    <td style="border: none; width: 50%;"><strong>Исполнитель:</strong><br><br>________________ / {director_name} /<br>М.П.</td>
                    <td style="border: none; width: 50%;"><strong>Заказчик:</strong><br><br>________________ / {customer_name} /<br>М.П.</td>
                </tr>
            </table>
        </body>
        </html>
        """
        pisa.CreatePDF(html_content, dest=buffer)

    # --- ГЕНЕРАЦИЯ ДОГОВОРА ---
    elif template == "dogovor":
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{ size: A4; margin: 20mm; }}
                body {{ font-family: "Times New Roman", serif; font-size: 11pt; line-height: 1.35; }}
                .title {{ text-align: center; font-weight: bold; font-size: 14pt; margin-bottom: 20px; }}
                .meta {{ display: flex; justify-content: space-between; margin-bottom: 20px; }}
                .signs {{ width: 100%; margin-top: 40px; }}
                .signs td {{ width: 50%; vertical-align: top; border: none; }}
            </style>
        </head>
        <body>
            <div class="title">ДОГОВОР ОКАЗАНИЯ УСЛУГ № {dogovor_number}</div>
            <div class="meta"><span>г. Москва</span><span>«{date_to_use}» г.</span></div>
            <p>{profile.company}, в лице {director_name}, с одной стороны, и {customer_name} (ИНН: {customer_inn}, адрес: {customer_address}), с другой стороны, заключили Договор:</p>
            <p><strong>1. ПРЕДМЕТ ДОГОВОРА</strong><br>1.1. Исполнитель обязуется оказать услуги, указанные в Смете (Приложение № 1).</p>
            <p><strong>2. СТОИМОСТЬ И ПОРЯДОК РАСЧЕТОВ</strong><br>2.1. Общая стоимость Услуг составляет {total_price:.2f} руб.<br>2.2. Оплата в течение 3 банковских дней.</p>
            <p><strong>3. ОТВЕТСТВЕННОСТЬ СТОРОН</strong><br>3.1. За нарушение сроков оплаты неустойка 0,1%.</p>
            <p><strong>4. ЗАКЛЮЧИТЕЛЬНЫЕ ПОЛОЖЕНИЯ</strong><br>4.1. Договор действует до полного исполнения.</p>
            <br><br>
            <table class="signs">
                <tr>
                    <td><strong>ИСПОЛНИТЕЛЬ:</strong><br>{profile.company}<br>ИНН: {profile.inn}<br><br>________________ / {director_name} /</td>
                    <td><strong>ЗАКАЗЧИК:</strong><br>{customer_name}<br>ИНН: {customer_inn}<br><br>________________ / ФИО /</td>
                </tr>
            </table>
        </body>
        </html>
        """
        pisa.CreatePDF(html_content, dest=buffer)

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
