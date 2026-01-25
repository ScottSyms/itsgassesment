"""Main coordinator agent orchestrating the ITSG-33 assessment."""

import os
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.utils.gemini_client import GeminiClient
from src.utils.document_parser import DocumentParser


class ITSG33Coordinator:
    """Coordinator for ITSG-33 accreditation process."""

    def __init__(self):
        """Initialize coordinator."""
        self.gemini = GeminiClient()
        self.doc_parser = DocumentParser()
        self.controls_data = self._load_controls()

    def _load_controls(self) -> List[Dict[str, Any]]:
        """Load ITSG-33 controls from data file."""
        data_path = Path(__file__).parent.parent.parent / "data" / "itsg33_controls.json"
        if data_path.exists():
            with open(data_path, "r") as f:
                return json.load(f)
        return []

    def get_controls_for_profile(self, profile: int) -> List[Dict[str, Any]]:
        """Get all controls required for a given profile level."""
        return [c for c in self.controls_data if c.get("profile", 1) <= profile]

    async def run_assessment(
        self,
        conops: str,
        documents: List[Dict[str, Any]],
        diagrams: List[Dict[str, Any]],
        client_id: str,
    ) -> Dict[str, Any]:
        """
        Run complete ITSG-33 assessment.

        Args:
            conops: Concept of operations document
            documents: List of document metadata with content
            diagrams: List of diagram metadata
            client_id: Client identifier

        Returns:
            Complete assessment results
        """
        results = {
            "client_id": client_id,
            "status": "in_progress",
            "phases": {},
        }

        try:
            # Phase 1: Analyze system and determine profile
            system_analysis = await self._analyze_system(conops, documents)
            results["phases"]["system_analysis"] = system_analysis
            profile = system_analysis.get("recommended_profile", 2)

            # Phase 2: Get required controls for profile
            required_controls = self.get_controls_for_profile(profile)
            results["phases"]["required_controls"] = {
                "profile": profile,
                "total_controls": len(required_controls),
                "controls_by_family": self._group_controls_by_family(required_controls),
            }

            # Phase 3: Analyze each document for evidence
            evidence_analysis = await self._analyze_documents_for_evidence(
                documents, required_controls
            )
            results["phases"]["evidence_analysis"] = evidence_analysis

            # Phase 4: Calculate control coverage
            coverage = self._calculate_coverage(required_controls, evidence_analysis)
            results["phases"]["coverage"] = coverage

            # Phase 5: Generate recommendations
            recommendations = await self._generate_recommendations(
                coverage, required_controls
            )
            results["phases"]["recommendations"] = recommendations

            results["status"] = "completed"
            results["summary"] = {
                "profile": profile,
                "total_controls": len(required_controls),
                "controls_with_evidence": coverage["controls_with_evidence"],
                "controls_partial": coverage["controls_partial"],
                "controls_missing": coverage["controls_missing"],
                "coverage_percentage": coverage["coverage_percentage"],
            }

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            import traceback
            results["traceback"] = traceback.format_exc()

        return results

    async def _analyze_system(
        self, conops: str, documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze system to determine security profile."""
        # Combine document content for context
        doc_content = ""
        for doc in documents[:3]:
            if "content" in doc:
                doc_content += f"\n\n--- {doc.get('filename', 'Document')} ---\n"
                doc_content += doc["content"][:3000]

        prompt = f"""Analyze this system and determine the appropriate ITSG-33 security profile.

CONOPS/System Description:
{conops[:5000] if conops else "No CONOPS provided"}

Additional Documentation:
{doc_content[:8000]}

Based on the above, determine:

1. SYSTEM TYPE: What kind of system is this? (e.g., web application, internal tool, data processing system)

2. DATA SENSITIVITY: What types of data does this system handle?
   - Classify as: Unclassified, Protected A, Protected B, Protected C, or Classified

3. SECURITY CATEGORIZATION (rate each as Low, Moderate, or High):
   - Confidentiality: How sensitive is the information?
   - Integrity: How critical is data accuracy?
   - Availability: How critical is system uptime?

4. RECOMMENDED PROFILE:
   - Profile 1 (Low): Basic security for low-sensitivity systems
   - Profile 2 (Moderate): Standard security for most government systems
   - Profile 3 (High): Enhanced security for sensitive/critical systems

5. RATIONALE: Explain why you recommend this profile

Return your analysis as JSON with these exact keys:
{{
    "system_type": "description of system type",
    "data_classification": "classification level",
    "confidentiality": "Low|Moderate|High",
    "integrity": "Low|Moderate|High",
    "availability": "Low|Moderate|High",
    "recommended_profile": 1|2|3,
    "rationale": "explanation for profile recommendation"
}}
"""

        try:
            response = await self.gemini.generate_async(prompt)
            # Try to parse JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                analysis = json.loads(response[json_start:json_end])
                return analysis
        except Exception as e:
            pass

        # Default to Profile 2 if analysis fails
        return {
            "system_type": "Unknown",
            "data_classification": "Protected B",
            "confidentiality": "Moderate",
            "integrity": "Moderate",
            "availability": "Moderate",
            "recommended_profile": 2,
            "rationale": "Default profile assigned due to insufficient information",
        }

    def _group_controls_by_family(
        self, controls: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """Group controls by family."""
        families = {}
        for control in controls:
            family = control.get("family", "Unknown")
            if family not in families:
                families[family] = []
            families[family].append(control.get("id", ""))
        return families

    async def _analyze_documents_for_evidence(
        self, documents: List[Dict[str, Any]], required_controls: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze each document to find evidence for controls."""
        evidence_map = {}  # control_id -> list of evidence items
        document_analyses = []

        for doc in documents:
            if "content" not in doc or not doc["content"]:
                continue

            doc_analysis = await self._analyze_single_document(
                doc, required_controls
            )
            document_analyses.append(doc_analysis)

            # Update evidence map
            for control_id, evidence in doc_analysis.get("controls_addressed", {}).items():
                if control_id not in evidence_map:
                    evidence_map[control_id] = []
                evidence_map[control_id].append({
                    "document": doc.get("filename", "Unknown"),
                    "evidence": evidence,
                })

        return {
            "document_analyses": document_analyses,
            "evidence_by_control": evidence_map,
        }

    async def _analyze_single_document(
        self, doc: Dict[str, Any], required_controls: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze a single document for control evidence."""
        # Create a summary of control families for the prompt
        control_summary = {}
        for control in required_controls:
            family = control.get("family", "")
            if family not in control_summary:
                control_summary[family] = []
            control_summary[family].append(f"{control['id']}: {control.get('name', '')}")

        control_list = "\n".join(
            [f"{fam}: {', '.join(ctrls[:5])}..." for fam, ctrls in control_summary.items()]
        )

        prompt = f"""Analyze this security document and identify which ITSG-33 controls it provides evidence for.

DOCUMENT: {doc.get('filename', 'Unknown')}
CONTENT:
{doc.get('content', '')[:12000]}

ITSG-33 CONTROL FAMILIES TO CHECK:
{control_list}

For each control that this document provides evidence for, identify:
1. The control ID (e.g., AC-1, AU-2)
2. What evidence this document provides
3. Whether the evidence is FULL (completely addresses the control), PARTIAL (some aspects), or MENTIONS (references but doesn't prove implementation)

Focus on finding REAL evidence of security controls being implemented, not just mentions.

Return as JSON:
{{
    "document_type": "type of document (policy, procedure, architecture, etc.)",
    "document_purpose": "what this document is for",
    "controls_addressed": {{
        "CONTROL-ID": {{
            "coverage": "FULL|PARTIAL|MENTIONS",
            "evidence_summary": "what evidence this document provides",
            "relevant_excerpt": "key quote or section that proves this"
        }}
    }},
    "key_security_topics": ["list of security topics covered"]
}}
"""

        try:
            response = await self.gemini.generate_async(prompt)
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                analysis = json.loads(response[json_start:json_end])
                analysis["filename"] = doc.get("filename", "Unknown")
                return analysis
        except Exception as e:
            pass

        return {
            "filename": doc.get("filename", "Unknown"),
            "document_type": "Unknown",
            "document_purpose": "Could not analyze",
            "controls_addressed": {},
            "key_security_topics": [],
            "error": "Analysis failed",
        }

    def _calculate_coverage(
        self,
        required_controls: List[Dict[str, Any]],
        evidence_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Calculate control coverage based on evidence."""
        evidence_map = evidence_analysis.get("evidence_by_control", {})

        full_coverage = []
        partial_coverage = []
        no_coverage = []

        for control in required_controls:
            control_id = control.get("id", "")
            if control_id in evidence_map:
                evidence_items = evidence_map[control_id]
                # Check if any evidence is FULL
                has_full = any(
                    e.get("evidence", {}).get("coverage") == "FULL"
                    for e in evidence_items
                )
                if has_full:
                    full_coverage.append({
                        "control_id": control_id,
                        "control_name": control.get("name", ""),
                        "family": control.get("family", ""),
                        "evidence_count": len(evidence_items),
                        "evidence": evidence_items,
                    })
                else:
                    partial_coverage.append({
                        "control_id": control_id,
                        "control_name": control.get("name", ""),
                        "family": control.get("family", ""),
                        "evidence_count": len(evidence_items),
                        "evidence": evidence_items,
                    })
            else:
                no_coverage.append({
                    "control_id": control_id,
                    "control_name": control.get("name", ""),
                    "family": control.get("family", ""),
                    "questions": control.get("questions", []),
                })

        total = len(required_controls)
        coverage_pct = (
            (len(full_coverage) + len(partial_coverage) * 0.5) / total * 100
            if total > 0
            else 0
        )

        return {
            "controls_with_evidence": len(full_coverage),
            "controls_partial": len(partial_coverage),
            "controls_missing": len(no_coverage),
            "coverage_percentage": round(coverage_pct, 1),
            "full_coverage": full_coverage,
            "partial_coverage": partial_coverage,
            "no_coverage": no_coverage,
        }

    async def _generate_recommendations(
        self,
        coverage: Dict[str, Any],
        required_controls: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate recommendations based on gaps."""
        missing_controls = coverage.get("no_coverage", [])
        partial_controls = coverage.get("partial_coverage", [])

        # Group missing by family
        missing_by_family = {}
        for ctrl in missing_controls:
            family = ctrl.get("family", "Unknown")
            if family not in missing_by_family:
                missing_by_family[family] = []
            missing_by_family[family].append(ctrl)

        # Generate prioritized recommendations
        high_priority = []
        medium_priority = []
        low_priority = []

        # High priority: Access Control, Identification & Auth, Audit
        high_families = ["AC", "IA", "AU", "SC"]
        for ctrl in missing_controls:
            if ctrl.get("family") in high_families:
                high_priority.append({
                    "control_id": ctrl["control_id"],
                    "control_name": ctrl["control_name"],
                    "action": "Provide evidence or implement this control",
                    "suggested_evidence": self._suggest_evidence(ctrl["control_id"]),
                })
            elif ctrl.get("family") in ["CM", "SI", "IR"]:
                medium_priority.append({
                    "control_id": ctrl["control_id"],
                    "control_name": ctrl["control_name"],
                    "action": "Provide evidence or implement this control",
                })
            else:
                low_priority.append({
                    "control_id": ctrl["control_id"],
                    "control_name": ctrl["control_name"],
                })

        return {
            "high_priority": high_priority[:10],
            "medium_priority": medium_priority[:10],
            "low_priority_count": len(low_priority),
            "missing_by_family": {
                fam: len(ctrls) for fam, ctrls in missing_by_family.items()
            },
            "next_steps": [
                "Upload security policies covering Access Control (AC) family",
                "Provide authentication and identity management documentation (IA)",
                "Submit audit logging configuration and procedures (AU)",
                "Include system architecture and network diagrams (SC)",
            ],
        }

    def _suggest_evidence(self, control_id: str) -> str:
        """Suggest what evidence would satisfy a control."""
        suggestions = {
            "AC-1": "Access Control Policy document",
            "AC-2": "Account management procedures, user provisioning documentation",
            "AC-3": "Access control configuration, RBAC documentation",
            "IA-1": "Identification and Authentication Policy",
            "IA-2": "Multi-factor authentication configuration",
            "AU-1": "Audit and Accountability Policy",
            "AU-2": "Audit logging configuration, log retention policy",
            "SC-1": "System and Communications Protection Policy",
            "SC-7": "Network architecture diagram, firewall rules",
        }
        return suggestions.get(control_id, "Policy, procedure, or configuration documentation")

    async def get_status(self) -> Dict[str, Any]:
        """Get current coordinator status."""
        return {
            "coordinator": "ITSG33Coordinator",
            "controls_loaded": len(self.controls_data),
            "status": "ready",
        }

    async def reassess_with_new_document(
        self,
        assessment_results: Dict[str, Any],
        new_document: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Reassess when a new document is added."""
        # Get required controls from previous assessment
        profile = assessment_results.get("phases", {}).get(
            "required_controls", {}
        ).get("profile", 2)
        required_controls = self.get_controls_for_profile(profile)

        # Analyze new document
        new_doc_analysis = await self._analyze_single_document(
            new_document, required_controls
        )

        # Merge with existing evidence
        existing_evidence = assessment_results.get("phases", {}).get(
            "evidence_analysis", {}
        ).get("evidence_by_control", {})

        for control_id, evidence in new_doc_analysis.get("controls_addressed", {}).items():
            if control_id not in existing_evidence:
                existing_evidence[control_id] = []
            existing_evidence[control_id].append({
                "document": new_document.get("filename", "Unknown"),
                "evidence": evidence,
            })

        # Recalculate coverage
        evidence_analysis = {"evidence_by_control": existing_evidence}
        coverage = self._calculate_coverage(required_controls, evidence_analysis)

        # Update recommendations
        recommendations = await self._generate_recommendations(
            coverage, required_controls
        )

        # Update results
        assessment_results["phases"]["evidence_analysis"]["evidence_by_control"] = existing_evidence
        assessment_results["phases"]["evidence_analysis"]["document_analyses"].append(new_doc_analysis)
        assessment_results["phases"]["coverage"] = coverage
        assessment_results["phases"]["recommendations"] = recommendations
        assessment_results["summary"] = {
            "profile": profile,
            "total_controls": len(required_controls),
            "controls_with_evidence": coverage["controls_with_evidence"],
            "controls_partial": coverage["controls_partial"],
            "controls_missing": coverage["controls_missing"],
            "coverage_percentage": coverage["coverage_percentage"],
        }

        return assessment_results
