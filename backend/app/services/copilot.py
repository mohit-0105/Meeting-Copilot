import json
import logging
import uuid
import re
from typing import List, Optional, Tuple, Dict
from collections import Counter
import httpx
from app.models.schemas import (
    WSCopilotResponse,
    ActionItem,
    MeetingSummary,
    MeetingInsights,
    SpeakerStat,
    AgendaItem,
    AgendaCheckResponse
)
from app.core.config import settings

logger = logging.getLogger("meeting-copilot.copilot")

class CopilotService:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.gemini_key = settings.GEMINI_API_KEY
        self.openai_key = settings.OPENAI_API_KEY

    def _build_context(self, segments: List[dict], max_segments: int = 50) -> str:
        """Formats the most recent transcript segments into readable conversation context."""
        recent = segments[-max_segments:] if len(segments) > max_segments else segments
        if not recent:
            return "No transcript recorded yet."
        
        context_lines = []
        for s in recent:
            timestamp = s.get("timestamp", "00:00")
            speaker = s.get("speaker", "Speaker")
            text = s.get("text", "")
            context_lines.append(f"[{timestamp}] {speaker}: {text}")
        return "\n".join(context_lines)

    async def answer_query(self, query: str, recent_segments: List[dict]) -> WSCopilotResponse:
        """
        Answers questions about what has been said in the meeting so far.
        """
        context = self._build_context(recent_segments)

        # 1. Google Gemini API
        if (self.provider == "gemini" or not self.provider or self.provider == "auto") and self.gemini_key:
            try:
                prompt = (
                    f"You are Meeting Copilot, a real-time AI assistant listening to a live meeting.\n"
                    f"Here is the transcript of the meeting so far:\n"
                    f"---\n{context}\n---\n\n"
                    f"User Question: {query}\n\n"
                    f"Provide a concise, accurate answer based strictly on what was said. "
                    f"Include any relevant timestamp references (e.g. ['00:15']) mentioned in the transcript."
                )
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        url,
                        json={"contents": [{"parts": [{"text": prompt}]}]}
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_answer = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                        refs = re.findall(r"\b\d{2}:\d{2}\b", raw_answer)
                        return WSCopilotResponse(query=query, answer=raw_answer, references=list(set(refs)))
                    else:
                        logger.warning(f"Gemini API returned status {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.error(f"Gemini query answer failed: {e}")

        # 2. OpenAI API
        if (self.provider == "openai" or not self.provider or self.provider == "auto") and self.openai_key:
            try:
                system_prompt = (
                    "You are Meeting Copilot, a real-time AI assistant for live meetings. "
                    "Answer user queries accurately based on the provided live transcript. "
                    "Keep answers concise and cite timestamp references when available."
                )
                user_msg = f"Live Transcript:\n{context}\n\nQuestion: {query}"
                url = "https://api.openai.com/v1/chat/completions"
                headers = {"Authorization": f"Bearer {self.openai_key}"}
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_msg}
                    ],
                    "temperature": 0.2
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_answer = data["choices"][0]["message"]["content"].strip()
                        refs = re.findall(r"\b\d{2}:\d{2}\b", raw_answer)
                        return WSCopilotResponse(query=query, answer=raw_answer, references=list(set(refs)))
                    else:
                        logger.warning(f"OpenAI API returned status {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.error(f"OpenAI query answer failed: {e}")

        # 3. Dynamic Mock Answer
        matched_points = []
        q_words = set(re.findall(r"\w+", query.lower()))
        for seg in recent_segments:
            text = seg.get("text", "")
            seg_words = set(re.findall(r"\w+", text.lower()))
            overlap = q_words.intersection(seg_words) - {"the", "a", "is", "what", "did", "about", "to", "in", "for"}
            if overlap:
                matched_points.append(f"{seg.get('speaker', 'Speaker')} mentioned: \"{text}\"")

        if matched_points:
            answer = f"According to the meeting record: " + " ".join(matched_points[:2])
        else:
            answer = (
                "Based on the discussion so far, the team discussed supply chain challenges "
                "and Sarah scheduled a deep dive for tomorrow at 2 PM to resolve it."
            )

        refs = [seg.get("timestamp", "00:00") for seg in recent_segments[:2]] if recent_segments else ["00:15", "00:40"]
        return WSCopilotResponse(
            query=query,
            answer=answer,
            references=refs
        )

    async def detect_action_item(self, text: str, speaker: str = "Unknown") -> Optional[ActionItem]:
        """
        Analyzes a segment for potential action items, assignees, and deadlines.
        """
        lowered = text.lower()
        trigger_keywords = ["schedule", "follow up", "will do", "need to", "action item", "todo", "assign", "prepare", "review"]
        
        if any(keyword in lowered for keyword in trigger_keywords):
            due_date = "Next Sync"
            if "tomorrow" in lowered:
                due_date = "Tomorrow"
                time_match = re.search(r"(\d{1,2}\s*(?:am|pm|:00))", lowered)
                if time_match:
                    due_date += f" at {time_match.group(1).upper()}"
            elif "by next week" in lowered or "next week" in lowered:
                due_date = "Next Week"
            elif "by friday" in lowered or "friday" in lowered:
                due_date = "Friday EOD"

            cleaned_title = text.strip()
            if len(cleaned_title) > 60:
                cleaned_title = cleaned_title[:57] + "..."

            return ActionItem(
                id=f"act_{uuid.uuid4().hex[:6]}",
                title=f"Action: {cleaned_title}",
                assignee=speaker if speaker != "Unknown" else "Sarah K.",
                due_date=due_date,
                status="pending"
            )
        return None

    async def generate_summary(
        self,
        meeting_id: str,
        title: str,
        segments: List[dict],
        action_items: List[ActionItem]
    ) -> MeetingSummary:
        """
        Generates structured executive summary, key points, and finalized action items.
        """
        context = self._build_context(segments)

        # 1. Google Gemini API
        if (self.provider == "gemini" or not self.provider or self.provider == "auto") and self.gemini_key:
            try:
                prompt = (
                    f"You are Meeting Copilot. Summarize the following meeting titled '{title}'.\n"
                    f"Transcript:\n{context}\n\n"
                    f"Provide response in strict JSON with keys:\n"
                    f"- 'summary': string (2-3 sentence executive summary)\n"
                    f"- 'key_points': list of 3-5 strings with key takeaways and decisions"
                )
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                        json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
                        if json_match:
                            parsed = json.loads(json_match.group(0))
                            return MeetingSummary(
                                meeting_id=meeting_id,
                                title=title,
                                summary=parsed.get("summary", ""),
                                key_points=parsed.get("key_points", []),
                                action_items=action_items
                            )
            except Exception as e:
                logger.error(f"Gemini summary generation failed: {e}")

        # 2. OpenAI API
        if (self.provider == "openai" or not self.provider or self.provider == "auto") and self.openai_key:
            try:
                system_prompt = (
                    "You are Meeting Copilot. Respond strictly with valid JSON containing:\n"
                    "{\n  \"summary\": \"Executive summary...\",\n  \"key_points\": [\"point 1\", \"point 2\"]\n}"
                )
                user_msg = f"Meeting Title: {title}\nTranscript:\n{context}"
                url = "https://api.openai.com/v1/chat/completions"
                headers = {"Authorization": f"Bearer {self.openai_key}"}
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_msg}
                    ],
                    "temperature": 0.2
                }
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_content = data["choices"][0]["message"]["content"].strip()
                        json_match = re.search(r"\{.*\}", raw_content, re.DOTALL)
                        if json_match:
                            parsed = json.loads(json_match.group(0))
                            return MeetingSummary(
                                meeting_id=meeting_id,
                                title=title,
                                summary=parsed.get("summary", ""),
                                key_points=parsed.get("key_points", []),
                                action_items=action_items
                            )
            except Exception as e:
                logger.error(f"OpenAI summary generation failed: {e}")

        # Fallback dynamic summary
        key_points = []
        if segments:
            for s in segments[:4]:
                speaker = s.get("speaker", "Attendee")
                text = s.get("text", "")
                if text:
                    key_points.append(f"{speaker}: {text}")
        if not key_points:
            key_points = [
                "Project Gamma API integration is progressing normally.",
                "International logistics bottleneck identified as a critical dependency.",
                "Sarah K. convened a working group for tomorrow at 2 PM."
            ]

        return MeetingSummary(
            meeting_id=meeting_id,
            title=title,
            summary=f"Strategic sync on '{title}' focusing on roadmap execution, key deliverables, and cross-team alignment.",
            key_points=key_points,
            action_items=action_items
        )

    async def calculate_insights(self, meeting_id: str, segments: List[dict]) -> MeetingInsights:
        """
        Analyzes meeting participation, speech distribution, sentiment, and key topics.
        """
        if not segments:
            return MeetingInsights(
                meeting_id=meeting_id,
                total_duration_estimate="00:00",
                total_words=0,
                speakers=[],
                sentiment="neutral",
                key_topics=[],
                engagement_score=50
            )

        speaker_counts: Dict[str, int] = Counter()
        speaker_words: Dict[str, int] = Counter()
        all_words: List[str] = []

        stop_words = {
            "the", "a", "an", "and", "or", "to", "in", "for", "of", "with", "at", "by", "from",
            "is", "are", "was", "were", "we", "i", "you", "they", "it", "that", "this", "on", "our"
        }

        for s in segments:
            speaker = s.get("speaker", "Speaker")
            text = s.get("text", "")
            words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", text)]
            speaker_counts[speaker] += 1
            speaker_words[speaker] += len(words)
            all_words.extend([w for w in words if w not in stop_words])

        total_words = sum(speaker_words.values()) or 1
        speaker_stats: List[SpeakerStat] = []

        for speaker, seg_count in speaker_counts.items():
            words_count = speaker_words[speaker]
            percentage = round((words_count / total_words) * 100, 1)
            # Estimate speaking time: ~130 words per minute -> ~2.16 words per second
            talk_seconds = int(words_count / 2.16) if words_count > 0 else seg_count * 5
            speaker_stats.append(SpeakerStat(
                speaker=speaker,
                segment_count=seg_count,
                word_count=words_count,
                talk_time_seconds=talk_seconds,
                talk_time_percentage=percentage
            ))

        # Sort speakers by talk time descending
        speaker_stats.sort(key=lambda s: s.talk_time_percentage, reverse=True)

        # Most common topics (keywords)
        top_keywords = [w.capitalize() for w, _ in Counter(all_words).most_common(5)]
        if not top_keywords:
            top_keywords = ["Strategy", "Roadmap", "Integration", "Logistics"]

        # Calculate estimated duration
        total_seconds = sum(s.talk_time_seconds for s in speaker_stats)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        duration_str = f"{minutes:02d}:{seconds:02d}"

        # Sentiment heuristics
        full_text = " ".join(s.get("text", "") for s in segments).lower()
        if any(w in full_text for w in ["bottleneck", "delay", "challenges", "urgent", "contingency"]):
            sentiment = "collaborative" if "agree" in full_text or "schedule" in full_text else "urgent"
        elif any(w in full_text for w in ["great", "excellent", "progressing", "welcome"]):
            sentiment = "positive"
        else:
            sentiment = "collaborative"

        # Engagement score based on balanced participation
        max_pct = max((s.talk_time_percentage for s in speaker_stats), default=100)
        engagement = max(60, min(95, int(100 - (max_pct - 35))))

        return MeetingInsights(
            meeting_id=meeting_id,
            total_duration_estimate=duration_str,
            total_words=total_words,
            speakers=speaker_stats,
            sentiment=sentiment,
            key_topics=top_keywords,
            engagement_score=engagement
        )

    async def check_agenda(self, meeting_id: str, agenda_topics: List[str], segments: List[dict]) -> AgendaCheckResponse:
        """
        Compares predefined agenda topics against meeting transcript to identify covered topics.
        """
        items: List[AgendaItem] = []
        full_text_entries = [(s.get("timestamp", "00:00"), s.get("text", "").lower()) for s in segments]

        for topic in agenda_topics:
            topic_words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", topic)]
            covered = False
            mentioned_at = None

            for timestamp, seg_text in full_text_entries:
                if any(w in seg_text for w in topic_words):
                    covered = True
                    mentioned_at = timestamp
                    break

            items.append(AgendaItem(
                topic=topic,
                covered=covered,
                mentioned_at=mentioned_at
            ))

        completed_count = sum(1 for i in items if i.covered)
        return AgendaCheckResponse(
            meeting_id=meeting_id,
            total_agenda_items=len(agenda_topics),
            completed_items=completed_count,
            items=items
        )

    async def generate_nudges(self, meeting_id: str, segments: List[dict], agenda: List[str]) -> List[str]:
        """
        Generates smart proactive suggestions / follow-up questions for the meeting facilitator.
        """
        if not segments:
            return ["Review agenda topics to begin the meeting effectively."]

        last_texts = " ".join([s.get("text", "") for s in segments[-4:]]).lower()
        nudges = []

        if "delay" in last_texts or "bottleneck" in last_texts or "challenge" in last_texts:
            nudges.append("Ask the team: 'What is the immediate contingency plan if the delay extends by 2 weeks?'")
        if "budget" in last_texts or "vendor" in last_texts or "quote" in last_texts:
            nudges.append("Clarify: 'Who has final budget sign-off for the vendor choice?'")
        if "tomorrow" in last_texts or "schedule" in last_texts:
            nudges.append("Confirm: 'Has a calendar invite been sent to all essential stakeholders?'")
        
        # Check unaddressed agenda
        if agenda:
            for item in agenda[:2]:
                if not any(word in last_texts for word in item.lower().split() if len(word) > 3):
                    nudges.append(f"Agenda Reminder: Ensure '{item}' is addressed before concluding.")

        if not nudges:
            nudges = [
                "Prompt quiet participants for input on the current proposal.",
                "Verify if the current timeline aligns with product launch goals."
            ]
        return nudges[:3]

    def export_html(self, meeting_title: str, meeting_id: str, summary_text: str, key_points: List[str], action_items: List[ActionItem], segments: List[dict]) -> str:
        """
        Renders a stunning modern HTML executive summary dashboard.
        """
        actions_html = "".join([
            f"<li style='margin-bottom:8px;'><input type='checkbox' {'checked' if a.status=='completed' else ''} disabled/> "
            f"<strong>{a.title}</strong> — <em>@{a.assignee}</em> (Due: {a.due_date or 'TBD'})</li>"
            for a in action_items
        ]) or "<li><em>No action items recorded.</em></li>"

        points_html = "".join([f"<li style='margin-bottom:6px;'>{kp}</li>" for kp in key_points])

        segments_html = "".join([
            f"<tr><td style='padding:8px; border-bottom:1px solid #e2e8f0; color:#64748b; font-family:monospace; width:80px;'>{s.get('timestamp','00:00')}</td>"
            f"<td style='padding:8px; border-bottom:1px solid #e2e8f0; font-weight:600; color:#2563eb; width:120px;'>{s.get('speaker','Speaker')}</td>"
            f"<td style='padding:8px; border-bottom:1px solid #e2e8f0; color:#1e293b;'>{s.get('text','')}</td></tr>"
            for s in segments
        ]) or "<tr><td colspan='3' style='padding:12px; text-align:center;'>No transcript lines recorded.</td></tr>"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Meeting Copilot — {meeting_title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #f8fafc; color: #0f172a; margin: 0; padding: 40px; }}
        .container {{ max-width: 900px; margin: 0 auto; background: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); padding: 40px; border: 1px solid #e2e8f0; }}
        .header {{ border-bottom: 2px solid #f1f5f9; padding-bottom: 24px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center; }}
        .badge {{ background: #eff6ff; color: #1d4ed8; padding: 6px 12px; border-radius: 20px; font-size: 13px; font-weight: 600; }}
        h1 {{ margin: 0 0 6px 0; font-size: 26px; }}
        h2 {{ font-size: 18px; color: #334155; margin-top: 28px; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; }}
        .summary-box {{ background: #f8fafc; border-left: 4px solid #3b82f6; padding: 16px; border-radius: 4px; font-size: 15px; line-height: 1.6; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
        ul {{ padding-left: 20px; line-height: 1.6; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>📋 {meeting_title}</h1>
                <div style="color: #64748b; font-size: 14px;">Meeting ID: <code>{meeting_id}</code></div>
            </div>
            <div class="badge">Completed • AI Summary</div>
        </div>
        <h2>📝 Executive Summary</h2>
        <div class="summary-box">{summary_text}</div>
        <h2>💡 Key Decisions & Points</h2>
        <ul>{points_html}</ul>
        <h2>✅ Action Items</h2>
        <ul style="list-style: none; padding-left: 0;">{actions_html}</ul>
        <h2>🎙️ Transcript Log</h2>
        <table>{segments_html}</table>
    </div>
</body>
</html>"""

    def format_slack_blocks(self, meeting_title: str, summary_text: str, action_items: List[ActionItem]) -> dict:
        """Formats meeting recap for Slack Incoming Webhooks."""
        actions_text = "\n".join([f"• {'[x]' if a.status=='completed' else '[ ]'} *{a.title}* (@{a.assignee})" for a in action_items]) or "_No actions_"
        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"📋 Meeting Summary: {meeting_title}"}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Executive Summary:*\n{summary_text}"}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Action Items:*\n{actions_text}"}
                }
            ]
        }

copilot_service = CopilotService()
