"""
Core agentic loop — Groq (Llama 3.3-70B) with tool/function calling.
Groq uses the OpenAI-compatible API format for tool calls.
"""

import json
import os
import re
from dataclasses import dataclass, field

from groq import Groq, BadRequestError, APIStatusError
from dotenv import load_dotenv

from agent.system_prompt import SYSTEM_PROMPT, FALLBACK_SYSTEM_PROMPT
from agent.tool_registry import TOOLS, execute_tool

load_dotenv()

# Primary model — large, capable, used for all normal turns
_PRIMARY_MODEL  = "llama-3.3-70b-versatile"
# Fallback for tool_use_failed (bad JSON from primary)
_FALLBACK_MODEL = "llama-3.1-8b-instant"


# ---------------------------------------------------------------------------
# Convert Anthropic-style tool definitions → OpenAI/Groq format
# ---------------------------------------------------------------------------
def _to_groq_tools(tools: list) -> list:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in tools
    ]


_GROQ_TOOLS = _to_groq_tools(TOOLS)


def _clean_tool_arguments(raw: str) -> str:
    """
    Fix common JSON issues produced by Llama when generating tool call arguments:
    - Escaped apostrophes  (\\'  →  ')
    - Single-quoted strings  →  double-quoted strings
    """
    # Remove backslash-escaped apostrophes (e.g. "Dr Bimal\'s" → "Dr Bimal's")
    cleaned = raw.replace("\\'", "'")
    return cleaned


