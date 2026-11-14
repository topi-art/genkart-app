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
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

BOT_TOKEN = "9065574882:AAEiC0Ls-YC1ADejERPNLcZSdEJS7qCZe_I"

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

CSS_STYLES = """
@page { size: a4; margin: 20mm; }
@font-face { font-family: "PTSans"; src: url("https://github.com/google/fonts/raw/main/ofl/ptsans/PT_Sans-Web-Regular.ttf"); }
body { font-family: "PTSans", sans-serif; font-size: 11pt; }
h1 { text-align: center; font-size: 14pt; }
table { width: 100%; margin-top: 15px; }
th, td { border: 1px solid #000; padding: 5px; text-align: left; }
"""

def format_money(val):
    return f"{val:,.2f}".replace(',', ' ').replace('.', ',')

@app.get("/")
def read_root(): return {"status": "ok"}

@app.get("/get-profile")
async def get_profile(chat_id: str):
    db = SessionLocal()
    profile = db.query(Profile).filter(Profile.chat_id == chat_id).first()
    db.close()
    if profile:
        return {"status": "ok", "company": profile.company, "inn": profile.inn, "address": profile.address, "contacts": profile.contacts}
    return {"status": "not_found"}

@app.post("/save-profile")
async def save_profile(chat_id: str = Form(...), company: str = Form(...), inn: str = Form(...), address: str = Form(...), contacts: str = Form(...)):
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
    template: str = Form("kp"), company: str = Form("ООО Ваша компания"), inn: str = Form("0000000000"), 
    address: str = Form("г. Москва"), contacts: str = Form("+7 (999) 999-99-99"), 
    services_json: str = Form("[]"), term: str = Form("30"), dogovor_number: str = Form("Б/Н"), 
    customer_name: str = Form("ООО Заказчик"), customer_inn: str = Form("1111111111"), 
    smeta_date: str = Form(""), chat_id: str = Form(None)
):
    try:
        services = json.loads(services_json)
        total_price = sum(float(s['price']) * int(s['qty']) for s in services)
        current_date = datetime.now().strftime("%d.%m.%Y")
        buffer = io.BytesIO()
        
        nds_text = "НДС не облагается (УСН)"

        if template == "kp":
            rows = "".join([f"<tr><td>{i+1}</td><td>{s['name']}</td><td>{term} дн.</td><td>{format_money(float(s['price'])*int(s['qty']))} руб.</td></tr>" for i, s in enumerate(services)])
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            <div><strong>{company}</strong><br>ИНН: {inn}<br>Адрес: {address}<br>Тел: {contacts}</div>
            <p style="text-align: right;">Исх. № {dogovor_number} от {current_date}</p>
            <h1>Коммерческое предложение</h1>
            <p>Уважаемый клиент! {company} предлагает вам следующие услуги:</p>
            <table><tr><th>№</th><th>Наименование</th><th>Срок</th><th>Стоимость</th></tr>{rows}</table>
            <p style="text-align:right;"><strong>Итого: {format_money(total_price)} руб.</strong> ({nds_text})</p>
            <p>1. КП действительно 14 дней.<br>2. Оплата 100% постоплата.<br>3. Не является офертой (ст. 435 ГК РФ).</p>
            <div style="margin-top: 30px;">С уважением,<br><br>Генеральный директор<br>{company}<br><br><br>_______________ / Иванов И.И. /</div>
            </body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        elif template == "smeta":
            rows = "".join([f"<tr><td>{i+1}</td><td>{s['name']}</td><td>усл.</td><td>{s['qty']}</td><td>{format_money(float(s['price']))}</td><td>{format_money(float(s['price'])*int(s['qty']))}</td></tr>" for i, s in enumerate(services)])
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            <p style="text-align: right;">Приложение № 1 к Договору № {dogovor_number} от {smeta_date}</p>
            <h1>Смета № 1</h1>
            <table><tr><th>№</th><th>Наименование</th><th>Ед.</th><th>Кол-во</th><th>Цена</th><th>Сумма</th></tr>{rows}<tr><td colspan="5" style="text-align:right;font-weight:bold;">Всего:</td><td style="text-align:right;font-weight:bold;">{format_money(total_price)}</td></tr></table>
            <p><strong>Всего наименований {len(services)}, на сумму {format_money(total_price)} руб.</strong> {nds_text}.</p>
            <table style="width: 100%; margin-top: 30px;"><tr><td style="border: none;"><strong>Исполнитель:</strong><br>{company}<br><br><br>_______________<br>М.П.</td><td style="border: none;"><strong>Заказчик:</strong><br>{customer_name}<br><br><br>_______________<br>М.П.</td></tr></table>
            </body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        elif template == "dogovor":
            first_service = services[0]['name'] if services else "Услуги"
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            <h1>ДОГОВОР ОКАЗАНИЯ УСЛУГ № {dogovor_number}</h1>
            <p style="text-align: right;">г. Москва, {current_date}</p>
            <p>{company}, в лице Генерального директора Иванова И.И., с одной стороны, и {customer_name} (ИНН: {customer_inn}), с другой стороны, заключили Договор:</p>
            <p><strong>1. ПРЕДМЕТ ДОГОВОРА</strong><br>1.1. Исполнитель обязуется оказать следующие услуги: <strong>{first_service}</strong>.</p>
            <p><strong>2. СТОИМОСТЬ И ПОРЯДОК РАСЧЕТОВ</strong><br>2.1. Общая стоимость Услуг составляет <strong>{format_money(total_price)} руб.</strong>, {nds_text}.</p>
            <p><strong>3. ОТВЕТСТВЕННОСТЬ СТОРОН</strong><br>3.1. Стороны несут ответственность согласно законодательству РФ.</p>
            <p><strong>4. ЗАКЛЮЧИТЕЛЬНЫЕ ПОЛОЖЕНИЯ</strong><br>4.1. Договор действует до полного исполнения.</p>
            <table style="width: 100%; margin-top: 20px;"><tr><td style="border: none;"><strong>Исполнитель:</strong><br>{company}<br>ИНН: {inn}<br><br>_______________<br>М.П.</td><td style="border: none;"><strong>Заказчик:</strong><br>{customer_name}<br>ИНН: {customer_inn}<br><br>_______________<br>М.П.</td></tr></table>
            </body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        elif template == "act":
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            <h1>АКТ СДАЧИ-ПРИЕМКИ ОКАЗАННЫХ УСЛУГ № 1</h1>
            <p style="text-align: right;">г. Москва, {smeta_date}</p>
            <p>Мы, нижеподписавшиеся, представитель Исполнителя <strong>{company}</strong>, с одной стороны, и представитель Заказчика <strong>{customer_name}</strong>, с другой стороны, составили настоящий Акт о том, что Услуги по Договору № {dogovor_number} выполнены в полном объеме и в срок.</p>
            <p>Общая стоимость оказанных Услуг составляет <strong>{format_money(total_price)} руб.</strong>, {nds_text}.</p>
            <p>Претензий по объему, качеству и срокам оказания Услуг Заказчик не имеет.</p>
            <table style="width: 100%; margin-top: 40px;"><tr><td style="border: none;"><strong>Исполнитель:</strong><br>{company}<br><br><br>_______________<br>М.П.</td><td style="border: none;"><strong>Заказчик:</strong><br>{customer_name}<br><br><br>_______________<br>М.П.</td></tr></table>
            </body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        elif template == "invoice":
            rows = "".join([f"<tr><td>{i+1}</td><td>{s['name']}</td><td>шт</td><td>{s['qty']}</td><td>{format_money(float(s['price']))}</td><td>{format_money(float(s['price'])*int(s['qty']))}</td></tr>" for i, s in enumerate(services)])
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            <div><strong>{company}</strong><br>ИНН: {inn}<br>Адрес: {address}</div>
            <h1>Счет на оплату № {dogovor_number} от {smeta_date}</h1>
            <p><strong>Поставщик:</strong> {company}, ИНН {inn}<br><strong>Покупатель:</strong> {customer_name}, ИНН {customer_inn}</p>
            <table><tr><th>№</th><th>Наименование</th><th>Ед.</th><th>Кол-во</th><th>Цена</th><th>Сумма</th></tr>{rows}
            <tr><td colspan="5" style="text-align:right;font-weight:bold;">Итого:</td><td style="text-align:right;font-weight:bold;">{format_money(total_price)}</td></tr>
            <tr><td colspan="5" style="text-align:right;font-weight:bold;">{nds_text}</td><td style="text-align:right;font-weight:bold;">0,00</td></tr>
            <tr><td colspan="5" style="text-align:right;font-weight:bold;">Всего к оплате:</td><td style="text-align:right;font-weight:bold;">{format_money(total_price)}</td></tr></table>
            <table style="width: 100%; margin-top: 40px;"><tr><td style="border: none;"><strong>Руководитель:</strong><br><br><br>_______________<br><br>М.П.</td><td style="border: none;"><strong>Главный бухгалтер:</strong><br><br><br>_______________</td></tr></table>
            </body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        buffer.seek(0)

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
        print(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
