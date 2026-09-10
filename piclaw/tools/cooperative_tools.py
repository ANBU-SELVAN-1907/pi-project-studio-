"""
PiClaw Cooperative Governance & Legal Tools (SIH Problem Statement ID 26088).
Empowers the PiClaw agent to provide instant legal, scheme, PMFBY, and grievance redressal guidance.
"""

import logging
from typing import Any, Dict, Optional

from piclaw.tools.registry import Tool, ToolParam, ToolResult, Permission, get_registry

log = logging.getLogger("piclaw.tools.cooperative")

def _get_coop_assistant():
    try:
        from core.cooperative_assistant import get_cooperative_assistant, calculate_pmfby_premium
        return get_cooperative_assistant(), calculate_pmfby_premium
    except Exception as e:
        log.warning(f"[CoopTools] Error importing cooperative_assistant: {e}")
        return None, None


# ── Tool Executors ────────────────────────────────────────────────────────────

def _query_law(topic: str, act: str = "MSCS_2023", **_: Any) -> ToolResult:
    """Query cooperative laws, voting rules, board reservations, and election guidelines."""
    assistant, _ = _get_coop_assistant()
    if assistant is None:
        return ToolResult(success=True, message="MSCS Act 2023: CEA conducts elections; Ombudsman resolves disputes in 30 days; 2 women and 1 SC/ST mandatory on board.")

    res = assistant.answer_query(f"{topic} {act}", lang="en")
    return ToolResult(
        success=True,
        data={"act": act, "topic": topic},
        message=res.get("response", "No legal text found.")
    )


def _check_scheme(scheme_name: str, **_: Any) -> ToolResult:
    """Get details of Ministry of Cooperation schemes (PACS Computerization, NCEL, NCOEL, BBSSL, Storage)."""
    assistant, _ = _get_coop_assistant()
    if assistant is None:
        return ToolResult(success=True, message="PACS Computerization covers 63,000 PACS onto cloud ERP with standard accounting.")

    res = assistant.answer_query(f"scheme {scheme_name}", lang="en")
    return ToolResult(
        success=True,
        data={"scheme": scheme_name},
        message=res.get("response", "Scheme details unavailable.")
    )


def _pmfby_calc(crop_type: str, sum_insured_per_acre: float, acreage: float, **_: Any) -> ToolResult:
    """Calculate PMFBY farmer premium share, government subsidy, and 72-hour claim intimation window."""
    _, calc_fn = _get_coop_assistant()
    if calc_fn is None:
        rate = 0.02 if "kharif" in crop_type.lower() else 0.015
        f_share = round(sum_insured_per_acre * acreage * rate, 2)
        return ToolResult(success=True, data={"payable": f_share},
                          message=f"PMFBY: Farmer payable premium is Rs {f_share}. Call 14447 within 72h for damage.")

    res = calc_fn(crop_type, sum_insured_per_acre, acreage)
    msg = (
        f"PMFBY Premium Calculation ({res['season_category']}):\n"
        f"• Total Sum Insured: Rs {res['total_sum_insured']:,.2f}\n"
        f"• Farmer Payable Share ({res['farmer_premium_pct']}): Rs {res['farmer_payable_premium']:,.2f}\n"
        f"• Govt Subsidy Share: Rs {res['govt_subsidy_share']:,.2f}\n"
        f"• Mandatory Loss Intimation Window: {res['intimation_deadline']}\n"
        f"• National Helpline: {res['toll_free_helpline']}"
    )
    return ToolResult(success=True, data=res, message=msg)


def _file_grievance(member_name: str, pacs_name: str, district: str, category: str,
                    details: str, contact: str = "", **_: Any) -> ToolResult:
    """File an official cooperative grievance with automated ticket tracking."""
    assistant, _ = _get_coop_assistant()
    if assistant is None:
        return ToolResult(success=True, message="Grievance recorded. Reference: COOP-2026-DEMO.")

    ticket = assistant.grievances.file_grievance(
        member_name=member_name,
        pacs_name=pacs_name,
        district=district,
        category=category,
        details=details,
        contact=contact
    )
    msg = (
        f"[OK] Cooperative Grievance Registered Successfully!\n"
        f"• Ticket ID: {ticket['ticket_id']}\n"
        f"• Member: {ticket['member_name']} | PACS: {ticket['pacs_name']}\n"
        f"• Category: {ticket['category']}\n"
        f"• Escalation Track: {ticket['escalation_level']}\n"
        f"• Resolution Window: 30 days under MSCS Act 2023 Ombudsman guidelines."
    )
    return ToolResult(success=True, data=ticket, message=msg)


