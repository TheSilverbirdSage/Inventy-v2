# Inventy - Project Handover Document

> **Last Updated:** 2026-10-29  
> **Status:** ✅ Per-User Inventory Isolation Fully Implemented and Verified  

---

## 1. Project Overview & Objective
**Inventy** is an AI-powered voice and text inventory management bot for tech resellers on Telegram.
- **Goal:** Enable resellers to log purchases, inspect inventory, track repairs, and record sales hands-free using Telegram voice notes and text messages.
- **Core Stack:**
  - **Bot Framework:** `python-telegram-bot` (v22.8)
  - **Audio Transcription:** Groq Whisper (`whisper-large-v3`) via OpenAI client in `transcriber.py`
  - **AI / Extraction Engine:** LangChain + Groq (`ChatGroq`, `openai/gpt-oss-120b`) + Pydantic in `ai_engine.py`
  - **Database:** MongoDB (`pymongo` v4.19.0) in `db_manager.py`

---

## 2. Repository Structure & Key Files
- `bot.py`: Telegram bot handlers (`start`, `handle_message`), voice download & transcription orchestration, AI intent handling (`ADD_ITEM`, `QUERY_STOCK`, `SELL_ITEM`, `UPDATE_ITEM`). All handlers extract `user_id = update.effective_user.id` and pass it to every database operation.
- `db_manager.py`: MongoDB wrapper class `DatabaseManager` providing user-scoped CRUD and financial calculations. Supports dependency injection via optional `client` parameter for offline/mock testing.
- `ai_engine.py`: Structured data extractor using LangChain and Pydantic (`ItemExtraction` schema).
- `transcriber.py`: Groq Whisper audio transcriber.
- `test_user_isolation.py`: Automated test suite testing multi-tenant isolation, cross-user access prevention, and financial calculations using `mongomock`.
- `.env`: Holds secrets (`TELEGRAM_BOT_TOKEN`, `MONGODB_URI`, `GROQ_API_KEY`).
- `requirements.txt`: Python package dependencies.
- `docs/superpowers/specs/2026-10-27-inventory-voice-bot-design.md`: Core product design specification.

---

## 3. Completed Feature: Per-User Inventory Isolation
### Architectural Summary
1. **User Identity Extraction**:
   - `bot.py` extracts `user_id = update.effective_user.id` at the start of `handle_message`.
   - All operations (`insert_item`, `find_items`, `mark_as_sold`, `add_repair_cost`, `update_item`) require and scope by `user_id`.
2. **Database Layer Security (`db_manager.py`)**:
   - `insert_item(item_data, user_id)` assigns `item_data['user_id'] = user_id`.
   - `find_items(query, user_id)` clones the query dict and adds `user_id: user_id`.
   - `find_item_by_id(item_id, user_id)` queries by both `_id` and `user_id`.
   - `mark_as_sold(item_id, sale_price, user_id)` ensures user ownership before calculating profit and updating `status: 'Sold'`.
   - `update_item` and `add_repair_cost` require matching `_id` and `user_id`, returning boolean success.
   - `DatabaseManager.ensure_indexes()` creates single and compound indexes on `user_id` and `(user_id, status)`.
   - Configured `serverSelectionTimeoutMS=5000` to prevent hanging on network lags.
3. **Voice Audio Cleanup**:
   - Added `try ... finally` block around voice note downloading and transcribing to guarantee temporary `.ogg` files are deleted even if errors occur.
4. **Testing Suite (`test_user_isolation.py`)**:
   - Validates multi-user creation, query isolation, cross-user read/update/delete prevention, and profit calculation. Runs completely self-contained in ~2 seconds.

---

## 4. How to Run & Verify
### Environment Setup
Activate the virtual environment:
```bash
source .venv/bin/activate
```
Dependencies are already installed in `.venv`.

### Running Tests
```bash
./.venv/bin/python test_user_isolation.py
```
*(All 7 isolation and security tests should pass with green checks).*

### Running the Bot
```bash
./.venv/bin/python bot.py
```

> [!NOTE]
> MongoDB Atlas connection requires the host machine's IP address to be whitelisted under MongoDB Atlas Network Access. If running from a new network, add your IP in the Atlas Dashboard (or `0.0.0.0/0` for development).

---

## 5. Next Steps & Recommended Roadmap for Next Agent
1. **Inventory Summary / Analytics Command**:
   - Add `/summary` or `/stats` handler allowing users to view total portfolio value, total invested, total items in stock, and total profit realized to date.
2. **Interactive Confirmation Loop for Sales**:
   - When multiple items match a sale query (e.g. user owns two iPhone 13s), present inline keyboard buttons to let the user select the exact device sold.
3. **Photo Attachment Support**:
   - Allow users to send photos along with voice notes to store item images or receipt proof.
