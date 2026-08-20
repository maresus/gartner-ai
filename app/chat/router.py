"""
Chat API router for Kovačnik V2.
Hybrid: Direct LLM for info, State machine for bookings.
"""
from __future__ import annotations

import uuid
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.chat.llm_chat import chat, chat_stream
from app.booking.state_machine import (
    BookingState,
    detect_booking_intent,
    start_booking,
    process_booking,
    is_booking_active,
)
from app.services.reservation_service import ReservationService


router = APIRouter(prefix="/chat", tags=["chat"])

# Service for DB persistence
_service = ReservationService()


class QuickBookingRequest(BaseModel):
    session_id: str | None = None
    booking_type: str = "room"  # "room" or "table"
    date: str
    nights: int | None = None
    time: str | None = None
    adults: int = 2
    children: int = 0
    children_ages: list[int] = []
    name: str
    phone: str
    email: str = ""
    dinner: bool = False
    note: str = ""
    gdpr: bool = False


@router.post("/quick-booking")
async def quick_booking(payload: QuickBookingRequest):
    """Sprejme celo rezervacijo naenkrat iz forme v widgetu."""
    from app.booking.state_machine import BookingState, _save_reservation

    if not payload.gdpr:
        return {"ok": False, "error": "GDPR soglasje je obvezno."}

    state = BookingState(
        type=payload.booking_type,
        step="awaiting_confirm",
        date=payload.date,
        nights=payload.nights or 0,
        time=payload.time or "",
        adults=payload.adults,
        children=payload.children,
        children_ages=payload.children_ages,
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        dinner=payload.dinner,
        note=payload.note,
    )

    reservation_id = _save_reservation(state, source="widget_form")

    session_id = payload.session_id or str(uuid.uuid4())
    nights_info = f", {payload.nights} noči" if payload.booking_type == "room" else ""
    time_info = f" ob {payload.time}" if payload.time else ""
    summary = f"[Rezervacija forme] {payload.booking_type}: {payload.date}{time_info}{nights_info}, {payload.adults}+{payload.children} oseb, {payload.name}"
    _service.log_conversation(session_id=session_id, user_message=summary, bot_response=f"Rezervacija #{reservation_id} shranjena.", intent="quick_booking_form")

    if reservation_id:
        return {"ok": True, "reservation_id": reservation_id}
    else:
        return {"ok": False, "error": "Napaka pri shranjevanju."}

# Simple in-memory session storage
_sessions: dict[str, dict] = {}


import re as _re
from datetime import datetime as _dt

def _try_extract_prefill(message: str) -> dict | None:
    """Izvleče datum, noči, odrasle, otroke iz sporočila. Vrne prefill dict ali None."""
    msg = message.lower()
    prefill: dict = {}

    # Datumski range: "6.-8.5." ali "6. do 8. maja" ali "od 6.5. do 8.5."
    range_match = _re.search(r'(\d{1,2})\.\s*[-–do]+\s*(\d{1,2})\.(\d{1,2})\.?(\d{4})?', msg)
    if range_match:
        day1, day2, month = int(range_match.group(1)), int(range_match.group(2)), int(range_match.group(3))
        year = int(range_match.group(4)) if range_match.group(4) else _dt.now().year
        try:
            d1 = _dt(year, month, day1)
            d2 = _dt(year, month, day2)
            prefill["date"] = d1.strftime("%Y-%m-%d")
            nights = (d2 - d1).days
            if 1 <= nights <= 30:
                prefill["nights"] = nights
        except ValueError:
            pass
    else:
        # Enojni datum: "6.5." ali "6. maja"
        single_match = _re.search(r'(\d{1,2})\.\s*(\d{1,2})\.?(\d{4})?', msg)
        if single_match:
            day, month = int(single_match.group(1)), int(single_match.group(2))
            year = int(single_match.group(3)) if single_match.group(3) else _dt.now().year
            try:
                prefill["date"] = _dt(year, month, day).strftime("%Y-%m-%d")
            except ValueError:
                pass

    if not prefill.get("date"):
        return None  # Brez datuma ni smisla odpirati forme

    # Odrasli
    adults_match = _re.search(r'(\d+)\s*(?:odrasl|oseb[^i]|gost)', msg)
    if adults_match:
        prefill["adults"] = int(adults_match.group(1))

    # Otroci
    kids_match = _re.search(r'(\d+)\s*(?:otro[kc]|malčk)', msg)
    if kids_match:
        prefill["children"] = int(kids_match.group(1))

    # Besedni zapis za odrasle/otroke
    word_nums = {"en ": 1, "ena ": 1, "eno ": 1, "dva ": 2, "dve ": 2, "tri ": 3, "štiri ": 4, "pet ": 5}
    if not prefill.get("adults"):
        for w, n in word_nums.items():
            if w + "odrasl" in msg or w + "oseb" in msg:
                prefill["adults"] = n
                break
    if not prefill.get("children"):
        for w, n in word_nums.items():
            if w + "otro" in msg or w + "malč" in msg:
                prefill["children"] = n
                break

    return prefill if prefill else None


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    action: str | None = None
    booking_type_hint: str | None = None
    booking_prefill: dict | None = None


