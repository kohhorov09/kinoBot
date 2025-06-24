from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, ReplyKeyboardMarkup
from telegram.constants import ChatMemberStatus
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
import logging
import json
import os

BOT_TOKEN = "7838589688:AAGam0Yj0wz1IErdJPj7LIGwPBGY8Z3C9aA"
ADMIN_ID = 7114973309

DATA_FILE = "data.json"

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

user_db, left_users, ADMINS, required_channels = load_data()
logging.basicConfig(level=logging.INFO)

def is_subscribed(member):
    return member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_db:
        user_db.add(user_id)
        save_data()

    not_subscribed = [ch for ch in required_channels if not await is_user_subscribed(ch, user_id, context)]
    if not_subscribed:
        buttons = [[InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch.lstrip('@')}")] for ch in not_subscribed]
        buttons.append([InlineKeyboardButton("✅ Tekshirish", callback_data="check_subs")])
        await update.message.reply_text("‼️ O‘yinni boshlashdan oldin quyidagi kanallarga obuna bo‘ling:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    game_button = InlineKeyboardButton("🎮 Join Game", web_app=WebAppInfo(url="https://coin-ton-6pu6.vercel.app/"))
    await update.message.reply_text("✅ Obuna tasdiqlandi. O‘yinni boshlang!", reply_markup=InlineKeyboardMarkup([[game_button]]))

async def is_user_subscribed(channel, user_id, context):
    try:
        member = await context.bot.get_chat_member(channel, user_id)
        return is_subscribed(member)
    except:
        return False

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("⛔ Bu bo‘lim faqat adminlar uchun.")
        return

    keyboard = ReplyKeyboardMarkup([
        ["📊 Statistika", "📋 Ro‘yxat"],
        ["➕ Obuna qo‘shish", "➖ Obunani o‘chirish"],
        ["📤 Xabar yuborish", "👤 Admin qo‘shish"],
        ["🗂 Adminlar", "⬅️ Ortga"]
    ], resize_keyboard=True)
    await update.message.reply_text("Admin menyusi:", reply_markup=keyboard)

async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in ADMINS:
        return

    if context.user_data.get("awaiting_broadcast"):
        success, failed = 0, 0
        success_list = []
        failed_list = []

        for uid in user_db:
            try:
                user = await context.bot.get_chat(uid)
                name = f"@{user.username}" if user.username else f"🆔 {uid}"
                await context.bot.send_message(uid, text)
                success += 1
                success_list.append(name)
            except:
                failed += 1
                failed_list.append(f"🆔 {uid}")

        context.user_data["awaiting_broadcast"] = False

        result_text = (
            f"✅ <b>Yuborilgan:</b> {success} ta\n"
            f"{chr(10).join(success_list) if success_list else '🚫 Hech kimga yuborilmadi'}\n\n"
            f"❌ <b>Xatolik:</b> {failed} ta\n"
            f"{chr(10).join(failed_list) if failed_list else '✅ Hamma xabar yuborildi'}"
        )

        await update.message.reply_text(result_text, parse_mode="HTML")
        return

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
        await update.message.reply_text("✉️ Yuboriladigan xabar matnini kiriting:")
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

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "back_to_admin":
        user = query.from_user
        message = query.message
        if user.id not in ADMINS:
            await message.edit_text("⛔ Siz admin emassiz.")
            return
        keyboard = ReplyKeyboardMarkup([
            ["📊 Statistika", "📋 Ro‘yxat"],
            ["➕ Obuna qo‘shish", "➖ Obunani o‘chirish"],
            ["📤 Xabar yuborish", "👤 Admin qo‘shish"],
            ["🗂 Adminlar", "⬅️ Ortga"]
        ], resize_keyboard=True)
        await context.bot.send_message(chat_id=user.id, text="📋 Admin menyusi:", reply_markup=keyboard)
        await message.delete()
        return

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
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_text))
    app.add_handler(CallbackQueryHandler(handle_callback))
    print("✅ Bot ishga tushdi")
    asyncio.run(app.run_polling())
