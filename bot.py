import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

from db_manager import DatabaseManager
from ai_engine import AIEngine
from transcriber import Transcriber

load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

# Initialize components
db = DatabaseManager(os.getenv("MONGODB_URI"))
ai = AIEngine()
transcriber = Transcriber()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    greeting = f"Welcome to Inventy, {user.first_name}! 📦" if user and user.first_name else "Welcome to Inventy! 📦"
    await update.message.reply_text(
        f"{greeting}\n\n"
        "Your personal inventory is ready. You can send me a voice note or text to:\n"
        "✅ Add a new item\n"
        "🔍 Check your stock\n"
        "💰 Mark an item as sold\n"
        "🛠️ Update repair costs or notes"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user:
        return

    user_id = update.effective_user.id
    user_text = ""

    # 1. Handle Voice Messages
    if update.message.voice:
        await update.message.reply_chat_action("typing")
        voice_file = await update.message.voice.get_file(read_timeout=60)
        voice_path = f"voice_{update.message.message_id}.ogg"
        await voice_file.download_to_drive(voice_path)

        try:
            user_text = transcriber.transcribe(voice_path)
        except Exception as e:
            logging.error(f"Transcription error: {e}")
            await update.message.reply_text("Sorry, I couldn't transcribe your voice note.")
            return
        finally:
            if os.path.exists(voice_path):
                try:
                    os.remove(voice_path)
                except OSError:
                    pass

    # 2. Handle Text Messages
    elif update.message.text:
        user_text = update.message.text
    else:
        return

    # 3. AI Analysis
    try:
        analysis = ai.analyze_input(user_text)
    except Exception as e:
        logging.error(f"AI Analysis error: {e}")
        await update.message.reply_text("I had some trouble understanding that. Could you try again?")
        return

    # 4. Intent Handling
    if analysis.intent == "ADD_ITEM":
        item_data = {
            "category": analysis.category,
            "model": analysis.model,
            "specs": analysis.specs,
            "notes": analysis.notes,
            "purchase_price": analysis.purchase_price,
            "notes": analysis.notes
        }
        item_id = db.insert_item(item_data, user_id=user_id)

        reply = (
            f"✅ Added to Inventory:\n"
            f"📦 {analysis.model} ({analysis.category})\n"
            f"⚙️ Specs: {analysis.specs}\n"
            f"💰 Cost: ${analysis.purchase_price}\n"
            f"📝 Notes: {analysis.notes}\n"
            f"🆔 ID: {item_id}"
        )
        await update.message.reply_text(reply)

    elif analysis.intent == "QUERY_STOCK":
        # Scoped stock search for active user
        query = {"status": "In Stock"}
        if analysis.model:
            query["model"] = {"$regex": analysis.model, "$options": "i"}
        elif analysis.category:
            query["category"] = {"$regex": analysis.category, "$options": "i"}

        items = db.find_items(query, user_id=user_id)
        if not items:
            await update.message.reply_text("I couldn't find any matching items in stock.")
            return

        response = "📦 Your Stock:\n\n"
        for item in items:
            response += f"• {item['model']} - {item['specs']} (${item['financials']['purchase_price']})\n"

        await update.message.reply_text(response)

    elif analysis.intent == "SELL_ITEM":
        query = {}
        if analysis.model:
            query["model"] = {"$regex": analysis.model, "$options": "i"}

        items = db.find_items(query, user_id=user_id)
        if not items:
            await update.message.reply_text("I couldn't find that item to mark it as sold.")
            return

        # Pick the first matching item that is in stock
        target_item = next((i for i in items if i['status'] == 'In Stock'), None)
        if not target_item:
            await update.message.reply_text("That item is already sold or not in stock.")
            return

        profit = db.mark_as_sold(target_item['_id'], analysis.sale_price or 0, user_id=user_id)
        if profit is None:
            await update.message.reply_text("Failed to mark item as sold.")
            return

        await update.message.reply_text(
            f"💰 Item marked as sold!\n"
            f"Sale Price: ${analysis.sale_price}\n"
            f"Profit: ${profit}"
        )

    elif analysis.intent == "UPDATE_ITEM":
        query = {}
        if analysis.model:
            query["model"] = {"$regex": analysis.model, "$options": "i"}

        items = db.find_items(query, user_id=user_id)
        if not items:
            await update.message.reply_text("I couldn't find that item to update.")
            return

        target_item = next((i for i in items if i['status'] == 'In Stock'), None)
        if not target_item:
            await update.message.reply_text("Item not found or already sold.")
            return

        if analysis.repair_cost:
            db.add_repair_cost(target_item['_id'], analysis.repair_cost, user_id=user_id)
            await update.message.reply_text(f"✅ Added ${analysis.repair_cost} to repair costs for {target_item['model']}.")

        if analysis.notes:
            db.update_item(target_item['_id'], {"notes": analysis.notes}, user_id=user_id)
            await update.message.reply_text(f"✅ Updated notes for {target_item['model']}.")

    else:
        await update.message.reply_text("I'm not sure how to help with that. Try saying 'I just bought an iPhone 14' or 'Do I have any MacBooks?'")

if __name__ == "__main__":
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    start_handler = CommandHandler('start', start)
    msg_handler = MessageHandler(filters.TEXT | filters.VOICE, handle_message)

    application.add_handler(start_handler)
    application.add_handler(msg_handler)

    application.run_polling()
