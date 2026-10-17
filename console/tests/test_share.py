"""隐私边界：上传的 coverage_share 只能含白名单字段。"""
import json

from app.share import to_coverage_share

from .conftest import load_example


def test_matches_example():
    assert to_coverage_share(load_example("coverage")) == load_example("coverage_share")


def test_valid_against_schema(schema):
    schema("coverage_share").validate(to_coverage_share(load_example("coverage")))


def test_no_raw_data_or_screenpipe_ids_leak():
    coverage = load_example("coverage")
    coverage["points"][0]["speech"] = "SECRET transcript"
    coverage["frame_ids"] = [5531]
    out = json.dumps(to_coverage_share(coverage))
    for forbidden in ("segment_ids", "S-L-", "teacher_id", "SECRET", "5531", "frame_ids"):
        assert forbidden not in out
