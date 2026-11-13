from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import io
import json
import requests
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Text
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

# --- БАЗА ДАННЫХ (Добавлены банковские реквизиты) ---
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
    director_rod = Column(String, default="Иванова И.И.")
    director_pos = Column(String, default="Генерального директора")
    # Банковские реквизиты для счета
    bank_name = Column(String, default="")
    bik = Column(String, default="")
    rs = Column(String, default="")
    ks = Column(String, default="")
    logo = Column(Text, nullable=True)

Base.metadata.create_all(bind=engine)

# --- СТИЛИ (ГОСТ Р 7.0.97-2016) ---
CSS_STYLES = """
@page { size: a4; margin: 20mm 15mm 20mm 30mm; }
@font-face { font-family: "PTSans"; src: url("https://github.com/google/fonts/raw/main/ofl/ptsans/PT_Sans-Web-Regular.ttf"); }
body { font-family: "PTSans", sans-serif; font-size: 12pt; line-height: 1.35; text-align: justify; color: #000; text-indent: 1.25cm; }
h1.title { text-align: center; font-size: 14pt; font-weight: bold; margin-bottom: 20px; text-transform: uppercase; text-indent: 0; }
.meta { width: 100%; margin-bottom: 20px; text-indent: 0; }
.meta td { border: none; padding: 0; }
.section-title { font-weight: bold; margin-top: 15px; margin-bottom: 10px; text-indent: 0; }
table { width: 100%; border-collapse: collapse; margin-top: 15px; text-indent: 0; }
th, td { border: 1px solid #000; padding: 6px; text-align: left; }
.header-info { margin-bottom: 20px; font-size: 10pt; text-align: left; text-indent: 0; }
.signature-block { margin-top: 30px; text-indent: 0; }
"""

# --- УТИЛИТЫ ---
def format_money(val):
    return f"{val:,.2f}".replace(',', ' ').replace('.', ',')

def num2words_rub(num):
    try:
        from num2words import num2words
        rub = int(num)
        kop = int(round((num - rub) * 100))
        rub_str = num2words(rub, lang='ru').capitalize()
        return f"{rub_str} рублей {kop:02d} копеек"
    except ImportError:
        return f"{format_money(num)} рублей"

def get_header_html(company, inn, address, contacts, logo_base64=None):
    logo_html = f'<img src="{logo_base64}" style="max-height: 50px; margin-bottom: 10px;"><br>' if logo_base64 else ''
    return f"""
    <div class="header-info">
        {logo_html}
        <strong>{company}</strong><br>ИНН/КПП: {inn}<br>Адрес: {address}<br>Тел: {contacts}
    </div>
    """

# --- ЭНДПОИНТЫ ---
@app.get("/")
def read_root(): return {"status": "ok"}

@app.get("/get-profile")
async def get_profile(chat_id: str):
    db = SessionLocal()
    profile = db.query(Profile).filter(Profile.chat_id == chat_id).first()
    db.close()
    if profile:
        return {"status": "ok", "company": profile.company, "inn": profile.inn, "address": profile.address, "contacts": profile.contacts, "director": profile.director, "director_rod": profile.director_rod, "director_pos": profile.director_pos, "bank_name": profile.bank_name, "bik": profile.bik, "rs": profile.rs, "ks": profile.ks, "logo": profile.logo}
    return {"status": "not_found"}

@app.post("/save-profile")
async def save_profile(
    chat_id: str = Form(...), company: str = Form(...), inn: str = Form(...), address: str = Form(...), 
    contacts: str = Form(...), director: str = Form(...), director_rod: str = Form(...), director_pos: str = Form(...), 
    bank_name: str = Form(None), bik: str = Form(None), rs: str = Form(None), ks: str = Form(None), logo: str = Form(None)
):
    db = SessionLocal()
    try:
        profile = db.query(Profile).filter(Profile.chat_id == chat_id).first()
        if profile:
            profile.company, profile.inn, profile.address, profile.contacts = company, inn, address, contacts
            profile.director, profile.director_rod, profile.director_pos = director, director_rod, director_pos
            if bank_name: profile.bank_name = bank_name
            if bik: profile.bik = bik
            if rs: profile.rs = rs
            if ks: profile.ks = ks
            if logo: profile.logo = logo
        else:
            db.add(Profile(chat_id=chat_id, company=company, inn=inn, address=address, contacts=contacts, director=director, director_rod=director_rod, director_pos=director_pos, bank_name=bank_name, bik=bik, rs=rs, ks=ks, logo=logo))
        db.commit()
        return {"status": "ok"}
    except Exception as e: return {"status": "error", "message": str(e)}
    finally: db.close()

