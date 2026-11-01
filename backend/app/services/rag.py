import re
import logging
from typing import List, Dict, Optional
import httpx
from app.db.database import db
from app.core.config import settings

logger = logging.getLogger("meeting-copilot.rag")

class RAGService:
    def __init__(self):
        self.gemini_key = settings.GEMINI_API_KEY
        self.openai_key = settings.OPENAI_API_KEY

    async def search_meetings(self, query: str) -> List[Dict]:
        """
        Searches all meetings transcripts using query terms.
        Returns matching segments with meeting metadata and relevance score.
        """
        words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", query)]
        if not words:
            return []

        all_results = []
        seen_ids = set()

        for word in words:
            matches = await db.search_all_transcripts(word)
            for m in matches:
                if m["id"] not in seen_ids:
                    seen_ids.add(m["id"])
                    # Simple BM25-like relevance scoring
                    text_lower = m["text"].lower()
                    score = sum(text_lower.count(w) for w in words)
                    m["relevance_score"] = score
                    all_results.append(m)

        all_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return all_results[:15]

    async def answer_cross_meeting_query(self, query: str) -> Dict:
        """
        Synthesizes an answer across all historical meetings using retrieved context.
        """
        matches = await self.search_meetings(query)
        if not matches:
            return {
                "query": query,
                "answer": "No historical meeting discussions found matching your query.",
                "sources": []
            }

        context_snippets = []
        sources = []
        for match in matches[:5]:
            snippet = f"[{match.get('meeting_title', 'Meeting')}] {match.get('speaker', 'Speaker')} ({match.get('timestamp', '00:00')}): {match.get('text', '')}"
            context_snippets.append(snippet)
            sources.append({
                "meeting_id": match.get("meeting_id"),
                "meeting_title": match.get("meeting_title"),
                "timestamp": match.get("timestamp"),
                "speaker": match.get("speaker"),
                "text": match.get("text")
            })

        context_text = "\n".join(context_snippets)

        # 1. Gemini LLM Cross-Meeting Synthesis
        if self.gemini_key:
            try:
                prompt = (
                    f"You are Meeting Copilot Cross-Meeting Intelligence.\n"
                    f"Answer this query using the following excerpts from historical meetings:\n"
                    f"---\n{context_text}\n---\n\n"
                    f"Query: {query}\n\n"
                    f"Provide a clear, synthesized answer citing the meeting title and speakers when relevant."
                )
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
                    if resp.status_code == 200:
                        data = resp.json()
                        answer = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                        return {
                            "query": query,
                            "answer": answer,
                            "sources": sources
                        }
            except Exception as e:
                logger.error(f"Gemini RAG query failed: {e}")

        # 2. OpenAI LLM Cross-Meeting Synthesis
        if self.openai_key:
            try:
                system_prompt = (
                    "You are Meeting Copilot Cross-Meeting Intelligence. "
                    "Synthesize information from multiple meetings to answer user questions clearly."
                )
                user_msg = f"Historical Meetings Excerpts:\n{context_text}\n\nQuery: {query}"
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
                        answer = data["choices"][0]["message"]["content"].strip()
                        return {
                            "query": query,
                            "answer": answer,
                            "sources": sources
                        }
            except Exception as e:
                logger.error(f"OpenAI RAG query failed: {e}")

        # Fallback Synthesis
        top_snippet = matches[0]
        answer = (
            f"Found discussion in '{top_snippet.get('meeting_title')}': "
            f"{top_snippet.get('speaker')} noted '{top_snippet.get('text')}' at [{top_snippet.get('timestamp')}]."
        )
        return {
            "query": query,
            "answer": answer,
            "sources": sources
        }

rag_service = RAGService()

