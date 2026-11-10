from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ВАЖНО: Вставьте сюда ваш АКТУАЛЬНЫЙ токен от BotFather
BOT_TOKEN = "9195903180:AAEvtP9JaGzhpbHCUQpUuDLJsAoavYw0FKU" 

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Бэкенд ГенКарт работает!"}

@app.post("/generate-card")
async def generate_card(file: UploadFile = File(...), title: str = Form("Название"), subtitle: str = Form("Описание"), chat_id: str = Form(None)):
    image_data = await file.read()
    img = Image.open(io.BytesIO(image_data)).convert("RGBA")
    
    bg = Image.new("RGB", (1080, 1080), (240, 240, 245))
    draw = ImageDraw.Draw(bg)
    for y in range(1080):
        color = int(240 - (y / 1080) * 30)
        draw.line([(0, y), (1080, y)], fill=(color, color, color + 5))
    
    img.thumbnail((800, 800))
    x = (1080 - img.width) // 2
    y = (1080 - img.height) // 2 + 50
    
    shadow = Image.new("RGBA", (img.width + 40, img.height + 40), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse((20, 20, img.width + 20, img.height + 20), fill=(0, 0, 0, 80))
    shadow = shadow.filter(ImageFilter.GaussianBlur(15))
    bg.paste(shadow, (x - 20, y + 10), shadow)
    bg.paste(img, (x, y), img)
    
    try:
        font_title = ImageFont.truetype("arial.ttf", 60)
        font_sub = ImageFont.truetype("arial.ttf", 40)
    except:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        
    draw.text((100, 100), title, fill=(40, 40, 40), font=font_title)
    draw.text((100, 180), subtitle, fill=(100, 100, 100), font=font_sub)
    
    img_byte_arr = io.BytesIO()
    bg.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    # Отправка в Telegram с проверкой
    if chat_id:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        files = {'photo': ('card.png', img_byte_arr.getvalue(), 'image/png')}
        data = {'chat_id': chat_id, 'caption': 'Ваша карточка готова!'}
        
        try:
            tg_response = requests.post(url, files=files, data=data)
            # Если Telegram вернул ошибку, выводим её в консоль Render (в логи)
            if tg_response.status_code != 200:
                print(f"ОШИБКА TELEGRAM: {tg_response.text}")
        except Exception as e:
            print(f"ОШИБКА ОТПРАВКИ: {e}")
        
        img_byte_arr.seek(0) 
    
    return StreamingResponse(img_byte_arr, media_type="image/png")
