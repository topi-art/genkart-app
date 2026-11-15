from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import io, json, requests
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import declarative_base, sessionmaker
from xhtml2pdf import pisa
from num2words import num2words

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ТВОЙ НОВЫЙ ТОКЕН (ИЗ СКРИНШОТА)
BOT_TOKEN = "8888816541:AAHvupbfatSzaMyE-ekvYCBkt9mqwJA-y5c"

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

def clean_text(text):
    if not text: return ""
    text = text.strip()
    if '"' in text:
        text = text.replace('"', '«', 1).replace('"', '»', 1)
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
    if kpp:
        inn_kpp_str = f"ИНН/КПП: {inn}/{kpp}"
    else:
        inn_kpp_str = f"ИНН: {inn}"
        
    tel_html = f"<br>Тел: {contacts}" if contacts else ""
    return f"<div class='header-info'><strong>{clean_text(company)}</strong><br>{inn_kpp_str}<br>Адрес: {clean_text(address)}{tel_html}</div>"

@app.get("/")
def read_root(): 
    return FileResponse("index.html")

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
        dir_sign = get_signature_fio(director)
        cust_sign = get_signature_fio(customer_director)

        if template == "kp":
            rows = "".join([f"<tr><td style='text-align:center;'>{i+1}</td><td>{s['name']}</td><td style='text-align:center;'>{s.get('unit', 'усл.')}</td><td style='text-align:center;'>{s['qty']}</td><td style='text-align:right;'>{format_money(float(s['price']))}</td><td style='text-align:right;'>{format_money(float(s['price'])*int(s['qty']))}</td></tr>" for i, s in enumerate(services)])
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            {header_html}
            <table class="meta"><tr><td style="text-align:right;">Исх. № {dogovor_number} от {date_to_use} г.</td></tr></table>
            <h1 class="title">Коммерческое предложение</h1>
            <table><tr><th style="text-align:center; width: 5%;">№</th><th style="width: 45%;">Наименование</th><th style="text-align:center; width: 10%;">Ед.</th><th style="text-align:center; width: 10%;">Кол-во</th><th style="text-align:right; width: 15%;">Цена</th><th style="text-align:right; width: 15%;">Сумма</th></tr>{rows}</table>
            <p style="text-align:right; margin-top: 10px; text-indent: 0;"><strong>Итого: {format_money(total_price)} руб.</strong><br>({nds_text})</p>
            </body></html>"""
            pisa.CreatePDF(html, dest=buffer)
        
        else:
            html = f"<html><body><h1>{template.upper()}</h1><p>Сумма: {format_money(total_price)} руб.</p></body></html>"
            pisa.CreatePDF(html, dest=buffer)

        buffer.seek(0)

        if chat_id:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            files = {'document': (f'{template}.pdf', buffer.getvalue(), 'application/pdf')}
            data = {'chat_id': chat_id, 'caption': 'Ваш документ готов! 📄'}
            response = requests.post(url, files=files, data=data)
            print("ОТВЕТ ОТ TELEGRAM:", response.text) # <--- ОТЛАДКА
            
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
