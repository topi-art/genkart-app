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

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Бэкенд работает!"}

@app.post("/generate-card")
async def generate_card(
    file: UploadFile = File(...), 
    title: str = Form("Название"), 
    subtitle: str = Form("Описание"),
    template: str = Form("template1"),
    font_style: str = Form("sans"),
    font_size: str = Form("normal"),
    chat_id: str = Form(None)
):
    image_data = await file.read()
    img = Image.open(io.BytesIO(image_data)).convert("RGBA")
    
    bg = Image.new("RGB", (1080, 1080), (245, 245, 247))
    draw = ImageDraw.Draw(bg)
    
    # Выбор шрифта
    font_paths = {
        "sans": "DejaVuSans-Bold.ttf",
        "serif": "DejaVuSerif-Bold.ttf",
        "mono": "DejaVuSansMono-Bold.ttf"
    }
    font_path = font_paths.get(font_style, "DejaVuSans-Bold.ttf")
    
    # Выбор размера
    sizes = {"small": 40, "normal": 60, "large": 80}
    title_size = sizes.get(font_size, 60)
    sub_size = title_size - 20 if title_size > 40 else 30

    try:
        font_title = ImageFont.truetype(font_path, title_size)
        font_sub = ImageFont.truetype(font_path, sub_size)
    except:
        try:
            font_title = ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{font_path}", title_size)
            font_sub = ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{font_path}", sub_size)
        except:
            font_title = ImageFont.load_default()
            font_sub = ImageFont.load_default()

    if template == "template1":
        img.thumbnail((700, 700))
        x = (1080 - img.width) // 2
        y = (1080 - img.height) // 2 + 50
        draw.rectangle([(0, 0), (1080, 200)], fill=(255, 255, 255))
        draw.text((80, 50), title, fill=(30, 30, 30), font=font_title)
        draw.text((80, 130), subtitle, fill=(100, 100, 100), font=font_sub)
        shadow = Image.new("RGBA", (img.width + 40, img.height + 40), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).ellipse((20, 20, img.width + 20, img.height + 20), fill=(0, 0, 0, 80))
        shadow = shadow.filter(ImageFilter.GaussianBlur(15))
        bg.paste(shadow, (x - 20, y + 10), shadow)
        bg.paste(img, (x, y), img)

    elif template == "template2":
        img.thumbnail((600, 600))
        x = 1080 - img.width - 50
        y = (1080 - img.height) // 2
        draw.rounded_rectangle([(40, 250), (500, 750)], radius=30, fill=(255, 255, 255, 230))
        draw.text((80, 300), title, fill=(30, 30, 30), font=font_title)
        draw.text((80, 400), subtitle, fill=(100, 100, 100), font=font_sub)
        shadow = Image.new("RGBA", (img.width + 40, img.height + 40), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).ellipse((20, 20, img.width + 20, img.height + 20), fill=(0, 0, 0, 80))
        shadow = shadow.filter(ImageFilter.GaussianBlur(15))
        bg.paste(shadow, (x - 20, y + 10), shadow)
        bg.paste(img, (x, y), img)

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
