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

# ОСТАВЛЯЕМ ТОЛЬКО ОДИН БОТ (GenDoc Помощник)
BOT_TOKEN = "8888816541:AAHr3KYdyGi3au_9xQQ83p7NVvI9A1Yp_xE" 
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
    kpp = Column(String, default="")
    address = Column(String, default="г. Москва")
    contacts = Column(String, default="+7 (999) 999-99-99")
    tax_mode = Column(String, default="usn")
    director = Column(String, default="Иванов И.И.")
    bank_name = Column(String, default="")
    bik = Column(String, default="")
    rs = Column(String, default="")
    ks = Column(String, default="")

Base.metadata.create_all(bind=engine)

CSS_STYLES = """
@page { size: a4; margin: 20mm 15mm 20mm 30mm; }
body { font-family: "Helvetica", sans-serif; font-size: 11pt; line-height: 1.35; text-align: justify; color: #000; text-indent: 1.25cm; }
h1.title { text-align: center; font-size: 14pt; font-weight: bold; margin-bottom: 20px; text-transform: uppercase; text-indent: 0; }
.meta { width: 100%; margin-bottom: 20px; text-indent: 0; }
.meta td { border: none; padding: 0; }
.section-title { font-weight: bold; margin-top: 15px; margin-bottom: 10px; text-indent: 0; }
table { width: 100%; border-collapse: collapse; margin-top: 15px; text-indent: 0; }
th, td { border: 1px solid #000; padding: 6px; text-align: left; }
.header-info { margin-bottom: 20px; font-size: 10pt; text-align: left; text-indent: 0; }
.signature-block { margin-top: 30px; text-indent: 0; }
.list-item { text-indent: 0; margin-bottom: 5px; }
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

def get_header_html(company, inn, kpp, address, contacts):
    kpp_str = f"/{kpp}" if kpp else ""
    return f"<div class='header-info'><strong>{company}</strong><br>ИНН/КПП: {inn}{kpp_str}<br>Адрес: {address}<br>Тел: {contacts}</div>"

@app.get("/")
def read_root(): 
    return FileResponse("index.html")

@app.post("/generate-doc")
async def generate_doc(
    template: str = Form("kp"), company: str = Form(""), inn: str = Form(""), kpp: str = Form(""), 
    address: str = Form(""), contacts: str = Form(""), tax_mode: str = Form("usn"),
    director: str = Form(""), services_json: str = Form("[]"), term: str = Form(""), dogovor_number: str = Form(""), 
    customer_name: str = Form(""), customer_inn: str = Form(""), chat_id: str = Form(None)
):
    try:
        services = json.loads(services_json)
        total_price = sum(float(s['price']) * int(s['qty']) for s in services)
        date_to_use = datetime.now().strftime("%d.%m.%Y")
        buffer = io.BytesIO()
        
        header_html = get_header_html(company, inn, kpp, address, contacts)
        dir_sign = get_signature_fio(director)

        if template == "kp":
            rows = "".join([f"<tr><td style='text-align:center;'>{i+1}</td><td>{s['name']}</td><td style='text-align:center;'>{s.get('unit', 'усл.')}</td><td style='text-align:center;'>{term}</td><td style='text-align:right;'>{format_money(float(s['price'])*int(s['qty']))} руб.</td></tr>" for i, s in enumerate(services)])
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            {header_html}
            <table class="meta"><tr><td style="text-align:right;">Исх. № {dogovor_number} от {date_to_use} г.</td></tr></table>
            <h1 class="title">Коммерческое предложение<br>на оказание услуг</h1>
            <p>Уважаемый клиент! {company} предлагает вам следующие услуги:</p>
            <table><tr><th style="text-align:center; width: 5%;">№</th><th style="width: 50%;">Наименование услуги</th><th style="text-align:center; width: 10%;">Ед.</th><th style="text-align:center; width: 15%;">Срок</th><th style="text-align:right; width: 20%;">Стоимость</th></tr>{rows}</table>
            <p style="text-align:right; margin-top: 10px; text-indent: 0;"><strong>Итого: {format_money(total_price)} руб.</strong></p>
            <p class="list-item">1. Настоящее КП действительно в течение 14 календарных дней.</p>
            <p class="list-item">2. Условия оплаты: 100% в течение 3 банковских дней после подписания Акта.</p>
            <p class="list-item">3. Не является офертой (ст. 435 ГК РФ).</p>
            <div class="signature-block"><strong>С уважением,</strong><br><br>Генеральный директор<br>{company}<br><br><br>_______________ {dir_sign}<br>М.П.</div>
            </body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        elif template == "smeta":
            rows = "".join([f"<tr><td style='text-align:center;'>{i+1}</td><td>{s['name']}</td><td style='text-align:center;'>{s.get('unit', 'усл.')}</td><td style='text-align:center;'>{s['qty']}</td><td style='text-align:right;'>{format_money(float(s['price']))}</td><td style='text-align:right;'>{format_money(float(s['price'])*int(s['qty']))}</td></tr>" for i, s in enumerate(services)])
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            <table class="meta"><tr><td style="text-align:right;">Приложение к Договору № {dogovor_number} от {date_to_use}</td></tr></table>
            <h1 class="title">Смета</h1>
            <table><tr><th style="text-align:center; width: 5%;">№</th><th style="width: 40%;">Наименование</th><th style="text-align:center; width: 10%;">Ед.</th><th style="text-align:center; width: 10%;">Кол-во</th><th style="text-align:right; width: 15%;">Цена</th><th style="text-align:right; width: 15%;">Сумма</th></tr>{rows}<tr><td colspan="5" style="text-align:right;font-weight:bold;">Всего:</td><td style="text-align:right;font-weight:bold;">{format_money(total_price)}</td></tr></table>
            </body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        elif template == "dogovor":
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            <h1 class="title">ДОГОВОР ОКАЗАНИЯ УСЛУГ № {dogovor_number}</h1>
            <table class="meta"><tr><td style="text-align: left;">г. Москва</td><td style="text-align: right;">{date_to_use} г.</td></tr></table>
            <p>{company}, в лице Генерального директора {director}, с одной стороны, и {customer_name} (ИНН: {customer_inn}), в лице Генерального директора, с другой стороны, заключили Договор:</p>
            <div class="section-title">1. ПРЕДМЕТ ДОГОВОРА</div>
            <p>1.1. Исполнитель обязуется оказать услуги.</p>
            <div class="section-title">2. СТОИМОСТЬ И ПОРЯДОК РАСЧЕТОВ</div>
            <p>2.1. Общая стоимость Услуг составляет <strong>{format_money(total_price)} руб.</strong></p>
            <div class="section-title">5. РЕКВИЗИТЫ И ПОДПИСИ СТОРОН</div>
            <table style="width: 100%; border: none; margin-top: 20px; text-indent: 0;"><tr>
                <td style="border: none; width: 50%; vertical-align: top;"><strong>Исполнитель:</strong><br>{company}<br>ИНН: {inn}<br>Адрес: {address}<br><br>_______________ / {director} /<br>М.П.</td>
                <td style="border: none; width: 50%; vertical-align: top;"><strong>Заказчик:</strong><br>{customer_name}<br>ИНН: {customer_inn}<br><br>_______________ / /<br>М.П.</td>
            </tr></table></body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        elif template == "act":
            rows = "".join([f"<tr><td style='text-align:center;'>{i+1}</td><td>{s['name']}</td><td style='text-align:center;'>{s.get('unit', 'усл.')}</td><td style='text-align:center;'>{s['qty']}</td><td style='text-align:right;'>{format_money(float(s['price']))}</td><td style='text-align:right;'>{format_money(float(s['price'])*int(s['qty']))}</td></tr>" for i, s in enumerate(services)])
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            <h1 class="title">АКТ СДАЧИ-ПРИЕМКИ ОКАЗАННЫХ УСЛУГ</h1>
            <table class="meta"><tr><td style="text-align: left;">г. Москва</td><td style="text-align: right;">{date_to_use} г.</td></tr></table>
            <p>Мы, нижеподписавшиеся, представитель Исполнителя <strong>{company}</strong> в лице Генерального директора {director}, с одной стороны, и представитель Заказчика <strong>{customer_name}</strong>, с другой стороны, составили настоящий Акт о том, что Услуги по Договору № {dogovor_number} выполнены в полном объеме и в срок.</p>
            <table><tr><th style="text-align:center; width: 5%;">№</th><th style="width: 40%;">Наименование услуги</th><th style="text-align:center; width: 10%;">Ед.</th><th style="text-align:center; width: 10%;">Кол-во</th><th style="text-align:right; width: 15%;">Цена</th><th style="text-align:right; width: 15%;">Сумма</th></tr>{rows}<tr><td colspan="5" style="text-align:right;font-weight:bold;">Всего к оплате:</td><td style="text-align:right;font-weight:bold;">{format_money(total_price)}</td></tr></table>
            </body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        elif template == "invoice":
            rows = "".join([f"<tr><td style='text-align:center;'>{i+1}</td><td>{s['name']}</td><td style='text-align:center;'>{s.get('unit', 'усл.')}</td><td style='text-align:center;'>{s['qty']}</td><td style='text-align:right;'>{format_money(float(s['price']))}</td><td style='text-align:right;'>{format_money(float(s['price'])*int(s['qty']))}</td></tr>" for i, s in enumerate(services)])
            sum_propis = num2words_rub(total_price)
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            {header_html}
            <h1 class="title">Счет на оплату № {dogovor_number} от {date_to_use} г.</h1>
            <table class="meta" style="margin-bottom: 15px;">
                <tr><td style="text-align: left;"><strong>Поставщик:</strong><br>{company}, ИНН {inn}, {address}</td></tr>
                <tr><td style="text-align: left; padding-top: 5px;"><strong>Покупатель:</strong><br>{customer_name}, ИНН {customer_inn}</td></tr>
            </table>
            <table>
                <tr><th style="text-align:center; width: 5%;">№</th><th style="width: 45%;">Наименование</th><th style="text-align:center; width: 10%;">Ед.</th><th style="text-align:center; width: 10%;">Кол-во</th><th style="text-align:right; width: 15%;">Цена</th><th style="text-align:right; width: 15%;">Сумма</th></tr>
                {rows}
                <tr><td colspan="5" style="text-align:right;font-weight:bold;">Итого:</td><td style="text-align:right;font-weight:bold;">{format_money(total_price)}</td></tr>
                <tr><td colspan="5" style="text-align:right;font-weight:bold;">Всего к оплате:</td><td style="text-align:right;font-weight:bold;">{format_money(total_price)}</td></tr>
            </table>
            <p>Сумма прописью: <strong>{sum_propis}</strong></p>
            <table style="width: 100%; border: none; margin-top: 40px; text-indent: 0;">
                <tr>
                    <td style="border: none; width: 50%; vertical-align: top;"><strong>Руководитель:</strong><br><br><br>_______________ {dir_sign}<br><br>М.П.</td>
                    <td style="border: none; width: 50%; vertical-align: top;"><strong>Главный бухгалтер:</strong><br><br><br>_______________ {dir_sign}</td>
                </tr>
            </table>
            </body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        buffer.seek(0)

        target_chat_id = chat_id if chat_id else MY_CHAT_ID
        if target_chat_id:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            files = {'document': (f'{template}.pdf', buffer.getvalue(), 'application/pdf')}
            data = {'chat_id': target_chat_id, 'caption': 'Ваш документ готов! 📄'}
            requests.post(url, files=files, data=data)
            
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
