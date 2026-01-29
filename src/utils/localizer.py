import json
from typing import Dict, Any, List
from src.utils.gemini_client import GeminiClient


class Localizer:
    """Utility to translate AI-generated findings."""

    def __init__(self):
        self.client = GeminiClient()

    async def translate_results(self, results: Dict[str, Any], target_lang: str) -> Dict[str, Any]:
        """
        Translate AI-generated findings in results to the target language.
        If target_lang is 'en', and results are in 'en', returns as is.
        """
        # Simple heuristic: if 'rationale' in system_analysis is in the wrong language, translate it
        # Actually, let's just translate if target_lang is different from assessment lang
        # For now, we assume original is English.

        if target_lang == "en":
            return results

        # Create a deep copy
        localized = json.loads(json.dumps(results))

        # Fields to translate:
        # 1. results["phases"]["system_analysis"]["rationale"]
        # 2. Each item in results["phases"]["evidence_analysis"]["document_analyses"]:
        #    - "document_purpose"
        #    - "controls_addressed"[ID]["evidence_summary"]
        # 3. recommendations["high_priority"][]["action"]

        to_translate = []

        # System Analysis Rationale
        if "system_analysis" in localized.get("phases", {}):
            if "rationale" in localized["phases"]["system_analysis"]:
                to_translate.append(
                    ("sa_rationale", localized["phases"]["system_analysis"]["rationale"])
                )

        # Evidence Summaries
        if "evidence_analysis" in localized.get("phases", {}):
            for i, doc in enumerate(
                localized["phases"]["evidence_analysis"].get("document_analyses", [])
            ):
                if "document_purpose" in doc:
                    to_translate.append((f"doc_{i}_purpose", doc["document_purpose"]))
                for ctrl_id, ev in doc.get("controls_addressed", {}).items():
                    if "evidence_summary" in ev:
                        to_translate.append(
                            (f"doc_{i}_ctrl_{ctrl_id}_summary", ev["evidence_summary"])
                        )

        # Recommendations
        if "recommendations" in localized.get("phases", {}):
            for i, item in enumerate(
                localized["phases"]["recommendations"].get("high_priority", [])
            ):
                if "action" in item:
                    to_translate.append((f"rec_high_{i}_action", item["action"]))
            for i, item in enumerate(
                localized["phases"]["recommendations"].get("medium_priority", [])
            ):
                if "action" in item:
                    to_translate.append((f"rec_med_{i}_action", item["action"]))

        if not to_translate:
            return localized

        # Bulk translate strings
        prompt = f"""
        Translate the following technical security assessment findings from English to French.
        Maintain technical accuracy and professional tone for a Canadian Government audience.
        Return ONLY a JSON object mapping the keys back to the translated values.
        
        Strings to translate:
        {json.dumps(dict(to_translate), indent=2)}
        """

        try:
            response = await self.client.generate_async(prompt)
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()

            translations = json.loads(response)

            # Apply translations back
            if "sa_rationale" in translations:
                localized["phases"]["system_analysis"]["rationale"] = translations["sa_rationale"]

            for i, doc in enumerate(
                localized["phases"]["evidence_analysis"].get("document_analyses", [])
            ):
                if f"doc_{i}_purpose" in translations:
                    doc["document_purpose"] = translations[f"doc_{i}_purpose"]
                for ctrl_id, ev in doc.get("controls_addressed", {}).items():
                    if f"doc_{i}_ctrl_{ctrl_id}_summary" in translations:
                        ev["evidence_summary"] = translations[f"doc_{i}_ctrl_{ctrl_id}_summary"]

            if "recommendations" in localized.get("phases", {}):
                for i, item in enumerate(
                    localized["phases"]["recommendations"].get("high_priority", [])
                ):
                    if f"rec_high_{i}_action" in translations:
                        item["action"] = translations[f"rec_high_{i}_action"]
                for i, item in enumerate(
                    localized["phases"]["recommendations"].get("medium_priority", [])
                ):
                    if f"rec_med_{i}_action" in translations:
                        item["action"] = translations[f"rec_med_{i}_action"]

        except Exception as e:
            print(f"Localization failed: {e}")

        return localized
