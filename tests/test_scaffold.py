import importlib
import importlib.metadata


def test_installed_distribution_exposes_importable_package():
    distribution = importlib.metadata.distribution("epic-creator-eval")
    assert distribution.metadata["Name"].lower().replace("_", "-") == "epic-creator-eval"

    package = importlib.import_module("epic_creator_eval")
    assert package.__name__ == "epic_creator_eval"
