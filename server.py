from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import io
import json
import requests
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from xhtml2pdf import pisa
from num2words import num2words
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BOT_TOKEN = "9195903180:AAGSvvim9LlwkYhCCNRoFk_e09OQ_Fyh_58" 

def decline_fio(fio):
    if not fio: return ""
    words = fio.split()
    res = []
    for word in words:
        if word.endswith("."): res.append(word)
        elif word.endswith("а"): res.append(word[:-1] + "ы")
        elif word.endswith("я"): res.append(word[:-1] + "и")
        elif word.endswith("на") or word.endswith("ва"): res.append(word + "ой")
        else: res.append(word + "а")
    return " ".join(res)

def get_signature_fio(fio):
    parts = fio.split()
    if len(parts) >= 2: return f"{parts[1]} {parts[0]}"
    return fio

DATABASE_URL = "sqlite:///./profiles_final.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, unique=True, index=True)
    company = Column(String, default="ООО Ваша компания")
    inn = Column(String, default="0000000000")
    kpp = Column(String, default="")
    address = Column(String, default="г. Москва")
    contacts = Column(String, default="+7 (999) 999-99-99")
    tax_mode = Column(String, default="usn")
    director = Column(String, default="Иванов И.И.")
    director_pos = Column(String, default="Генерального директора")
    director_pos_nom = Column(String, default="Генеральный директор")
    bank_name = Column(String, default="")
    bik = Column(String, default="")
    rs = Column(String, default="")
    ks = Column(String, default="")
    logo = Column(Text, nullable=True)

Base.metadata.create_all(bind=engine)

CSS_STYLES = """
@page { size: a4; margin: 20mm 15mm 20mm 30mm; }
@font-face { font-family: "PTSans"; src: url("https://github.com/google/fonts/raw/main/ofl/ptsans/PT_Sans-Web-Regular.ttf"); }
body { font-family: "PTSans", sans-serif; font-size: 11pt; line-height: 1.35; text-align: justify; color: #000; text-indent: 1.25cm; }
h1.title { text-align: center; font-size: 14pt; font-weight: bold; margin-bottom: 20px; text-transform: uppercase; text-indent: 0; }
.meta { width: 100%; margin-bottom: 20px; text-indent: 0; }
.meta td { border: none; padding: 0; }
.section-title { font-weight: bold; margin-top: 15px; margin-bottom: 10px; text-indent: 0; }
table { width: 100%; border-collapse: collapse; margin-top: 15px; text-indent: 0; }
th, td { border: 1px solid #000; padding: 6px; text-align: left; }
.header-info { margin-bottom: 20px; font-size: 10pt; text-align: left; text-indent: 0; }
.signature-block { margin-top: 30px; text-indent: 0; }
.list-item { text-indent: 0; margin-bottom: 5px; }
"""

def format_money(val):
    return f"{val:,.2f}".replace(',', ' ').replace('.', ',')

def num2words_rub(num):
    try:
        rub = int(num)
        kop = int(round((num - rub) * 100))
        rub_str = num2words(rub, lang='ru').capitalize()
        return f"{rub_str} рублей {kop:02d} копеек"
    except:
        return f"{format_money(num)} рублей"

def get_header_html(company, inn, kpp, address, contacts, logo_base64=None):
    logo_html = f'<img src="{logo_base64}" style="max-height: 50px; margin-bottom: 10px;"><br>' if logo_base64 else ''
    kpp_str = f"/{kpp}" if kpp else ""
    return f"""
    <div class="header-info">
        {logo_html}
        <strong>{company}</strong><br>ИНН/КПП: {inn}{kpp_str}<br>Адрес: {address}<br>Тел: {contacts}
    </div>
    """

@app.get("/")
def read_root(): return {"status": "ok"}

@app.get("/get-profile")
async def get_profile(chat_id: str):
    db = SessionLocal()
    profile = db.query(Profile).filter(Profile.chat_id == chat_id).first()
    db.close()
    if profile:
        return {"status": "ok", "company": profile.company, "inn": profile.inn, "kpp": profile.kpp, "address": profile.address, "contacts": profile.contacts, "tax_mode": profile.tax_mode, "director": profile.director, "director_pos": profile.director_pos, "director_pos_nom": profile.director_pos_nom, "bank_name": profile.bank_name, "bik": profile.bik, "rs": profile.rs, "ks": profile.ks, "logo": profile.logo}
    return {"status": "not_found"}

@app.post("/save-profile")
async def save_profile(
    chat_id: str = Form(...), company: str = Form(...), inn: str = Form(...), kpp: str = Form(""), address: str = Form(...), 
    contacts: str = Form(...), tax_mode: str = Form("usn"), director: str = Form(...), director_pos: str = Form(...), director_pos_nom: str = Form(...),
    bank_name: str = Form(None), bik: str = Form(None), rs: str = Form(None), ks: str = Form(None), logo: str = Form(None)
):
    db = SessionLocal()
    try:
        profile = db.query(Profile).filter(Profile.chat_id == chat_id).first()
        if profile:
            profile.company, profile.inn, profile.kpp, profile.address, profile.contacts = company, inn, kpp, address, contacts
            profile.tax_mode = tax_mode
            profile.director, profile.director_pos, profile.director_pos_nom = director, director_pos, director_pos_nom
            if bank_name: profile.bank_name = bank_name
            if bik: profile.bik = bik
            if rs: profile.rs = rs
            if ks: profile.ks = ks
            if logo: profile.logo = logo
        else:
            db.add(Profile(chat_id=chat_id, company=company, inn=inn, kpp=kpp, address=address, contacts=contacts, tax_mode=tax_mode, director=director, director_pos=director_pos, director_pos_nom=director_pos_nom, bank_name=bank_name, bik=bik, rs=rs, ks=ks, logo=logo))
        db.commit()
        return {"status": "ok"}
    except Exception as e: return {"status": "error", "message": str(e)}
    finally: db.close()

@app.post("/generate-doc")
async def generate_doc(
    template: str = Form("kp"), company: str = Form("ООО Ваша компания"), inn: str = Form("0000000000"), kpp: str = Form(""), 
    address: str = Form("г. Москва"), contacts: str = Form("+7 (999) 999-99-99"), tax_mode: str = Form("usn"),
    director: str = Form("Иванов И.И."), director_pos: str = Form("Генерального директора"), director_pos_nom: str = Form("Генеральный директор"),
    services_json: str = Form("[]"), term: str = Form("30"), dogovor_number: str = Form("Б/Н"), dogovor_date: str = Form(""), 
    customer_name: str = Form("ООО Заказчик"), customer_inn: str = Form("1111111111"), customer_kpp: str = Form(""), customer_address: str = Form("г. Москва"), 
    customer_director: str = Form("Петров П.П."), customer_pos: str = Form("Генерального директора"), customer_pos_nom: str = Form("Генеральный директор"), customer_pos_dat: str = Form("Генеральному директору"),
    smeta_date: str = Form(""), smeta_appendix: str = Form("1"),
