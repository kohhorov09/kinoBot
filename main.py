from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.constants import ChatMemberStatus
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
import json
import os
import logging

BOT_TOKEN = "8011433609:AAGagjhf7Fm5pDaroeInxxBq9saDvzQ24ns"
ADMIN_ID = 7114973309
DATA_FILE = "data.json"
MOVIE_FILE = "movies.json"

# Load and Save Functions
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return (
                set(data.get("users", [])),
                set(data.get("left", [])),
                set(data.get("admins", [ADMIN_ID])),
                data.get("channels", [])
            )
    return set(), set(), {ADMIN_ID}, []

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "users": list(user_db),
            "left": list(left_users),
            "admins": list(ADMINS),
            "channels": required_channels
        }, f, ensure_ascii=False, indent=2)

def load_movies():
    if os.path.exists(MOVIE_FILE):
        with open(MOVIE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_movies():
    with open(MOVIE_FILE, "w", encoding="utf-8") as f:
        json.dump(movies, f, ensure_ascii=False, indent=2)

user_db, left_users, ADMINS, required_channels = load_data()
movies = load_movies()
used_codes = set(map(int, movies.keys()))
movie_id_counter = max(used_codes, default=0)
logging.basicConfig(level=logging.INFO)

def is_subscribed(member):
    return member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]

async def is_user_subscribed(channel, user_id, context):
    try:
        member = await context.bot.get_chat_member(channel, user_id)
        return is_subscribed(member)
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.full_name

    if user_id not in user_db:
        user_db.add(user_id)
        save_data()

    not_subscribed = [ch for ch in required_channels if not await is_user_subscribed(ch, user_id, context)]
    if not_subscribed:
        buttons = [[InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch.lstrip('@')}")] for ch in not_subscribed]
        await update.message.reply_text(
            "‼️ Avval quyidagi kanallarga obuna bo‘ling va /start buyrug‘ini qaytadan yuboring:",
            reply_markup=InlineKeyboardMarkup(buttons))
        return

    await update.message.reply_text(
        f"👋 Assalomu alaykum {name}!\n\n✍🏻 Iltimos, kino kodini yuboring....")

async def handle_movie_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    # Debug: Kino kodi nima kiritilganini tekshiramiz
    print("✅ handle_movie_code ishladi")

    # Agar matn raqam bo‘lmasa
    if not text.isdigit():
        await update.message.reply_text("❗ Iltimos, faqat kino kodini yuboring.")
        return

    movie_id = text  # str shaklida qoladi
    if movie_id in movies:
        movie = movies[movie_id]
        try:
            await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=movie["file_id"],
                    caption=movie.get("caption", "")
)

        except Exception as e:
            print(f"❌ Video yuborishda xatolik: {e}")
            await update.message.reply_text("⚠️ Kino yuborishda muammo yuz berdi.")
    else:
        await update.message.reply_text("❌ Bunday  kino topilmadi.")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "add_movie":
        context.user_data["awaiting_movie_video"] = True
        await query.edit_message_text("📥 Iltimos, kino videosini yuboring:")

    elif query.data == "delete_movie":
        context.user_data["awaiting_delete_code"] = True
        await query.edit_message_text("🗑 O‘chirmoqchi bo‘lgan kino kodini yuboring:")

SERVER_CHANNEL_ID = -1002725004956  # o'zingizning kanal ID'ingiz

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_movie_video"):
        return
    print('ishlayabdi')
    global movie_id_counter
    while True:
        movie_id_counter += 1
        if movie_id_counter not in used_codes:
            break

    video = update.message.video

    try:
        # 🔁 Caption hozircha mavjud emas, shunchaki "Kod: ####" bilan vaqtincha yuboriladi
        temp_caption = f"Kanaldan kinoni o'chrib tashlamang aks holda bot kinoni tashlab bermaydi shuning uchun kanaldan kinoni o'chirmang \n\n kino kodi: {movie_id_counter}"

        sent_msg = await context.bot.send_video(
            chat_id=SERVER_CHANNEL_ID,
            video=video.file_id,
            caption=temp_caption
        )

        file_id = sent_msg.video.file_id  # serverdan qaytgan yangi file_id

        context.user_data["file_id"] = file_id
        context.user_data["movie_id"] = movie_id_counter
        context.user_data["awaiting_movie_video"] = False
        context.user_data["awaiting_movie_caption"] = True

        await update.message.reply_text("📝 Kino uchun tavsif  yozing:")

    except Exception as e:
        print(f"❌ Server kanalga yuborishda xatolik: {e}")
        await update.message.reply_text("⚠️ Kino saqlashda xatolik yuz berdi.")


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMINS:
        await update.message.reply_text("⛔ Siz admin emassiz.")
        return

    keyboard = ReplyKeyboardMarkup([
        ["🎬 Kino sozlamalari"],
        ["📊 Statistika", "📋 Ro‘yxat"],
        ["➕ Obuna qo‘shish", "➖ Obunani o‘chirish"],
        ["📤 Xabar yuborish", "👤 Admin qo‘shish"],
        ["🗂 Adminlar", "⬅️ Ortga"]
    ], resize_keyboard=True)

    await update.message.reply_text("📋 Admin menyusi:", reply_markup=keyboard)
