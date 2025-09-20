# app/services/humanizer.py

def humanize_triage(triage_payload: dict) -> dict:
    """
    Convert raw triage output into human-friendly advice.
    """
    human_response = {}

    level = triage_payload.get("recommended_level", "Unknown")
    suggested_action = triage_payload.get("suggested_action")
    reasons = triage_payload.get("reasons", [])

    # Map recommended level to plain-language messages
    level_messages = {
        "Emergency": "⚠️ High risk: Immediate attention required! Go to ER.",
        "Urgent": "🚨 Moderate risk: Visit a healthcare provider soon.",
        "PrimaryCare": "🏥 Mild risk: Book an appointment with your doctor.",
        "SelfCare": "✅ Low risk: Monitor symptoms and rest at home.",
        "Unknown": "❓ Unable to determine risk level. Monitor symptoms carefully.",
    }

    human_response["message"] = level_messages.get(level, "❓ Unknown risk level")
    human_response["recommended_level"] = level
    human_response["reasons"] = reasons
    human_response["suggested_action"] = suggested_action or human_response["message"]

    # Include hospital recommendation if available
    if "hospital_recommendation" in triage_payload:
        human_response["hospital_recommendation"] = triage_payload["hospital_recommendation"]

    return human_response
