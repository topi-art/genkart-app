from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import io
import requests

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

BOT_TOKEN = "9065574882:AAEiC0Ls-YC1ADejERPNLcZSdEJS7qCZe_I"

@app.get("/")
def read_root(): return {"status": "ok"}

@app.post("/generate-doc")
async def generate_doc(chat_id: str = Form(None)):
    try:
        buffer = io.BytesIO()
        buffer.write("Это тестовый файл. Если вы его видите, значит сервер работает, а проблема была в генерации PDF.".encode('utf-8'))
        buffer.seek(0)

        if chat_id:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            files = {'document': ('test.txt', buffer.getvalue(), 'text/plain')}
            data = {'chat_id': chat_id, 'caption': 'Тестовый файл'}
            response = requests.post(url, files=files, data=data)
            if response.status_code == 200:
                return {"status": "ok"}
            else:
                return JSONResponse(status_code=500, content={"status": "error", "message": response.text})
        return {"status": "error", "message": "Нет chat_id"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