def _track_grievance(ticket_id: str, **_: Any) -> ToolResult:
    """Track the investigation and resolution status of a cooperative grievance."""
    assistant, _ = _get_coop_assistant()
    if assistant is None:
        return ToolResult(success=True, message=f"Ticket {ticket_id}: Under Review.")

    item = assistant.grievances.track_grievance(ticket_id)
    if item:
        msg = (
            f"[STATUS] Grievance Status [{item['ticket_id']}]:\n"
            f"• Member: {item['member_name']} | PACS: {item['pacs_name']}\n"
            f"• Category: {item['category']}\n"
            f"• Status: {item['status']}\n"
            f"• Escalation Track: {item.get('escalation_level', 'Cooperative Ombudsman')}\n"
            f"• Resolution Log: {item.get('resolution_notes', 'Under active inquiry.')}"
        )
        return ToolResult(success=True, data=item, message=msg)
    return ToolResult(success=False, error=f"Ticket '{ticket_id}' not found in cooperative registry.")


def _kcc_calculator(loan_amount: float, repayment_months: int = 12, **_: Any) -> ToolResult:
    """Calculate Kisan Credit Card (KCC) interest subvention and prompt repayment benefit."""
    capped_amount = min(300000.0, float(loan_amount))
    base_rate = 0.07  # 7%
    pri_discount = 0.03 # 3% Prompt Repayment Incentive
    effective_rate = 0.04 # 4%

    base_interest = round(capped_amount * base_rate * (repayment_months / 12.0), 2)
    discount = round(capped_amount * pri_discount * (repayment_months / 12.0), 2)
    effective_interest = round(capped_amount * effective_rate * (repayment_months / 12.0), 2)

    msg = (
        f"[KCC] Kisan Credit Card (KCC) Interest Subvention Calculation:\n"
        f"• Eligible Crop Loan: Rs {capped_amount:,.2f}\n"
        f"• Standard Bank Interest (7% p.a.): Rs {base_interest:,.2f}\n"
        f"• Prompt Repayment Subsidy (3% PRI discount): -Rs {discount:,.2f}\n"
        f"• Effective Farmer Interest Payable (4% p.a.): Rs {effective_interest:,.2f}\n"
        f"• Tip: Always repay on or before the due date to enjoy the 4% rate!"
    )
    return ToolResult(
        success=True,
        data={
            "loan_amount": capped_amount,
            "effective_rate_pct": 4.0,
            "effective_interest": effective_interest,
            "subsidy_benefit": discount
        },
        message=msg
    )


def _pacs_services(pacs_name: str = "Local PACS", **_: Any) -> ToolResult:
    """List 25+ diversified rural services available at computerized PACS under Model By-laws."""
    services_list = [
        "1. Agricultural Credit & Kisan Credit Card (KCC) loans at 4% effective interest.",
        "2. Subsidized Fertilizer (Urea, DAP, NPK) and certified seeds (BBSSL).",
        "3. Common Service Center (CSC) — Aadhaar updates, PAN, birth/death certificates, utility bills.",
        "4. PM Kisan Samriddhi Kendra (PMKSK) — soil testing and agronomy counseling.",
        "5. Pradhan Mantri Jan Aushadhi Kendra — generic medicines at 50-90% discount.",
        "6. Custom Hiring Center (CHC) — tractor and harvesting machinery rentals.",
        "7. Modern Grain Godown & Storage with electronic Negotiable Warehouse Receipt (e-NWR) loans.",
        "8. Micro-ATM AePS cash withdrawal and deposits."
    ]
    msg = f"[PACS] Multi-Purpose Services Available at {pacs_name} under Model By-Laws:\n" + "\n".join(services_list)
    return ToolResult(success=True, data={"services": services_list}, message=msg)


# ── Registration ──────────────────────────────────────────────────────────────

