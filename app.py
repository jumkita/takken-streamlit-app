import csv
import io
import os
import random
import statistics
from datetime import datetime

import streamlit as st

from question_bank import COMPOSITION, PASS_HISTORY, QUESTION_BANK


st.set_page_config(
    page_title="宅建 直前ブースター",
    page_icon="🏠",
    layout="centered",
)


st.markdown(
    """
<style>
.main > div {
  max-width: 860px;
}
.pill {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  background: #eef2ff;
  color: #1e3a8a;
  font-size: 12px;
  margin-right: 6px;
}
.warn {
  border-left: 4px solid #f59e0b;
  padding: 8px 12px;
  background: #fffbeb;
  font-size: 13px;
}
</style>
""",
    unsafe_allow_html=True,
)


def init_state() -> None:
    if "quiz" not in st.session_state:
        st.session_state.quiz = None
    if "history" not in st.session_state:
        st.session_state.history = []


def require_access_key() -> None:
    secret_key = ""
    try:
        secret_key = st.secrets.get("ACCESS_KEY", "")
    except Exception:
        secret_key = ""
    if not secret_key:
        secret_key = os.getenv("ACCESS_KEY", "")

    # キー未設定なら認証なしで利用可能（デモ用）
    if not secret_key:
        return

    if st.session_state.get("auth_ok"):
        return

    st.title("🔐 利用認証")
    st.write("購入者用アクセスキーを入力してください。")
    typed = st.text_input("アクセスキー", type="password")
    if st.button("認証する", type="primary", use_container_width=True):
        if typed == secret_key:
            st.session_state.auth_ok = True
            st.success("認証に成功しました。")
            st.rerun()
        st.error("アクセスキーが違います。")
    st.stop()


def estimate_pass_line(questions: list[dict]) -> int:
    recent = [h["score"] for h in PASS_HISTORY[:5]]
    base = round(statistics.mean(recent))
    avg_diff = statistics.mean(q["difficulty"] for q in questions)

    adjust = 0
    if avg_diff >= 2.3:
        adjust = -1
    elif avg_diff <= 1.7:
        adjust = 1

    line = base + adjust
    return max(31, min(39, line))


def generate_mock_questions() -> list[dict]:
    picked = []
    for field, count in COMPOSITION.items():
        pool = [q for q in QUESTION_BANK if q["field"] == field]
        if len(pool) < count:
            raise ValueError(f"{field} の問題数が不足しています。必要:{count}, 現在:{len(pool)}")
        picked.extend(random.sample(pool, count))
    random.shuffle(picked)
    return picked


def generate_field_questions(field: str, count: int) -> list[dict]:
    pool = [q for q in QUESTION_BANK if q["field"] == field]
    if count > len(pool):
        count = len(pool)
    questions = random.sample(pool, count)
    random.shuffle(questions)
    return questions


def start_quiz(mode: str, questions: list[dict], study_mode: str) -> None:
    st.session_state.quiz = {
        "mode": mode,
        "study_mode": study_mode,  # review / practice
        "questions": questions,
        "answers": {},
        "revealed": [],  # 復習モードで判定済みの問題ID
        "current": 0,
        "submitted": False,
        "result": None,
        "started_at": datetime.now(),
        "pass_line": estimate_pass_line(questions),
    }


def score_quiz(quiz: dict) -> dict:
    questions = quiz["questions"]
    answers = quiz["answers"]
    total = len(questions)
    correct = 0
    field_total = {}
    field_correct = {}
    wrong_rows = []

    for q in questions:
        qid = q["id"]
        field = q["field"]
        picked = answers.get(qid)
        ok = picked == q["answer"]
        if ok:
            correct += 1
            field_correct[field] = field_correct.get(field, 0) + 1
        field_total[field] = field_total.get(field, 0) + 1

        if not ok:
            wrong_rows.append(
                {
                    "id": qid,
                    "field": field,
                    "question": q["question"],
                    "picked": "未回答" if picked is None else q["choices"][picked],
                    "correct": q["choices"][q["answer"]],
                    "explanation": q["explanation"],
                }
            )

    rows = []
    for field in field_total:
        rows.append(
            {
                "分野": field,
                "正解数": field_correct.get(field, 0),
                "問題数": field_total[field],
                "正答率": f"{(field_correct.get(field, 0) / field_total[field]) * 100:.1f}%",
            }
        )

    return {
        "correct": correct,
        "total": total,
        "rate": correct / total,
        "field_rows": rows,
        "wrong_rows": wrong_rows,
        "pass_line": quiz["pass_line"],
    }


