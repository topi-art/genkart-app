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

# ТОКЕН (GenDoc Помощник)
BOT_TOKEN = "8888816541:AAHr3KYdyGi3au_9xQQ83p7NVvI9A1Yp_xE" 

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

def get_short_name(fio):
    parts = fio.split()
    if len(parts) >= 3:
        return f"{parts[1]} {parts[2]}"
    return fio

def get_signature_fio(fio):
    parts = fio.split()
    if len(parts) >= 2: return f"{parts[1]} {parts[0]}"
    return fio

def clean_text(text):
    if not text: return ""
    text = text.strip()
    # Меняем кавычки на елочки
    text = text.replace('"', '«', 1).replace('"', '»', 1) if '"' in text else text
    text = text.replace('»', '»').replace('"', '»')
    # Добавляем точку, если нет
    if text and text[-1] not in ['.', '!', '?']:
        text += '.'
    return text

DATABASE_URL = "sqlite:///./profiles_final.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, unique=True, index=True)
    company = Column(String, default="ООО «Ваша компания»")
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
@font-face { font-family: "PTSans"; src: url("https://github.com/google/fonts/raw/main/ofl/ptsans/PT_Sans-Web-Regular.ttf"); }
body { font-family: "PTSans", sans-serif; font-size: 11pt; line-height: 1.35; text-align: justify; color: #000; text-indent: 1.25cm; }
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
    tel_html = f"<br>Тел: {contacts}" if contacts else ""
    return f"<div class='header-info'><strong>{clean_text(company)}</strong><br>ИНН/КПП: {inn}{kpp_str}<br>Адрес: {clean_text(address)}{tel_html}</div>"

@app.get("/")
def read_root(): 
    return FileResponse("index.html")

@app.get("/get-profile")
async def get_profile(chat_id: str):
    db = SessionLocal()
    profile = db.query(Profile).filter(Profile.chat_id == chat_id).first()
    db.close()
    if profile:
        return {"status": "ok", "company": profile.company, "inn": profile.inn, "kpp": profile.kpp, "address": profile.address, "contacts": profile.contacts, "tax_mode": profile.tax_mode, "director": profile.director, "bank_name": profile.bank_name, "bik": profile.bik, "rs": profile.rs, "ks": profile.ks}
    return {"status": "not_found"}

@app.post("/save-profile")
async def save_profile(
    chat_id: str = Form(...), company: str = Form(""), inn: str = Form(""), kpp: str = Form(""), address: str = Form(""), contacts: str = Form(""),
    tax_mode: str = Form("usn"), director: str = Form(""), bank_name: str = Form(""), bik: str = Form(""), rs: str = Form(""), ks: str = Form("")
):
    db = SessionLocal()
    try:
        profile = db.query(Profile).filter(Profile.chat_id == chat_id).first()
        if profile:
            profile.company, profile.inn, profile.kpp, profile.address, profile.contacts = company, inn, kpp, address, contacts
            profile.tax_mode, profile.director = tax_mode, director
            profile.bank_name, profile.bik, profile.rs, profile.ks = bank_name, bik, rs, ks
        else:
            db.add(Profile(chat_id=chat_id, company=company, inn=inn, kpp=kpp, address=address, contacts=contacts, tax_mode=tax_mode, director=director, bank_name=bank_name, bik=bik, rs=rs, ks=ks))
        db.commit()
        return {"status": "ok"}
    except Exception as e: return {"status": "error", "message": str(e)}
    finally: db.close()

@app.post("/generate-doc")
async def generate_doc(
    template: str = Form("kp"), company: str = Form(""), inn: str = Form(""), kpp: str = Form(""), 
    address: str = Form(""), contacts: str = Form(""), tax_mode: str = Form("usn"),
    director: str = Form(""), services_json: str = Form("[]"), term: str = Form(""), dogovor_number: str = Form(""), 
    customer_name: str = Form(""), customer_inn: str = Form(""), customer_kpp: str = Form(""), customer_address: str = Form(""), customer_director: str = Form(""), 
    smeta_date: str = Form(""), smeta_appendix: str = Form("1"), chat_id: str = Form(None),
    bank_name: str = Form(None), bik: str = Form(None), rs: str = Form(None), ks: str = Form(None)
):
    try:
        services = json.loads(services_json)
        total_price = sum(float(s['price']) * int(s['qty']) for s in services)
        date_to_use = datetime.now().strftime("%d.%m.%Y")
        smeta_date_to_use = smeta_date if smeta_date else date_to_use
        buffer = io.BytesIO()
        
        nds_text = "В том числе НДС 22%" if tax_mode == "osno" else "НДС не облагается на основании п. 2 ст. 346.11 НК РФ (УСН)"
        header_html = get_header_html(company, inn, kpp, address, contacts)
        dir_rod = decline_fio(director)
        cust_rod = decline_fio(customer_director)
        dir_sign = get_signature_fio(director)
        cust_sign = get_signature_fio(customer_director)
        sum_propis = num2words_rub(total_price)
        
        kpp_str = f", КПП: {kpp}" if kpp else ""
        cust_kpp_str = f", КПП: {customer_kpp}" if customer_kpp else ""

        if template == "kp":
            rows = "".join([f"<tr><td style='text-align:center;'>{i+1}</td><td>{s['name']}</td><td style='text-align:center;'>{s.get('unit', 'усл.')}</td><td style='text-align:center;'>{s['qty']}</td><td style='text-align:right;'>{format_money(float(s['price']))}</td><td style='text-align:right;'>{format_money(float(s['price'])*int(s['qty']))}</td></tr>" for i, s in enumerate(services)])
            customer_greeting = get_short_name(customer_director) if customer_director else "клиент"
            greeting = f"Уважаемый {customer_greeting}!" if customer_greeting != "клиент" else "Уважаемый клиент!"
                
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            {header_html}
            <table class="meta"><tr><td style="text-align:right;">Исх. № {dogovor_number} от {date_to_use} г.</td></tr></table>
            <h1 class="title">Коммерческое предложение<br>на оказание услуг</h1>
            <p>{greeting} {clean_text(company)} предлагает вам следующие услуги:</p>
            <table><tr><th style="text-align:center; width: 5%;">№</th><th style="width: 45%;">Наименование услуги</th><th style="text-align:center; width: 10%;">Ед.</th><th style="text-align:center; width: 10%;">Кол-во</th><th style="text-align:right; width: 15%;">Цена</th><th style="text-align:right; width: 15%;">Сумма</th></tr>{rows}
            <tr><td colspan="5" style="text-align:right;font-weight:bold;">Итого:</td><td style="text-align:right;font-weight:bold;">{format_money(total_price)}</td></tr></table>
            <p style="text-indent: 0; margin-top: 10px;">{nds_text}.</p>
            <p class="list-item">1. Срок действия предложения: 14 календарных дней.</p>
            <p class="list-item">2. Условия оплаты: 100% в течение 5 рабочих дней после подписания акта.</p>
            <div class="signature-block"><strong>С уважением,</strong><br><br>Генеральный директор<br>{clean_text(company)}<br><br><br>_______________ / {director} /<br>М.П.</div>
            </body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        elif template == "smeta":
            rows = "".join([f"<tr><td style='text-align:center;'>{i+1}</td><td>{s['name']}</td><td style='text-align:center;'>{s.get('unit', 'усл.')}</td><td style='text-align:center;'>{s['qty']}</td><td style='text-align:right;'>{format_money(float(s['price']))}</td><td style='text-align:right;'>{format_money(float(s['price'])*int(s['qty']))}</td></tr>" for i, s in enumerate(services)])
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            <table class="meta"><tr><td style="text-align:right;">Приложение № {smeta_appendix} к Договору № {dogovor_number} от {smeta_date_to_use}</td></tr></table>
            <h1 class="title">Смета № {smeta_appendix}</h1>
            <p style="text-align:center; text-indent:0;">от {smeta_date_to_use} г.</p>
            <table><tr><th style="text-align:center; width: 5%;">№</th><th style="width: 40%;">Наименование</th><th style="text-align:center; width: 10%;">Ед.</th><th style="text-align:center; width: 10%;">Кол-во</th><th style="text-align:right; width: 15%;">Цена</th><th style="text-align:right; width: 15%;">Сумма</th></tr>{rows}<tr><td colspan="5" style="text-align:right;font-weight:bold;">Всего:</td><td style="text-align:right;font-weight:bold;">{format_money(total_price)}</td></tr></table>
            <p><strong>Всего наименований {len(services)}, на сумму {format_money(total_price)} руб. ({sum_propis}).</strong> {nds_text}.</p>
            <table style="width: 100%; border: none; margin-top: 30px; text-indent: 0;"><tr><td style="border: none; width: 50%;"><strong>Исполнитель:</strong><br>{clean_text(company)}<br>ИНН: {inn}{kpp_str}<br>Адрес: {clean_text(address)}<br><br>Генеральный директор<br>_______________ / {director} /<br>М.П.</td><td style="border: none; width: 50%;"><strong>Заказчик:</strong><br>{clean_text(customer_name)}<br>ИНН: {customer_inn}{cust_kpp_str}<br>Адрес: {clean_text(customer_address)}<br><br>Генеральный директор<br>_______________ / {customer_director} /<br>М.П.</td></tr></table>
            </body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        elif template == "dogovor":
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            <h1 class="title">ДОГОВОР ОКАЗАНИЯ УСЛУГ № {dogovor_number}</h1>
            <table class="meta"><tr><td style="text-align: left;">г. Москва</td><td style="text-align: right;">{date_to_use} г.</td></tr></table>
            <p>{clean_text(company)}, в лице Генерального директора {dir_rod}, действующего на основании Устава, с одной стороны, и {clean_text(customer_name)} (ИНН: {customer_inn}{cust_kpp_str}, адрес: {clean_text(customer_address)}), в лице Генерального директора {cust_rod}, действующего на основании Устава, с другой стороны, заключили Договор:</p>
            <div class="section-title">1. ПРЕДМЕТ ДОГОВОРА</div>
            <p>1.1. Исполнитель обязуется оказать следующие услуги: <strong>{services[0]['name'] if services else 'Услуги'}</strong>.</p>
            <div class="section-title">2. СТОИМОСТЬ И ПОРЯДОК РАСЧЕТОВ</div>
            <p>2.1. Общая стоимость Услуг составляет <strong>{format_money(total_price)} руб.</strong>, {nds_text}.</p>
            <p>2.2. Оплата 100% в течение 3 банковских дней с момента подписания Акта.</p>
            <div class="section-title">3. ПОРЯДОК СДАЧИ-ПРИЕМКИ</div>
            <p>3.1. Заказчик обязан в течение 3 рабочих дней подписать Акт или направить мотивированный отказ. В случае отсутствия отказа, услуги считаются принятыми.</p>
            <div class="section-title">4. ОТВЕТСТВЕННОСТЬ СТОРОН</div>
            <p>4.1. За неисполнение или ненадлежащее исполнение обязательств по настоящему Договору Стороны несут ответственность в соответствии с действующим законодательством РФ.</p>
            <div class="section-title">5. РЕКВИЗИТЫ И ПОДПИСИ СТОРОН</div>
            <table style="width: 100%; border: none; margin-top: 20px; text-indent: 0;"><tr>
                <td style="border: none; width: 50%; vertical-align: top;"><strong>Исполнитель:</strong><br>{clean_text(company)}<br>ИНН: {inn}{kpp_str}<br>Адрес: {clean_text(address)}<br><br>_______________ / {director} /<br>М.П.</td>
                <td style="border: none; width: 50%; vertical-align: top;"><strong>Заказчик:</strong><br>{clean_text(customer_name)}<br>ИНН: {customer_inn}{cust_kpp_str}<br>Адрес: {clean_text(customer_address)}<br><br>_______________ / {customer_director} /<br>М.П.</td>
            </tr></table></body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        elif template == "act":
            rows = "".join([f"<tr><td style='text-align:center;'>{i+1}</td><td>{s['name']}</td><td style='text-align:center;'>{s.get('unit', 'усл.')}</td><td style='text-align:center;'>{s['qty']}</td><td style='text-align:right;'>{format_money(float(s['price']))}</td><td style='text-align:right;'>{format_money(float(s['price'])*int(s['qty']))}</td></tr>" for i, s in enumerate(services)])
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            <h1 class="title">АКТ СДАЧИ-ПРИЕМКИ ОКАЗАННЫХ УСЛУГ № {smeta_appendix}</h1>
            <table class="meta"><tr><td style="text-align: left;">г. Москва</td><td style="text-align: right;">{smeta_date_to_use} г.</td></tr></table>
            <p>Мы, нижеподписавшиеся, представитель Исполнителя <strong>{clean_text(company)}</strong> в лице Генерального директора {dir_rod}, с одной стороны, и представитель Заказчика <strong>{clean_text(customer_name)}</strong> в лице Генерального директора {cust_rod}, с другой стороны, составили настоящий Акт о том, что Услуги по Договору № {dogovor_number} от {date_to_use} выполнены в полном объеме и в срок.</p>
            <table><tr><th style="text-align:center; width: 5%;">№</th><th style="width: 40%;">Наименование услуги</th><th style="text-align:center; width: 10%;">Ед.</th><th style="text-align:center; width: 10%;">Кол-во</th><th style="text-align:right; width: 15%;">Цена</th><th style="text-align:right; width: 15%;">Сумма</th></tr>{rows}<tr><td colspan="5" style="text-align:right;font-weight:bold;">Всего к оплате:</td><td style="text-align:right;font-weight:bold;">{format_money(total_price)}</td></tr></table>
            <p><strong>Всего наименований {len(services)}, на сумму {format_money(total_price)} руб. ({sum_propis}).</strong> {nds_text}.</p>
            <p>Претензий по объему, качеству и срокам оказания Услуг Заказчик не имеет.</p>
            <table style="width: 100%; border: none; margin-top: 40px; text-indent: 0;"><tr>
                <td style="border: none; width: 50%; vertical-align: top;"><strong>Исполнитель:</strong><br>{clean_text(company)}<br>ИНН: {inn}{kpp_str}<br>Адрес: {clean_text(address)}<br><br>Генеральный директор<br>_______________ / {director} /<br>М.П.</td>
                <td style="border: none; width: 50%; vertical-align: top;"><strong>Заказчик:</strong><br>{clean_text(customer_name)}<br>ИНН: {customer_inn}{cust_kpp_str}<br>Адрес: {clean_text(customer_address)}<br><br>Генеральный директор<br>_______________ / {customer_director} /<br>М.П.</td>
            </tr></table></body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        elif template == "invoice":
            rows = "".join([f"<tr><td style='text-align:center;'>{i+1}</td><td>{s['name']}</td><td style='text-align:center;'>{s.get('unit', 'усл.')}</td><td style='text-align:center;'>{s['qty']}</td><td style='text-align:right;'>{format_money(float(s['price']))}</td><td style='text-align:right;'>{format_money(float(s['price'])*int(s['qty']))}</td></tr>" for i, s in enumerate(services)])
            nds_row = f"<tr><td colspan='5' style='text-align:right;font-weight:bold;'>В том числе НДС 22%:</td><td style='text-align:right;font-weight:bold;'>{format_money(total_price * 0.22 / 1.22)}</td></tr>" if tax_mode == "osno" else "<tr><td colspan='5' style='text-align:right;font-weight:bold;'>Без налога (НДС):</td><td style='text-align:right;font-weight:bold;'>0,00</td></tr>"
            
            bank_table = f"""<table style="width: 100%; border-collapse: collapse; text-indent: 0; font-size: 10pt; margin-bottom: 20px;">
                <tr><td style="border: 1px solid #000; padding: 5px; width: 15%;">Банк получателя:</td><td style="border: 1px solid #000; padding: 5px;" colspan="3">{bank_name or "____________________"}</td></tr>
                <tr><td style="border: 1px solid #000; padding: 5px;">БИК:</td><td style="border: 1px solid #000; padding: 5px; width: 35%;">{bik or "__________"}</td><td style="border: 1px solid #000; padding: 5px; width: 15%;">Сч. №:</td><td style="border: 1px solid #000; padding: 5px;">{ks or "____________________"}</td></tr>
                <tr><td style="border: 1px solid #000; padding: 5px;">Получатель:</td><td style="border: 1px solid #000; padding: 5px;" colspan="3">{clean_text(company)}<br>ИНН {inn} {(' / КПП ' + kpp) if kpp else ''}</td></tr>
                <tr><td style="border: 1px solid #000; padding: 5px;">Р/с:</td><td style="border: 1px solid #000; padding: 5px;" colspan="3">{rs or "____________________"}</td></tr>
            </table>"""
            
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            {header_html}
            {bank_table}
            <h1 class="title">Счет на оплату № {dogovor_number} от {smeta_date_to_use} г.</h1>
            <table class="meta" style="margin-bottom: 15px;">
                <tr><td style="text-align: left;"><strong>Поставщик:</strong><br>{clean_text(company)}, ИНН {inn}{kpp_str}, {clean_text(address)}</td></tr>
                <tr><td style="text-align: left; padding-top: 5px;"><strong>Покупатель:</strong><br>{clean_text(customer_name)}, ИНН {customer_inn}{cust_kpp_str}, {clean_text(customer_address)}</td></tr>
            </table>
            <table>
                <tr><th style="text-align:center; width: 5%;">№</th><th style="width: 45%;">Наименование</th><th style="text-align:center; width: 10%;">Ед.</th><th style="text-align:center; width: 10%;">Кол-во</th><th style="text-align:right; width: 15%;">Цена</th><th style="text-align:right; width: 15%;">Сумма</th></tr>
                {rows}
                <tr><td colspan="5" style="text-align:right;font-weight:bold;">Итого:</td><td style="text-align:right;font-weight:bold;">{format_money(total_price)}</td></tr>
                {nds_row}
                <tr><td colspan="5" style="text-align:right;font-weight:bold;">Всего к оплате:</td><td style="text-align:right;font-weight:bold;">{format_money(total_price)}</td></tr>
            </table>
            <p>Всего наименований {len(services)}, на сумму {format_money(total_price)} руб.</p>
            <p>Сумма прописью: <strong>{sum_propis}</strong></p>
            <p style="font-size: 9pt; color: #555; text-indent: 0; margin-top: 15px;">Оплата данного счета означает согласие с условиями оказания услуг.</p>
            <table style="width: 100%; border: none; margin-top: 20px; text-indent: 0;">
                <tr>
                    <td style="border: none; width: 50%; vertical-align: top;"><strong>Руководитель:</strong><br><br><br>_______________ / {director} /<br><br>М.П.</td>
                    <td style="border: none; width: 50%; vertical-align: top;"><strong>Главный бухгалтер:</strong><br><br><br>_______________ / {director} /</td>
                </tr>
            </table>
            </body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        buffer.seek(0)

        if chat_id:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            files = {'document': (f'{template}.pdf', buffer.getvalue(), 'application/pdf')}
            data = {'chat_id': chat_id, 'caption': 'Ваш документ готов! 📄'}
            requests.post(url, files=files, data=data)
            
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