def is_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return (
        update.effective_user.id in ADMINS and
        context.user_data.get("awaiting_broadcast", False)
    )
async def broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 🔐 Faqat adminlarga ruxsat
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        return

    # Faqat "xabar yuborish" rejimida ishlaydi
    if not context.user_data.get("awaiting_broadcast"):
        return

    success, failed = 0, 0

    for uid in user_db:
        try:
            # TEXT
            if update.message.text:
                await context.bot.send_message(chat_id=uid, text=update.message.text)

            # PHOTO
            elif update.message.photo:
                await context.bot.send_photo(chat_id=uid, photo=update.message.photo[-1].file_id, caption=update.message.caption or "")

            # VIDEO
            elif update.message.video:
                await context.bot.send_video(chat_id=uid, video=update.message.video.file_id, caption=update.message.caption or "")

            # AUDIO
            elif update.message.audio:
                await context.bot.send_audio(chat_id=uid, audio=update.message.audio.file_id, caption=update.message.caption or "")

            # VOICE
            elif update.message.voice:
                await context.bot.send_voice(chat_id=uid, voice=update.message.voice.file_id, caption=update.message.caption or "")

            # VIDEO_NOTE (tumaloq video)
            elif update.message.video_note:
                await context.bot.send_video_note(chat_id=uid, video_note=update.message.video_note.file_id)

            # STICKER
            elif update.message.sticker:
                await context.bot.send_sticker(chat_id=uid, sticker=update.message.sticker.file_id)

            # ANIMATION (GIF)
            elif update.message.animation:
                await context.bot.send_animation(chat_id=uid, animation=update.message.animation.file_id, caption=update.message.caption or "")

            # FORWARDED MESSAGE
            elif update.message.forward_from or update.message.forward_from_chat:
                await context.bot.forward_message(chat_id=uid, from_chat_id=update.message.chat_id, message_id=update.message.message_id)

            else:
                failed += 1
                continue

            success += 1

        except Exception as e:
            print(f"❌ {uid} foydalanuvchiga xabar yuborilmadi: {e}")
            failed += 1

    # Xabar rejimini o‘chirib qo‘yamiz
    context.user_data["awaiting_broadcast"] = False

    await update.message.reply_text(
        f"✅ Yuborildi: {success} ta\n❌ Xato: {failed} ta"
    )


async def admin_textt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Agar broadcast holatida bo‘lsa — hech narsa qilmaymiz, broadcast_handler o‘zi olib ketadi

    user_id = update.effective_user.id
    text = update.message.text.strip()
    if context.user_data.get("awaiting_broadcast"):
        return

    # 🔁 Har bir foydalanuvchi (hatto admin ham) kod yuborsa — kinoni ko‘rish funksiyasiga uzatamiz