@app.post("/generate-doc")
async def generate_doc(
    template: str = Form("kp"), company: str = Form("ООО Ваша компания"), inn: str = Form("0000000000"), 
    address: str = Form("г. Москва"), contacts: str = Form("+7 (999) 999-99-99"), 
    director: str = Form("Иванов И.И."), director_rod: str = Form("Иванова И.И."), director_pos: str = Form("Генерального директора"),
    services_json: str = Form("[]"), term: str = Form("30"), dogovor_number: str = Form("Б/Н"), dogovor_date: str = Form(""), 
    customer_name: str = Form("ООО Заказчик"), customer_inn: str = Form("1111111111"), customer_address: str = Form("г. Москва"), 
    customer_director: str = Form("Петров П.П."), customer_director_rod: str = Form("Петрова П.П."), customer_pos: str = Form("Представителя"),
    smeta_date: str = Form(""), smeta_appendix: str = Form("1"), chat_id: str = Form(None), logo: str = Form(None),
    bank_name: str = Form(None), bik: str = Form(None), rs: str = Form(None), ks: str = Form(None)
):
    try:
        services = json.loads(services_json)
        total_price = sum(float(s['price']) * int(s['qty']) for s in services)
        current_date = datetime.now().strftime("%d.%m.%Y")
        date_to_use = dogovor_date if dogovor_date else current_date
        smeta_date_to_use = smeta_date if smeta_date else current_date
        buffer = io.BytesIO()
        nds_text = "НДС не облагается на основании п. 2 ст. 346.11 НК РФ (УСН)"
        header_html = get_header_html(company, inn, address, contacts, logo)

        # --- КП ---
        if template == "kp":
            rows = "".join([f"<tr><td style='text-align:center;'>{i+1}</td><td>{s['name']}</td><td style='text-align:center;'>{term} дн.</td><td style='text-align:right;'>{format_money(float(s['price'])*int(s['qty']))} руб.</td></tr>" for i, s in enumerate(services)])
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            {header_html}<table class="meta"><tr><td style="text-align:right;">Исх. № {dogovor_number} от {date_to_use} г.</td></tr></table>
            <h1 class="title">Коммерческое предложение<br>на оказание услуг</h1>
            <p>Уважаемый клиент! {company} предлагает вам следующие услуги:</p>
            <table><tr><th style="text-align:center; width: 5%;">№</th><th style="width: 60%;">Наименование услуги</th><th style="text-align:center; width: 15%;">Срок</th><th style="text-align:right; width: 20%;">Стоимость</th></tr>{rows}</table>
            <p style="text-align:right; margin-top: 10px; text-indent: 0;"><strong>Итого: {format_money(total_price)} руб.</strong><br>({nds_text})</p>
            <p>1. КП действительно 14 дней.<br>2. Оплата 100% постоплата.<br>3. Не является офертой (ст. 435 ГК РФ).</p>
            <div class="signature-block"><strong>С уважением,</strong><br><br>{director_pos}<br>{company}<br><br><br>_______________ / {director} /</div>
            </body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        # --- СМЕТА ---
        elif template == "smeta":
            rows = "".join([f"<tr><td style='text-align:center;'>{i+1}</td><td>{s['name']}</td><td style='text-align:center;'>усл.</td><td style='text-align:center;'>{s['qty']}</td><td style='text-align:right;'>{format_money(float(s['price']))}</td><td style='text-align:right;'>{format_money(float(s['price'])*int(s['qty']))}</td></tr>" for i, s in enumerate(services)])
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            <table class="meta"><tr><td style="text-align:right;">Приложение № {smeta_appendix} к Договору № {dogovor_number} от {smeta_date_to_use}</td></tr></table>
            <h1 class="title">Смета № {smeta_appendix}</h1>
            <table><tr><th style="text-align:center; width: 5%;">№</th><th style="width: 45%;">Наименование</th><th style="text-align:center; width: 10%;">Ед.</th><th style="text-align:center; width: 10%;">Кол-во</th><th style="text-align:right; width: 15%;">Цена</th><th style="text-align:right; width: 15%;">Сумма</th></tr>{rows}<tr><td colspan="5" style="text-align:right;font-weight:bold;">Всего:</td><td style="text-align:right;font-weight:bold;">{format_money(total_price)}</td></tr></table>
            <p><strong>Всего наименований {len(services)}, на сумму {format_money(total_price)} руб.</strong> {nds_text}.</p>
            <table style="width: 100%; border: none; margin-top: 30px; text-indent: 0;"><tr><td style="border: none; width: 50%;"><strong>Исполнитель:</strong><br>{company}<br><br><br>_______________ / {director} /<br>М.П.</td><td style="border: none; width: 50%;"><strong>Заказчик:</strong><br>{customer_name}<br><br><br>_______________ / {customer_director} /<br>М.П.</td></tr></table>
            </body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        # --- ДОГОВОР ---
        elif template == "dogovor":
            first_service = services[0]['name'] if services else "Услуги"
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            <h1 class="title">ДОГОВОР ОКАЗАНИЯ УСЛУГ № {dogovor_number}</h1>
            <table class="meta"><tr><td style="text-align: left;">г. Москва</td><td style="text-align: right;">{date_to_use} г.</td></tr></table>
            <p>{company}, в лице {director_pos} {director_rod}, с одной стороны, и {customer_name} (ИНН: {customer_inn}, адрес: {customer_address}), в лице {customer_pos} {customer_director_rod}, с другой стороны, заключили Договор:</p>
            <div class="section-title">1. ПРЕДМЕТ ДОГОВОРА</div>
            <p>1.1. Исполнитель обязуется оказать следующие услуги: <strong>{first_service}</strong> (далее — «Услуги»).</p>
            <p>1.2. Перечень и стоимость Услуг определяются в Смете (Приложение № {smeta_appendix}).</p>
            <div class="section-title">2. СТОИМОСТЬ И ПОРЯДОК РАСЧЕТОВ</div>
            <p>2.1. Общая стоимость Услуг составляет <strong>{format_money(total_price)} руб.</strong>, {nds_text}.</p>
            <p>2.2. Оплата 100% в течение 3 банковских дней с момента подписания Акта.</p>
            <div class="section-title">3. ОТВЕТСТВЕННОСТЬ СТОРОН</div>
            <p>3.1. За неисполнение обязательств Стороны несут ответственность согласно законодательству РФ.</p>
            <div class="section-title">4. ЗАКЛЮЧИТЕЛЬНЫЕ ПОЛОЖЕНИЯ</div>
            <p>4.1. Договор вступает в силу с момента подписания и действует до полного исполнения.</p>
            <div class="section-title">5. РЕКВИЗИТЫ И ПОДПИСИ СТОРОН</div>
            <table style="width: 100%; border: none; margin-top: 20px; text-indent: 0;">
                <tr>
                    <td style="border: none; width: 50%; vertical-align: top; padding-right: 10px;">
                        <strong>Исполнитель:</strong><br>{company}<br>ИНН: {inn}<br>Адрес: {address}<br><br>{director_pos}<br><br>_______________ / {director} /<br>М.П.
                    </td>
                    <td style="border: none; width: 50%; vertical-align: top; padding-left: 10px;">
                        <strong>Заказчик:</strong><br>{customer_name}<br>ИНН: {customer_inn}<br>Адрес: {customer_address}<br><br>{customer_pos}<br><br>_______________ / {customer_director} /<br>М.П.
                    </td>
                </tr>
            </table>
            </body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        # --- АКТ ---
        elif template == "act":
            rows = "".join([f"<tr><td style='text-align:center;'>{i+1}</td><td>{s['name']}</td><td style='text-align:center;'>усл.</td><td style='text-align:center;'>{s['qty']}</td><td style='text-align:right;'>{format_money(float(s['price']))}</td><td style='text-align:right;'>{format_money(float(s['price'])*int(s['qty']))}</td></tr>" for i, s in enumerate(services)])
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            <h1 class="title">АКТ СДАЧИ-ПРИЕМКИ ОКАЗАННЫХ УСЛУГ № {smeta_appendix}</h1>
            <table class="meta"><tr><td style="text-align: left;">г. Москва</td><td style="text-align: right;">{smeta_date_to_use} г.</td></tr></table>
            <p>Мы, нижеподписавшиеся, представитель Исполнителя <strong>{company}</strong> в лице {director_pos} {director_rod}, с одной стороны, и представитель Заказчика <strong>{customer_name}</strong> в лице {customer_pos} {customer_director_rod}, с другой стороны, составили настоящий Акт о том, что Услуги по Договору № {dogovor_number} от {date_to_use} выполнены в полном объеме и в срок.</p>
            <table><tr><th style="text-align:center; width: 5%;">№</th><th style="width: 45%;">Наименование услуги</th><th style="text-align:center; width: 10%;">Ед.</th><th style="text-align:center; width: 10%;">Кол-во</th><th style="text-align:right; width: 15%;">Цена</th><th style="text-align:right; width: 15%;">Сумма</th></tr>{rows}<tr><td colspan="5" style="text-align:right;font-weight:bold;">Всего к оплате:</td><td style="text-align:right;font-weight:bold;">{format_money(total_price)}</td></tr></table>
            <p><strong>Всего наименований {len(services)}, на сумму {format_money(total_price)} руб.</strong> {nds_text}.</p>
            <p>Претензий по объему, качеству и срокам оказания Услуг Заказчик не имеет.</p>
            <table style="width: 100%; border: none; margin-top: 40px; text-indent: 0;">
                <tr>
                    <td style="border: none; width: 50%; vertical-align: top; padding-right: 10px;"><strong>Исполнитель:</strong><br>{company}<br>ИНН: {inn}<br>Адрес: {address}<br><br>{director_pos}<br><br>_______________ / {director} /<br>М.П.</td>
                    <td style="border: none; width: 50%; vertical-align: top; padding-left: 10px;"><strong>Заказчик:</strong><br>{customer_name}<br>ИНН: {customer_inn}<br>Адрес: {customer_address}<br><br>{customer_pos}<br><br>_______________ / {customer_director} /<br>М.П.</td>
                </tr>
            </table>
            </body></html>"""
            pisa.CreatePDF(html, dest=buffer)

        # --- СЧЕТ ---
        elif template == "invoice":
            rows = "".join([f"<tr><td style='text-align:center;'>{i+1}</td><td>{s['name']}</td><td style='text-align:center;'>шт</td><td style='text-align:center;'>{s['qty']}</td><td style='text-align:right;'>{format_money(float(s['price']))}</td><td style='text-align:right;'>{format_money(float(s['price'])*int(s['qty']))}</td></tr>" for i, s in enumerate(services)])
            sum_propis = num2words_rub(total_price)
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            {header_html}
            <h1 class="title" style="margin-top:20px;">Счет на оплату № {dogovor_number} от {smeta_date_to_use} г.</h1>
            <table class="meta" style="margin-bottom: 10px;">
                <tr><td style="text-align: left;"><strong>Поставщик (Исполнитель):</strong><br>{company}, ИНН {inn}, {address}</td></tr>
                <tr><td style="text-align: left; padding-top: 10px;"><strong>Покупатель (Заказчик):</strong><br>{customer_name}, ИНН {customer_inn}, {customer_address}</td></tr>
            </table>
            <table>
                <tr><th style="text-align:center; width: 5%;">№</th><th style="width: 45%;">Наименование</th><th style="text-align:center; width: 10%;">Ед.</th><th style="text-align:center; width: 10%;">Кол-во</th><th style="text-align:right; width: 15%;">Цена</th><th style="text-align:right; width: 15%;">Сумма</th></tr>
                {rows}
                <tr><td colspan="5" style="text-align:right;font-weight:bold;">Итого:</td><td style="text-align:right;font-weight:bold;">{format_money(total_price)}</td></tr>
                <tr><td colspan="5" style="text-align:right;font-weight:bold;">{nds_text}</td><td style="text-align:right;font-weight:bold;">0,00</td></tr>
                <tr><td colspan="5" style="text-align:right;font-weight:bold;">Всего к оплате:</td><td style="text-align:right;font-weight:bold;">{format_money(total_price)}</td></tr>
            </table>
            <p style="margin-top:20px; text-indent: 0;"><strong>Всего наименований {len(services)}, на сумму {format_money(total_price)} руб.</strong></p>
            <p style="text-indent: 0;"><strong>Сумма прописью:</strong> {sum_propis}.</p>
            <div class="section-title">Банковские реквизиты для оплаты:</div>
            <table style="width: 100%; border: none; text-indent: 0; font-size: 10pt;">
                <tr><td style="border:none; width: 30%;">Банк:</td><td style="border:none;">{bank_name or "____________________"}</td></tr>
                <tr><td style="border:none;">БИК:</td><td style="border:none;">{bik or "__________"}</td></tr>
                <tr><td style="border:none;">Расчетный счет:</td><td style="border:none;">{rs or "____________________"}</td></tr>
                <tr><td style="border:none;">Корр. счет:</td><td style="border:none;">{ks or "____________________"}</td></tr>
            </table>
            <table style="width: 100%; border: none; margin-top: 30px; text-indent: 0;">
                <tr>
                    <td style="border: none; width: 50%; vertical-align: top; padding-right: 10px;"><strong>Руководитель:</strong><br><br><br>_______________ / {director} /<br><br>М.П.</td>
                    <td style="border: none; width: 50%; vertical-align: top; padding-left: 10px;"><strong>Главный бухгалтер:</strong><br><br><br>_______________ / {director} /</td>
                </tr>
            </table>
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
