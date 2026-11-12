from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import io
import os
import json
from datetime import datetime
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

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Бэкенд работает!"}

@app.post("/generate-doc")
async def generate_doc(
    template: str = Form("kp"),
    company: str = Form("ООО Ваша компания"),
    inn: str = Form("0000000000"),
    address: str = Form("г. Москва, ул. Примерная, д. 1"),
    contacts: str = Form("+7 (999) 999-99-99"),
    services_json: str = Form("[]"),
    term: str = Form("30"),
    dogovor_number: str = Form("Б/Н"),
    dogovor_date: str = Form(""),
    customer_name: str = Form("ООО Заказчик"),
    customer_inn: str = Form("1111111111"),
    customer_address: str = Form("г. Москва, ул. Заказная, д. 2"),
    director_name: str = Form("Иванов И.И."),
    smeta_date: str = Form("")
):
    services = json.loads(services_json)
    total_price = sum(float(s['price']) * int(s['qty']) for s in services)
    current_date = datetime.now().strftime("%d.%m.%Y")
    date_to_use = dogovor_date if dogovor_date else current_date
    smeta_date_to_use = smeta_date if smeta_date else current_date
    
    buffer = io.BytesIO()

    # --- ГЕНЕРАЦИЯ КП ---
    if template == "kp":
        rows_html = ""
        for i, s in enumerate(services):
            amount = float(s['price']) * int(s['qty'])
            rows_html += f"<tr><td>{i+1}</td><td>{s['name']}</td><td>{term} дней</td><td style='text-align:right;'>{amount:.2f}</td></tr>"

        html = f"""
        <html><head><style>
            body {{ font-family: "Times New Roman", serif; font-size: 11pt; }}
            .header {{ border-bottom: 1px solid #000; padding-bottom: 10px; }}
            .title {{ text-align: center; font-weight: bold; font-size: 14pt; margin: 20px 0; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
            th, td {{ border: 1px solid #000; padding: 8px; }}
        </style></head><body>
            <div class="header"><strong>{company}</strong><br>ИНН {inn}<br>{address}<br>Тел: {contacts}</div>
            <div class="title">КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ</div>
            <p>Компания {company} предлагает вам следующие услуги:</p>
            <table><tr><th>№</th><th>Услуга</th><th>Срок</th><th>Стоимость</th></tr>{rows_html}</table>
            <p style="text-align:right;"><strong>Итого: {total_price:.2f} руб.</strong> (НДС не облагается, УСН)</p>
            <p><strong>Условия:</strong><br>1. КП действительно 14 дней.<br>2. Оплата 100% постоплата.</p>
            <br><p>С уважением,<br>Директор {company} _______________ / {director_name} /</p>
        </body></html>
        """
        pisa.CreatePDF(html, dest=buffer)

    # --- ГЕНЕРАЦИЯ СМЕТЫ ---
    elif template == "smeta":
        rows_html = ""
        for i, s in enumerate(services):
            amount = float(s['price']) * int(s['qty'])
            rows_html += f"<tr><td>{i+1}</td><td>{s['name']}</td><td>усл.</td><td>{s['qty']}</td><td>{s['price']}</td><td>{amount:.2f}</td></tr>"

        html = f"""
        <html><head><style>
            body {{ font-family: Arial, sans-serif; font-size: 10pt; }}
            .header {{ text-align: right; margin-bottom: 20px; }}
            .title {{ text-align: center; font-size: 13pt; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ border: 1px solid #000; padding: 6px; }}
            th {{ background: #eee; }}
        </style></head><body>
            <div class="header">Приложение № 1 к Договору № {dogovor_number} от {smeta_date_to_use}</div>
            <div class="title">СМЕТА НА ОКАЗАНИЕ УСЛУГ</div>
            <table><tr><th>№</th><th>Наименование</th><th>Ед.</th><th>Кол-во</th><th>Цена</th><th>Сумма</th></tr>{rows_html}
            <tr><td colspan="5" style="text-align:right; font-weight:bold;">Всего к оплате:</td><td style="font-weight:bold;">{total_price:.2f}</td></tr></table>
            <p style="margin-top:20px;"><strong>Всего наименований {len(services)}, на сумму {total_price:.2f} рублей.</strong></p>
            <br><br>
            <table style="border:none;"><tr>
                <td style="border:none;">Исполнитель: ______________ / {director_name} /<br>М.П.</td>
                <td style="border:none;">Заказчик: ______________ / {customer_name} /<br>М.П.</td>
            </tr></table>
        </body></html>
        """
        pisa.CreatePDF(html, dest=buffer)

    # --- ГЕНЕРАЦИЯ ДОГОВОРА ---
    elif template == "dogovor":
        html = f"""
        <html><head><style>
            body {{ font-family: "Times New Roman", serif; font-size: 11pt; line-height: 1.35; }}
            .title {{ text-align: center; font-weight: bold; font-size: 14pt; margin-bottom: 20px; }}
            .meta {{ display: flex; justify-content: space-between; }}
        </style></head><body>
            <div class="title">ДОГОВОР ОКАЗАНИЯ УСЛУГ № {dogovor_number}</div>
            <div class="meta"><span>г. Москва</span><span>«{date_to_use}» г.</span></div>
            <p>{company}, в лице {director_name}, с одной стороны, и {customer_name} (ИНН: {customer_inn}, адрес: {customer_address}), с другой стороны, заключили Договор:</p>
            <p><strong>1. ПРЕДМЕТ ДОГОВОРА</strong><br>1.1. Исполнитель обязуется оказать услуги согласно Смете.</p>
            <p><strong>2. СТОИМОСТЬ И ПОРЯДОК РАСЧЕТОВ</strong><br>2.1. Общая стоимость Услуг составляет {total_price:.2f} руб.</p>
            <p><strong>3. ОТВЕТСТВЕННОСТЬ СТОРОН</strong><br>3.1. За нарушение сроков оплаты неустойка 0,1%.</p>
            <p><strong>4. ЗАКЛЮЧИТЕЛЬНЫЕ ПОЛОЖЕНИЯ</strong><br>4.1. Договор действует до полного исполнения.</p>
            <br><br>
            <table style="border:none; width:100%;"><tr>
                <td style="border:none; width:50%;"><strong>ИСПОЛНИТЕЛЬ:</strong><br>{company}<br>ИНН: {inn}<br><br>______________ / {director_name} /</td>
                <td style="border:none; width:50%;"><strong>ЗАКАЗЧИК:</strong><br>{customer_name}<br>ИНН: {customer_inn}<br><br>______________ / ФИО /</td>
            </tr></table>
        </body></html>
        """
        pisa.CreatePDF(html, dest=buffer)

    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf")
