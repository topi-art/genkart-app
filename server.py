from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import requests
import numpy as np

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BOT_TOKEN = "9195903180:AAGSvvim9LlwkYhCCNRoFk_e09OQ_Fyh_58" 

# ВСЕ 10 ФОНОВ
BACKGROUNDS = {
    "bg1": "Screenshot_20261111_185802_Pinterest.jpg", # Белые облака
    "bg2": "Screenshot_20261111_190005_Pinterest.jpg", # Лента
    "bg3": "Screenshot_20261111_185931_Pinterest.jpg", # Травертин
    "bg4": "Screenshot_20261111_190043_Pinterest.jpg", # Бордовая ткань
    "bg5": "Screenshot_20261111_190100_Pinterest.jpg", # Жидкое стекло
    "bg6": "Screenshot_20261111_185352_Pinterest.jpg", # Пузыри
    "bg7": "Screenshot_20261111_185847_Pinterest.jpg", # Розовые облака
    "bg8": "Screenshot_20261111_185912_Pinterest.jpg", # Скалы
    "bg9": "Screenshot_20261111_190025_Pinterest.jpg", # Розовая ткань
    "bg10": "Screenshot_20261111_185521_Pinterest.jpg" # Оливковый подиум
}

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Бэкенд работает!"}

@app.post("/generate-card")
async def generate_card(
    file: UploadFile = File(...), 
    title: str = Form("Название"), 
    subtitle: str = Form("Описание"),
    features: str = Form(""),
    background: str = Form("bg1"),
    template: str = Form("template1"),
    size: str = Form("medium"),
    rotation: str = Form("none"),
    font_style: str = Form("sans"),
    font_size: str = Form("normal"),
    is_video: bool = Form(False),
    chat_id: str = Form(None)
):
    image_data = await file.read()
    
    # 1. УДАЛЯЕМ ФОН
    product_img = None
    try:
        response = requests.post(
            'https://api.nobg.akshit.io/api/v1/remove-background',
            files={'image': ('image.jpg', image_data, 'image/jpeg')},
            timeout=25
        )
        if response.status_code == 200:
            product_img = Image.open(io.BytesIO(response.content)).convert("RGBA")
    except Exception as e:
        print(f"ОШИБКА NOBG: {e}")

    if not product_img:
        product_img = Image.open(io.BytesIO(image_data)).convert("RGBA")

    # 2. ПОВОРОТ ТОВАРА
    if rotation == "left":
        product_img = product_img.rotate(15, expand=True, resample=Image.BICUBIC)
    elif rotation == "right":
        product_img = product_img.rotate(-15, expand=True, resample=Image.BICUBIC)

    # 3. Фон
    bg_filename = BACKGROUNDS.get(background, BACKGROUNDS["bg1"])
    try:
        bg = Image.open(bg_filename).convert("RGBA")
        bg = bg.resize((1080, 1080))
    except:
        bg = Image.new("RGB", (1080, 1080), (245, 245, 247))

    # 4. Шрифты
    font_paths = {"sans": "DejaVuSans-Bold.ttf", "serif": "DejaVuSerif-Bold.ttf"}
    font_path = font_paths.get(font_style, "DejaVuSans-Bold.ttf")
    sizes = {"small": 40, "normal": 60, "large": 80}
    title_size = sizes.get(font_size, 60)
    sub_size = title_size - 20 if title_size > 40 else 30
    features_size = 30
    
    try:
        font_title = ImageFont.truetype(font_path, title_size)
        font_sub = ImageFont.truetype(font_path, sub_size)
        font_features = ImageFont.truetype(font_path, features_size)
    except:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_features = ImageFont.load_default()

    draw = ImageDraw.Draw(bg)

    # 5. РАЗМЕР ТОВАРА
    if size == "small":
        product_img.thumbnail((500, 500))
    elif size == "large":
        product_img.thumbnail((900, 900))
    else:
        product_img.thumbnail((700, 700))

    # 6. ЛОГИКА РАЗМЕЩЕНИЯ
    if template == "template1": # Сверху
        x = (1080 - product_img.width) // 2 
        y = 400
        title_bbox = draw.textbbox((0, 0), title, font=font_title)
        draw.text(((1080 - (title_bbox[2] - title_bbox[0])) // 2, 80), title, fill=(30, 30, 30), font=font_title)
        sub_bbox = draw.textbbox((0, 0), subtitle, font=font_sub)
        draw.text(((1080 - (sub_bbox[2] - sub_bbox[0])) // 2, 160), subtitle, fill=(100, 100, 100), font=font_sub)

    elif template == "template2": # Слева
        x = 1080 - product_img.width - 50
        y = 400
        draw.text((80, 300), title, fill=(255, 255, 255), font=font_title)
        draw.text((80, 400), subtitle, fill=(200, 200, 200), font=font_sub)

    elif template == "template3": # Справа
        x = 50
        y = 400
        draw.text((550, 300), title, fill=(255, 255, 255), font=font_title)
        draw.text((550, 400), subtitle, fill=(200, 200, 200), font=font_sub)

    elif template == "template4": # Инфографика
        x = 1080 - product_img.width - 50
        y = 400
        draw.text((80, 150), title, fill=(255, 255, 255), font=font_title)
        draw.text((80, 250), subtitle, fill=(200, 200, 200), font=font_sub)
        if features:
            feature_lines = features.split('\n')
            for i, line in enumerate(feature_lines[:4]):
                cy = 350 + i * 80
                draw.text((80, cy), line, fill=(255, 255, 255), font=font_features)

    # 7. ТЕНЬ И ТОВАР
    if not is_video:
        if template in ["template1", "template2", "template3"]:
            shadow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow)
            shadow_bbox = (x + 20, y + product_img.height - 30, x + product_img.width - 20, y + product_img.height + 30)
            shadow_draw.ellipse(shadow_bbox, fill=(0, 0, 0, 100))
            shadow = shadow.filter(ImageFilter.GaussianBlur(15))
            bg.paste(shadow, (0, 0), shadow)
        bg.paste(product_img, (x, y), product_img)
        
        img_byte_arr = io.BytesIO()
        bg.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        media_type = "image/png"
        filename = "card.png"

    # 8. ГЕНЕРАЦИЯ ВИДЕО (GIF)
    else:
        frames = []
        angles = np.linspace(-25, 25, 30)
        
        for angle in angles:
            frame = bg.copy()
            rotated_product = product_img.rotate(angle, expand=True, resample=Image.BICUBIC)
            
            rx = x + (product_img.width - rotated_product.width) // 2
            ry = y + (product_img.height - rotated_product.height) // 2
            
            if template in ["template1", "template2", "template3"]:
                shadow = Image.new("RGBA", frame.size, (0, 0, 0, 0))
                shadow_draw = ImageDraw.Draw(shadow)
                shadow_bbox = (rx + 20, ry + rotated_product.height - 30, rx + rotated_product.width - 20, ry + rotated_product.height + 30)
                shadow_draw.ellipse(shadow_bbox, fill=(0, 0, 0, 100))
                shadow = shadow.filter(ImageFilter.GaussianBlur(15))
                frame.paste(shadow, (0, 0), shadow)
                
            frame.paste(rotated_product, (rx, ry), rotated_product)
            frames.append(frame)

        img_byte_arr = io.BytesIO()
        frames[0].save(
            img_byte_arr,
            format='GIF',
            save_all=True,
            append_images=frames[1:],
            duration=100,
            loop=0
        )
        img_byte_arr.seek(0)
        media_type = "image/gif"
        filename = "card.gif"

    # 9. Отправка в Telegram
    if chat_id:
        if is_video:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendAnimation"
            files = {'animation': (filename, img_byte_arr.getvalue(), media_type)}
        else:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            files = {'document': (filename, img_byte_arr.getvalue(), media_type)}
            
        data = {'chat_id': chat_id, 'caption': 'Ваша карточка готова!'}
        try:
            requests.post(url, files=files, data=data)
        except Exception as e:
            print(f"ОШИБКА: {e}")
        img_byte_arr.seek(0)
    
    return StreamingResponse(img_byte_arr, media_type=media_type)
