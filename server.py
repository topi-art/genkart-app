from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import io, json, requests
from datetime import datetime
from fpdf import FPDF

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

BOT_TOKEN = "9065574882:AAEiC0Ls-YC1ADejERPNLcZSdEJS7qCZe_I"

class PDF(FPDF):
    def header(self):
        self.add_font('DejaVu', '', 'https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf', uni=True)
        self.set_font('DejaVu', '', 10)
        self.cell(0, 10, 'Документ сгенерирован автоматически', 0, 1, 'C')

@app.get("/")
def read_root(): return {"status": "ok"}

@app.post("/generate-doc")
async def generate_doc(
    template: str = Form("kp"), company: str = Form("ООО Ваша компания"), 
    inn: str = Form("0000000000"), address: str = Form("г. Москва"), 
    contacts: str = Form("+7 (999) 999-99-99"), services_json: str = Form("[]"), chat_id: str = Form(None)
):
    try:
        services = json.loads(services_json)
        total_price = sum(float(s['price']) * int(s['qty']) for s in services)
        pdf = PDF()
        pdf.add_page()
        pdf.set_font('DejaVu', '', 12)
        pdf.multi_cell(0, 8, f"{company}\nИНН: {inn}\nАдрес: {address}\nТел: {contacts}")
        pdf.ln(10)
        pdf.set_font('DejaVu', 'B', 14)
        title = "КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ" if template == "kp" else "СМЕТА"
        pdf.cell(0, 10, title, 0, 1, 'C')
        pdf.ln(10)
        pdf.set_font('DejaVu', '', 10)
        pdf.cell(0, 8, f"Дата: {datetime.now().strftime('%d.%m.%Y')}", 0, 1, 'R')
        pdf.ln(5)
        pdf.set_font('DejaVu', 'B', 10)
        pdf.cell(10, 8, '№', 1); pdf.cell(100, 8, 'Наименование', 1); pdf.cell(20, 8, 'Кол-во', 1); pdf.cell(40, 8, 'Сумма', 1); pdf.ln()
        pdf.set_font('DejaVu', '', 10)
        for i, s in enumerate(services):
            amount = float(s['price']) * int(s['qty'])
            pdf.cell(10, 8, str(i+1), 1); pdf.cell(100, 8, s['name'][:40], 1); pdf.cell(20, 8, str(s['qty']), 1); pdf.cell(40, 8, f"{amount:,.2f} руб.", 1); pdf.ln()
        pdf.ln(5)
        pdf.set_font('DejaVu', 'B', 12)
        pdf.cell(0, 10, f"ИТОГО: {total_price:,.2f} руб.", 0, 1, 'R')
        buffer = io.BytesIO(); pdf.output(buffer); buffer.seek(0)
        if chat_id:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            files = {'document': ('document.pdf', buffer.getvalue(), 'application/pdf')}
            data = {'chat_id': chat_id, 'caption': 'Ваш документ готов!'}
            requests.post(url, files=files, data=data)
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
