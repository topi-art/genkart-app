from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import io
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

# --- СТИЛИ ПО ГОСТ (Поля, шрифты, защита подписей) ---
CSS_STYLES = """
@page { 
    size: a4; 
    margin: 20mm 15mm 20mm 30mm; /* Верх 20, Право 15, Низ 20, Лево 30 */
}
body { 
    font-family: 'DejaVu Sans', sans-serif; 
    font-size: 11pt; 
    line-height: 1.35; 
    text-align: justify; 
    color: #000; 
}
h1.title { 
    text-align: center; 
    font-size: 14pt; 
    font-weight: bold; 
    margin-bottom: 20px; 
    text-transform: uppercase; 
}
.meta { 
    width: 100%; 
    margin-bottom: 20px; 
}
.meta td { 
    border: none; 
    padding: 0; 
}
.section-title { 
    font-weight: bold; 
    margin-top: 15px; 
    margin-bottom: 10px; 
}
table { 
    width: 100%; 
    border-collapse: collapse; 
    margin-top: 15px; 
}
th, td { 
    border: 1px solid #000; 
    padding: 6px; 
    text-align: left; 
}
.signatures { 
    width: 100%; 
    margin-top: 40px; 
    break-inside: avoid; /* Защита от разрыва подписей */
    page-break-inside: avoid;
}
.signatures td { 
    border: none; 
    width: 50%; 
    vertical-align: top; 
    padding: 0; 
}
.header-info { 
    margin-bottom: 20px; 
    font-size: 10pt; 
    text-align: left;
}
"""

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
    chat_id: str = Form(...), company: str = Form(...), inn: str = Form(...), 
    address: str = Form(...), contacts: str = Form(...)
):
    db = SessionLocal()
    try:
        profile = db.query(Profile).filter(Profile.chat_id == chat_id).first()
        if profile:
            profile.company, profile.inn, profile.address, profile.contacts = company, inn, address, contacts
        else:
            db.add(Profile(chat_id=chat_id, company=company, inn=inn, address=address, contacts=contacts))
        db.commit()
        return {"status": "ok", "message": "Сохранено"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@app.post("/generate-doc")
async def generate_doc(
    template: str = Form("kp"), company: str = Form("ООО Ваша компания"),
    inn: str = Form("0000000000"), address: str = Form("г. Москва"),
    contacts: str = Form("+7 (999) 999-99-99"), services_json: str = Form("[]"),
    term: str = Form("30"), dogovor_number: str = Form("Б/Н"),
    dogovor_date: str = Form(""), customer_name: str = Form("ООО Заказчик"),
    customer_inn: str = Form("1111111111"), customer_address: str = Form("г. Москва"),
    director_name: str = Form("Иванов И.И."), smeta_date: str = Form(""), chat_id: str = Form(None)
):
    try:
        services = json.loads(services_json)
        total_price = sum(float(s['price']) * int(s['qty']) for s in services)
        current_date = datetime.now().strftime("%d.%m.%Y")
        date_to_use = dogovor_date if dogovor_date else current_date
        smeta_date_to_use = smeta_date if smeta_date else current_date
        buffer = io.BytesIO()

        # --- 1. ГЕНЕРАЦИЯ КП ---
        if template == "kp":
            rows = ""
            for i, s in enumerate(services):
                amount = float(s['price']) * int(s['qty'])
                rows += f"<tr><td style='text-align:center;'>{i+1}</td><td>{s['name']}</td><td style='text-align:center;'>{term} дн.</td><td style='text-align:right;'>{amount:,.2f} руб.</td></tr>"
            
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            <div class="header-info">
                <strong>{company}</strong><br>
                ИНН/КПП: {inn}<br>
                Адрес: {address}<br>
                Тел: {contacts}
            </div>
            <table class="meta"><tr><td style="text-align:right;">Исх. № {dogovor_number} от {date_to_use} г.</td></tr></table>
            
            <h1 class="title">Коммерческое предложение<br>на оказание услуг</h1>
            
            <p>Уважаемый клиент!<br>{company} предлагает вам следующие услуги на указанных ниже условиях:</p>
            
            <table>
                <tr><th style="text-align:center; width: 5%;">№</th><th style="width: 60%;">Наименование услуги</th><th style="text-align:center; width: 15%;">Срок</th><th style="text-align:right; width: 20%;">Стоимость</th></tr>
                {rows}
            </table>
            
            <p style="text-align:right; margin-top: 10px;"><strong>Итого к оплате: {total_price:,.2f} руб.</strong><br>(НДС не облагается)</p>
            
            <div class="section-title">Условия предложения:</div>
            <p>1. Настоящее коммерческое предложение действительно в течение 14 календарных дней.<br>
            2. Порядок оплаты: 100% постоплата в течение 3 банковских дней с момента выставления счета и подписания акта.<br>
            3. Указанные цены носят информационный характер. Настоящее КП не является публичной офертой.</p>
            
            <div class="signatures">
                <table>
                    <tr>
                        <td>
                            <strong>С уважением,</strong><br><br>
                            Генеральный директор<br>{company}<br><br><br>
                            _______________ / {director_name} /
                        </td>
                        <td></td>
                    </tr>
                </table>
            </div>
            </body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        # --- 2. ГЕНЕРАЦИЯ СМЕТЫ ---
        elif template == "smeta":
            rows = ""
            for i, s in enumerate(services):
                amount = float(s['price']) * int(s['qty'])
                rows += f"<tr><td style='text-align:center;'>{i+1}</td><td>{s['name']}</td><td style='text-align:center;'>усл.</td><td style='text-align:center;'>{s['qty']}</td><td style='text-align:right;'>{float(s['price']):,.2f}</td><td style='text-align:right;'>{amount:,.2f}</td></tr>"
            
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            <table class="meta"><tr><td style="text-align:right;">Приложение № 1 к Договору № {dogovor_number} от {smeta_date_to_use}</td></tr></table>
            
            <h1 class="title">Смета (расчет стоимости услуг)</h1>
            
            <table>
                <tr><th style="text-align:center; width: 5%;">№</th><th style="width: 45%;">Наименование</th><th style="text-align:center; width: 10%;">Ед.</th><th style="text-align:center; width: 10%;">Кол-во</th><th style="text-align:right; width: 15%;">Цена, руб.</th><th style="text-align:right; width: 15%;">Сумма, руб.</th></tr>
                {rows}
                <tr><td colspan="5" style="text-align:right;font-weight:bold;">Всего к оплате:</td><td style="text-align:right;font-weight:bold;">{total_price:,.2f}</td></tr>
            </table>
            
            <p style="margin-top:20px;"><strong>Всего наименований {len(services)}, на сумму {total_price:,.2f} рублей.</strong> НДС не облагается.</p>
            
            <div class="signatures">
                <table class="signatures">
                    <tr>
                        <td>
                            <strong>Исполнитель:</strong><br>
                            {company}<br><br><br>
                            _______________ / {director_name} /<br>
                            М.П.
                        </td>
                        <td>
                            <strong>Заказчик:</strong><br>
                            {customer_name}<br><br><br>
                            _______________ / ФИО /<br>
                            М.П.
                        </td>
                    </tr>
                </table>
            </div>
            </body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        # --- 3. ГЕНЕРАЦИЯ ДОГОВОРА ---
        elif template == "dogovor":
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            <h1 class="title">ДОГОВОР ОКАЗАНИЯ УСЛУГ № {dogovor_number}</h1>
            
            <table class="meta">
                <tr>
                    <td style="text-align: left;">г. Москва</td>
                    <td style="text-align: right;">«{date_to_use}» г.</td>
                </tr>
            </table>
            
            <p>{company}, в лице {director_name}, действующего на основании Устава, именуемое в дальнейшем «Исполнитель», с одной стороны, и {customer_name} (ИНН: {customer_inn}, адрес: {customer_address}), именуемое в дальнейшем «Заказчик», в лице представителя, с другой стороны, заключили настоящий Договор о нижеследующем:</p>
            
            <div class="section-title">1. ПРЕДМЕТ ДОГОВОРА</div>
            <p>1.1. Исполнитель обязуется по заданию Заказчика оказать услуги (далее — «Услуги»), а Заказчик обязуется принять и оплатить эти Услуги.</p>
            <p>1.2. Перечень, объем и стоимость Услуг определяются в Смете (Приложение № 1), являющейся неотъемлемой частью настоящего Договора.</p>
            
            <div class="section-title">2. СТОИМОСТЬ УСЛУГ И ПОРЯДОК РАСЧЕТОВ</div>
            <p>2.1. Общая стоимость Услуг по настоящему Договору составляет <strong>{total_price:,.2f} руб.</strong>, НДС не облагается.</p>
            <p>2.2. Оплата производится Заказчиком путем перечисления 100% стоимости Услуг на расчетный счет Исполнителя в течение 3 (трех) банковских дней с даты подписания Сторонами Акта сдачи-приемки оказанных услуг и выставления счета.</p>
            
            <div class="section-title">3. ОТВЕТСТВЕННОСТЬ СТОРОН</div>
            <p>3.1. За неисполнение или ненадлежащее исполнение обязательств по настоящему Договору Стороны несут ответственность в соответствии с действующим законодательством РФ.</p>
            
            <div class="section-title">4. ЗАКЛЮЧИТЕЛЬНЫЕ ПОЛОЖЕНИЯ</div>
            <p>4.1. Настоящий Договор вступает в силу с момента его подписания и действует до полного исполнения Сторонами своих обязательств.</p>
            <p>4.2. Договор составлен в двух экземплярах, имеющих одинаковую юридическую силу, по одному для каждой из Сторон.</p>
            
            <div class="section-title">5. АДРЕСА, РЕКВИЗИТЫ И ПОДПИСИ СТОРОН</div>
            <div class="signatures">
                <table class="signatures">
                    <tr>
                        <td>
                            <strong>Исполнитель:</strong><br>
                            {company}<br>
                            ИНН: {inn}<br>
                            Адрес: {address}<br><br>
                            Генеральный директор<br><br><br>
                            _______________ / {director_name} /<br>
                            М.П.
                        </td>
                        <td>
                            <strong>Заказчик:</strong><br>
                            {customer_name}<br>
                            ИНН: {customer_inn}<br>
                            Адрес: {customer_address}<br><br>
                            Должность<br><br><br>
                            _______________ / ФИО /<br>
                            М.П.
                        </td>
                    </tr>
                </table>
            </div>
            </body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        buffer.seek(0)

        # --- ОТПРАВКА В TELEGRAM ---
        if chat_id:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            files = {'document': ('document.pdf', buffer.getvalue(), 'application/pdf')}
            data = {'chat_id': chat_id, 'caption': 'Ваш документ готов!'}
            try:
                response = requests.post(url, files=files, data=data)
                if response.status_code == 200:
                    return {"status": "ok", "message": "Отправлено в ТГ"}
                else:
                    return JSONResponse(status_code=500, content={"status": "error", "message": f"Ошибка ТГ: {response.text}"})
            except Exception as e:
                return JSONResponse(status_code=500, content={"status": "error", "message": f"Ошибка ТГ: {str(e)}"})
        else:
            return {"status": "error", "message": "Нет chat_id"}

    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
