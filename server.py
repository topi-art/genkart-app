
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from rembg import remove
import io
import math
import numpy as np
import moviepy.editor as mpy

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

# --- ФУНКЦИЯ ДЛЯ СОЗДАНИЯ КАРТОЧКИ ---
@app.post("/generate-card")
async def generate_card(file: UploadFile = File(...), title: str = Form("Название товара"), subtitle: str = Form("Описание")):
    # 1. Читаем загруженное фото
    input_image = Image.open(io.BytesIO(await file.read()))
    
    # 2. Удаляем фон (используем rembg)
    output_image = remove(input_image)
    
    # 3. Создаем фон для карточки (светло-серый градиент, как на вашем примере)
    bg = Image.new("RGB", (1080, 1080), (245, 245, 245))
    draw = ImageDraw.Draw(bg)
    
    # 4. Вставляем вырезанный товар на фон
    # Уменьшаем товар, если он слишком большой
    output_image.thumbnail((800, 800))
    # Центрируем
    x = (1080 - output_image.width) // 2
    y = (1080 - output_image.height) // 2 + 100
    bg.paste(output_image, (x, y), output_image)
    
    # 5. Добавляем текст (пока используем стандартный шрифт, позже можем загрузить красивый)
    # Заголовок
    draw.text((100, 100), title, fill=(50, 50, 50))
    # Подзаголовок
    draw.text((100, 150), subtitle, fill=(100, 100, 100))
    
    # 6. Сохраняем результат в память и отправляем клиенту
    img_byte_arr = io.BytesIO()
    bg.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    return StreamingResponse(img_byte_arr, media_type="image/png")

# --- ФУНКЦИЯ ДЛЯ СОЗДАНИЯ ВИДЕО (АНИМАЦИЯ) ---
@app.post("/generate-video")
async def generate_video(file: UploadFile = File(...)):
    input_image = Image.open(io.BytesIO(await file.read()))
    output_image = remove(input_image)
    
    # Создаем чистый фон для видео
    bg = Image.new("RGB", (1080, 1080), (245, 245, 245))
    output_image.thumbnail((800, 800))
    x = (1080 - output_image.width) // 2
    y = (1080 - output_image.height) // 2
    bg.paste(output_image, (x, y), output_image)
    
    # Сохраняем промежуточную картинку для moviepy
    temp_img_path = "/tmp/temp_card.png"
    bg.save(temp_img_path)
    
    # Создаем анимацию (зум и легкое покачивание)
    clip = mpy.ImageClip(temp_img_path).set_duration(3)
    # Эффект приближения
    clip = clip.resize(lambda t: 1 + 0.1 * t)
    
    # Сохраняем видео в память
    video_byte_arr = io.BytesIO()
    clip.write_videofile("/tmp/output.mp4", fps=24, codec="libx264", audio=False)
    
    with open("/tmp/output.mp4", "rb") as f:
        video_byte_arr.write(f.read())
    video_byte_arr.seek(0)
    
    return StreamingResponse(video_byte_arr, media_type="video/mp4")
