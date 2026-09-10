"""
Comprehensive Verification Suite for SIH Problem Statement ID 26088:
Multilingual Cooperative Governance & Legal Assistance Chatbot (SahakarSaathi).

Test Scenarios:
1. Multilingual Natural Language Responses across 10 Indian Languages (EN, HI, TA, TE, MR, KN, GU, BN, ML, PA).
2. Guidance on Cooperative Laws & MSCS Act 2023 Provisions.
3. Information on Ministry of Cooperation Schemes (PACS Computerization, NCEL, NCOEL, BBSSL, Grain Storage).
4. PMFBY Crop Insurance & Claims (Kharif 2%, Rabi 1.5%, Commercial 5%, 72-Hour Intimation Window).
5. Financial Literacy Assistance (KCC 4% Effective Interest Subvention).
6. Cooperative Grievance Redressal Mechanism (Registration, Ticket ID Generation, Ombudsman Escalation, Tracking).
7. Hardware Edge Kiosk Mode (Low-Literacy Tactile Buttons, Voice I/O, Evaluation Benchmark).
8. PiClaw Agent Tools (7 Cooperative Governance & Legal Tools).
"""

import sys
import os
import time

sys.path.insert(0, '.')

from core.cooperative_assistant import (
    get_cooperative_assistant,
    calculate_pmfby_premium,
    SUPPORTED_LANGUAGES,
    COOPERATIVE_KNOWLEDGE_BASE
)
from core.coop_kiosk_hardware import get_coop_kiosk_hardware
from piclaw.tools.registry import get_registry
from piclaw.main import _register_tools

ok_count = 0
fail_count = 0

def chk(label: str, condition: bool, detail: str = ""):
    global ok_count, fail_count
    if condition:
        ok_count += 1
        print(f"  [OK] {label}" + (f" — {detail[:65]}" if detail else ""))
    else:
        fail_count += 1
        print(f"  [FAIL] {label}" + (f" — {detail[:65]}" if detail else ""))


