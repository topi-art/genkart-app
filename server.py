
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Бэкенд ГенКарт работает!"}

@app.post("/generate-card")
async def generate_card(file: UploadFile = File(...), title: str = Form("Название"), subtitle: str = Form("Описание")):
    # 1. Читаем фото
    image_data = await file.read()
    img = Image.open(io.BytesIO(image_data)).convert("RGBA")
    
    # 2. Создаем фон (градиент)
    bg = Image.new("RGB", (1080, 1080), (240, 240, 245))
    draw = ImageDraw.Draw(bg)
    for y in range(1080):
        color = int(240 - (y / 1080) * 30)
        draw.line([(0, y), (1080, y)], fill=(color, color, color + 5))
    
    # 3. Накладываем тень (эффект объема)
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.ellipse((0, 0, img.width, img.height), fill=(0, 0, 0, 100))
    shadow = shadow.filter(ImageFilter.GaussianBlur(20))
    
    # 4. Вставляем товар
    img.thumbnail((800, 800))
    x = (1080 - img.width) // 2
    y = (1080 - img.height) // 2 + 50
    
    # Рисуем тень под товаром
    bg.paste(shadow, (x, y + 20), shadow)
    # Рисуем сам товар
    bg.paste(img, (x, y), img)
    
    # 5. Добавляем текст
    try:
        font_title = ImageFont.truetype("arial.ttf", 60)
        font_sub = ImageFont.truetype("arial.ttf", 40)
    except:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        
    draw.text((100, 100), title, fill=(40, 40, 40), font=font_title)
    draw.text((100, 180), subtitle, fill=(100, 100, 100), font=font_sub)
    
    # 6. Отправляем результат
    img_byte_arr = io.BytesIO()
    bg.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    return StreamingResponse(img_byte_arr, media_type="image/png")
