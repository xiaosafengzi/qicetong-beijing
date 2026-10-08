"""Check both already-tracked secrets and nested archive contents before publication."""
import io
import zipfile

from scripts.check_release import forbidden_path, inspect_payload


def test_local_data_and_secret_paths_are_forbidden():
    for name in (".env.production", "runtime/access.txt", "data/public_case_records_2026.jsonl", "artifacts/台账.xlsx", "../oops.txt", "weights/model.gguf", "C:/private.txt"):
        assert forbidden_path(name)
    assert not forbidden_path(".env.example")
    assert not forbidden_path("artifacts/public-notice-summary.json")


def test_already_selected_secret_is_detected_even_if_ignored(tmp_path):
    secret = tmp_path / ".env.local"
    secret.write_text("placeholder", encoding="utf-8")
    result = inspect_payload([secret], tmp_path)
    assert result["findings"][0][1] == "local_only_path_in_payload"


def test_nested_zip_secret_and_traversal_are_detected_without_values(tmp_path):
    nested = io.BytesIO()
    token = "ghp_" + "a" * 40
    with zipfile.ZipFile(nested, "w") as archive:
        archive.writestr("config.json", '{"api_key":"' + token + '"}')
        archive.writestr("../escape.txt", "example")
    outer = tmp_path / "agent.zip"
    with zipfile.ZipFile(outer, "w") as archive:
        archive.writestr("skill.zip", nested.getvalue())
    result = inspect_payload([outer], tmp_path)
    assert result["zip_archives_checked"] == 2
    kinds = {kind for _, kind in result["findings"]}
    assert "possible_literal_secret" in kinds and "forbidden_archive_path" in kinds
    assert token not in str(result)
