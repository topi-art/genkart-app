from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import io
import json
import requests
from datetime import datetime
from xhtml2pdf import pisa

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ВСТАВЬ ТОКЕН СВОЕГО НОВОГО БОТА
BOT_TOKEN = "9065574882:AAEiC0Ls-YC1ADejERPNLcZSdEJS7qCZe_I" 

# Стили для красивого PDF
CSS_STYLES = """
@page { size: a4; margin: 20mm 15mm 20mm 30mm; }
body { font-family: "Helvetica", sans-serif; font-size: 11pt; line-height: 1.35; text-align: justify; color: #000; }
h1.title { text-align: center; font-size: 14pt; font-weight: bold; margin-bottom: 20px; text-transform: uppercase; }
table { width: 100%; margin-top: 15px; border-collapse: collapse; }
th, td { border: 1px solid #000; padding: 6px; text-align: left; }
.header-info { margin-bottom: 20px; font-size: 10pt; text-align: left; }
"""

def format_money(val):
    return f"{val:,.2f}".replace(',', ' ').replace('.', ',')

@app.get("/")
def read_root(): 
    return {"status": "ok"}

@app.post("/generate-doc")
async def generate_doc(
    template: str = Form("kp"), company: str = Form("ООО Ваша компания"), 
    inn: str = Form("0000000000"), address: str = Form("г. Москва"), 
    contacts: str = Form("+7 (999) 999-99-99"), services_json: str = Form("[]"), 
    chat_id: str = Form(None)
):
    try:
        services = json.loads(services_json)
        total_price = sum(float(s['price']) * int(s['qty']) for s in services)
        current_date = datetime.now().strftime("%d.%m.%Y")
        
        header_html = f"<div class='header-info'><strong>{company}</strong><br>ИНН: {inn}<br>Адрес: {address}<br>Тел: {contacts}</div>"
        
        # Формируем таблицу
        rows = ""
        for i, s in enumerate(services):
            sum_s = float(s['price']) * int(s['qty'])
            rows += f"<tr><td align='center'>{i+1}</td><td>{s['name']}</td><td align='center'>{s.get('unit', 'усл.')}</td><td align='center'>{s['qty']}</td><td align='right'>{format_money(float(s['price']))}</td><td align='right'>{format_money(sum_s)}</td></tr>"

        # Генерируем HTML для PDF
        html = f"""
        <html><head><meta charset="utf-8"><style>{CSS_STYLES}</style></head><body>
        {header_html}
        <h1 class="title">{template.upper()}</h1>
        <p>Дата: {current_date}</p>
        <table>
            <tr><th>№</th><th>Наименование</th><th>Ед.</th><th>Кол-во</th><th>Цена</th><th>Сумма</th></tr>
            {rows}
            <tr><td colspan="5" align="right"><b>Итого:</b></td><td align="right"><b>{format_money(total_price)}</b></td></tr>
        </table>
        </body></html>
        """
        
        # Создаем PDF
        buffer = io.BytesIO()
        pisa.CreatePDF(html, dest=buffer)
        buffer.seek(0)

        # Отправляем в Telegram
        if chat_id:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            files = {'document': ('document.pdf', buffer.getvalue(), 'application/pdf')}
            data = {'chat_id': chat_id, 'caption': 'Ваш документ готов! 📄'}
            response = requests.post(url, files=files, data=data)
            
            if response.status_code != 200:
                return JSONResponse(status_code=500, content={"status": "error", "message": f"Ошибка ТГ: {response.text}"})
                
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
