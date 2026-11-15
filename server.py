import subprocess
import sys

# Принудительно устанавливаем нужные библиотеки
subprocess.check_call([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn", "python-multipart", "xhtml2pdf", "requests"])

from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import io, json, requests
from datetime import datetime
from xhtml2pdf import pisa

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

BOT_TOKEN = "9065574882:AAEiC0Ls-YC1ADejERPNLcZSdEJS7qCZe_I"

@app.get("/")
def read_root(): 
    return FileResponse("index.html")

@app.get("/get-profile")
async def get_profile(chat_id: str):
    return {"status": "not_found"}

@app.post("/save-profile")
async def save_profile(
    chat_id: str = Form(None), company: str = Form(""), inn: str = Form(""), address: str = Form(""), contacts: str = Form("")
):
    return {"status": "ok"}

@app.post("/generate-doc")
async def generate_doc(
    template: str = Form("kp"), company: str = Form("ООО Ваша компания"), 
    inn: str = Form("0000000000"), address: str = Form("г. Москва"), 
    contacts: str = Form("+7 (999) 999-99-99"), services_json: str = Form("[]"), 
    chat_id: str = Form(None), term: str = Form(""), dogovor_number: str = Form(""), 
    dogovor_date: str = Form(""), customer_name: str = Form(""), customer_inn: str = Form(""), smeta_date: str = Form("")
):
    try:
        services = json.loads(services_json)
        total_price = sum(float(s['price']) * int(s['qty']) for s in services)
        
        titles = {"kp": "КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ", "smeta": "СМЕТА", "dogovor": "ДОГОВОР", "act": "АКТ", "invoice": "СЧЕТ"}
        title = titles.get(template, "ДОКУМЕНТ")
        
        rows = "".join([f"<tr><td align='center'>{i+1}</td><td>{s['name']}</td><td align='center'>{s.get('unit', 'усл.')}</td><td align='center'>{s['qty']}</td><td align='right'>{float(s['price']):,.2f}</td><td align='right'>{float(s['price'])*int(s['qty']):,.2f}</td></tr>" for i, s in enumerate(services)])

        html = f"""
        <html><head><meta charset="utf-8"><style>
        @page {{ size: a4; margin: 20mm; }}
        body {{ font-family: "Helvetica", sans-serif; font-size: 11pt; color: #000; }}
        h1 {{ text-align: center; font-size: 14pt; text-transform: uppercase; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ border: 1px solid #000; padding: 6px; }}
        </style></head><body>
        <h1>{title}</h1>
        <p>Дата: {datetime.now().strftime('%d.%m.%Y')}</p>
        <p><strong>{company}</strong><br>ИНН: {inn}<br>Адрес: {address}<br>Тел: {contacts}</p>
        <table>
            <tr><th>№</th><th>Наименование</th><th>Ед.</th><th>Кол-во</th><th>Цена</th><th>Сумма</th></tr>
            {rows}
            <tr><td colspan="5" align="right"><b>ИТОГО:</b></td><td align="right"><b>{total_price:,.2f} руб.</b></td></tr>
        </table>
        </body></html>
        """
        
        buffer = io.BytesIO()
        pisa.CreatePDF(html, dest=buffer)
        buffer.seek(0)

        if chat_id:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            files = {'document': ('document.pdf', buffer.getvalue(), 'application/pdf')}
            data = {'chat_id': chat_id, 'caption': 'Ваш документ готов! 📄'}
            requests.post(url, files=files, data=data)
            
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
