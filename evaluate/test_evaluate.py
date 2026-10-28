"""Test cho evaluate.py — chạy: pytest test_evaluate.py"""

import json
import unicodedata
from pathlib import Path

import pytest

from evaluate import ABSTAIN, CORRECT, WRONG, load_jsonl, main, normalize_str, score_one

HERE = Path(__file__).resolve().parent

# Đáp án mẫu theo đúng ví dụ trong đề (luôn có, không phụ thuộc file dữ liệu)
SAMPLE_GOLD = [
    {"id": "q1", "type": "number", "answer": 89526400, "alias": []},
    {"id": "q2", "type": "percent", "answer": 2.08, "alias": []},
    {"id": "q3", "type": "string", "answer": "Xi măng Hà Tiên PCB40 bao 50kg", "alias": ["SP0001"]},
    {"id": "q4", "type": "string", "answer": "Costar Omega 3 1000mg lọ 100 viên",
     "alias": ["SP0076", "Costar Omega 3 1000 mg lọ 100 viên"]},
    {"id": "q5", "type": "list", "answer": ["Cà phê sữa (M)", "Trà đào cam sả (M)"],
     "alias": [["SP0003"], ["SP0017"]]},
    {"id": "q6", "type": "list", "answer": [287435200, 346554700], "alias": []},
    {"id": "q7", "type": "table",
     "answer": {"columns": ["khach_hang", "so_tien_no"],
                "rows": [["Đỗ Đức An", 404500], ["Dương Tâm Bích", 158600]]},
     "alias": [["KH0124"], ["KH0233"]]},
    {"id": "q8", "type": "date", "answer": "2025-02-15", "alias": []},
    {"id": "q9", "type": "boolean", "answer": False, "alias": []},
    {"id": "q10", "type": "unanswerable", "answer": None, "alias": []},
]


def _find_gold_file():
    for p in (HERE / "data/train/answers.jsonl", HERE / "train/answers.jsonl"):
        if p.exists():
            return p
    return None


def write_jsonl(path, records):
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def gold_to_submission(gold):
    """Chuyển một dòng đáp án sang format submission."""
    if gold["type"] == "unanswerable":
        return {"id": gold["id"], "type": "unanswerable", "reason": "không đủ dữ liệu"}
    return {"id": gold["id"], "type": gold["type"], "answer": gold["answer"]}


def run(tmp_path, gold, preds):
    gold_path, pred_path = tmp_path / "gold.jsonl", tmp_path / "pred.jsonl"
    write_jsonl(gold_path, gold)
    write_jsonl(pred_path, preds)
    return main(["--pred", str(pred_path), "--gold", str(gold_path),
                 "--errors", str(tmp_path / "errors.jsonl")])


def gold(qid):
    return next(g for g in SAMPLE_GOLD if g["id"] == qid)


def status(qid, answer, qtype=None):
    g = gold(qid)
    return score_one(g, {"id": qid, "type": qtype or g["type"], "answer": answer})[0]


# 1. Chấm đáp án với chính nó -> toàn bộ đúng, điểm 1.0
def test_self_score_sample(tmp_path):
    res = run(tmp_path, SAMPLE_GOLD, [gold_to_submission(g) for g in SAMPLE_GOLD])
    assert res["correct"] == res["total"] == len(SAMPLE_GOLD)
    assert res["score"] == 1.0


def test_self_score_real_file(tmp_path):
    path = _find_gold_file()
    if path is None:
        pytest.skip("không tìm thấy answers.jsonl")
    golds, _ = load_jsonl(path)
    res = run(tmp_path, golds, [gold_to_submission(g) for g in golds])
    assert res["correct"] == res["total"] == len(golds)
    assert res["wrong"] == res["abstain"] == 0
    assert res["score"] == 1.0


