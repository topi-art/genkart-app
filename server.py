from fastapi import FastAPI
import requests

app = FastAPI()

# ВАШ АКТУАЛЬНЫЙ ТОКЕН
BOT_TOKEN = "9195903180:AAF_-oVZiNNNa8P0vEYutD16S1vTv8nHffk" 
YOUR_CHAT_ID = "1124115675"

@app.get("/")
def read_root():
    # Этот код выполнится, как только вы откроете ссылку сервера в браузере
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {'chat_id': YOUR_CHAT_ID, 'text': '✅ Сервер работает! Токен верный.'}
    
    try:
        response = requests.post(url, data=data)
        print(f"ОТВЕТ TELEGRAM: {response.text}") # Это появится в логах
    except Exception as e:
        print(f"ОШИБКА: {e}")
        
    return {"status": "ok"}
