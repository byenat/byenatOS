import os
import requests
from typing import Dict, Any, List, Optional


class ByenatOS:
    def __init__(self, api_base: Optional[str] = None, api_key: Optional[str] = None):
        self.api_base = api_base or os.getenv("BYENATOS_API_BASE", "http://localhost:8080")
        self.api_key = api_key or os.getenv("BYENATOS_API_KEY", "")
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})
        self.session.headers.update({"Content-Type": "application/json"})

    def get_personalized_prompt(self, user_id: str, current_request: str = "") -> str:
        payload = {
            "user_id": user_id,
            "current_request": current_request,
            "include_details": False,
            "context_type": "prompt"
        }
        resp = self.session.post(f"{self.api_base}/api/psp/context", json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        context = data.get("context", {})
        return self._format_system_prompt(context)

    def submit_hinata_batch(self, app_id: str, user_id: str, hinata_batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        payload = {
            "app_id": app_id,
            "user_id": user_id,
            "hinata_batch": hinata_batch,
            "processing_options": {}
        }
        resp = self.session.post(f"{self.api_base}/api/hinata/submit", json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()

    def _format_system_prompt(self, context: Dict[str, Any]) -> str:
        lines = ["# Personal System Prompt", ""]
        core = context.get("core_interests", [])
        goals = context.get("current_goals", [])
        prefs = context.get("learning_preferences", [])
        style = context.get("communication_style", [])
        focus = context.get("high_priority_focus", [])
        relevant = context.get("relevant_context", [])

        if core:
            lines.append("## Core Interests")
            lines.extend(f"- {c}" for c in core[:5])
            lines.append("")
        if goals:
            lines.append("## Current Goals")
            lines.extend(f"- {g}" for g in goals[:3])
            lines.append("")
        if prefs:
            lines.append("## Learning Preferences")
            lines.extend(f"- {p}" for p in prefs[:3])
            lines.append("")
        if style:
            lines.append("## Communication Style")
            lines.extend(f"- {s}" for s in style[:2])
            lines.append("")
        if focus:
            lines.append("## High Priority Focus")
            lines.extend(f"- {f}" for f in focus[:3])
            lines.append("")
        if relevant:
            lines.append("## Relevant Context")
            lines.extend(f"- {r}" for r in relevant[:5])
            lines.append("")
        return "\n".join(lines)