# 2. Toàn abstain -> điểm 0
def test_all_abstain(tmp_path):
    res = run(tmp_path, SAMPLE_GOLD, [{"id": g["id"], "type": "abstain"} for g in SAMPLE_GOLD])
    assert res["abstain"] == len(SAMPLE_GOLD)
    assert res["score"] == 0


def test_missing_and_unparseable_lines_are_abstain(tmp_path):
    (tmp_path / "gold.jsonl").write_text(json.dumps(gold("q1")) + "\n" + json.dumps(gold("q8")) + "\n",
                                         encoding="utf-8")
    (tmp_path / "pred.jsonl").write_text('{"id": "q1", "type": "number", "answer": 1\n', encoding="utf-8")
    res = main(["--pred", str(tmp_path / "pred.jsonl"), "--gold", str(tmp_path / "gold.jsonl"),
                "--errors", str(tmp_path / "errors.jsonl")])
    assert res["abstain"] == 2 and res["score"] == 0


def test_unanswerable_reason_not_str_is_abstain():
    pred = {"id": "q10", "type": "unanswerable", "reason": 123}
    assert score_one(gold("q10"), pred)[0] == ABSTAIN
    assert score_one(gold("q10"), {"id": "q10", "type": "unanswerable"})[0] == CORRECT


# 3. Các ca sai format / sai giá trị
@pytest.mark.parametrize("qid, answer, reason_prefix", [
    ("q1", "89526400", "sai format"),      # số dạng chuỗi
    ("q1", True, "sai format"),            # bool không phải number
    ("q2", 0.0208, "sai giá trị"),         # percent dạng tỉ lệ thay vì số phần trăm
    ("q8", "15/02/2025", "sai format"),    # date sai định dạng
    ("q9", "có", "sai format"),            # boolean dạng chuỗi
    ("q9", 0, "sai format"),               # boolean dạng số
    ("q3", ["Xi măng Hà Tiên PCB40 bao 50kg"], "sai format"),  # string bọc trong list
    ("q6", ["287435200", "346554700"], "sai format"),          # phần tử list số dạng chuỗi
])
def test_wrong_cases(qid, answer, reason_prefix):
    st, reason = score_one(gold(qid), {"id": qid, "type": gold(qid)["type"], "answer": answer})
    assert st == WRONG
    assert reason.startswith(reason_prefix)


def test_percent_example_from_rulebook():
    g = {"id": "p", "type": "percent", "answer": 12.4, "alias": []}
    assert score_one(g, {"id": "p", "type": "percent", "answer": 12.4})[0] == CORRECT
    assert score_one(g, {"id": "p", "type": "percent", "answer": 0.124})[0] == WRONG
    assert score_one(g, {"id": "p", "type": "percent", "answer": "12,4%"})[0] == WRONG


def test_number_float_tolerance():
    assert status("q1", 89526400.0) == CORRECT
    assert status("q2", 2.08 + 1e-9) == CORRECT
    assert status("q1", 89526401) == WRONG


def test_wrong_type():
    assert score_one(gold("q1"), {"id": "q1", "type": "percent", "answer": 89526400}) == \
        (WRONG, "sai type: dự đoán 'percent', đáp án 'number'")
    assert status("q10", None, qtype="number") == WRONG
    assert status("q1", None, qtype="unanswerable") == WRONG


def test_month_date():
    g = {"id": "d", "type": "date", "answer": "2025-09", "alias": []}
    assert score_one(g, {"id": "d", "type": "date", "answer": "2025-09"})[0] == CORRECT
    assert score_one(g, {"id": "d", "type": "date", "answer": "tháng 9/2025"})[0] == WRONG


# 4. Chuẩn hóa chuỗi và alias
@pytest.mark.parametrize("answer", [
    "xi măng hà tiên pcb40 bao 50kg",
    "XI MĂNG HÀ TIÊN PCB40 BAO 50KG",
    "  Xi măng   Hà Tiên, PCB40 - bao 50kg. ",
    "SP0001",
    "sp-0001",
])
def test_string_correct(answer):
    assert status("q3", answer) == CORRECT