import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def run_tests():
    print("=" * 65)
    print(" [TEST] SIH 26088 SahakarSaathi Verification Suite")
    print("=" * 65)

    assistant = get_cooperative_assistant()
    hardware = get_coop_kiosk_hardware()

    # 1. 10 Indian Languages Coverage
    chk("10 Indian Languages Supported", len(SUPPORTED_LANGUAGES) >= 10, f"{len(SUPPORTED_LANGUAGES)} languages")
    for code in ["en", "hi", "ta", "te", "mr", "kn", "gu", "bn", "ml", "pa"]:
        chk(f"Language [{code}] native entry", code in SUPPORTED_LANGUAGES, SUPPORTED_LANGUAGES[code]["native"])

    # 2. MSCS Act 2023 Provisions
    mscs = COOPERATIVE_KNOWLEDGE_BASE["laws"]["mscs_act_2023"]
    chk("MSCS Act 2023 Key Provisions", len(mscs["key_provisions"]) >= 5, mscs["title"])
    chk("MSCS Act 2023 Ombudsman present", any("Ombudsman" in p for p in mscs["key_provisions"]))
    chk("MSCS Act 2023 Women & SC/ST Reservation", any("Women" in p for p in mscs["key_provisions"]))

    # 3. Model By-laws for PACS
    pacs_bylaws = COOPERATIVE_KNOWLEDGE_BASE["laws"]["pacs_model_bylaws"]
    chk("PACS Model By-laws", len(pacs_bylaws["key_provisions"]) >= 3, pacs_bylaws["title"])

    # 4. Ministry of Cooperation Schemes
    schemes = COOPERATIVE_KNOWLEDGE_BASE["schemes"]
    chk("PACS Computerization Scheme", "pacs_computerization" in schemes, schemes["pacs_computerization"]["budget"])
    chk("NCEL Export Cooperative", "NCEL" in schemes["new_national_cooperatives"])
    chk("NCOEL Organic Cooperative", "NCOEL" in schemes["new_national_cooperatives"])
    chk("BBSSL Certified Seeds Cooperative", "BBSSL" in schemes["new_national_cooperatives"])
    chk("World Largest Grain Storage Scheme", "grain_storage_plan" in schemes)

    # 5. PMFBY Crop Insurance & Premium Calculations
    pmfby_kharif = calculate_pmfby_premium("kharif", 40000.0, 2.5)
    chk("PMFBY Kharif 2.0% Farmer Share", pmfby_kharif["farmer_payable_premium"] == 2000.0, f"Payable: Rs {pmfby_kharif['farmer_payable_premium']}")
    chk("PMFBY Govt Subsidy Computed", pmfby_kharif["govt_subsidy_share"] > 0, f"Subsidy: Rs {pmfby_kharif['govt_subsidy_share']}")
    chk("PMFBY 72-Hour Intimation Window", "72 Hours" in pmfby_kharif["intimation_deadline"])
    chk("PMFBY Helpline 14447", pmfby_kharif["toll_free_helpline"] == "14447")

    pmfby_rabi = calculate_pmfby_premium("rabi", 50000.0, 2.0)
    chk("PMFBY Rabi 1.5% Farmer Share", pmfby_rabi["farmer_payable_premium"] == 1500.0, f"Payable: Rs {pmfby_rabi['farmer_payable_premium']}")

    # 6. Financial Literacy & KCC Calculation
    r_fin = assistant.answer_query("kcc interest 4 percent", lang="en")
    chk("Financial Literacy Intent", r_fin["intent"] == "FINANCIAL", r_fin["response"][:50])
    chk("KCC 4% Subvention Mentioned", "4%" in r_fin["response"])

    # 7. Grievance Filing & Ticket ID Generation
    test_ticket = assistant.grievances.file_grievance(
        member_name="Devendra Patil",
        pacs_name="Kolhapur Shetkari Sahakari Mandali",
        district="Kolhapur, Maharashtra",
        category="SHARE_CAPITAL_REFUND",
        details="Share capital refund delayed after formal retirement.",
        contact="9822123456"
    )
    chk("Grievance Ticket Generated", test_ticket["ticket_id"].startswith("COOP-2026-"), test_ticket["ticket_id"])
    chk("Grievance Status is REGISTERED", test_ticket["status"] == "REGISTERED")

    # 8. Grievance Tracking
    tracked = assistant.grievances.track_grievance(test_ticket["ticket_id"])
    chk("Grievance Tracking Found", tracked is not None and tracked["member_name"] == "Devendra Patil")

    # 9. Multilingual Query Responses
    r_hi = assistant.answer_query("pmfby फसल बीमा क्लेम", lang="hi")
    chk("Hindi PMFBY Guidance", "72 घंटे" in r_hi["response"], r_hi["response"][:50])

    r_ta = assistant.answer_query("கூட்டுறவு சட்டங்கள்", lang="ta")
    chk("Tamil Law Guidance", "கூட்டுறவு" in r_ta["response"], r_ta["response"][:50])

    # 10. Hardware Edge Kiosk Functions
    metrics = hardware.get_evaluation_metrics()
    chk("SIH 26088 Compliance Status", metrics["status"] == "COMPLIANT_SIH_26088", metrics["status"])
    chk("Edge Latency Target", metrics["edge_response_latency_ms"] < 250, f"{metrics['edge_response_latency_ms']} ms")
    chk("RAM Overhead Target", metrics["ram_footprint_mb"] < 30.0, f"{metrics['ram_footprint_mb']} MB")

    btn1 = hardware.physical_button_press(1)
    chk("Hardware Tactile Button 1 (PMFBY)", btn1["action"] == "EMERGENCY_PMFBY_INTIMATION")

    btn2 = hardware.physical_button_press(2)
    chk("Hardware Tactile Button 2 (KCC)", btn2["action"] == "KCC_LOAN_ASSISTANCE")

    btn3 = hardware.physical_button_press(3)
    chk("Hardware Tactile Button 3 (Grievance)", btn3["action"] == "GRIEVANCE_REGISTERED")

    # 11. PiClaw Agent Tools (Cooperative Suite)
    _register_tools()
    reg = get_registry()
    chk("PiClaw Registry 38 Tools Total", len(reg.names()) == 38, f"{len(reg.names())} tools")

    t_law = reg.execute("coop.query_law", {"topic": "ombudsman"})
    chk("Tool: coop.query_law", t_law.success, t_law.message[:50])

    t_scheme = reg.execute("coop.check_scheme", {"scheme_name": "pacs computerization"})
    chk("Tool: coop.check_scheme", t_scheme.success, t_scheme.message[:50])

    t_pmfby = reg.execute("coop.pmfby_calc", {"crop_type": "kharif", "sum_insured_per_acre": 40000.0, "acreage": 2.0})
    chk("Tool: coop.pmfby_calc", t_pmfby.success, t_pmfby.message[:50])

    t_kcc = reg.execute("coop.kcc_calculator", {"loan_amount": 150000.0})
    chk("Tool: coop.kcc_calculator", t_kcc.success, t_kcc.message[:50])

    t_serv = reg.execute("coop.pacs_services", {"pacs_name": "Rampur PACS"})
    chk("Tool: coop.pacs_services", t_serv.success, t_serv.message[:50])

    # 12. Patent-Level Innovations: DP-CSR and Merkle Ledger
    dp_telemetry = assistant.get_router_telemetry("किसान फसल बीमा 72 घंटे में क्लेम कैसे करें")
    chk("DP-CSR Intent Routed", dp_telemetry["intent"] == "PMFBY", dp_telemetry["intent"])
    chk("DP-CSR Latency < 1ms", dp_telemetry["latency_ms"] < 1.0, f"{dp_telemetry['latency_ms']} ms")
    chk("DP-CSR Confidence > 0.85", dp_telemetry["confidence"] >= 0.85, str(dp_telemetry["confidence"]))

    merkle_check = assistant.verify_tamper_evidence()
    chk("Merkle Ledger Valid", merkle_check["valid"] is True)
    chk("Merkle Tamper Detected", merkle_check["tamper_detected"] is False)
    chk("Merkle Root SHA-256", len(merkle_check["merkle_root"]) == 64, merkle_check["merkle_root"][:16] + "...")

    proof = assistant.get_audit_proof(test_ticket["ticket_id"])
    chk("Merkle Proof Generated", proof is not None and proof["verified"] is True)

    print()
    print("=" * 65)
    print(f"  RESULT: {ok_count}/35 checks passed, {fail_count} failed")
    print("=" * 65)

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
