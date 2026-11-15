from __future__ import annotations

import pytest

from reg.errors import InputError
from reg.io import dataset_fingerprint, id_mismatch, join, load_dataset, load_run, read_json, read_jsonl, write_json

from .conftest import write_jsonl


def test_missing_file(tmp_path):
    with pytest.raises(InputError, match="not found"):
        read_jsonl(tmp_path / "nope.jsonl")


def test_bad_json_line(tmp_path):
    p = tmp_path / "x.jsonl"
    p.write_text('{"id": "a"}\n{oops\n')
    with pytest.raises(InputError, match=r"x.jsonl:2: invalid JSON"):
        read_jsonl(p)


def test_non_object_line(tmp_path):
    p = tmp_path / "x.jsonl"
    p.write_text("[1, 2]\n")
    with pytest.raises(InputError, match="JSON object"):
        read_jsonl(p)


def test_empty_file(tmp_path):
    p = tmp_path / "x.jsonl"
    p.write_text("\n\n")
    with pytest.raises(InputError, match="no records"):
        read_jsonl(p)


def test_validation_error_points_at_record(tmp_path):
    p = write_jsonl(tmp_path / "d.jsonl", [{"id": "a", "question": "q"}, {"id": "b"}])
    with pytest.raises(InputError, match="record 2: question"):
        load_dataset(p)


def test_duplicate_ids(tmp_path):
    p = write_jsonl(tmp_path / "r.jsonl", [{"id": "a"}, {"id": "a"}])
    with pytest.raises(InputError, match="duplicate id 'a'"):
        load_run(p)


def test_join_reports_missing_and_extra(tmp_path):
    d = load_dataset(write_jsonl(tmp_path / "d.jsonl", [{"id": i, "question": "q"} for i in "abcdefg"]))
    r = load_run(write_jsonl(tmp_path / "r.jsonl", [{"id": "a"}, {"id": "z"}]))
    with pytest.raises(InputError) as e:
        join(d, r)
    msg = str(e.value)
    assert "6 missing (b, c, d, e, f, ...)" in msg
    assert "1 unexpected (z)" in msg


def test_id_mismatch_none_when_equal():
    assert id_mismatch({"a"}, {"a"}, "x") is None


def test_fingerprint_ignores_order(tmp_path):
    rows = [{"id": "a", "question": "q1"}, {"id": "b", "question": "q2"}]
    a = load_dataset(write_jsonl(tmp_path / "a.jsonl", rows))
    b = load_dataset(write_jsonl(tmp_path / "b.jsonl", rows[::-1]))
    c = load_dataset(write_jsonl(tmp_path / "c.jsonl", [rows[0], {"id": "b", "question": "changed"}]))
    assert dataset_fingerprint(a) == dataset_fingerprint(b) != dataset_fingerprint(c)


def test_read_json_errors(tmp_path):
    with pytest.raises(InputError, match="not found"):
        read_json(tmp_path / "x.json")
    (tmp_path / "bad.json").write_text("{")
    with pytest.raises(InputError, match="invalid JSON"):
        read_json(tmp_path / "bad.json")
    (tmp_path / "list.json").write_text("[]")
    with pytest.raises(InputError, match="JSON object"):
        read_json(tmp_path / "list.json")


def test_write_json_roundtrip(tmp_path):
    write_json(tmp_path / "sub" / "x.json", {"b": 1, "a": 2})
    assert read_json(tmp_path / "sub" / "x.json") == {"a": 2, "b": 1}
