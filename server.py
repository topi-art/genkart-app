from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import io, json, requests
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import declarative_base, sessionmaker
from xhtml2pdf import pisa
from num2words import num2words
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ТВОЙ ТОКЕН
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

def get_short_name(fio):
    parts = fio.split()
    if len(parts) >= 3: return f"{parts[1]} {parts[2]}"
    return fio

def get_signature_fio(fio):
    parts = fio.split()
    if len(parts) >= 2: return f"{parts[1]} {parts[0]}"
    return fio

def clean_text(text):
    if not text: return ""
    text = text.strip()
    if '"' in text: text = text.replace('"', '«', 1).replace('"', '»', 1)
    return text

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

# --- БАЗА ДАННЫХ ---
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

Base.metadata.create_all(bind=engine)

# --- ГЕНЕРАЦИЯ WORD (DOCX) ---
def generate_docx(template, company, inn, kpp, address, contacts, director, services, total_price, customer_name, customer_inn, customer_kpp, customer_address, customer_director, tax_mode, dogovor_number):
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(11)

    p = doc.add_paragraph()
    run = p.add_run(clean_text(company) + "\n")
    run.bold = True
    p.add_run(f"ИНН/КПП: {inn}{('/' + kpp) if kpp else ''}\nАдрес: {clean_text(address)}\nТел: {contacts}\n")

    p_date = doc.add_paragraph(f"Исх. № {dogovor_number} от {datetime.now().strftime('%d.%m.%Y')} г.")
    p_date.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    titles = {"kp": "КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ", "smeta": "СМЕТА", "dogovor": "ДОГОВОР", "act": "АКТ", "invoice": "СЧЕТ"}
    h = doc.add_heading(titles.get(template, "ДОКУМЕНТ"), level=1)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER

    if template == "kp":
        greeting = f"Уважаемый {get_short_name(customer_director)}!" if customer_director else "Уважаемый клиент!"
        doc.add_paragraph(f"{greeting} {clean_text(company)} предлагает вам следующие услуги:")

    table = doc.add_table(rows=1, cols=6)
    table.style = 'Table Grid'
    hdr_cells = table.rows[0].cells
    headers = ['№', 'Наименование', 'Ед.', 'Кол-во', 'Цена', 'Сумма']
    for i, h_text in enumerate(headers):
        hdr_cells[i].text = h_text

    for i, s in enumerate(services):
        row_cells = table.add_row().cells
        row_cells[0].text = str(i+1)
        row_cells[1].text = s['name']
        row_cells[2].text = s.get('unit', 'усл.')
        row_cells[3].text = str(s['qty'])
        row_cells[4].text = format_money(float(s['price']))
        row_cells[5].text = format_money(float(s['price'])*int(s['qty']))

    p_total = doc.add_paragraph()
    p_total.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run_total = p_total.add_run(f"Итого: {format_money(total_price)} руб.")
    run_total.bold = True

    if tax_mode == "osno":
        nds = total_price * 22 / 122
        doc.add_paragraph(f"В том числе НДС 22%: {format_money(nds)} руб.")
    else:
        doc.add_paragraph("НДС не облагается (УСН).")

    doc.add_paragraph("\n\nС уважением,")
    doc.add_paragraph(f"Генеральный директор\n{clean_text(company)}")
    doc.add_paragraph("\n\n_______________ / " + director + " /")
    doc.add_paragraph("М.П.")

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- СТИЛИ ДЛЯ PDF ---
CSS_STYLES = """
@page { size: a4; margin: 20mm 15mm 20mm 30mm; }
@font-face { font-family: "PTSans"; src: url("https://github.com/google/fonts/raw/main/ofl/ptsans/PT_Sans-Web-Regular.ttf"); }
body { font-family: "PTSans", sans-serif; font-size: 11pt; line-height: 1.35; text-align: justify; color: #000; text-indent: 1.25cm; }
h1.title { text-align: center; font-size: 14pt; font-weight: bold; margin-bottom: 20px; text-transform: uppercase; text-indent: 0; }
.header-info { margin-bottom: 20px; font-size: 10pt; text-align: left; text-indent: 0; }
table { width: 100%; border-collapse: collapse; margin-top: 15px; text-indent: 0; }
th, td { border: 1px solid #000; padding: 6px; text-align: left; }
.signature-block { margin-top: 30px; text-indent: 0; }
"""

def get_header_html(company, inn, kpp, address, contacts):
    inn_kpp_str = f"ИНН/КПП: {inn}/{kpp}" if kpp else f"ИНН: {inn}"
    tel_html = f"<br>Тел: {contacts}" if contacts else ""
    return f"<div class='header-info'><strong>{clean_text(company)}</strong><br>{inn_kpp_str}<br>Адрес: {clean_text(address)}{tel_html}</div>"

# --- ЭНДПОИНТЫ ---
@app.get("/")
def read_root(): return FileResponse("index.html")

@app.post("/generate-doc")
async def generate_doc(
    template: str = Form("kp"), format_type: str = Form("pdf"),
    company: str = Form(""), inn: str = Form(""), kpp: str = Form(""), 
    address: str = Form(""), contacts: str = Form(""), tax_mode: str = Form("usn"),
    director: str = Form(""), services_json: str = Form("[]"), dogovor_number: str = Form(""), 
    customer_name: str = Form(""), customer_inn: str = Form(""), customer_kpp: str = Form(""), 
    customer_address: str = Form(""), customer_director: str = Form(""), chat_id: str = Form(None)
):
    try:
        services = json.loads(services_json)
        total_price = sum(float(s['price']) * int(s['qty']) for s in services)
        date_to_use = datetime.now().strftime("%d.%m.%Y")
        
        if format_type == "docx":
            buffer = generate_docx(template, company, inn, kpp, address, contacts, director, services, total_price, customer_name, customer_inn, customer_kpp, customer_address, customer_director, tax_mode, dogovor_number)
            ext = "docx"
            mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            buffer = io.BytesIO()
            header_html = get_header_html(company, inn, kpp, address, contacts)
            rows = "".join([f"<tr><td style='text-align:center;'>{i+1}</td><td>{s['name']}</td><td style='text-align:center;'>{s.get('unit', 'усл.')}</td><td style='text-align:center;'>{s['qty']}</td><td style='text-align:right;'>{format_money(float(s['price']))}</td><td style='text-align:right;'>{format_money(float(s['price'])*int(s['qty']))}</td></tr>" for i, s in enumerate(services)])
            
            html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
            {header_html}
            <h1 class="title">{template.upper()}</h1>
            <p>Исх. № {dogovor_number} от {date_to_use} г.</p>
            <table><tr><th>№</th><th>Наименование</th><th>Ед.</th><th>Кол-во</th><th>Цена</th><th>Сумма</th></tr>{rows}</table>
            <p style="text-align:right; margin-top: 10px; text-indent: 0;"><strong>Итого: {format_money(total_price)} руб.</strong></p>
            <div class="signature-block">_______________ / {director} /</div>
            </body></html>"""
            pisa.CreatePDF(html, dest=buffer)
            buffer.seek(0)
            ext = "pdf"
            mime = "application/pdf"

        if chat_id:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            files = {'document': (f'{template}.{ext}', buffer.getvalue(), mime)}
            data = {'chat_id': chat_id, 'caption': f'Ваш документ ({ext.upper()}) готов! 📄'}
            requests.post(url, files=files, data=data)
            
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