def to_result_csv(result: dict, quiz: dict) -> bytes:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["mode", quiz["mode"]])
    writer.writerow(["timestamp", datetime.now().isoformat(timespec="seconds")])
    writer.writerow(["score", f"{result['correct']}/{result['total']}"])
    writer.writerow(["rate", f"{result['rate'] * 100:.1f}%"])
    writer.writerow(["pass_line", result["pass_line"]])
    writer.writerow([])
    writer.writerow(["分野", "正解数", "問題数", "正答率"])
    for row in result["field_rows"]:
        writer.writerow([row["分野"], row["正解数"], row["問題数"], row["正答率"]])
    writer.writerow([])
    writer.writerow(["誤答ID", "分野", "問題", "あなたの回答", "正解", "解説"])
    for row in result["wrong_rows"]:
        writer.writerow([row["id"], row["field"], row["question"], row["picked"], row["correct"], row["explanation"]])
    return out.getvalue().encode("utf-8-sig")


def render_setup() -> None:
    st.title("🏠 宅建 直前ブースター")
    st.caption("スマホでも使える、直前期向けの4択復習アプリ")

    st.markdown(
        """
<div class="warn">
本アプリの問題・解説は、過去問の出題傾向を参考にした<strong>オリジナル作成</strong>です。<br>
本試験の法改正・最新運用は必ず公式情報でも確認してください。
</div>
""",
        unsafe_allow_html=True,
    )

    st.subheader("演習モード")
    mode = st.radio("モードを選択", ["本番形式（50問）", "分野別（短時間復習）"], horizontal=True)
    study_mode_label = st.radio(
        "解答スタイル",
        ["復習モード（1問ごとに正解・解説を表示）", "実践モード（最後にまとめて採点）"],
        horizontal=True,
    )
    study_mode = "review" if study_mode_label.startswith("復習モード") else "practice"

    if mode == "本番形式（50問）":
        st.write("実試験の構成比（権利14 / 業法20 / 法令8 / 税その他8）で50問を出題します。")
        if st.button("本番形式を開始", type="primary", use_container_width=True):
            questions = generate_mock_questions()
            start_quiz("mock", questions, study_mode)
            st.rerun()
    else:
        fields = list(COMPOSITION.keys())
        field = st.selectbox("分野", fields, index=0)
        max_count = len([q for q in QUESTION_BANK if q["field"] == field])
        count = st.slider("問題数", min_value=5, max_value=max_count, value=min(10, max_count), step=1)
        if st.button("分野別演習を開始", type="primary", use_container_width=True):
            questions = generate_field_questions(field, count)
            start_quiz("field", questions, study_mode)
            st.rerun()

    with st.expander("合格推定ラインの考え方"):
        st.write("直近合格点（目安）:", " / ".join(f"{x['year']}:{x['score']}点" for x in PASS_HISTORY[:6]))
        st.write("直近の平均点をベースに、今回セットの難易度（易/標準/難）で ±1 点補正しています。")


