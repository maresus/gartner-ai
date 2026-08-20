"""
Direct LLM chat - the core of V2 architecture.
One LLM call for info queries.
"""
from __future__ import annotations

import os
from pathlib import Path
from openai import OpenAI

from app.rag.search import get_context


_SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "system.txt"

# Model config from env (default: gpt-5.2)
_DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()


def _load_system_prompt() -> str:
    if _SYSTEM_PROMPT_PATH.exists():
        return _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
    return "Si pomočnik Domačije Kovačnik."


def chat(
    message: str,
    history: list[dict[str, str]] | None = None,
    client: OpenAI | None = None,
    model: str | None = None,
    booking_type_hint: str | None = None,
) -> dict[str, str]:
    """
    Main chat function for info queries.
    Returns {"reply": "..."}
    """
    if model is None:
        model = _DEFAULT_MODEL

    if client is None:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Get RAG context
    rag_context = get_context(message, top_k=3)

    # Build conversation
    system_prompt = _load_system_prompt()

    # Inject current date/day so bot knows "jutri", "danes", "ta vikend"...
    from datetime import datetime
    _DAYS_SL = ["ponedeljek", "torek", "sreda", "četrtek", "petek", "sobota", "nedelja"]
    now = datetime.now()
    today_day = _DAYS_SL[now.weekday()]
    tomorrow_day = _DAYS_SL[(now.weekday() + 1) % 7]
    system_prompt += (
        f"\n\n## Trenutni datum\n"
        f"Danes je {today_day}, {now.strftime('%-d. %-m. %Y')}. "
        f"Jutri je {tomorrow_day}. "
        f"Vikend je ta {_DAYS_SL[5]} in {_DAYS_SL[6]}."
    )

    if rag_context:
        system_prompt += f"\n\n## Dodatni kontekst iz baze znanja:\n{rag_context}"

    if booking_type_hint:
        hints = {
            "room": "Gost želi rezervirati SOBO. Odgovori toplo in osebno, nato naravno predlagaj: \"Izpolnite obrazec za rezervacijo — gumb je spodaj — pa vas pokličemo za potrditev.\"",
            "table": "Gost želi rezervirati MIZO (vikend kosilo, samo sobota in nedelja). Odgovori toplo, povej kaj je trenutno v ponudbi (srajčica 40 €), nato predlagaj: \"Izpolnite obrazec za povpraševanje — gumb je spodaj — Barbara vas bo kontaktirala in potrdila termin.\"",
            "brunch": "Gost želi BRUNCH. Brunch pripravljamo samo po dogovoru — ni standardna ponudba. Odgovori toplo, povej da ga z veseljem pripravimo po dogovoru, nato naravno reči: \"Izpolnite obrazec spodaj (izberite Brunch) — pokličemo vas in skupaj uredimo vse podrobnosti.\" NE omenjaj ur, jedilnika ali fiksnih cen — to dogovorimo skupaj.",
        }
        system_prompt += f"\n\n## NAVODILO ZA TA ODGOVOR:\n{hints.get(booking_type_hint, '')}"

    messages = [{"role": "system", "content": system_prompt}]

    # Add history (last 6 messages)
    if history:
        for msg in history[-6:]:
            messages.append(msg)

    messages.append({"role": "user", "content": message})

    # Single LLM call
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=450,
    )

    reply = (response.choices[0].message.content or "").strip()

    if not reply:
        reply = "Oprostite, nisem razumel vprašanja. Pokličite nas: 031 330 113"

    return {"reply": reply}


def chat_stream(
    message: str,
    history: list[dict[str, str]] | None = None,
    client: OpenAI | None = None,
    model: str | None = None,
    booking_type_hint: str | None = None,
):
    """Streaming version of chat – yields text chunks as they arrive."""
    if model is None:
        model = _DEFAULT_MODEL
    if client is None:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    rag_context = get_context(message, top_k=3)
    system_prompt = _load_system_prompt()

    from datetime import datetime
    _DAYS_SL = ["ponedeljek", "torek", "sreda", "četrtek", "petek", "sobota", "nedelja"]
    now = datetime.now()
    today_day = _DAYS_SL[now.weekday()]
    tomorrow_day = _DAYS_SL[(now.weekday() + 1) % 7]
    system_prompt += (
        f"\n\n## Trenutni datum\n"
        f"Danes je {today_day}, {now.strftime('%-d. %-m. %Y')}. "
        f"Jutri je {tomorrow_day}. "
        f"Vikend je ta {_DAYS_SL[5]} in {_DAYS_SL[6]}."
    )

    if rag_context:
        system_prompt += f"\n\n## Dodatni kontekst iz baze znanja:\n{rag_context}"

    if booking_type_hint:
        hints = {
            "room": "Gost želi rezervirati SOBO. Odgovori toplo in osebno, nato naravno predlagaj: \"Izpolnite obrazec za rezervacijo — gumb je spodaj — pa vas pokličemo za potrditev.\"",
            "table": "Gost želi rezervirati MIZO (vikend kosilo, samo sobota in nedelja). Odgovori toplo, povej kaj je trenutno v ponudbi (srajčica 40 €), nato predlagaj: \"Izpolnite obrazec za povpraševanje — gumb je spodaj — Barbara vas bo kontaktirala in potrdila termin.\"",
            "brunch": "Gost želi BRUNCH. Brunch pripravljamo samo po dogovoru — ni standardna ponudba. Odgovori toplo, povej da ga z veseljem pripravimo po dogovoru, nato naravno reči: \"Izpolnite obrazec spodaj (izberite Brunch) — pokličemo vas in skupaj uredimo vse podrobnosti.\" NE omenjaj ur, jedilnika ali fiksnih cen — to dogovorimo skupaj.",
        }
        system_prompt += f"\n\n## NAVODILO ZA TA ODGOVOR:\n{hints.get(booking_type_hint, '')}"

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        for msg in history[-6:]:
            messages.append(msg)
    messages.append({"role": "user", "content": message})

    try:
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=450,
            stream=True,
        )
        for chunk in stream:
            text = chunk.choices[0].delta.content
            if text:
                yield text
    except Exception as e:
        yield f"Oprostite, napaka: {e}"