def _parse_tool_arguments(raw: str) -> dict:
    """Parse tool call arguments, cleaning common Llama JSON artefacts."""
    cleaned = _clean_tool_arguments(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Last resort: remove all backslash escapes before apostrophes
        fallback = re.sub(r"\\(?=')", "", cleaned)
        try:
            return json.loads(fallback)
        except json.JSONDecodeError:
            return {}


def _summarise_tool_result(tool_name: str, result: dict) -> dict:
    """
    Replace bulky tool results with a compact summary before storing in history.
    Full data is handled by the UI/session_state — the model only needs to know
    whether the call succeeded and a brief description of what was produced.
    """
    if tool_name == "generate_prompts" and result.get("status") == "success":
        cluster_prompts = result.get("cluster_prompts", {})
        summary = {c: f"{len(p)} prompts generated" for c, p in cluster_prompts.items()}
        return {
            "status": "success",
            "message": "Prompts generated successfully. The UI will display them for the user to select.",
            "clusters": summary,
        }

    if tool_name == "analyse_reference_image" and result.get("status") == "success":
        prompt_preview = result.get("prompt", "")[:200]
        return {
            "status": "success",
            "message": (
                "Reference image analysed. A ready-to-use image generation prompt has been produced. "
                "Show the full prompt to the user and tell them they can copy it directly into an image generation tool."
            ),
            "analysis_preview": result.get("analysis", "")[:300],
            "prompt_preview": prompt_preview,
        }

    if tool_name in ("generate_creative", "generate_template_creative") and result.get("status") == "success":
        # Prompt-only mode — return descriptions so the agent can show them
        if result.get("prompt_only"):
            prompts = result.get("prompts", [])
            return {
                "status": "success",
                "prompt_only": True,
                "prompt_count": len(prompts),
                "prompt_description": result.get("prompt_description", ""),
                "message": f"{len(prompts)} prompt variation(s) generated. Show each one to the user.",
            }
        images = result.get("images", [])
        return {
            "status": "success",
            "message": f"{len(images)} ad image(s) generated and shown to the user for approval.",
            "image_count": len(images),
        }

    if tool_name == "lookup_product" and result.get("status") == "found":
        p = result.get("product", {})
        return {
            "status": "found",
            "product_name": p.get("product_name", ""),
            "brand_name": p.get("brand_name", ""),
            "category": p.get("category", ""),
            "has_benefits": bool(p.get("benefits")),
            "has_problems": bool(p.get("problems")),
            "has_ingredients": bool(p.get("ingredients")),
            # Keep full product data so agent can offer autofill
            "product": p,
        }

    # Default — return as-is for small results (e.g. not_found, errors)
    return result


@dataclass
class AgentResponse:
    """Structured response returned to the UI after each agent turn."""
    text: str
    cluster_prompts: dict = field(default_factory=dict)
    template_prompts: list = field(default_factory=list)   # 3 doctor-template / reference variation descriptions
    analysis_meta: dict = field(default_factory=dict)       # raw analyse_reference_image result for saving to memory
    images: list = field(default_factory=list)
    awaiting_approval: bool = False
    approval_payload: dict = field(default_factory=dict)
    campaign_context: dict = field(default_factory=dict)


class AdAgent:
    """
    Stateful conversational agent backed by Groq Llama 3.3-70B.
    Falls back to Mixtral on tool_use_failed errors.
    One instance per user session.
    """

    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model  = _PRIMARY_MODEL
        self.conversation_history: list[dict] = []
        self._pending_images: list[dict] = []

    def reset(self):
        self.conversation_history = []
        self._pending_images = []
        self.model = _PRIMARY_MODEL  # reset to primary on new conversation

    def chat(self, user_message: str) -> AgentResponse:
        """
        Send a user message, run the agentic loop, return a structured response.
        Loops until the model stops calling tools.
        """
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
        })

        cluster_prompts: dict = {}
        template_prompts: list = []
        analysis_meta: dict = {}
        images: list = []
        campaign_context: dict = {}

        while True:
            try:
                # Fallback model has low TPM — use compact prompt + short history
                _sys = FALLBACK_SYSTEM_PROMPT if self.model == _FALLBACK_MODEL else SYSTEM_PROMPT
                _hist = self.conversation_history[-6:] if self.model == _FALLBACK_MODEL else self.conversation_history
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "system", "content": _sys}] + _hist,
                    tools=_GROQ_TOOLS,
                    tool_choice="auto",
                    max_tokens=1024 if self.model == _FALLBACK_MODEL else 4096,
                )
            except BadRequestError as e:
                # Groq returns 400 tool_use_failed when Llama produces invalid JSON
                # in the tool call arguments
                if "tool_use_failed" in str(e):
                    if self.model != _FALLBACK_MODEL:
                        # First failure — switch to fallback model and retry
                        print(f"[Agent] tool_use_failed on {self.model} — retrying with {_FALLBACK_MODEL}")
                        self.model = _FALLBACK_MODEL
                        continue
                    else:
                        # Fallback also failed — disable tools, get plain text recovery response
                        print(f"[Agent] tool_use_failed on fallback too — retrying with tool_choice=none")
                        _sys = FALLBACK_SYSTEM_PROMPT
                        _hist = self.conversation_history[-4:]
                        recovery = self.client.chat.completions.create(
                            model=_FALLBACK_MODEL,
                            messages=[{"role": "system", "content": _sys}] + _hist,
                            max_tokens=512,
                        )
                        text = recovery.choices[0].message.content or (
                            "I had trouble processing that. Could you confirm all the required details "
                            "(product name, problems, solutions, and theme) so I can generate your prompts?"
                        )
                        return AgentResponse(text=text)
                raise
            except APIStatusError as e:
                # 413 = request too large — aggressively trim tool result messages
                # (they hold the bulk of tokens: full prompt JSON, image paths, etc.)
                if e.status_code == 413:
                    before = len(self.conversation_history)
                    # Drop all tool-role messages except the very last one
                    tool_indices = [i for i, m in enumerate(self.conversation_history) if m.get("role") == "tool"]
                    if len(tool_indices) > 1:
                        # Remove all but the last tool result
                        drop = set(tool_indices[:-1])
                        self.conversation_history = [m for i, m in enumerate(self.conversation_history) if i not in drop]
                        print(f"[Agent] 413 — dropped {len(drop)} old tool results ({before} → {len(self.conversation_history)} turns), retrying")
                        continue
                    elif len(self.conversation_history) > 4:
                        # No tool results to drop — hard-trim to last 4 turns
                        self.conversation_history = self.conversation_history[-4:]
                        print(f"[Agent] 413 — hard-trimmed history to 4 turns, retrying")
                        continue
                    else:
                        raise
                raise

            message       = response.choices[0].message
            finish_reason = response.choices[0].finish_reason

            # Build assistant history entry
            assistant_msg: dict = {
                "role":    "assistant",
                "content": message.content or "",
            }
            if message.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id":   tc.id,
                        "type": "function",
                        "function": {
                            "name":      tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ]
            self.conversation_history.append(assistant_msg)

            if finish_reason == "tool_calls" and message.tool_calls:
                for tc in message.tool_calls:
                    # Parse arguments — handles escaped apostrophes and other artefacts
                    inputs = _parse_tool_arguments(tc.function.arguments)

                    result = execute_tool(tc.function.name, inputs)

                    if tc.function.name == "generate_prompts" and result.get("status") == "success":
                        cluster_prompts = result.get("cluster_prompts", {})
                        campaign_context = {
                            k: v for k, v in inputs.items()
                            if k not in ("num_variations", "product_image", "person_image")
                        }

                    if tc.function.name == "generate_template_creative" and result.get("status") == "success":
                        if result.get("prompt_only"):
                            # Capture the 4 variation descriptions for the UI widget
                            template_prompts = result.get("prompts", [])
                        else:
                            images = result.get("images", [])
                            self._pending_images = images

                    if tc.function.name == "analyse_reference_image" and result.get("status") == "success":
                        # Surface the generated prompt in the template_prompts widget
                        gen_prompt = result.get("prompt", "")
                        if gen_prompt:
                            template_prompts = [gen_prompt]
                        analysis_meta = {
                            "analysis":        result.get("analysis", ""),
                            "prompt":          gen_prompt,
                            "image_path":      inputs.get("image_path", ""),
                            "prompts":         [gen_prompt] if gen_prompt else [],
                            "product_context": "",
                        }

                    if tc.function.name == "generate_creative" and result.get("status") == "success":
                        images = result.get("images", [])
                        self._pending_images = images

                    self.conversation_history.append({
                        "role":         "tool",
                        "tool_call_id": tc.id,
                        "content":      json.dumps(_summarise_tool_result(tc.function.name, result)),
                    })

            else:
                text             = message.content or ""
                awaiting_approval = bool(images)
                approval_payload  = {"images": images} if images else {}

                return AgentResponse(
                    text=text,
                    cluster_prompts=cluster_prompts,
                    template_prompts=template_prompts,
                    analysis_meta=analysis_meta,
                    images=[img["path"] for img in images],
                    awaiting_approval=awaiting_approval,
                    approval_payload=approval_payload,
                    campaign_context=campaign_context,
                )