def render_quiz() -> None:
    quiz = st.session_state.quiz
    questions = quiz["questions"]
    total = len(questions)
    idx = quiz["current"]
    q = questions[idx]
    study_mode = quiz.get("study_mode", "practice")
    is_review = study_mode == "review"
    revealed_set = set(quiz.get("revealed", []))
    qid = q["id"]
    is_revealed = qid in revealed_set

    st.subheader("📝 演習中")
    st.progress((idx + 1) / total, text=f"進捗 {idx + 1}/{total}")
    st.caption(f"現在の解答スタイル: {'復習モード' if is_review else '実践モード'}")
    st.markdown(
        f"<span class='pill'>{q['field']}</span><span class='pill'>出題傾向 {q['year']}</span>",
        unsafe_allow_html=True,
    )
    st.write(f"**Q{idx + 1}. {q['question']}**")

    key = f"ans_{qid}"
    prev_val = quiz["answers"].get(qid)
    default_index = prev_val if prev_val is not None else 0
    choice = st.radio(
        "選択肢",
        q["choices"],
        index=default_index,
        key=key,
        disabled=is_review and is_revealed,
    )
    picked_index = q["choices"].index(choice)
    quiz["answers"][qid] = picked_index

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("← 前へ", use_container_width=True, disabled=(idx == 0)):
            quiz["current"] -= 1
            st.rerun()
    with col2:
        if st.button("次へ →", use_container_width=True, disabled=(idx == total - 1)):
            quiz["current"] += 1
            st.rerun()
    with col3:
        if is_review:
            if not is_revealed:
                if st.button("この回答で判定", type="primary", use_container_width=True):
                    revealed_set.add(qid)
                    quiz["revealed"] = list(revealed_set)
                    if idx < total - 1:
                        quiz["current"] += 1
                    st.rerun()
            else:
                st.button("判定済み", use_container_width=True, disabled=True)

    if is_review and is_revealed:
        if quiz["answers"].get(qid) == q["answer"]:
            st.success(f"正解: {q['choices'][q['answer']]}")
        else:
            st.error(f"不正解: 正解は「{q['choices'][q['answer']]}」です")
        st.info(f"解説: {q['explanation']}")

    can_submit = (len(revealed_set) == total) if is_review else (len(quiz["answers"]) == total)
    submit_label = "全体結果を見る" if is_review else "採点する"
    if st.button(submit_label, type="primary", use_container_width=True, disabled=not can_submit, key="final_submit"):
        result = score_quiz(quiz)
        quiz["submitted"] = True
        quiz["result"] = result
        st.session_state.history.append(
            {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "mode": f"{'本番' if quiz['mode'] == 'mock' else '分野別'}-{'復習' if is_review else '実践'}",
                "score": f"{result['correct']}/{result['total']}",
                "rate": f"{result['rate'] * 100:.1f}%",
            }
        )
        st.rerun()

    progress_label = "判定済み" if is_review else "回答済み"
    current_progress = len(revealed_set) if is_review else len(quiz["answers"])
    st.caption(f"{progress_label}: {current_progress}/{total}")


def render_result() -> None:
    quiz = st.session_state.quiz
    result = quiz["result"]
    assert result is not None

    st.subheader("✅ 採点結果")
    st.caption(f"解答スタイル: {'復習モード' if quiz.get('study_mode') == 'review' else '実践モード'}")
    c1, c2, c3 = st.columns(3)
    c1.metric("得点", f"{result['correct']} / {result['total']}")
    c2.metric("正答率", f"{result['rate'] * 100:.1f}%")
    c3.metric("合格推定ライン", f"{result['pass_line']} 点")

    if quiz["mode"] == "mock":
        if result["correct"] >= result["pass_line"]:
            st.success("合格推定ラインをクリアしました。直前仕上げとして良い状態です。")
        else:
            need = result["pass_line"] - result["correct"]
            st.warning(f"合格推定ラインまであと {need} 点。誤答分野の復習を優先しましょう。")

    st.write("### 分野別成績")
    st.dataframe(result["field_rows"], use_container_width=True, hide_index=True)

    st.write("### 誤答復習（解説つき）")
    if not result["wrong_rows"]:
        st.info("全問正解です。素晴らしいです。")
    else:
        for row in result["wrong_rows"]:
            with st.expander(f"{row['id']} | {row['field']}"):
                st.write(f"**問題**: {row['question']}")
                st.write(f"**あなたの回答**: {row['picked']}")
                st.write(f"**正解**: {row['correct']}")
                st.write(f"**解説**: {row['explanation']}")

    csv_bytes = to_result_csv(result, quiz)
    st.download_button(
        "結果CSVをダウンロード",
        data=csv_bytes,
        file_name=f"takken_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("同じセットを解き直す", use_container_width=True):
            quiz["submitted"] = False
            quiz["result"] = None
            quiz["answers"] = {}
            quiz["current"] = 0
            st.rerun()
    with c2:
        if st.button("新しい問題セットを作る", type="primary", use_container_width=True):
            st.session_state.quiz = None
            st.rerun()


def render_history() -> None:
    if not st.session_state.history:
        return
    with st.sidebar:
        st.write("### 最近の演習")
        st.dataframe(st.session_state.history[-10:], hide_index=True, use_container_width=True)


def main() -> None:
    init_state()
    require_access_key()
    render_history()

    if st.session_state.quiz is None:
        render_setup()
        return

    if st.session_state.quiz["submitted"]:
        render_result()
    else:
        render_quiz()


if __name__ == "__main__":
    main()
