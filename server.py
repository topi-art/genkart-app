from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
import json
import requests
from datetime import datetime

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- ТОКЕН СТАРОГО БОТА ---
BOT_TOKEN = "9195903180:AAGSvvim9LlwkYhCCNRoFk_e09OQ_Fyh_58"

@app.get("/")
def read_root(): return {"status": "ok"}

@app.post("/generate-doc")
async def generate_doc(
    template: str = Form("kp"), 
    company: str = Form("ООО Ваша компания"), 
    services_json: str = Form("[]"), 
    chat_id: str = Form(None)
):
    try:
        services = json.loads(services_json)
        total_price = sum(float(s['price']) * int(s['qty']) for s in services)
        
        # Формируем красивый текст
        text = f"📄 <b>Документ: {template.upper()}</b>\n\n"
        text += f"🏢 <b>Компания:</b> {company}\n"
        text += f"📅 <b>Дата:</b> {datetime.now().strftime('%d.%m.%Y')}\n\n"
        text += "📋 <b>Услуги:</b>\n"
        
        for s in services:
            amount = float(s['price']) * int(s['qty'])
            text += f"• {s['name']} | Кол-во: {s['qty']} | Сумма: {amount:,.2f} руб.\n"
            
        text += f"\n💰 <b>ИТОГО: {total_price:,.2f} руб.</b>"
        
        if chat_id:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
            
            response = requests.post(url, data=data)
            if response.status_code == 200:
                return {"status": "ok", "message": "Отправлено"}
            else:
                return {"status": "error", "message": response.text}
        return {"status": "error", "message": "Нет chat_id"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