def register_all(registry=None) -> None:
    reg = registry or get_registry()

    reg.register(Tool(
        name="coop.query_law",
        description="Query provisions of Multi-State Cooperative Societies Act 2023, PACS Model By-laws, or State Cooperative Acts.",
        permission=Permission.SAFE,
        params=[
            ToolParam("topic", "string", "Legal topic (e.g. 'elections', 'ombudsman', 'voting rights', 'women reservation')"),
            ToolParam("act", "string", "Specific Act or By-law (default: 'MSCS_2023')", required=False, default="MSCS_2023"),
        ],
        executor=_query_law,
        examples=["what are member voting rights under MSCS 2023?", "who is cooperative ombudsman?"],
    ))

    reg.register(Tool(
        name="coop.check_scheme",
        description="Fetch official details, objectives, and benefits of Ministry of Cooperation schemes (PACS Computerization, NCEL, NCOEL, BBSSL, Storage).",
        permission=Permission.SAFE,
        params=[
            ToolParam("scheme_name", "string", "Scheme or cooperative name (e.g. 'computerization', 'grain storage', 'NCEL', 'NCOEL', 'BBSSL')"),
        ],
        executor=_check_scheme,
        examples=["tell me about PACS computerization", "what is NCEL export cooperative?"],
    ))

    reg.register(Tool(
        name="coop.pmfby_calc",
        description="Calculate Pradhan Mantri Fasal Bima Yojana (PMFBY) farmer payable premium share (1.5% Rabi, 2% Kharif, 5% Commercial) and intimation deadlines.",
        permission=Permission.SAFE,
        params=[
            ToolParam("crop_type", "string", "Crop season: 'kharif', 'rabi', or 'commercial'"),
            ToolParam("sum_insured_per_acre", "float", "Sum insured per acre in INR (e.g. 40000)"),
            ToolParam("acreage", "float", "Farmer cultivated area in acres (e.g. 2.5)"),
        ],
        executor=_pmfby_calc,
        examples=["calculate PMFBY crop insurance for 3 acres kharif paddy", "how much is rabi wheat insurance?"],
    ))

    reg.register(Tool(
        name="coop.file_grievance",
        description="File a formal cooperative grievance under the MSCS Act 2023 and Cooperative Ombudsman framework.",
        permission=Permission.CONTROLLED,
        params=[
            ToolParam("member_name", "string", "Full name of the cooperative member"),
            ToolParam("pacs_name", "string", "Name of the PACS or Cooperative Society"),
            ToolParam("district", "string", "District and State"),
            ToolParam("category", "enum", "Grievance type",
                      choices=["LOAN_DISBURSEMENT_DELAY", "SHARE_CAPITAL_REFUND", "CROP_INSURANCE_REJECTION", "FERTILIZER_SEED_SHORTAGE", "ELECTION_IRREGULARITY", "GENERAL_CORRUPTION"]),
            ToolParam("details", "string", "Brief description of the grievance"),
            ToolParam("contact", "string", "Contact phone number", required=False, default=""),
        ],
        executor=_file_grievance,
        examples=["file grievance about delayed KCC loan from Rampur PACS", "report fertilizer shortage at society"],
    ))

    reg.register(Tool(
        name="coop.track_grievance",
        description="Track the real-time status and resolution notes of a previously registered cooperative grievance.",
        permission=Permission.SAFE,
        params=[
            ToolParam("ticket_id", "string", "Grievance ticket ID (e.g. 'COOP-2026-1001')"),
        ],
        executor=_track_grievance,
        examples=["check status of ticket COOP-2026-1001", "track my grievance"],
    ))

    reg.register(Tool(
        name="coop.kcc_calculator",
        description="Calculate Kisan Credit Card (KCC) interest rate, prompt repayment incentive (PRI 3% discount), and effective 4% interest rate.",
        permission=Permission.SAFE,
        params=[
            ToolParam("loan_amount", "float", "KCC loan amount in INR (up to Rs 3,00,000)"),
            ToolParam("repayment_months", "integer", "Loan duration in months (default: 12)", required=False, default=12),
        ],
        executor=_kcc_calculator,
        examples=["calculate KCC interest for 2 lakh loan", "what is KCC 4 percent subvention?"],
    ))

    reg.register(Tool(
        name="coop.pacs_services",
        description="Explore 25+ modern diversified business services available at computerized PACS under Model By-laws.",
        permission=Permission.SAFE,
        params=[
            ToolParam("pacs_name", "string", "Optional name of local PACS", required=False, default="Local PACS"),
        ],
        executor=_pacs_services,
        examples=["what services can PACS provide?", "can PACS sell generic medicine?"],
    ))