def _get_session(session_id: str | None) -> tuple[str, dict]:
    """Get or create session."""
    # If client provides session_id, use it (create if needed)
    if session_id:
        if session_id not in _sessions:
            _sessions[session_id] = {"history": [], "booking": None}
        return session_id, _sessions[session_id]

    # No session_id provided, generate new one
    new_id = str(uuid.uuid4())
    _sessions[new_id] = {"history": [], "booking": None}
    return new_id, _sessions[new_id]


def _is_side_question(message: str, booking: BookingState) -> bool:
    """Check if message is a side question during booking."""
    msg_l = message.lower()

    # Question indicators
    question_words = (
        "koliko", "kdo", "kaj", "kje", "kdaj", "ali", "kako", "zakaj", "?",
        "kakšen", "kakšna", "kakšno", "kateri", "katera", "katero",
        "imate", "imate li", "a imate", "ali imate", "je kje", "je kaj", "so kje",
        "lahko", "se da", "a je", "ali je", "obstaja", "ponujate",
    )
    has_question = any(q in msg_l for q in question_words)

    # If it looks like valid booking data, it's not a side question
    # Date pattern
    if booking.step == "awaiting_date" and any(c.isdigit() for c in message):
        import re
        if re.search(r'\d{1,2}\.\d{1,2}', message):
            return False

    # Number for nights
    if booking.step == "awaiting_nights":
        if any(c.isdigit() for c in message):
            return False

    # Number for adults
    if booking.step == "awaiting_adults":
        if any(c.isdigit() for c in message) or any(w in msg_l for w in ("odrasl", "oseb")):
            return False

    # Number for children (or "no")
    if booking.step == "awaiting_children_count":
        if any(c.isdigit() for c in message) or any(w in msg_l for w in ("otrok", "brez", "ne", "nimamo")):
            return False

    # Ages for children
    if booking.step == "awaiting_children_ages":
        if any(c.isdigit() for c in message) or any(w in msg_l for w in ("let", "star")):
            return False

    # Name
    if booking.step == "awaiting_contact":
        words = message.strip().split()
        if len(words) >= 1 and not any(c.isdigit() for c in message) and not has_question:
            return False

    # Phone
    if booking.step == "awaiting_phone":
        if sum(c.isdigit() for c in message) >= 6:
            return False

    # Yes/No answers
    if booking.step in ("awaiting_dinner", "awaiting_confirm"):
        simple = msg_l.strip()
        if simple in ("da", "ne", "ja", "no", "ok", "yes", "prosim", "hvala"):
            return False

    return has_question


def _handle_side_question(message: str, booking: BookingState, session: dict) -> str | None:
    """Handle side question during booking. Returns answer or None if not a question."""
    if not _is_side_question(message, booking):
        return None

    # Add context that we're mid-booking - LLM should be brief
    context_msg = f"[Uporabnik je SREDI rezervacije sobe za {booking.date or 'TBD'}. Odgovori KRATKO (1-2 stavka), brez ponujanja dodatnih opcij ali spraševanja za datume.]"

    # Prepend context to message
    augmented_message = f"{context_msg}\n\nVprašanje: {message}"

    result = chat(message=augmented_message, history=session.get("history"))
    return result["reply"]


