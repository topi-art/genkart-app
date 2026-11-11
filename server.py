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

# СЛОВАРЬ ФОНОВ (ключ = имя, значение = имя файла на GitHub)
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
    background: str = Form("bg1"), # Выбор фона
    font_style: str = Form("sans"),
    font_size: str = Form("normal"),
    chat_id: str = Form(None)
):
    image_data = await file.read()
    img = Image.open(io.BytesIO(image_data)).convert("RGBA")
    
    # 1. Загружаем выбранный фон
    bg_filename = BACKGROUNDS.get(background, "Screenshot_20261111_135917_Pinterest.jpg")
    try:
        bg = Image.open(bg_filename).convert("RGBA")
        bg = bg.resize((1080, 1080))
    except:
        bg = Image.new("RGB", (1080, 1080), (245, 245, 247))

    draw = ImageDraw.Draw(bg)
    
    # 2. Настройка шрифтов
    font_paths = {"sans": "DejaVuSans-Bold.ttf", "serif": "DejaVuSerif-Bold.ttf"}
    font_path = font_paths.get(font_style, "DejaVuSans-Bold.ttf")
    sizes = {"small": 40, "normal": 60, "large": 80}
    title_size = sizes.get(font_size, 60)
    
    try:
        font_title = ImageFont.truetype(font_path, title_size)
    except:
        font_title = ImageFont.load_default()

    # 3. Вставляем товар (с маской-кругом, чтобы смотрелось как на подиуме)
    img.thumbnail((700, 700))
    mask = Image.new("L", img.size, 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0, img.width, img.height), fill=255)
    
    x = (1080 - img.width) // 2
    y = (1080 - img.height) // 2 + 50
    
    bg.paste(img, (x, y), mask)
    
    # 4. Добавляем текст
    # Для контраста на разных фонах используем белый или черный цвет (пока белый)
    draw.text((80, 80), title, fill=(255, 255, 255), font=font_title)
    draw.text((80, 160), subtitle, fill=(200, 200, 200), font=font_title)

    # 5. Сохраняем и отправляем
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