def test_string_alias_spelling():
    assert status("q4", "Costar Omega 3 1000 mg lọ 100 viên") == CORRECT
    assert status("q4", "SP0076") == CORRECT


def test_string_vietnamese_diacritics_matter():
    assert status("q3", "Xi mang Ha Tien PCB40 bao 50kg") == WRONG
    g = {"id": "s", "type": "string", "answer": "Sting dâu 330ml", "alias": []}
    assert score_one(g, {"id": "s", "type": "string", "answer": "Sting dầu 330ml"})[0] == WRONG
    assert score_one(g, {"id": "s", "type": "string", "answer": "sting dâu 330 ml"})[0] == CORRECT


def test_string_nfd_input():
    nfd = unicodedata.normalize("NFD", "Xi măng Hà Tiên PCB40 bao 50kg")
    assert nfd != gold("q3")["answer"]
    assert status("q3", nfd) == CORRECT
    assert normalize_str(nfd) == normalize_str(gold("q3")["answer"])


# 5. Table: đảo thứ tự dòng vẫn đúng
def test_table_row_order_irrelevant():
    ans = {"columns": ["khach_hang", "so_tien_no"],
           "rows": [["Dương Tâm Bích", 158600], ["Đỗ Đức An", 404500]]}
    assert status("q7", ans) == CORRECT


def test_table_alias_and_column_by_name_or_position():
    # Dùng mã khách hàng, đảo thứ tự cột nhưng tên cột khớp -> so theo tên
    ans = {"columns": ["so_tien_no", "khach_hang"], "rows": [[404500, "KH0124"], [158600, "KH0233"]]}
    assert status("q7", ans) == CORRECT
    # Tên cột khác hẳn -> so theo vị trí
    ans = {"columns": ["Khách", "Nợ"], "rows": [["Đỗ Đức An", 404500], ["Dương Tâm Bích", 158600]]}
    assert status("q7", ans) == CORRECT


def test_table_wrong_cases():
    base = [["Đỗ Đức An", 404500], ["Dương Tâm Bích", 158600]]
    cols = ["khach_hang", "so_tien_no"]
    assert status("q7", {"columns": cols, "rows": [["Đỗ Đức An", 404500], ["Dương Tâm Bích", 158601]]}) == WRONG
    assert status("q7", {"columns": cols, "rows": base[:1]}) == WRONG
    assert status("q7", {"columns": cols, "rows": [["Đỗ Đức An", "404.500đ"], base[1]]}) == WRONG
    assert status("q7", {"columns": cols, "rows": [base[0], base[0]]}) == WRONG
    assert status("q7", {"rows": base}) == WRONG


# 6. List: đảo thứ tự là sai
def test_list_order_matters():
    assert status("q5", ["Trà đào cam sả (M)", "Cà phê sữa (M)"]) == WRONG
    assert status("q6", [346554700, 287435200]) == WRONG


def test_list_correct_with_alias():
    assert status("q5", ["SP0003", "trà đào cam sả M"]) == CORRECT
    assert status("q5", ["Cà phê sữa (M)"]) == WRONG
    assert status("q5", "Cà phê sữa (M), Trà đào cam sả (M)") == WRONG


def test_errors_file_written(tmp_path):
    preds = [gold_to_submission(g) for g in SAMPLE_GOLD]
    preds[0] = {"id": "q1", "type": "number", "answer": "89526400"}
    res = run(tmp_path, SAMPLE_GOLD, preds)
    assert res["wrong"] == 1
    assert res["score"] == pytest.approx((len(SAMPLE_GOLD) - 2) / len(SAMPLE_GOLD))
    errs, _ = load_jsonl(tmp_path / "errors.jsonl")
    assert [e["id"] for e in errs] == ["q1"]
    assert errs[0]["reason"].startswith("sai format")