def _get_booking_continuation(booking: BookingState) -> str:
    """Get the continuation prompt for current booking step."""
    prompts = {
        "awaiting_type": "Želite rezervirati **sobo** ali **mizo**?",
        "awaiting_date": "Za kateri datum prihoda razmišljate? (npr. 15.7.2026)",
        "awaiting_nights": "Koliko nočitev? (npr. 3)",
        "awaiting_adults": "Koliko odraslih oseb?",
        "awaiting_children_count": "Ali boste imeli otroke? Če da, koliko?",
        "awaiting_children_ages": f"Koliko let {'ima otrok' if booking.children == 1 else 'imajo otroci'}?",
        "awaiting_contact": "Vaše ime in priimek?",
        "awaiting_phone": "Vaša telefonska številka?",
        "awaiting_dinner": "Želite tudi večerjo? (30 €/odraslo osebo, 15 €/otrok do 12 let)",
        "awaiting_confirm": "Ali potrjujete rezervacijo? (da/ne)",
    }
    return prompts.get(booking.step, "Kako nadaljujemo?")


@router.post("", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest, background_tasks: BackgroundTasks) -> ChatResponse:
    """Main chat endpoint - hybrid approach."""
    session_id, session = _get_session(payload.session_id)
    message = payload.message.strip()

    # Check if we're in an active booking flow
    booking: BookingState | None = session.get("booking")

    if is_booking_active(booking):
        # Check if this is a side question (not booking data)
        side_answer = _handle_side_question(message, booking, session)
        if side_answer:
            # Answer the question, then remind about booking
            continuation = _get_booking_continuation(booking)
            reply = f"{side_answer}\n\n—\nNadaljujemo z rezervacijo?\n{continuation}"
            # Log side question during booking
            _service.log_conversation(
                session_id=session_id,
                user_message=message,
                bot_response=reply,
                intent="side_question_during_booking",
            )
            return ChatResponse(reply=reply, session_id=session_id)

        # Continue booking flow
        booking, reply = process_booking(booking, message)
        session["booking"] = booking

        # Log booking interaction
        _service.log_conversation(
            session_id=session_id,
            user_message=message,
            bot_response=reply,
            intent=f"booking_{booking.type}",
        )

        # If booking completed or cancelled, clear it
        if booking.step in ("confirmed", "cancelled"):
            session["booking"] = None

        return ChatResponse(reply=reply, session_id=session_id)

    # Check for new booking intent → open visual form instead of step-by-step
    booking_type = detect_booking_intent(message)
    # Fallback: konkretni datum v sporočilu brez eksplicitnega booking namena → odpri formo
    prefill = _try_extract_prefill(message)
    if not booking_type and prefill:
        booking_type = "room"  # privzeto soba ko je datum + ni eksplicitnega namena

    if booking_type:
        # LLM generira topel, oseben odgovor ki naravno predlaga formo
        result = chat(
            message=message,
            history=session["history"],
            booking_type_hint=booking_type,
        )
        reply = result["reply"]
        session["history"].append({"role": "user", "content": message})
        session["history"].append({"role": "assistant", "content": reply})
        if len(session["history"]) > 20:
            session["history"] = session["history"][-20:]
        _service.log_conversation(
            session_id=session_id,
            user_message=message,
            bot_response=reply,
            intent=f"open_booking_form_{booking_type}",
        )
        return ChatResponse(
            reply=reply,
            session_id=session_id,
            action="open_booking_form",
            booking_type_hint=booking_type,
            booking_prefill=prefill,
        )

    # Regular chat - direct LLM
    result = chat(
        message=message,
        history=session["history"],
    )

    # Update history
    session["history"].append({"role": "user", "content": message})
    session["history"].append({"role": "assistant", "content": result["reply"]})

    # Keep history manageable
    if len(session["history"]) > 20:
        session["history"] = session["history"][-20:]

    # Auto-extract booking v ozadju — ne blokira odgovora
    background_tasks.add_task(_try_auto_save_inquiry, session_id, session)

    # Log info query
    _service.log_conversation(
        session_id=session_id,
        user_message=message,
        bot_response=result["reply"],
        intent="info_query",
    )

    return ChatResponse(reply=result["reply"], session_id=session_id)


