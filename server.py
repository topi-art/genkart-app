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

# ВСЕ ТРИ ТОКЕНА
BOT_TOKEN_1 = "8888816541:AAHr3KYdyGi3au_9xQQ83p7NVvI9A1Yp_xE" # Новый 1
BOT_TOKEN_2 = "9065574882:AAEiC01s-YC1ADejERPNLcZSdEJS7qCZe_I" # Новый 2
BOT_TOKEN_3 = "9195903180:AAGSvvim9LlwkYhCCNRoFk_e09OQ_Fyh_58" # Старый
MY_CHAT_ID = "1124115675"

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
table { width: 100%; border-collapse: collapse; margin-top: 15px; text-indent: 0; }
th, td { border: 1px solid #000; padding: 6px; text-align: left; }
.header-info { margin-bottom: 20px; font-size: 10pt; text-align: left; text-indent: 0; }
"""

def format_money(val):
    return f"{val:,.2f}".replace(',', ' ').replace('.', ',')

def get_header_html(company, inn, address, contacts):
    return f"<div class='header-info'><strong>{company}</strong><br>ИНН: {inn}<br>Адрес: {address}<br>Тел: {contacts}</div>"

@app.get("/")
def read_root(): 
    return FileResponse("index.html")

@app.get("/get-profile")
async def get_profile(chat_id: str):
    return {"status": "not_found"}

@app.post("/save-profile")
async def save_profile(chat_id: str = Form(...), company: str = Form(""), inn: str = Form(""), address: str = Form(""), contacts: str = Form("")):
    return {"status": "ok"}

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
        rows = "".join([f"<tr><td style='text-align:center;'>{i+1}</td><td>{s['name']}</td><td style='text-align:center;'>{s.get('unit', 'усл.')}</td><td style='text-align:center;'>{s['qty']}</td><td style='text-align:right;'>{format_money(float(s['price']))}</td><td style='text-align:right;'>{format_money(float(s['price'])*int(s['qty']))}</td></tr>" for i, s in enumerate(services)])
        
        html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
        {header_html}
        <h1 class="title">{template.upper()}</h1>
        <table>
            <tr><th>№</th><th>Наименование</th><th>Ед.</th><th>Кол-во</th><th>Цена</th><th>Сумма</th></tr>
            {rows}
            <tr><td colspan="5" style="text-align:right;font-weight:bold;">ИТОГО:</td><td style="text-align:right;font-weight:bold;">{format_money(total_price)}</td></tr>
        </table>
        </body></html>"""
        
        pisa.CreatePDF(html, dest=buffer)
        buffer.seek(0)

        target_chat_id = chat_id if chat_id else MY_CHAT_ID
        
        # Отправляем во все три бота
        tokens = [BOT_TOKEN_1, BOT_TOKEN_2, BOT_TOKEN_3]
        for token in tokens:
            try:
                url = f"https://api.telegram.org/bot{token}/sendDocument"
                files = {'document': (f'{template}.pdf', buffer.getvalue(), 'application/pdf')}
                data = {'chat_id': target_chat_id, 'caption': 'Ваш документ готов! 📄'}
                requests.post(url, files=files, data=data)
            except:
                pass
            
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
