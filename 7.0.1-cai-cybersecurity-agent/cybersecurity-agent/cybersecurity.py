"""
Cybersecurity Agent

Specialized agent for security analysis, threat assessment, and vulnerability evaluation.
"""

from typing import Dict, List, Any
import asyncio
import importlib.util
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
_base_spec = importlib.util.spec_from_file_location("cai_cybersecurity_base", MODULE_DIR / "base.py")
if _base_spec is None or _base_spec.loader is None:
    raise ImportError("Unable to load base CAI helpers for the cybersecurity agent.")

_base_module = importlib.util.module_from_spec(_base_spec)
_base_spec.loader.exec_module(_base_module)
BaseCAIAgent = getattr(_base_module, "BaseCAIAgent")

class CyberSecurityAgent(BaseCAIAgent):
    """
    Cybersecurity specialist agent for threat analysis and security assessment
    """
    
    def __init__(self):
        super().__init__(
            agent_name="CyberSecurity",
            agent_type="security_specialist",
            instructions=(
                "You are a senior cybersecurity analyst. Provide clear, actionable guidance, "
                "prioritize defensive posture, and reference relevant industry frameworks when helpful."
            ),
        )
        
        self.security_frameworks = [
            "OWASP Top 10",
            "NIST Cybersecurity Framework", 
            "CIS Controls",
            "ISO 27001"
        ]
        
        print("🔒 Cybersecurity Agent initialized")

    async def respond(self, prompt: str) -> str:
        """Run an open-ended CAI conversation turn."""

        return await self.chat(prompt)
    
    async def analyze_security_posture(self, analysis_context: Dict) -> Dict:
        """
        Analyze overall security posture based on reconnaissance and vulnerability data
        """
        
        target = analysis_context.get("target", {})
        recon_data = analysis_context.get("reconnaissance_data", {})
        vuln_data = analysis_context.get("vulnerability_data", {})
        
        print(f"🔍 Analyzing security posture for {target.get('target', 'unknown target')}")
        
        # Simulate security analysis processing
        await asyncio.sleep(1)
        
        # Analyze based on available data
        security_findings = []
        risk_score = 0
        
        # Analyze reconnaissance findings
        if recon_data.get("findings"):
            security_findings.extend([
                "Information disclosure through exposed services",
                "Potential attack surface enumerated",
                "Network topology partially revealed"
            ])
            risk_score += len(recon_data["findings"]) * 2
        
        # Analyze vulnerability scan results
        if vuln_data.get("vulnerabilities"):
            security_findings.extend([
                "Critical vulnerabilities identified",
                "Unpatched services detected",
                "Weak security configurations found"
            ])
            risk_score += len(vuln_data["vulnerabilities"]) * 5
        
        # Base security assessment
        security_findings.extend([
            "SSL/TLS configuration assessment needed",
            "Access control mechanisms evaluation required",
            "Security headers analysis recommended"
        ])
        
        # Determine risk level
        if risk_score > 50:
            risk_level = "critical"
        elif risk_score > 30:
            risk_level = "high"
        elif risk_score > 15:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Generate recommendations
        recommendations = [
            "Implement Web Application Firewall (WAF)",
            "Enable security headers (HSTS, CSP, X-Frame-Options)",
            "Conduct regular vulnerability assessments",
            "Implement intrusion detection system (IDS)",
            "Establish security monitoring and logging",
            "Perform penetration testing",
            "Review and update security policies"
        ]
        
        result = {
            "agent": "cybersecurity",
            "analysis_type": "security_posture_assessment",
            "target": target,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "findings": security_findings,
            "recommendations": recommendations,
            "frameworks_applied": self.security_frameworks,
            "compliance_status": {
                "owasp_top_10": "partial_compliance",
                "nist_framework": "needs_improvement",
                "iso_27001": "non_compliant"
            },
            "next_actions": [
                "Prioritize critical vulnerabilities",
                "Implement security monitoring",
                "Develop incident response plan",
                "Schedule security training"
            ]
        }
        
        print(f"✅ Security analysis completed - Risk Level: {risk_level.upper()}")
        return result
    
    async def perform_threat_modeling(self, target_info: Dict) -> Dict:
        """Perform threat modeling analysis"""
        
        print(f"🚨 Performing threat modeling analysis")
        await asyncio.sleep(1.5)
        
        threats = [
            {
                "threat": "SQL Injection",
                "likelihood": "medium",
                "impact": "high",
                "mitigation": "Input validation and parameterized queries"
            },
            {
                "threat": "Cross-Site Scripting (XSS)", 
                "likelihood": "high",
                "impact": "medium",
                "mitigation": "Output encoding and Content Security Policy"
            },
            {
                "threat": "Authentication Bypass",
                "likelihood": "low",
                "impact": "critical",
                "mitigation": "Multi-factor authentication and session management"
            }
        ]
        
        return {
            "agent": "cybersecurity",
            "analysis_type": "threat_modeling",
            "target": target_info,
            "identified_threats": threats,
            "threat_count": len(threats),
            "overall_threat_level": "medium"
        }
    
    async def assess_compliance(self, target_info: Dict, framework: str = "OWASP") -> Dict:
        """Assess compliance against security frameworks"""
        
        print(f"📋 Assessing {framework} compliance")
        await asyncio.sleep(1)
        
        if framework.upper() == "OWASP":
            compliance_items = [
                {"control": "A01:2021 – Broken Access Control", "status": "non_compliant", "priority": "high"},
                {"control": "A02:2021 – Cryptographic Failures", "status": "partial", "priority": "medium"},
                {"control": "A03:2021 – Injection", "status": "compliant", "priority": "low"},
                {"control": "A04:2021 – Insecure Design", "status": "non_compliant", "priority": "high"},
                {"control": "A05:2021 – Security Misconfiguration", "status": "partial", "priority": "medium"}
            ]
        else:
            compliance_items = [
                {"control": "Generic Security Control 1", "status": "compliant", "priority": "low"},
                {"control": "Generic Security Control 2", "status": "partial", "priority": "medium"}
            ]
        
        return {
            "agent": "cybersecurity",
            "analysis_type": "compliance_assessment",
            "framework": framework,
            "target": target_info,
            "compliance_items": compliance_items,
            "overall_compliance": "partial",
            "compliance_score": 65
        }