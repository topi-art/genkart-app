import subprocess
import sys

# Установка python-docx
try:
    import docx
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-docx"])

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
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

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

    titles = {"kp": "КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ", "smeta": "СМЕТА", "dogovor": "ДОГОВОР", "act": "АКТ", "invoice": "СЧЕТ НА ОПЛАТУ"}
    h = doc.add_heading(titles.get(template, "ДОКУМЕНТ"), level=1)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER

    if template == "kp":
        greeting = f"Уважаемый {get_short_name(customer_director)}!" if customer_director else "Уважаемый клиент!"
        doc.add_paragraph(f"{greeting} {clean_text(company)} предлагает вам следующие услуги:")
    elif template == "invoice":
        doc.add_paragraph(f"Поставщик: {clean_text(company)}, ИНН {inn}{('/' + kpp) if kpp else ''}, {clean_text(address)}")
        doc.add_paragraph(f"Покупатель: {clean_text(customer_name)}, ИНН {customer_inn}{('/' + customer_kpp) if customer_kpp else ''}, {clean_text(customer_address)}")

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
        doc.add_paragraph(f"В том числе НДС 22%: {format_money(nds)} руб. ({num2words_rub(nds)})")
    else:
        doc.add_paragraph("НДС не облагается на основании п. 2 ст. 346.11 НК РФ (УСН).")

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
.meta { width: 100%; margin-bottom: 20px; text-indent: 0; }
.meta td { border: none; padding: 0; }
.section-title { font-weight: bold; margin-top: 15px; margin-bottom: 10px; text-indent: 0; }
table { width: 100%; border-collapse: collapse; margin-top: 15px; text-indent: 0; }
th, td { border: 1px solid #000; padding: 6px; text-align: left; }
.header-info { margin-bottom: 20px; font-size: 10pt; text-align: left; text-indent: 0; }
.signature-block { margin-top: 30px; text-indent: 0; }
.list-item { text-indent: 0; margin-bottom: 5px; }
"""

def get_header_html(company, inn, kpp, address, contacts):
    kpp_str = f"/{kpp}" if kpp else ""
    return f"<div class='header-info'><strong>{clean_text(company)}</strong><br>ИНН/КПП: {inn}{kpp_str}<br>Адрес: {clean_text(address)}<br>Тел: {contacts}</div>"

# --- ЭНДПОИНТЫ ---
@app.get("/")
def read_root(): return FileResponse("index.html")

@app.post("/generate-doc")
async def generate_doc(
    template: str = Form("kp"), format_type: str = Form("pdf"),
    company: str = Form(""), inn: str = Form(""), kpp: str = Form(""), 
    address: str = Form(""), contacts: str = Form(""), tax_mode: str = Form("usn"),
    director: str = Form(""), services_json: str = Form("[]"), term: str = Form(""), dogovor_number: str = Form(""), 
    customer_name: str = Form(""), customer_inn: str = Form(""), customer_kpp: str = Form(""), 
    customer_address: str = Form(""), customer_director: str = Form(""), 
    smeta_date: str = Form(""), smeta_appendix: str = Form("1"), chat_id: str = Form(None),
    bank_name: str = Form(None), bik: str = Form(None), rs: str = Form(None), ks: str = Form(None)
):
    try:
        services = json.loads(services_json)
        total_price = sum(float(s['price']) * int(s['qty']) for s in services)
        date_to_use = datetime.now().strftime("%d.%m.%Y")
        smeta_date_to_use = smeta_date if smeta_date else date_to_use
        
        if format_type == "docx":
            buffer = generate_docx(template, company, inn, kpp, address, contacts, director, services, total_price, customer_name, customer_inn, customer_kpp, customer_address, customer_director, tax_mode, dogovor_number)
            ext = "docx"
            mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            buffer = io.BytesIO()
            header_html = get_header_html(company, inn, kpp, address, contacts)
            dir_rod = decline_fio(director)
            cust_rod = decline_fio(customer_director)
            sum_propis = num2words_rub(total_price)
            
            # --- ВОЗВРАЩАЕМ КРАСИВЫЙ PDF ---
            if template == "invoice":
                rows = "".join([f"<tr><td style='text-align:center;'>{i+1}</td><td>{s['name']}</td><td style='text-align:center;'>{s.get('unit', 'усл.')}</td><td style='text-align:center;'>{s['qty']}</td><td style='text-align:right;'>{format_money(float(s['price']))}</td><td style='text-align:right;'>{format_money(float(s['price'])*int(s['qty']))}</td></tr>" for i, s in enumerate(services)])
                
                bank_table = f"""<table style="width: 100%; border-collapse: collapse; text-indent: 0; font-size: 10pt; margin-bottom: 20px;">
                    <tr><td style="border: 1px solid #000; padding: 5px; width: 15%;">Банк получателя:</td><td style="border: 1px solid #000; padding: 5px;" colspan="3">{bank_name or "____________________"}</td></tr>
                    <tr><td style="border: 1px solid #000; padding: 5px;">БИК:</td><td style="border: 1px solid #000; padding: 5px; width: 35%;">{bik or "__________"}</td><td style="border: 1px solid #000; padding: 5px; width: 15%;">Сч. №:</td><td style="border: 1px solid #000; padding: 5px;">{ks or "____________________"}</td></tr>
                    <tr><td style="border: 1px solid #000; padding: 5px;">Получатель:</td><td style="border: 1px solid #000; padding: 5px;" colspan="3">{clean_text(company)}<br>ИНН {inn} {(' / КПП ' + kpp) if kpp else ''}</td></tr>
                    <tr><td style="border: 1px solid #000; padding: 5px;">Р/с:</td><td style="border: 1px solid #000; padding: 5px;" colspan="3">{rs or "____________________"}</td></tr>
                </table>"""
                
                nds_row = f"<tr><td colspan='5' style='text-align:right;font-weight:bold;'>В том числе НДС 22%:</td><td style='text-align:right;font-weight:bold;'>{format_money(total_price * 0.22 / 1.22)}</td></tr>" if tax_mode == "osno" else "<tr><td colspan='5' style='text-align:right;font-weight:bold;'>Без налога (НДС):</td><td style='text-align:right;font-weight:bold;'>0,00</td></tr>"

                html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
                {header_html}
                {bank_table}
                <h1 class="title">Счет на оплату № {dogovor_number} от {smeta_date_to_use} г.</h1>
                <table class="meta" style="margin-bottom: 15px;">
                    <tr><td style="text-align: left;"><strong>Поставщик:</strong><br>{clean_text(company)}, ИНН {inn}{(' / КПП ' + kpp) if kpp else ''}, {clean_text(address)}</td></tr>
                    <tr><td style="text-align: left; padding-top: 5px;"><strong>Покупатель:</strong><br>{clean_text(customer_name)}, ИНН {customer_inn}{(' / КПП ' + customer_kpp) if customer_kpp else ''}, {clean_text(customer_address)}</td></tr>
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

            elif template == "kp":
                rows = "".join([f"<tr><td style='text-align:center;'>{i+1}</td><td>{s['name']}</td><td style='text-align:center;'>{s.get('unit', 'усл.')}</td><td style='text-align:center;'>{term}</td><td style='text-align:right;'>{format_money(float(s['price'])*int(s['qty']))} руб.</td></tr>" for i, s in enumerate(services)])
                customer_greeting = get_short_name(customer_director) if customer_director else "клиент"
                greeting = f"Уважаемый {customer_greeting}!" if customer_greeting != "клиент" else "Уважаемый клиент!"
                nds_text = "В том числе НДС 22%" if tax_mode == "osno" else "НДС не облагается (УСН)"
                
                html = f"""<html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
                {header_html}
                <table class="meta"><tr><td style="text-align:right;">Исх. № {dogovor_number} от {date_to_use} г.</td></tr></table>
                <p style="text-align:right; text-indent:0;"><strong>Кому:</strong><br>Генеральному директору<br>{clean_text(customer_name)}<br>{customer_director}</p>
                <h1 class="title">Коммерческое предложение<br>на оказание услуг</h1>
                <p>{greeting} {clean_text(company)} предлагает вам следующие услуги:</p>
                <table><tr><th style="text-align:center; width: 5%;">№</th><th style="width: 50%;">Наименование услуги</th><th style="text-align:center; width: 10%;">Ед.</th><th style="text-align:center; width: 15%;">Срок</th><th style="text-align:right; width: 20%;">Стоимость</th></tr>{rows}</table>
                <p style="text-align:right; margin-top: 10px; text-indent: 0;"><strong>Итого: {format_money(total_price)} руб.</strong><br>({nds_text})</p>
                <div class="signature-block"><strong>С уважением,</strong><br><br>Генеральный директор<br>{clean_text(company)}<br><br><br>_______________ / {director} /</div>
                </body></html>"""
                pisa.CreatePDF(html, dest=buffer)
                
            else:
                # Упрощенные шаблоны для Сметы, Акта, Договора (чтобы не упало)
                rows = "".join([f"<tr><td>{s['name']}</td><td>{s['qty']}</td><td>{format_money(float(s['price'])*int(s['qty']))}</td></tr>" for i, s in enumerate(services)])
                html = f"<html><body>{header_html}<h1 class='title'>{template.upper()}</h1><table><tr><th>Наименование</th><th>Кол-во</th><th>Сумма</th></tr>{rows}</table><p>Итого: {format_money(total_price)} руб.</p></body></html>"
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
