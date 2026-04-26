from services.model_service import ModelService


def test_model_service_fallback_predictions_when_models_missing():
    service = ModelService(
        success_model_path="nonexistent-success.pkl",
        delay_model_path="nonexistent-delay.pkl",
    )

    features = {
        "deadline_days": 7,
        "complexity": 0.5,
        "resources": 1,
        "dependencies": 0,
        "priority": 0.8,
    }

    assert service.predict_success(features) == 0.5
    assert service.predict_delay(features) == 0.5