@router.post("/stream")
async def chat_stream_endpoint(payload: ChatRequest, background_tasks: BackgroundTasks):
    """Streaming chat – pošlje besede sproti (SSE text/event-stream)."""
    session_id, session = _get_session(payload.session_id)
    message = payload.message.strip()

    # For streaming we only support info queries (not booking state machine)
    booking: BookingState | None = session.get("booking")
    if is_booking_active(booking):
        # Fall back to normal non-streaming for active bookings
        booking, reply = process_booking(booking, message)
        session["booking"] = booking
        _service.log_conversation(session_id=session_id, user_message=message, bot_response=reply, intent=f"booking_{booking.type}")
        if booking.step in ("confirmed", "cancelled"):
            session["booking"] = None
        async def _single():
            yield f"data: {reply}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(_single(), media_type="text/event-stream")

    booking_type = detect_booking_intent(message)

    full_reply_parts: list[str] = []

    async def _generate():
        nonlocal full_reply_parts
        import asyncio
        hint = booking_type if booking_type else None
        for chunk in chat_stream(message=message, history=session.get("history"), booking_type_hint=hint):
            full_reply_parts.append(chunk)
            # SSE format
            safe = chunk.replace("\n", "\\n")
            yield f"data: {safe}\n\n"
        yield "data: [DONE]\n\n"

        # After streaming: update history and log
        full_reply = "".join(full_reply_parts)
        session["history"].append({"role": "user", "content": message})
        session["history"].append({"role": "assistant", "content": full_reply})
        if len(session["history"]) > 20:
            session["history"] = session["history"][-20:]
        intent = f"open_booking_form_{booking_type}" if booking_type else "info_query"
        _service.log_conversation(session_id=session_id, user_message=message, bot_response=full_reply, intent=intent)
        if not booking_type:
            background_tasks.add_task(_try_auto_save_inquiry, session_id, session)

    return StreamingResponse(_generate(), media_type="text/event-stream", headers={"X-Session-Id": session_id})


def _try_auto_save_inquiry(session_id: str, session: dict) -> int | None:
    """
    Po vsakem chat odgovoru preveri ali ima pogovor dovolj podatkov za rezervacijo.
    Če ja → shrani v bazo in pošlji email. Samo enkrat na sejo.
    """
    # Ne shranjuj dvakrat za isto sejo
    if session.get("auto_saved"):
        return None

    history = session.get("history", [])
    if len(history) < 4:  # premalo pogovora
        return None

    # Sestavimo celoten pogovor za ekstrakcijo
    conversation_text = ""
    for msg in history[-16:]:
        role = "Uporabnik" if msg["role"] == "user" else "AI"
        conversation_text += f"{role}: {msg['content']}\n"

    # LLM ekstrakcija podatkov
    import os, json
    from openai import OpenAI
    from datetime import datetime as _dt
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    current_year = _dt.now().year
    extraction_prompt = f"""Iz spodnjega pogovora izvleci podatke o rezervaciji/povpraševanju.
Vrni SAMO JSON brez razlage. Če podatek manjka, daj null.
Zahtevani podatki: ime (vsaj priimek), kontakt (telefon ali email), datum, število oseb.
Če kateri koli od teh 4 podatkov manjka → vrni: {{"complete": false}}

POMEMBNO:
- Tekoče leto je {current_year}. Če leto ni eksplicitno navedeno, uporabi {current_year}.
- "število oseb" = skupaj oseb (odrasli + otroci), ni treba razčlenjevati.
- date format: DD.MM.YYYY

Format če je kompletno:
{{
  "complete": true,
  "booking_type": "table" ali "room",
  "name": "...",
  "phone": "..." ali null,
  "email": "..." ali null,
  "date": "DD.MM.YYYY",
  "people": 2,
  "time": "HH:MM" ali null,
  "note": "..." ali null
}}"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": extraction_prompt},
                {"role": "user", "content": conversation_text},
            ],
            max_tokens=300,
        )
        raw = (resp.choices[0].message.content or "").strip()

        # Parse JSON (včasih LLM doda ```json blok)
        raw = raw.strip().strip("```json").strip("```").strip()
        data = json.loads(raw)
    except Exception:
        return None

    if not data.get("complete"):
        return None

    # Shrani rezervacijo
    from app.booking.state_machine import BookingState, _save_reservation
    state = BookingState(
        type=data.get("booking_type", "table"),
        step="awaiting_confirm",
        date=data.get("date", ""),
        nights=0,
        time=data.get("time") or "",
        adults=int(data.get("people") or 1),
        children=0,
        name=data.get("name", ""),
        phone=data.get("phone") or "",
        email=data.get("email") or "",
        note=data.get("note") or "Povpraševanje zbrano v pogovoru z botom.",
    )

    reservation_id = _save_reservation(state, source="chatbot")
    if reservation_id:
        session["auto_saved"] = True
        # Zabeleži v pogovoru
        _service.log_conversation(
            session_id=session_id,
            user_message="[AUTO] Sistem je samodejno zaznal in shranil povpraševanje iz pogovora.",
            bot_response=f"Rezervacija #{reservation_id} samodejno shranjena (chatbot ekstrakcija).",
            intent="auto_extracted_booking",
        )
    return reservation_id