# Faqat hech qanday rejim yo‘q bo‘lsa — kinoni chiqarish funksiyasiga uzatamiz
    if (
        text.isdigit() and
    not any([
        context.user_data.get("awaiting_delete_code"),
        context.user_data.get("awaiting_movie_caption"),
        context.user_data.get("awaiting_broadcast"),
        context.user_data.get("adding_channel"),
        context.user_data.get("adding_admin"),
        context.user_data.get("awaiting_movie_video")
    ])
):
        return await handle_movie_code(update, context)


    # 🔒 Quyidagisi faqat adminlar uchun
    if user_id not in ADMINS:
        return


    # 🔒 Quyidagisi faqat adminlar uchun

    if context.user_data.get("adding_channel"):
        if text.startswith("@"):
            required_channels.append(text)
            save_data()
            await update.message.reply_text(f"✅ Kanal qo‘shildi: {text}")
        else:
            await update.message.reply_text("❌ Kanal @ bilan boshlanishi kerak")
        context.user_data["adding_channel"] = False
        return

    if context.user_data.get("adding_admin"):
        try:
            new_admin = int(text)
            ADMINS.add(new_admin)
            save_data()
            await update.message.reply_text(f"✅ Admin qo‘shildi: {new_admin}")
        except:
            await update.message.reply_text("❌ Noto‘g‘ri ID")
        context.user_data["adding_admin"] = False
        return

    if context.user_data.get("awaiting_delete_code"):
        code = text.strip()
        if code in movies:
            del movies[code]
            save_movies()
            await update.message.reply_text(f"🗑 Kino o‘chirildi. \n\n kino kodi {code}")
        else:
            await update.message.reply_text("❌ Bunday kod topilmadi.")
        context.user_data["awaiting_delete_code"] = False
        return

    if context.user_data.get("awaiting_movie_caption"):
        caption = text
        movie_id = context.user_data["movie_id"]
        file_id = context.user_data["file_id"]

        movies[str(movie_id)] = {"file_id": file_id, "caption": caption}
        save_movies()
        used_codes.add(movie_id)

        await update.message.reply_text(f"✅ Kino saqlandi!\n🎬 Kino kodi: <b>{movie_id}</b>", parse_mode="HTML")
        context.user_data["awaiting_movie_caption"] = False
        return

    # 🔄 Admin matn tugmalari (Statistika, Obuna qo‘shish va h.k.)
    if text == "📋 Ro‘yxat":
        if required_channels:
            ch_list = "\n".join([f"{i+1}. {ch}" for i, ch in enumerate(required_channels)])
            await update.message.reply_text(f"📋 Kanallar Ro‘yxati:\n\n{ch_list}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")]]))
        else:
            await update.message.reply_text("📭 Hech qanday kanal yo‘q.")
        return

    if text == "📊 Statistika":
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="show_users")]])
        await update.message.reply_text(
            f"📈 Bot Statistikasi:\n\n✅ Faol Obunachilar: {len(user_db)}\n🚫 No-faol Onunachilar: {len(left_users)}",
            reply_markup=keyboard
        )
        return

    if text == "➕ Obuna qo‘shish":
        context.user_data["adding_channel"] = True
        await update.message.reply_text("📥 Yangi kanalni yuboring (@ bilan):")
        return

    if text == "➖ Obunani o‘chirish":
        if not required_channels:
            await update.message.reply_text("📭 Obuna kanallari yo‘q")
            return
        buttons = [[InlineKeyboardButton(f"❌ {ch}", callback_data=f"remove_{i}")] for i, ch in enumerate(required_channels)]
        await update.message.reply_text("🗑 Qaysi kanalni o‘chirmoqchisiz?", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if text == "📤 Xabar yuborish":
        context.user_data["awaiting_broadcast"] = True
        await update.message.reply_text("✉️ Foydalanuvchilarga yuboriladigan xabarni  kriting:")
        return


    if text == "👤 Admin qo‘shish":
        if user_id != ADMIN_ID:
            await update.message.reply_text("⛔ Faqat asosiy admin admin qo‘sha oladi")
            return
        context.user_data["adding_admin"] = True
        await update.message.reply_text("🆔 Admin ID raqamini yuboring:")
        return

    if text == "⬅️ Ortga":
        await start(update, context)
        return

    if text == "🗂 Adminlar":
        buttons = [[InlineKeyboardButton(f"👤 {aid}", callback_data=f"admin_{aid}")] for aid in ADMINS]
        buttons.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")])
        await update.message.reply_text("👥 Adminlar ro‘yxati:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if text == "🎬 Kino sozlamalari":
        buttons = [
            [InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add_movie")],
            [InlineKeyboardButton("🗑 Kino o‘chirish", callback_data="delete_movie")],
            [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")]
        ]
        await update.message.reply_text("🎬 Kino sozlamalari:", reply_markup=InlineKeyboardMarkup(buttons))
        return
   
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "add_movie":
        context.user_data["awaiting_movie_video"] = True
        await query.edit_message_text("📥 Iltimos, kino videosini yuboring:")
        return

    elif query.data == "delete_movie":
        context.user_data["awaiting_delete_code"] = True
        await query.edit_message_text("❌ O‘chirmoqchi bo‘lgan kino kodini yuboring:")
        return

    if query.data == "back_to_admin":
        user = query.from_user
        message = query.message
        if user.id not in ADMINS:
            await message.edit_text("⛔ Siz admin emassiz.")
            return
        await message.delete()
        return

    elif query.data.startswith("remove_admin_"):
        aid = int(query.data.split("_")[2])

        # 🔒 Faqat asosiy admin boshqa adminlarni o‘chira oladi
        if query.from_user.id != ADMIN_ID:
            await query.answer("⛔ Sizda boshqa adminlarni o‘chirish huquqi yo‘q!", show_alert=True)
            return

        # 🔐 Asosiy adminni o‘chirib bo‘lmaydi
        if aid == ADMIN_ID:
            await query.answer("⛔ Asosiy adminni o‘chira olmaysiz!", show_alert=True)
            return

        if aid in ADMINS:
            ADMINS.remove(aid)
            save_data()
            await query.edit_message_text(
                f"🗑 Admin o‘chirildi:\n🆔 <code>{aid}</code>",
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text("❌ Admin topilmadi.")

    elif query.data.startswith("remove_") and not query.data.startswith("remove_admin_"):
        try:
            index = int(query.data.split("_")[1])
            if 0 <= index < len(required_channels):
                removed_channel = required_channels.pop(index)
                save_data()
                await query.edit_message_text(f"✅ O‘chirildi: {removed_channel}")
            else:
                await query.edit_message_text("❌ Noto‘g‘ri kanal indeksi.")
        except Exception as e:
            await query.edit_message_text("❌ Kanalni o‘chirishda xatolik yuz berdi.")


    elif query.data == "show_users":
        buttons = []
        user_list = sorted(list(user_db))
        for i in range(0, len(user_list), 2):
            row = []
            for j in range(2):
                if i + j < len(user_list):
                    uid = user_list[i + j]
                    row.append(InlineKeyboardButton(str(uid), callback_data=f"view_{uid}"))
            buttons.append(row)
        buttons.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")])
        await query.edit_message_text("📋 Foydalanuvchilar ro‘yxati:", reply_markup=InlineKeyboardMarkup(buttons))

    elif query.data.startswith("view_"):
        uid = int(query.data.split("_")[1])
        try:
            user = await context.bot.get_chat(uid)
            full_name = user.full_name or "Noma’lum"
            username = f"@{user.username}" if user.username else "🚫 Yo‘q"
            status = "🔵 Faol" if uid in user_db else "🔴 No-faol"

            text = (
                f"👤 <b>Foydalanuvchi maʼlumoti:</b>\n\n"
                f"🆔 ID: <code>{uid}</code>\n"
                f"📛 To‘liq ismi: <b>{full_name}</b>\n"
                f"👤 Username: {username}\n"
                f"📶 Holati: {status}"
            )
        except:
            text = f"❌ Foydalanuvchi topilmadi.\nID: <code>{uid}</code>"

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Orqaga", callback_data="show_users")]])
        )

    elif query.data.startswith("admin_"):
        aid = int(query.data.split("_")[1])
        try:
            admin_user = await context.bot.get_chat(aid)
            full_name = admin_user.full_name or "Noma’lum"
            username = f"@{admin_user.username}" if admin_user.username else "🚫 Yo‘q"
            status = "🔵 Faol" if aid in user_db else "🔴 No-faol"

            text = (
                f"👨‍💼 <b>Admin maʼlumoti:</b>\n\n"
                f"🆔 ID: <code>{aid}</code>\n"
                f"📛 To‘liq ismi: <b>{full_name}</b>\n"
                f"👤 Username: {username}\n"
                f"📶 Holati: {status}"
            )

            buttons = [
                [InlineKeyboardButton("🗑 Adminni o‘chirish", callback_data=f"remove_admin_{aid}")],
                [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admins")]
            ]
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

        except:
            await query.edit_message_text("❌ Admin topilmadi.")

    elif query.data.startswith("remove_admin_"):
        aid = int(query.data.split("_")[2])
        if aid == ADMIN_ID:
            await query.answer("⛔ Asosiy adminni o‘chira olmaysiz!", show_alert=True)
            return
        if aid in ADMINS:
            ADMINS.remove(aid)
            save_data()
            await query.edit_message_text(f"🗑 Admin o‘chirildi:\n🆔 <code>{aid}</code>", parse_mode="HTML")
        else:
            await query.edit_message_text("❌ Admin topilmadi.")

    elif query.data == "back_to_admins":
        buttons = [[InlineKeyboardButton(f"👤 {aid}", callback_data=f"admin_{aid}")] for aid in ADMINS]
        buttons.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")])
        await query.edit_message_text("👥 Adminlar ro‘yxati:", reply_markup=InlineKeyboardMarkup(buttons))
if __name__ == "__main__":
    import asyncio

    # Bot yaratish
    app = Application.builder().token(BOT_TOKEN).build()

    # 🟢 Boshlanish buyrug'i
    app.add_handler(CommandHandler("start", start))

    # 🔒 Admin menyusi
    app.add_handler(CommandHandler("admin", admin))

    # 🧠 Kino kodi, admin komandalarini aniqlovchi handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_textt))

# 🎥 Kino video faylini qabul qiluvchi handler (kino qo‘shish jarayoni uchun)
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))

# 🔊 Broadcast rejimida har qanday kontentni qabul qiluvchi handler
    app.add_handler(MessageHandler(filters.ALL, broadcast_handler))

    # 📲 Inline tugmalar va callback’larni qabul qiluvchi handler
    app.add_handler(CallbackQueryHandler(handle_callback))

    # ✅ Ishga tushirish
    print("✅ Bot ishga tushdi")
    asyncio.run(app.run_polling())
