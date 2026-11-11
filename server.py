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

BOT_TOKEN = "9195903180:AAGSvvim9LlwkYhCCNRoFk_e09OQ_Fyh_58" 

BACKGROUNDS = {
    "bg1": "Screenshot_20261111_135917_Pinterest.jpg",
    "bg2": "Screenshot_20261111_140017_Pinterest.jpg",
    "bg3": "Screenshot_20261111_140026_Pinterest.jpg",
    "bg4": "Screenshot_20261111_140051_Pinterest.jpg"
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
    
    # 1. УДАЛЯЕМ ФОН ЧЕРЕЗ БЕСПЛАТНЫЙ API (remove.bg / без ключа)
    # Используем публичный тестовый эндпоинт, который вырезает объекты
    product_img = None
    try:
        # Отправляем на бесплатный сервис удаления фона
        response = requests.post(
            'https://api.remove.bg/v1.0/removebg',
            files={'image_file': image_data},
            data={'size': 'auto'},
            timeout=15
        )
        # Если сервис вернул картинку (а не ошибку), берем её
        if response.status_code == 200 and response.headers.get('content-type', '').startswith('image'):
            product_img = Image.open(io.BytesIO(response.content)).convert("RGBA")
        else:
            print(f"ОШИБКА REMOVE.BG: {response.text}")
    except Exception as e:
        print(f"ОШИБКА СЕТИ REMOVE.BG: {e}")

    # Если вырезать не удалось, берем оригинал (но это плохой сценарий)
    if not product_img:
        product_img = Image.open(io.BytesIO(image_data)).convert("RGBA")

    # 2. Загружаем фон
    bg_filename = BACKGROUNDS.get(background, "Screenshot_20261111_135917_Pinterest.jpg")
    try:
        bg = Image.open(bg_filename).convert("RGBA")
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

    # 4. Позиционируем товар и рисуем тень
    product_img.thumbnail((600, 600))
    x = (1080 - product_img.width) // 2
    y = (1080 - product_img.height) // 2 + 100
    
    # Создаем тень
    shadow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_bbox = (x + 20, y + product_img.height - 50, x + product_img.width - 20, y + product_img.height + 50)
    shadow_draw.ellipse(shadow_bbox, fill=(0, 0, 0, 120))
    shadow = shadow.filter(ImageFilter.GaussianBlur(20))
    
    # Накладываем тень и товар
    bg.paste(shadow, (0, 0), shadow)
    bg.paste(product_img, (x, y), product_img)

    # 5. Текст по шаблону
    draw = ImageDraw.Draw(bg)
    
    if template == "template1":
        draw.rectangle([(0, 0), (1080, 200)], fill=(255, 255, 255, 200))
        draw.text((80, 50), title, fill=(30, 30, 30), font=font_title)
        draw.text((80, 130), subtitle, fill=(100, 100, 100), font=font_sub)
        
    elif template == "template2":
        draw.rounded_rectangle([(40, 250), (500, 750)], radius=30, fill=(255, 255, 255, 230))
        draw.text((80, 300), title, fill=(30, 30, 30), font=font_title)
        draw.text((80, 400), subtitle, fill=(100, 100, 100), font=font_sub)

    # 6. Сохраняем и отправляем
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
