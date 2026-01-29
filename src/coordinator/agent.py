"""Main coordinator agent orchestrating the ITSG-33 assessment."""

import os
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from PIL import Image

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
        videos: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Run complete ITSG-33 assessment.

        Args:
            conops: Concept of operations document
            documents: List of document metadata with content
            diagrams: List of diagram metadata
            client_id: Client identifier
            videos: List of video metadata with keyframes

        Returns:
            Complete assessment results
        """
        results = {
            "client_id": client_id,
            "status": "in_progress",
            "phases": {},
        }

        # Combine documents and videos for evidence analysis
        all_evidence_sources = documents + (videos or [])

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

            # Phase 3: Determine control applicability based on system characteristics
            applicability = await self._assess_control_applicability(
                system_analysis, conops, documents, required_controls
            )
            results["phases"]["applicability"] = applicability
            applicable_controls = applicability["applicable_controls"]

            # Phase 4: Analyze each source for evidence (only for applicable controls)
            evidence_analysis = await self._analyze_documents_for_evidence(
                all_evidence_sources, applicable_controls
            )
            results["phases"]["evidence_analysis"] = evidence_analysis

            # Phase 5: Calculate control coverage (based on applicable controls only)
            coverage = self._calculate_coverage(applicable_controls, evidence_analysis)
            # Add not_applicable from the applicability phase
            coverage["not_applicable"] = applicability["not_applicable_controls"]
            coverage["controls_not_applicable"] = len(applicability["not_applicable_controls"])
            results["phases"]["coverage"] = coverage

            # Phase 6: Generate recommendations
            recommendations = await self._generate_recommendations(coverage, applicable_controls)
            results["phases"]["recommendations"] = recommendations

            results["status"] = "completed"
            results["summary"] = {
                "profile": profile,
                "total_controls": len(required_controls),
                "applicable_controls": len(applicable_controls),
                "controls_not_applicable": len(applicability["not_applicable_controls"]),
                "controls_with_evidence": coverage["controls_with_evidence"],
                "controls_partial": coverage["controls_partial"],
                "controls_missing": coverage["controls_missing"],
                "coverage_percentage": coverage["coverage_percentage"],
                "quality_score": coverage.get("quality_score", 0),
                "machine_verifiable_count": coverage.get("machine_verifiable_count", 0),
                "human_curated_count": coverage.get("human_curated_count", 0),
            }

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            import traceback

            results["traceback"] = traceback.format_exc()

        return results

    async def _analyze_system(self, conops: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
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

    def _group_controls_by_family(self, controls: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Group controls by family."""
        families = {}
        for control in controls:
            family = control.get("family", "Unknown")
            if family not in families:
                families[family] = []
            families[family].append(control.get("id", ""))
        return families

    async def _assess_control_applicability(
        self,
        system_analysis: Dict[str, Any],
        conops: str,
        documents: List[Dict[str, Any]],
        required_controls: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Assess which controls are applicable to this system based on its characteristics.

        Some controls may not apply based on:
        - System architecture (cloud vs on-premise)
        - Technology stack (no encryption = no encryption controls)
        - Deployment model (internal vs external facing)
        - Data types processed
        """
        # Get document content for context
        doc_content = ""
        for doc in documents[:3]:
            if "content" in doc:
                doc_content += f"\n--- {doc.get('filename', 'Document')} ---\n"
                doc_content += doc["content"][:2000]

        # Create control list for the prompt
        control_list = "\n".join(
            [f"- {c['id']}: {c.get('name', '')} ({c.get('family', '')})" for c in required_controls]
        )

        prompt = f"""Based on this system's characteristics, determine which ITSG-33 controls are APPLICABLE.

SYSTEM ANALYSIS:
- System Type: {system_analysis.get("system_type", "Unknown")}
- Data Classification: {system_analysis.get("data_classification", "Unknown")}
- Confidentiality: {system_analysis.get("confidentiality", "Unknown")}
- Integrity: {system_analysis.get("integrity", "Unknown")}
- Availability: {system_analysis.get("availability", "Unknown")}

CONOPS/SYSTEM DESCRIPTION:
{conops[:3000] if conops else "No CONOPS provided"}

ADDITIONAL DOCUMENTATION:
{doc_content[:5000]}

CONTROLS TO EVALUATE:
{control_list}

For each control, determine if it is APPLICABLE or NOT APPLICABLE to this specific system.

A control is NOT APPLICABLE if:
- The system doesn't use the technology the control addresses (e.g., no wireless = no wireless controls)
- The system architecture makes the control irrelevant (e.g., SaaS = no physical server controls)
- The deployment model excludes certain requirements (e.g., internal only = fewer external-facing controls)
- The control addresses something the system simply doesn't have or do

Be CONSERVATIVE - when in doubt, mark as APPLICABLE. Only mark NOT APPLICABLE when clearly justified.

Return as JSON:
{{
    "applicable": [
        {{"control_id": "AC-1", "reason": "Access control policies are required for all systems"}}
    ],
    "not_applicable": [
        {{"control_id": "PE-1", "reason": "Cloud-hosted system with no physical infrastructure managed by the organization"}}
    ]
}}
"""

        try:
            response = await self.gemini.generate_async(prompt)
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response[json_start:json_end])

                # Build lists of applicable and not applicable controls
                applicable_ids = {item["control_id"] for item in result.get("applicable", [])}
                not_applicable_items = result.get("not_applicable", [])
                not_applicable_ids = {item["control_id"] for item in not_applicable_items}

                # Build the applicable controls list (full control objects)
                applicable_controls = []
                not_applicable_controls = []

                for control in required_controls:
                    control_id = control.get("id", "")
                    if control_id in not_applicable_ids:
                        # Find the reason
                        reason = next(
                            (
                                item["reason"]
                                for item in not_applicable_items
                                if item["control_id"] == control_id
                            ),
                            "Determined not applicable based on system analysis",
                        )
                        not_applicable_controls.append(
                            {
                                "control_id": control_id,
                                "control_name": control.get("name", ""),
                                "family": control.get("family", ""),
                                "not_applicable_reason": reason,
                                "auto_determined": True,
                            }
                        )
                    else:
                        # Default to applicable if not explicitly marked as not applicable
                        applicable_controls.append(control)

                return {
                    "applicable_controls": applicable_controls,
                    "not_applicable_controls": not_applicable_controls,
                    "total_assessed": len(required_controls),
                    "applicable_count": len(applicable_controls),
                    "not_applicable_count": len(not_applicable_controls),
                }
        except Exception as e:
            pass

        # Default: all controls are applicable if analysis fails
        return {
            "applicable_controls": required_controls,
            "not_applicable_controls": [],
            "total_assessed": len(required_controls),
            "applicable_count": len(required_controls),
            "not_applicable_count": 0,
            "note": "Applicability assessment failed - all controls marked as applicable",
        }

    async def _analyze_documents_for_evidence(
        self, documents: List[Dict[str, Any]], required_controls: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze each document to find evidence for controls."""
        evidence_map = {}  # control_id -> list of evidence items
        document_analyses = []

        for doc in documents:
            if "content" not in doc or not doc["content"]:
                continue

            doc_analysis = await self._analyze_single_document(doc, required_controls)
            document_analyses.append(doc_analysis)

            # Update evidence map
            for control_id, evidence in doc_analysis.get("controls_addressed", {}).items():
                if control_id not in evidence_map:
                    evidence_map[control_id] = []
                evidence_map[control_id].append(
                    {
                        "document": doc.get("filename", "Unknown"),
                        "evidence": evidence,
                    }
                )

        return {
            "document_analyses": document_analyses,
            "evidence_by_control": evidence_map,
        }

    async def _analyze_single_document(
        self, doc: Dict[str, Any], required_controls: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze a single document or video for control evidence."""
        user_control_hints = doc.get("user_control_hints") or []
        user_explanation = doc.get("user_explanation") or doc.get("significance_note")
        declared_type = doc.get("declared_type") or doc.get("document_type")

        hint_lines = []
        if user_control_hints:
            hint_lines.append(f"Suggested Controls: {', '.join(user_control_hints)}")
        if declared_type:
            hint_lines.append(f"Declared Type: {declared_type}")
        if user_explanation:
            hint_lines.append(f"CRITICAL USER SIGNIFICANCE NOTE: {user_explanation}")
            hint_lines.append(
                "TRUST THIS NOTE: The user has identified the above as the primary significance of this file. Use it as your main lead for control mapping."
            )

        hint_block = "\n".join(hint_lines) if hint_lines else "None provided"

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

        prompt = f"""Analyze this security evidence and identify which ITSG-33 controls it provides evidence for.

 DOCUMENT: {doc.get("filename", "Unknown")}
 USER-SUBMITTED HINTS & SIGNIFICANCE:
 {hint_block}

 CONTENT SUMMARY:
 {doc.get("content", "")[:12000]}

 EVIDENCE STRENGTH CLASSIFICATION (classify each piece of evidence by type):
 1. SYSTEM_GENERATED - Logs, audit records, config exports, IAM policy dumps, compliance script output
 2. INFRASTRUCTURE_AS_CODE - Terraform, Helm charts, Ansible playbooks, K8s manifests
 3. AUTOMATED_TEST - CI pipeline output, security scan reports, CIS benchmark results
 4. CODE_ENFORCEMENT - Authorization middleware, input validation code, crypto usage
 5. SCREENSHOT - Admin console screenshots, RBAC settings in UI, configuration panels
 6. VIDEO_WALKTHROUGH - Demonstrative recordings, walkthroughs (non-auditable)
 7. NARRATIVE - Written descriptions, attestations, policy statements

 Rule: Prefer machine-verifiable artifacts (tiers 1-4) over human-curated ones (tiers 5-7).

 ITSG-33 CONTROL FAMILIES TO CHECK:
 {control_list}

 For each control that this evidence provides proof for, identify:
 1. The control ID (e.g., AC-1, AU-2)
 2. What evidence this source provides
 3. Coverage: FULL (completely addresses), PARTIAL (some aspects), MENTIONS (references only)
 4. Evidence strength tier (1-7 from classification above)
 5. Evidence type category (SYSTEM_GENERATED, INFRASTRUCTURE_AS_CODE, etc.)

 Focus on finding REAL evidence of security controls being implemented.
 If user-submitted notes or hints are unsupported or contradicted by the content, note the gap.

 Return as JSON:
 {{
     "document_type": "type of evidence (policy, log, video_frames, etc.)",
     "document_purpose": "what this evidence demonstrates",
     "controls_addressed": {{
         "CONTROL-ID": {{
             "coverage": "FULL|PARTIAL|MENTIONS",
             "evidence_strength_tier": 1-7,
             "evidence_type_category": "SYSTEM_GENERATED|...",
             "evidence_summary": "what evidence this source provides",
             "relevant_excerpt": "key quote, log line, or visual description"
         }}
     }},
     "key_security_topics": ["list of security topics covered"]
 }}
 """

        # Prepare multimodal content for Gemini
        gemini_content = [prompt]

        # Add keyframes if it's a video
        if doc.get("type") == "video" and "keyframes" in doc:
            for frame in doc["keyframes"]:
                try:
                    img = Image.open(frame["path"])
                    gemini_content.append(img)
                except Exception:
                    pass

        # Add image if it's an image
        if doc.get("type") == "image" and "path" in doc:
            try:
                img = Image.open(doc["path"])
                gemini_content.append(img)
            except Exception:
                pass

        try:
            response = await self.gemini.generate_async(gemini_content)
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
        """Calculate control coverage based on evidence, including quality score."""
        evidence_map = evidence_analysis.get("evidence_by_control", {})

        # Evidence strength scores by tier
        STRENGTH_SCORES = {1: 100, 2: 90, 3: 80, 4: 70, 5: 50, 6: 30, 7: 20}
        COVERAGE_MULTIPLIERS = {"FULL": 1.0, "PARTIAL": 0.5, "MENTIONS": 0.25}

        full_coverage = []
        partial_coverage = []
        no_coverage = []

        # Track weighted scores for quality calculation
        total_weighted_score = 0
        max_possible_score = len(required_controls) * 100  # Max 100 per control

        for control in required_controls:
            control_id = control.get("id", "")
            if control_id in evidence_map:
                evidence_items = evidence_map[control_id]

                # Calculate best evidence score for this control
                best_weighted_score = 0
                best_strength_tier = 7
                has_full = False

                for ev in evidence_items:
                    evidence_data = ev.get("evidence", {})
                    coverage = evidence_data.get("coverage", "MENTIONS")
                    strength_tier = evidence_data.get("evidence_strength_tier", 7)

                    # Ensure tier is an integer
                    if isinstance(strength_tier, str):
                        try:
                            strength_tier = int(strength_tier)
                        except ValueError:
                            strength_tier = 7

                    # Calculate effective score (strength * coverage multiplier)
                    strength_score = STRENGTH_SCORES.get(strength_tier, 20)
                    coverage_mult = COVERAGE_MULTIPLIERS.get(coverage, 0.25)
                    effective_score = strength_score * coverage_mult

                    if effective_score > best_weighted_score:
                        best_weighted_score = effective_score
                        best_strength_tier = strength_tier

                    if coverage == "FULL":
                        has_full = True

                total_weighted_score += best_weighted_score

                # Build control entry with best evidence strength
                control_entry = {
                    "control_id": control_id,
                    "control_name": control.get("name", ""),
                    "family": control.get("family", ""),
                    "evidence_count": len(evidence_items),
                    "evidence": evidence_items,
                    "best_evidence_strength": best_strength_tier,
                    "is_machine_verifiable": best_strength_tier <= 4,
                }

                if has_full:
                    full_coverage.append(control_entry)
                else:
                    partial_coverage.append(control_entry)
            else:
                no_coverage.append(
                    {
                        "control_id": control_id,
                        "control_name": control.get("name", ""),
                        "family": control.get("family", ""),
                        "questions": control.get("questions", []),
                    }
                )

        total = len(required_controls)

        # Traditional coverage percentage
        coverage_pct = (
            (len(full_coverage) + len(partial_coverage) * 0.5) / total * 100 if total > 0 else 0
        )

        # Quality score (strength-weighted)
        quality_score = (
            (total_weighted_score / max_possible_score) * 100 if max_possible_score > 0 else 0
        )

        # Count machine-verifiable vs human-curated evidence
        machine_verifiable_count = sum(
            1 for c in full_coverage + partial_coverage if c.get("is_machine_verifiable", False)
        )
        human_curated_count = len(full_coverage) + len(partial_coverage) - machine_verifiable_count

        return {
            "controls_with_evidence": len(full_coverage),
            "controls_partial": len(partial_coverage),
            "controls_missing": len(no_coverage),
            "coverage_percentage": round(coverage_pct, 1),
            "quality_score": round(quality_score, 1),
            "machine_verifiable_count": machine_verifiable_count,
            "human_curated_count": human_curated_count,
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
                high_priority.append(
                    {
                        "control_id": ctrl["control_id"],
                        "control_name": ctrl["control_name"],
                        "action": "Provide evidence or implement this control",
                        "suggested_evidence": self._suggest_evidence(ctrl["control_id"]),
                    }
                )
            elif ctrl.get("family") in ["CM", "SI", "IR"]:
                medium_priority.append(
                    {
                        "control_id": ctrl["control_id"],
                        "control_name": ctrl["control_name"],
                        "action": "Provide evidence or implement this control",
                    }
                )
            else:
                low_priority.append(
                    {
                        "control_id": ctrl["control_id"],
                        "control_name": ctrl["control_name"],
                        "action": "Provide evidence documentation",
                    }
                )

        return {
            "high_priority": high_priority,
            "medium_priority": medium_priority,
            "low_priority": low_priority,
            "low_priority_count": len(low_priority),
            "missing_by_family": {fam: len(ctrls) for fam, ctrls in missing_by_family.items()},
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
        profile = (
            assessment_results.get("phases", {}).get("required_controls", {}).get("profile", 2)
        )
        required_controls = self.get_controls_for_profile(profile)

        # Get applicable controls from previous assessment (or all if not available)
        applicability = assessment_results.get("phases", {}).get("applicability", {})
        applicable_controls = applicability.get("applicable_controls", required_controls)
        not_applicable_controls = applicability.get("not_applicable_controls", [])

        # Analyze new document against applicable controls only
        new_doc_analysis = await self._analyze_single_document(new_document, applicable_controls)

        # Merge with existing evidence
        existing_evidence = (
            assessment_results.get("phases", {})
            .get("evidence_analysis", {})
            .get("evidence_by_control", {})
        )

        for control_id, evidence in new_doc_analysis.get("controls_addressed", {}).items():
            if control_id not in existing_evidence:
                existing_evidence[control_id] = []
            existing_evidence[control_id].append(
                {
                    "document": new_document.get("filename", "Unknown"),
                    "evidence": evidence,
                }
            )

        # Recalculate coverage based on applicable controls only
        evidence_analysis = {"evidence_by_control": existing_evidence}
        coverage = self._calculate_coverage(applicable_controls, evidence_analysis)

        # Preserve not_applicable and rejected_evidence from previous assessment
        coverage["not_applicable"] = (
            assessment_results.get("phases", {})
            .get("coverage", {})
            .get("not_applicable", not_applicable_controls)
        )
        coverage["controls_not_applicable"] = len(coverage["not_applicable"])

        coverage["rejected_evidence"] = (
            assessment_results.get("phases", {}).get("coverage", {}).get("rejected_evidence", [])
        )
        coverage["controls_rejected_evidence"] = len(coverage.get("rejected_evidence", []))

        # Update recommendations
        recommendations = await self._generate_recommendations(coverage, applicable_controls)

        # Update results
        assessment_results["phases"]["evidence_analysis"]["evidence_by_control"] = existing_evidence
        assessment_results["phases"]["evidence_analysis"]["document_analyses"].append(
            new_doc_analysis
        )
        assessment_results["phases"]["coverage"] = coverage
        assessment_results["phases"]["recommendations"] = recommendations
        assessment_results["summary"] = {
            "profile": profile,
            "total_controls": len(required_controls),
            "applicable_controls": len(applicable_controls),
            "controls_not_applicable": coverage["controls_not_applicable"],
            "controls_with_evidence": coverage["controls_with_evidence"],
            "controls_partial": coverage["controls_partial"],
            "controls_missing": coverage["controls_missing"],
            "controls_rejected_evidence": coverage.get("controls_rejected_evidence", 0),
            "coverage_percentage": coverage["coverage_percentage"],
        }

        return assessment_results
