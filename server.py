from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import io
import requests
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text
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

DATABASE_URL = "sqlite:///./profiles_v5.db"
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
    custom_conditions = Column(Text, nullable=True)

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
    finally:
        db.close()

@app.post("/generate-doc")
async def generate_doc(
    chat_id: str = Form(...),
    service: str = Form(...),
    price: str = Form(...),
    term: str = Form("30"),
    template: str = Form("kp"),
    dogovor_number: str = Form("Б/Н"),
    dogovor_date: str = Form(""),
    customer_name: str = Form(""),
    customer_inn: str = Form(""),
    customer_address: str = Form(""),
    director_name: str = Form(""),
    smeta_date: str = Form(""),
    contract_sections: str = Form(None)
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
    
    date_to_use = dogovor_date if dogovor_date else current_date
    smeta_date_to_use = smeta_date if smeta_date else current_date

    # --- ГЕНЕРАЦИЯ КП (ПО ВАШЕМУ ПРИМЕРУ) ---
    if template == "kp":
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
                table, th, td {{ border: 1px solid #000; }}
                th, td {{ padding: 8px; text-align: left; }}
                .right {{ text-align: right; }}
                .bold {{ font-weight: bold; }}
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
            
            <p>Уважаемый(ая) [Имя Отчество клиента]!</p>
            <p>Компания {profile.company} предлагает вам услуги: <strong>{service}</strong> на следующих условиях:</p>
            
            <table>
                <tr>
                    <th>№</th>
                    <th>Наименование услуги</th>
                    <th>Срок выполнения</th>
                    <th>Стоимость, руб.</th>
                </tr>
                <tr>
                    <td>1</td>
                    <td>{service}</td>
                    <td>{term} дней</td>
                    <td class="right">{price},00</td>
                </tr>
            </table>
            
            <p class="right bold">Итого к оплате: {price} (Сумма прописью) рублей 00 копеек, НДС не облагается (УСН).</p>
            
            <p class="bold">Условия сотрудничества:</p>
            <ol>
                <li>Настоящее коммерческое предложение действительно в течение 14 (четырнадцати) календарных дней с даты его формирования.</li>
                <li>Порядок оплаты: 100% постоплата в течение 3 (трех) банковских дней с момента выставления счета и подписания акта оказанных услуг.</li>
                <li>Ответственность за сохранность груза в пути застрахована.</li>
                <li>Указанные цены носят информационный характер. Настоящее КП не является публичной офертой в соответствии со ст. 437 ГК РФ.</li>
            </ol>
            
            <br><br>
            <p>С уважением,<br>
            Генеральный директор {profile.company} _______________ / {director_name} /</p>
        </body>
        </html>
        """
        pisa.CreatePDF(html_content, dest=buffer)

    # --- ГЕНЕРАЦИЯ СМЕТЫ (ПО ВАШЕМУ ПРИМЕРУ) ---
    elif template == "smeta":
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
            <div class="app-header">
                Приложение № 1<br>
                к Договору оказания услуг № {dogovor_number} от {smeta_date_to_use} г.
            </div>
            
            <h1>СМЕТА НА ОКАЗАНИЕ УСЛУГ</h1>
            
            <table>
                <tr>
                    <th>№</th>
                    <th>Наименование работ / услуг</th>
                    <th>Ед. изм.</th>
                    <th>Кол-во</th>
                    <th>Цена, руб.</th>
                    <th>Сумма, руб.</th>
                </tr>
                <tr>
                    <td style="text-align: center;">1</td>
                    <td>{service}</td>
                    <td style="text-align: center;">усл.</td>
                    <td class="num">1</td>
                    <td class="num">{price},00</td>
                    <td class="num">{price},00</td>
                </tr>
                <tr class="bold">
                    <td colspan="5" class="num">Всего к оплате:</td>
                    <td class="num">{price},00</td>
                </tr>
            </table>
            
            <p style="margin-top: 15px;"><strong>Всего наименований 1, на сумму {price} (Сумма прописью) рублей 00 копеек.</strong></p>
            
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

    # --- ГЕНЕРАЦИЯ ДОГОВОРА (ПО ВАШЕМУ ПРИМЕРУ) ---
    elif template == "dogovor":
        # Если клиент не ввел свой текст, используем стандартный
        if not contract_sections:
            contract_sections = """
            1. ПРЕДМЕТ ДОГОВОРА
            1.1. Исполнитель обязуется по заданию Заказчика оказать услуги: {service}.
            2. СТОИМОСТЬ УСЛУГ
            2.1. Общая стоимость Услуг составляет {price} руб.
            """.format(service=service, price=price)

        # Преобразуем переносы строк в HTML-теги
        sections_html = contract_sections.replace('\n', '<br>')

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
            <div class="meta">
                <span>г. Москва</span>
                <span>«{date_to_use}» г.</span>
            </div>
            
            <p>{profile.company}, именуемое в дальнейшем «Исполнитель», в лице {director_name}, с одной стороны, и {customer_name} (ИНН: {customer_inn}, адрес: {customer_address}), именуемое в дальнейшем «Заказчик», с другой стороны, заключили настоящий Договор о нижеследующем:</p>
            
            <div>{sections_html}</div>
            
            <br><br>
            <table class="signs">
                <tr>
                    <td>
                        <strong>ИСПОЛНИТЕЛЬ:</strong><br>
                        {profile.company}<br>
                        ИНН: {profile.inn}<br>
                        Адрес: {profile.address}<br><br>
                        Генеральный директор<br>
                        ________________ / {director_name} /<br>
                        М.П.
                    </td>
                    <td>
                        <strong>ЗАКАЗЧИК:</strong><br>
                        {customer_name}<br>
                        ИНН: {customer_inn}<br>
                        Адрес: {customer_address}<br><br>
                        Должность<br>
                        ________________ / ФИО /<br>
                        М.П.
                    </td>
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
