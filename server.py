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
    return {"status": "ok", "message": "Бэкенд работает!"}

@app.post("/generate-card")
async def generate_card(
    file: UploadFile = File(...), 
    title: str = Form("Название"), 
    subtitle: str = Form("Описание"),
    template: str = Form("template1") # Принимаем выбор шаблона
):
    image_data = await file.read()
    img = Image.open(io.BytesIO(image_data)).convert("RGBA")
    
    # 1. Создаем фон (светло-серый)
    bg = Image.new("RGB", (1080, 1080), (245, 245, 247))
    draw = ImageDraw.Draw(bg)
    
    # 2. Пытаемся загрузить красивые шрифты (если их нет, берем стандарт)
    try:
        font_title = ImageFont.truetype("arial.ttf", 60)
        font_sub = ImageFont.truetype("arial.ttf", 40)
    except:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # 3. Логика шаблонов
    if template == "template1":
        # Шаблон 1: Классика (Товар по центру, текст сверху)
        img.thumbnail((700, 700))
        x = (1080 - img.width) // 2
        y = (1080 - img.height) // 2 + 50
        
        # Подложка сверху
        draw.rectangle([(0, 0), (1080, 200)], fill=(255, 255, 255))
        draw.text((80, 50), title, fill=(30, 30, 30), font=font_title)
        draw.text((80, 130), subtitle, fill=(100, 100, 100), font=font_sub)
        
        # Тень и товар
        shadow = Image.new("RGBA", (img.width + 40, img.height + 40), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).ellipse((20, 20, img.width + 20, img.height + 20), fill=(0, 0, 0, 80))
        shadow = shadow.filter(ImageFilter.GaussianBlur(15))
        bg.paste(shadow, (x - 20, y + 10), shadow)
        bg.paste(img, (x, y), img)

    elif template == "template2":
        # Шаблон 2: Асимметрия (Товар справа, текст слева на плашке)
        img.thumbnail((600, 600))
        x = 1080 - img.width - 50
        y = (1080 - img.height) // 2
        
        # Подложка слева (скругленная)
        draw.rounded_rectangle([(40, 250), (500, 750)], radius=30, fill=(255, 255, 255, 230))
        draw.text((80, 300), title, fill=(30, 30, 30), font=font_title)
        draw.text((80, 400), subtitle, fill=(100, 100, 100), font=font_sub)
        
        # Тень и товар
        shadow = Image.new("RGBA", (img.width + 40, img.height + 40), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).ellipse((20, 20, img.width + 20, img.height + 20), fill=(0, 0, 0, 80))
        shadow = shadow.filter(ImageFilter.GaussianBlur(15))
        bg.paste(shadow, (x - 20, y + 10), shadow)
        bg.paste(img, (x, y), img)

    # 4. Сохраняем и отправляем
    img_byte_arr = io.BytesIO()
    bg.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    return StreamingResponse(img_byte_arr, media_type="image/png")
