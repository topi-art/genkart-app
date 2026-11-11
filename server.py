from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import requests
from rembg import remove

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BOT_TOKEN = "9195903180:AAGSvvim9LlwkYhCCNRoFk_e09OQ_Fyh_58" 

BACKGROUNDS = {
    "bg1": {"file": "Screenshot_20261111_135917_Pinterest.jpg", "x": 350, "y": 450},
    "bg2": {"file": "Screenshot_20261111_140017_Pinterest.jpg", "x": 350, "y": 450},
    "bg3": {"file": "Screenshot_20261111_140026_Pinterest.jpg", "x": 350, "y": 400},
    "bg4": {"file": "Screenshot_20261111_140051_Pinterest.jpg", "x": 350, "y": 450}
}

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Бэкенд работает!"}

@app.post("/generate-card")
async def generate_card(
    file: UploadFile = File(...), 
    title: str = Form("Название"), 
    subtitle: str = Form("Описание"),
    background: str = Form("bg1"),
    template: str = Form("template1"),
    font_style: str = Form("sans"),
    font_size: str = Form("normal"),
    chat_id: str = Form(None)
):
    image_data = await file.read()
    
    # 1. УДАЛЯЕМ ФОН ПРЯМО НА СЕРВЕРЕ (облегченная модель)
    try:
        product_img = remove(image_data)
        product_img = Image.open(io.BytesIO(product_img)).convert("RGBA")
    except Exception as e:
        print(f"ОШИБКА REMBG: {e}")
        product_img = Image.open(io.BytesIO(image_data)).convert("RGBA")

    # 2. Загружаем фон и координаты
    bg_info = BACKGROUNDS.get(background, BACKGROUNDS["bg1"])
    try:
        bg = Image.open(bg_info["file"]).convert("RGBA")
        bg = bg.resize((1080, 1080))
    except:
        bg = Image.new("RGB", (1080, 1080), (245, 245, 247))

    # 3. Шрифты
    font_paths = {"sans": "DejaVuSans-Bold.ttf", "serif": "DejaVuSerif-Bold.ttf"}
    font_path = font_paths.get(font_style, "DejaVuSans-Bold.ttf")
    sizes = {"small": 40, "normal": 60, "large": 80}
    title_size = sizes.get(font_size, 60)
    sub_size = title_size - 20 if title_size > 40 else 30
    
    try:
        font_title = ImageFont.truetype(font_path, title_size)
        font_sub = ImageFont.truetype(font_path, sub_size)
    except:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    draw = ImageDraw.Draw(bg)

    # 4. Товар и его позиция
    product_img.thumbnail((500, 500))
    x = bg_info["x"]
    y = bg_info["y"]

    # 5. Логика шаблонов текста
    if template == "template1":
        draw.rectangle([(0, 0), (1080, 200)], fill=(255, 255, 255, 200))
        draw.text((80, 50), title, fill=(30, 30, 30), font=font_title)
        draw.text((80, 130), subtitle, fill=(100, 100, 100), font=font_sub)

    elif template == "template2":
        draw.rounded_rectangle([(40, 250), (500, 750)], radius=30, fill=(255, 255, 255, 230))
        draw.text((80, 300), title, fill=(30, 30, 30), font=font_title)
        draw.text((80, 400), subtitle, fill=(100, 100, 100), font=font_sub)

    elif template == "template3":
        draw.text((60, 150), title, fill=(30, 30, 30), font=font_title)
        draw.text((60, 250), subtitle, fill=(100, 100, 100), font=font_sub)
        for i in range(3):
            cy = 350 + i * 120
            draw.ellipse([(60, cy), (120, cy + 60)], fill=(230, 230, 230))
            draw.text((150, cy + 10), "Преимущество", fill=(80, 80, 80), font=font_sub)

    # 6. Тень и товар
    shadow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_bbox = (x + 20, y + product_img.height - 50, x + product_img.width - 20, y + product_img.height + 50)
    shadow_draw.ellipse(shadow_bbox, fill=(0, 0, 0, 120))
    shadow = shadow.filter(ImageFilter.GaussianBlur(20))
    
    bg.paste(shadow, (0, 0), shadow)
    bg.paste(product_img, (x, y), product_img)

    # 7. Отправка
    img_byte_arr = io.BytesIO()
    bg.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    if chat_id:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
        files = {'document': ('card.png', img_byte_arr.getvalue(), 'image/png')}
        data = {'chat_id': chat_id, 'caption': 'Ваша карточка готова!'}
        try:
            requests.post(url, files=files, data=data)
        except Exception as e:
            print(f"ОШИБКА: {e}")
        img_byte_arr.seek(0)
    
    return StreamingResponse(img_byte_arr, media_type="image/png")
