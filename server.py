from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
import io, json, requests, os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import declarative_base, sessionmaker
from xhtml2pdf import pisa

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

BOT_TOKEN = "9065574882:AAEiC0Ls-YC1ADejERPNLcZSdEJS7qCZe_I" 

DATABASE_URL = "sqlite:///./profiles_final.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, unique=True, index=True)
    company = Column(String, default="")
    inn = Column(String, default="")
    address = Column(String, default="")
    contacts = Column(String, default="")

Base.metadata.create_all(bind=engine)

CSS_STYLES = """
@page { size: a4; margin: 20mm 15mm 20mm 30mm; }
body { font-family: "Helvetica", sans-serif; font-size: 11pt; line-height: 1.35; text-align: justify; color: #000; }
h1.title { text-align: center; font-size: 14pt; font-weight: bold; margin-bottom: 20px; text-transform: uppercase; }
.meta { width: 100%; margin-bottom: 20px; }
.meta td { border: none; padding: 0; }
table { width: 100%; margin-top: 15px; }
th, td { border: 1px solid #000; padding: 6px; text-align: left; }
.header-info { margin-bottom: 20px; font-size: 10pt; text-align: left; }
"""

def format_money(val):
    return f"{val:,.2f}".replace(',', ' ').replace('.', ',')

def get_header_html(company, inn, address, contacts):
    return f"<div class='header-info'><strong>{company}</strong><br>ИНН: {inn}<br>Адрес: {address}<br>Тел: {contacts}</div>"

