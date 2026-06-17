from backend.app.services.domain import load_domain_catalog
from backend.app.services.extractor import VoiceExtractor


def test_extracts_complete_work_order_from_noisy_field_phrase():
    extractor = VoiceExtractor(load_domain_catalog())

    result = extractor.extract_work_order(
        "Inspecting pump P-M-P 204 Bravo. Bearing temperature high, "
        "fault code F-12. Action: applied coolant. Need replacement seal kit, severity high.",
        client_uuid="voice-1",
        worker_id="tech-1",
    )

    order = result.work_order
    assert order.equipment_code == "PMP-204B"
    assert order.fault_code == "F12"
    assert order.severity == "HIGH"
    assert order.location == "North Plant Bay 4"
    assert order.action_taken == "applied coolant"
    assert order.parts_required == ["replacement seal kit"]
    assert result.missing_fields == []

