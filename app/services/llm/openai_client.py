import json
from datetime import datetime, timezone

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.llm_report import LLMReport

RECENT_VERBATIM_MESSAGES = 120
MAX_VERBATIM_TEXT_CHARS = 600


def analyze_chat_with_llm(messages: list[dict]) -> dict:
    settings = get_settings()
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not configured.")

    client = OpenAI(api_key=settings.openai_api_key)
    compressed_context = _compress_context(client, messages, settings.openai_model)
    payload = _build_analysis_payload(messages, compressed_context)

    system_prompt = (
        "You analyze relationship communication patterns in chat logs. "
        "Use evidence only from provided messages. Do not invent quotes. "
        "Do not diagnose people and do not predict outcomes."
    )
    developer_prompt = (
        "Return JSON only. Match this exact schema with correct types: "
        "{mixed_signal_index:int(0..100), confidence:float(0..1), summary:str(2-4 sentences), "
        "timeline:[{timestamp:ISO8601,message:str,tags:[str],type:warm|cool|mixed}] max 10 items, "
        "stats:{initiation_percent:number,reply_delay_ratio:number,red_flags:int}, "
        "signals:[{name:str,score:0..1,explanation:str,evidence:[{timestamp:ISO8601,excerpt:str,sender:str}]}]}. "
        "Evidence excerpts must be direct text from provided messages. "
        "Timeline must contain AT MOST 10 items; if more candidates exist, include only the most significant moments."
    )

    raw = _request_json(
        client=client,
        model=settings.openai_model,
        system_prompt=system_prompt,
        developer_prompt=developer_prompt,
        user_payload=payload,
    )

    raw = _enforce_timeline_limit(raw)
    try:
        report = LLMReport.model_validate(raw)
    except ValidationError:
        repaired = _request_json_repair(client, settings.openai_model, raw)
        repaired = _enforce_timeline_limit(repaired)
        report = LLMReport.model_validate(repaired)

    normalized = report.model_dump(mode="json")
    normalized["timeline"] = normalized["timeline"][:10]
    return normalized


def _compress_context(client: OpenAI, messages: list[dict], model: str) -> str | None:
    if len(messages) <= RECENT_VERBATIM_MESSAGES:
        return None

    older = messages[:-RECENT_VERBATIM_MESSAGES]
    compact = [
        {
            "timestamp": _to_iso(row.get("ts")),
            "sender": str(row.get("sender", ""))[:80],
            "text": str(row.get("text", ""))[:220],
        }
        for row in older
    ]
    completion = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Summarize older chat context without adding new content. "
                    "Output JSON with keys summary and notable_events (array of short bullet strings)."
                ),
            },
            {"role": "user", "content": json.dumps({"messages": compact}, ensure_ascii=True)},
        ],
    )
    content = completion.choices[0].message.content or "{}"
    data = json.loads(content)
    summary = str(data.get("summary", "")).strip()
    notable = data.get("notable_events", [])
    notable_text = "; ".join(str(item) for item in notable[:8])
    merged = summary if not notable_text else f"{summary} Notable events: {notable_text}"
    return merged[:3000]


def _build_analysis_payload(messages: list[dict], compressed_context: str | None) -> dict:
    recent = messages[-RECENT_VERBATIM_MESSAGES:]
    recent_payload = [
        {
            "timestamp": _to_iso(row.get("ts")),
            "sender": str(row.get("sender", ""))[:80],
            "text": str(row.get("text", ""))[:MAX_VERBATIM_TEXT_CHARS],
        }
        for row in recent
    ]
    return {
        "context_policy": {
            "compressed_older_context": bool(compressed_context),
            "recent_verbatim_messages": len(recent_payload),
        },
        "older_context_summary": compressed_context,
        "recent_messages": recent_payload,
    }


def _request_json(
    client: OpenAI,
    model: str,
    system_prompt: str,
    developer_prompt: str,
    user_payload: dict,
) -> dict:
    completion = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": developer_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=True)},
        ],
    )
    content = completion.choices[0].message.content or "{}"
    return json.loads(content)


def _enforce_timeline_limit(payload: dict) -> dict:
    if isinstance(payload, dict) and isinstance(payload.get("timeline"), list):
        payload["timeline"] = payload["timeline"][:10]
    return payload


def _request_json_repair(client: OpenAI, model: str, invalid_json: dict) -> dict:
    completion = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Fix this JSON so it exactly matches the required schema and type constraints. "
                    "Return JSON only."
                ),
            },
            {"role": "user", "content": json.dumps(invalid_json, ensure_ascii=True)},
        ],
    )
    content = completion.choices[0].message.content or "{}"
    return json.loads(content)


def _to_iso(value: object) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    return str(value or "")