@app.get("/")
def read_root(): 
    html_content = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>GenDoc</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            :root { --bg: #121212; --card: #1e1e1e; --text: #ffffff; --muted: #888888; --accent: #ff2a75; --accent-txt: #ffffff; }
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
            body { background: var(--bg); color: var(--text); padding: 16px; padding-bottom: 100px; }
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
            .logo { font-size: 20px; font-weight: 800; } .logo span { color: var(--accent); }
            .step-card { background: var(--card); border-radius: 16px; padding: 20px; margin-bottom: 16px; border: 1px solid #2a2a2a; }
            .step-header { display: flex; align-items: center; margin-bottom: 16px; font-size: 16px; font-weight: 600; }
            .step-number { background: #333; color: var(--muted); width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; margin-right: 10px; }
            .input-text { width: 100%; padding: 14px; border-radius: 10px; border: 1px solid #333; background: #121212; color: white; margin-bottom: 10px; font-size: 14px; }
            .input-text::placeholder { color: #555; }
            .templates { display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap; }
            .tpl-btn { flex: 1; min-width: 30%; padding: 10px; background: #121212; color: var(--muted); border: 1px solid #333; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 12px; text-align: center; }
            .tpl-btn.active { background: #2a2a2a; color: var(--accent); border-color: var(--accent); }
            .btn-generate { background: var(--accent); color: var(--accent-txt); border: none; width: 100%; padding: 16px; border-radius: 12px; font-size: 16px; font-weight: 700; cursor: pointer; margin-bottom: 10px; }
            .btn-secondary { background: #333; color: #fff; border: none; width: 100%; padding: 12px; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; margin-bottom: 15px; }
            .dynamic-fields { display: none; margin-top: 15px; padding-top: 15px; border-top: 1px solid #333; }
            .dynamic-fields.active { display: block; }
            .status-text { font-size: 13px; color: var(--accent); text-align: center; margin-top: 10px; }
            .disclaimer { font-size: 11px; color: #777; text-align: center; margin-top: 20px; line-height: 1.4; padding: 0 10px; }
            .service-row { display: flex; gap: 8px; margin-bottom: 8px; align-items: center; }
            .service-row input { margin-bottom: 0; padding: 10px; font-size: 12px;}
            .input-name { flex: 3; }
            .input-unit { flex: 1; min-width: 50px; }
            .input-qty { flex: 1; min-width: 45px; }
            .input-price { flex: 2; }
            .btn-remove { background: #ff2a75; color: white; border: none; border-radius: 8px; padding: 10px; cursor: pointer; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="header"><div class="logo">Gen<span>Doc</span></div></div>

        <div id="profileSection" class="step-card">
            <div class="step-header"><div class="step-number">1</div>Профиль компании</div>
            <input type="text" id="companyInput" class="input-text" placeholder="Название компании" value='ООО "Тест"'>
            <div style="display: flex; gap: 10px;">
                <input type="text" id="innInput" class="input-text" placeholder="ИНН" value="1234567890">
                <button class="btn-secondary" style="width: auto; white-space: nowrap; margin-bottom: 10px;" onclick="fetchCompanyData()">Найти по ИНН</button>
            </div>
            <input type="text" id="addressInput" class="input-text" placeholder="Юридический адрес" value="123456, г. Москва, ул. Ленина, д. 1">
            <input type="text" id="contactInput" class="input-text" placeholder="Контакты" value="+7 999 999-99-99">
            <button class="btn-generate" id="btnSaveProfile" style="background: #444;">Сохранить профиль</button>
        </div>

        <div id="generateSection" class="step-card">
            <div class="step-header"><div class="step-number">2</div>Данные документа</div>
            <div class="templates">
                <button class="tpl-btn active" onclick="setTemplate('kp', this)">КП</button>
                <button class="tpl-btn" onclick="setTemplate('smeta', this)">Смета</button>
                <button class="tpl-btn" onclick="setTemplate('dogovor', this)">Договор</button>
                <button class="tpl-btn" onclick="setTemplate('act', this)">Акт</button>
                <button class="tpl-btn" onclick="setTemplate('invoice', this)">Счет</button>
            </div>

            <div id="servicesContainer">
                <div class="service-row">
                    <input type="text" class="input-text input-name" placeholder="Услуга" value='Транспортировка груза'>
                    <input type="text" class="input-text input-unit" placeholder="Ед." value="рейс">
                    <input type="text" class="input-text input-qty" placeholder="Кол-во" value="1">
                    <input type="text" class="input-text input-price" placeholder="Цена" value="10000">
                    <button class="btn-remove" onclick="removeService(this)">×</button>
                </div>
            </div>
            <button class="btn-secondary" onclick="addService()" style="margin-top: 5px;">+ Добавить услугу</button>
            <input type="text" id="termInput" class="input-text" placeholder="Сроки" value="1 рейс" style="margin-top: 10px;">

            <div id="dogovorFields" class="dynamic-fields">
                <input type="text" id="dogovorNumber" class="input-text" placeholder="Номер договора" value="б/н">
                <input type="text" id="dogovorDate" class="input-text" placeholder="Дата договора" value="12.11.2026">
                <input type="text" id="customerName" class="input-text" placeholder="Наименование Заказчика" value='ООО "Заказчик"'>
                <input type="text" id="customerInn" class="input-text" placeholder="ИНН Заказчика" value="0987654321">
            </div>

            <div id="smetaFields" class="dynamic-fields">
                <input type="text" id="smetaNumber" class="input-text" placeholder="Номер договора" value="б/н">
                <input type="text" id="smetaDate" class="input-text" placeholder="Дата документа" value="12.11.2026">
            </div>

            <button class="btn-generate" id="btnGenerateDoc" style="margin-top: 15px;">Создать документ 📄</button>
            <div class="disclaimer">⚠️ <b>Внимание!</b> Бот использует шаблоны и может допускать ошибки. Обязательно проверяйте итоговый файл.</div>
            <div class="status-text" id="statusText"></div>
        </div>

        <script>
            const tg = window.Telegram.WebApp; tg.expand(); tg.setHeaderColor('#121212');
            const chatId = tg.initDataUnsafe?.user?.id;
            const statusText = document.getElementById('statusText');
            let currentTemplate = 'kp';

            function addService() {
                const container = document.getElementById('servicesContainer');
                const row = document.createElement('div');
                row.className = 'service-row';
                row.innerHTML = `<input type="text" class="input-text input-name" placeholder="Наименование" value=""><input type="text" class="input-text input-unit" placeholder="Ед." value="шт"><input type="text" class="input-text input-qty" placeholder="Кол-во" value="1"><input type="text" class="input-text input-price" placeholder="Цена" value=""><button class="btn-remove" onclick="removeService(this)">×</button>`;
                container.appendChild(row);
            }
            function removeService(btn) { if (document.querySelectorAll('.service-row').length > 1) btn.parentElement.remove(); }

            async function loadProfile() {
                if (!chatId) return;
                try {
                    const res = await fetch(`/get-profile?chat_id=${chatId}`);
                    const data = await res.json();
                    if (data.status === "ok") {
                        document.getElementById('companyInput').value = data.company;
                        document.getElementById('innInput').value = data.inn;
                        document.getElementById('addressInput').value = data.address;
                        document.getElementById('contactInput').value = data.contacts;
                    }
                } catch (e) {}
            }
            loadProfile();

            async function fetchCompanyData() {
                const inn = document.getElementById('innInput').value;
                if (inn.length < 10) { alert("Введите корректный ИНН"); return; }
                const btn = event.target; btn.textContent = "Поиск...";
                try {
                    const res = await fetch(`https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party`, {
                        method: 'POST', headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': 'Token 03b8cf0f4550f0c15403feb88d0eb58bfba8af06' },
                        body: JSON.stringify({ query: inn })
                    });
                    const data = await res.json();
                    if (data.suggestions && data.suggestions.length > 0) {
                        const comp = data.suggestions[0].data;
                        document.getElementById('companyInput').value = comp.name.short_with_opf;
                        document.getElementById('addressInput').value = comp.address ? comp.address.value : "";
                    } else { alert("Компания не найдена"); }
                } catch (e) { alert("Ошибка при поиске ИНН."); } finally { btn.textContent = "Найти по ИНН"; }
            }

            function setTemplate(tpl, btn) {
                currentTemplate = tpl;
                document.querySelectorAll('.tpl-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                document.querySelectorAll('.dynamic-fields').forEach(b => b.classList.remove('active'));
                if (tpl === 'dogovor') document.getElementById('dogovorFields').classList.add('active');
                if (tpl === 'smeta' || tpl === 'act' || tpl === 'invoice') document.getElementById('smetaFields').classList.add('active');
            }

            document.getElementById('btnSaveProfile').addEventListener('click', async () => {
                const btn = document.getElementById('btnSaveProfile'); btn.textContent = "Сохранение...";
                const fd = new FormData();
                fd.append('chat_id', chatId); fd.append('company', document.getElementById('companyInput').value);
                fd.append('inn', document.getElementById('innInput').value);
                fd.append('address', document.getElementById('addressInput').value); fd.append('contacts', document.getElementById('contactInput').value);
                try {
                    const res = await fetch('/save-profile', { method: 'POST', body: fd });
                    if (res.ok) { btn.textContent = "Сохранено!"; setTimeout(() => btn.textContent = "Сохранить профиль", 2000); } else { btn.textContent = "Ошибка сервера"; }
                } catch (e) { btn.textContent = "Ошибка сети"; }
            });

            document.getElementById('btnGenerateDoc').addEventListener('click', async () => {
                const btn = document.getElementById('btnGenerateDoc'); btn.disabled = true; btn.textContent = "Отправка..."; statusText.textContent = "Генерация...";
                
                const services = [];
                document.querySelectorAll('.service-row').forEach(row => {
                    const name = row.querySelector('.input-name').value;
                    const unit = row.querySelector('.input-unit').value;
                    const qty = row.querySelector('.input-qty').value;
                    const price = row.querySelector('.input-price').value;
                    if (name && price) services.push({ name, unit, qty, price });
                });
                if (services.length === 0) { tg.showAlert("Добавьте хотя бы одну услугу!"); btn.disabled = false; btn.textContent = "Создать документ 📄"; return; }

                const fd = new FormData();
                fd.append('chat_id', chatId); fd.append('template', currentTemplate);
                fd.append('company', document.getElementById('companyInput').value); fd.append('inn', document.getElementById('innInput').value);
                fd.append('address', document.getElementById('addressInput').value); fd.append('contacts', document.getElementById('contactInput').value);
                fd.append('term', document.getElementById('termInput').value); fd.append('services_json', JSON.stringify(services));

                if (currentTemplate === 'dogovor') {
                    fd.append('dogovor_number', document.getElementById('dogovorNumber').value); fd.append('dogovor_date', document.getElementById('dogovorDate').value);
                    fd.append('customer_name', document.getElementById('customerName').value); fd.append('customer_inn', document.getElementById('customerInn').value);
                }
                if (currentTemplate === 'smeta' || currentTemplate === 'act' || currentTemplate === 'invoice') {
                    fd.append('dogovor_number', document.getElementById('smetaNumber').value); fd.append('smeta_date', document.getElementById('smetaDate').value);
                }

                try {
                    const res = await fetch('/generate-doc', { method: 'POST', body: fd });
                    if (res.ok) { tg.showAlert("Документ отправлен в чат!"); statusText.textContent = "Готово!"; } else { statusText.textContent = "Ошибка сервера."; }
                } catch (e) { statusText.textContent = "Ошибка сети."; } finally { btn.disabled = false; btn.textContent = "Создать документ 📄"; }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/get-profile")
async def get_profile(chat_id: str):
    db = SessionLocal()
    profile = db.query(Profile).filter(Profile.chat_id == chat_id).first()
    db.close()
    if profile:
        return {"status": "ok", "company": profile.company, "inn": profile.inn, "address": profile.address, "contacts": profile.contacts}
    return {"status": "not_found"}

@app.post("/save-profile")
async def save_profile(
    chat_id: str = Form(...), company: str = Form(""), inn: str = Form(""), address: str = Form(""), contacts: str = Form("")
):
    db = SessionLocal()
    try:
        profile = db.query(Profile).filter(Profile.chat_id == chat_id).first()
        if profile:
            profile.company, profile.inn, profile.address, profile.contacts = company, inn, address, contacts
        else:
            db.add(Profile(chat_id=chat_id, company=company, inn=inn, address=address, contacts=contacts))
        db.commit()
        return {"status": "ok"}
    except Exception as e: 
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
    finally: 
        db.close()

@app.post("/generate-doc")
async def generate_doc(
    template: str = Form("kp"), company: str = Form(""), inn: str = Form(""), address: str = Form(""), contacts: str = Form(""),
    services_json: str = Form("[]"), term: str = Form(""), dogovor_number: str = Form(""), dogovor_date: str = Form(""), 
    customer_name: str = Form(""), customer_inn: str = Form(""), smeta_date: str = Form(""), chat_id: str = Form(None)
):
    try:
        services = json.loads(services_json)
        total_price = sum(float(s['price']) * int(s['qty']) for s in services)
        current_date = datetime.now().strftime("%d.%m.%Y")
        date_to_use = dogovor_date if dogovor_date else current_date
        smeta_date_to_use = smeta_date if smeta_date else current_date
        buffer = io.BytesIO()
        
        header_html = get_header_html(company, inn, address, contacts)

        if template == "kp":
            rows = "".join([f"<tr><td style='text-align:center;'>{i+1}</td><td>{s['name']}</td><td style='text-align:center;'>{term}</td><td style='text-align:right;'>{format_money(float(s['price'])*int(s['qty']))} руб.</td></tr>" for i, s in enumerate(services)])
            html = f"<html><head><meta charset='utf-8'><style>{CSS_STYLES}</style></head><body>{header_html}<table class='meta'><tr><td style='text-align:right;'>Исх. № {dogovor_number} от {date_to_use} г.</td></tr></table><h1 class='title'>Коммерческое предложение</h1><table><tr><th style='text-align:center; width: 5%;'>№</th><th style='width: 50%;'>Наименование</th><th style='text-align:center; width: 15%;'>Срок</th><th style='text-align:right; width: 20%;'>Стоимость</th></tr>{rows}</table><p style='text-align:right; margin-top: 10px;'><strong>Итого: {format_money(total_price)} руб.</strong></p></body></html>"
            pisa.CreatePDF(html, dest=buffer)
            
        elif template == "smeta":
            rows = "".join([f"<tr><td style='text-align:center;'>{i+1}</td><td>{s['name']}</td><td style='text-align:center;'>{s.get('unit', 'усл.')}</td><td style='text-align:center;'>{s['qty']}</td><td style='text-align:right;'>{format_money(float(s['price']))}</td><td style='text-align:right;'>{format_money(float(s['price'])*int(s['qty']))}</td></tr>" for i, s in enumerate(services)])
            html = f"<html><head><meta charset='utf-8'><style>{CSS_STYLES}</style></head><body><table class='meta'><tr><td style='text-align:right;'>Приложение к Договору № {dogovor_number} от {smeta_date_to_use}</td></tr></table><h1 class='title'>Смета</h1><table><tr><th>№</th><th>Наименование</th><th>Ед.</th><th>Кол-во</th><th>Цена</th><th>Сумма</th></tr>{rows}</table></body></html>"
            pisa.CreatePDF(html, dest=buffer)
            
        elif template == "dogovor":
             html = f"<html><head><meta charset='utf-8'><style>{CSS_STYLES}</style></head><body><h1 class='title'>ДОГОВОР № {dogovor_number}</h1><p>{company}, в лице директора, с одной стороны, и {customer_name} (ИНН {customer_inn}), с другой стороны, заключили договор на сумму {format_money(total_price)} руб.</p></body></html>"
             pisa.CreatePDF(html, dest=buffer)
             
        elif template == "act":
             html = f"<html><head><meta charset='utf-8'><style>{CSS_STYLES}</style></head><body><h1 class='title'>АКТ № {dogovor_number}</h1><p>Услуги выполнены на сумму {format_money(total_price)} руб.</p></body></html>"
             pisa.CreatePDF(html, dest=buffer)
             
        elif template == "invoice":
             html = f"<html><head><meta charset='utf-8'><style>{CSS_STYLES}</style></head><body><h1 class='title'>СЧЕТ № {dogovor_number}</h1><p>К оплате: {format_money(total_price)} руб.</p></body></html>"
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
