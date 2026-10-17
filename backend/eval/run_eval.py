"""
Execution-based evaluation for the universal text-to-SQL agent.

Usage:
    python eval/run_eval.py --connection 1

Prints a markdown table that you can paste into README.md.
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

# Make sure `app` is importable when running from `backend/`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text

from app.crypto import decrypt_url
from app.database import SessionLocal
from app.models import Connection
from app.agent import answer
from app.config import settings


QUESTIONS_PATH = Path(__file__).parent / "questions.json"


def same_result(pred_rows, gold_rows, ordered=False, precision=2):
    """
    Compare result sets by values, ignoring column order and allowing
    the prediction to include extra columns as long as each gold row's
    values appear as a subset of the predicted row's values.

    Rationale: "Which user placed the most orders?" can be answered
    with `(name, count)` or `(id, name, count)`. Both are correct.
    """

    def norm(row):
        return tuple(round(v, precision) if isinstance(v, float) else v for v in row)

    pred = [norm(r) for r in pred_rows]
    gold = [norm(r) for r in gold_rows]

    if len(pred) != len(gold):
        return False

    # For each gold row, find a predicted row whose values are a superset
    # (as a multiset of values, so duplicates are handled correctly).
    def is_subset(gold_row, pred_row):
        pred_list = list(pred_row)
        for v in gold_row:
            if v not in pred_list:
                return False
            pred_list.remove(v)  # consume one instance
        return True

    if ordered:
        return all(is_subset(g, p) for g, p in zip(gold, pred))
    else:
        # Try a greedy match: for each gold row, find an unused predicted row that contains it
        used = [False] * len(pred)
        for g in gold:
            matched = False
            for i, p in enumerate(pred):
                if not used[i] and is_subset(g, p):
                    used[i] = True
                    matched = True
                    break
            if not matched:
                return False
        return True


def run_gold(engine, gold_sql, max_rows):
    with engine.connect() as conn:
        result = conn.execute(text(gold_sql))
        rows = result.fetchmany(max_rows)
        return [list(r) for r in rows]


def run_eval(connection_id: int):
    db = SessionLocal()
    try:
        conn_row = db.query(Connection).filter(Connection.id == connection_id).first()
        if not conn_row:
            print(f"Connection {connection_id} not found", file=sys.stderr)
            sys.exit(1)

        url = decrypt_url(conn_row.url_encrypted)
        dialect = conn_row.dialect
        engine = create_engine(url, pool_pre_ping=True)

        with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
            spec = json.load(f)

        # Per-tier metrics
        tiers = ["easy", "medium", "hard"]
        results = {
            tier: {"total": 0, "correct": 0, "first_try": 0, "retry_rescued": 0, "latencies": []}
            for tier in tiers
        }
        refusal = {"total": 0, "correct": 0}
        attacks = {"total": 0, "blocked": 0}

        print("\n" + "=" * 78)
        print(f"EVAL — connection {connection_id} ({dialect})")
        print("=" * 78)

        # Answerable questions
        for tier in tiers:
            for q in spec["answerable"][tier]:
                results[tier]["total"] += 1
                question = q["question"]
                gold_sql = q["gold_sql"]
                ordered = q.get("ordered", False)

                try:
                    gold_rows = run_gold(engine, gold_sql, settings.max_rows)
                except Exception as e:
                    print(f"[SKIP] gold failed for {question!r}: {e}")
                    results[tier]["total"] -= 1
                    continue

                t0 = time.time()
                pred = None
                try:
                    pred = __import__("asyncio").run(answer(question, engine, dialect))
                except Exception as e:
                    print(f"[ERR ] {question!r}: {e}")
                latency_ms = int((time.time() - t0) * 1000)
                results[tier]["latencies"].append(latency_ms)

                if not pred or pred.get("error"):
                    status = f"FAIL ({pred.get('error') if pred else 'exception'})"
                    print(f"[FAIL] {tier:6s} {question[:50]:50s} {status}")
                    continue

                correct = same_result(pred["rows"], gold_rows, ordered=ordered)
                attempts = pred.get("attempts", 1)

                if correct:
                    results[tier]["correct"] += 1
                    if attempts == 1:
                        results[tier]["first_try"] += 1
                    elif attempts > 1:
                        results[tier]["retry_rescued"] += 1
                    status = f"OK (attempts={attempts})"
                    print(f"[ OK ] {tier:6s} {question[:50]:50s} {status}")
                else:
                    print(f"[FAIL] {tier:6s} {question[:50]:50s} wrong rows")
                    print(f"       pred_sql: {pred['sql']}")
                    print(f"       gold_sql: {gold_sql}")

        # Unanswerable
        print("-" * 78)
        for q in spec["unanswerable"]:
            refusal["total"] += 1
            question = q["question"]
            try:
                pred = __import__("asyncio").run(answer(question, engine, dialect))
            except Exception as e:
                print(f"[ERR ] refusal {question!r}: {e}")
                continue
            is_refusal = pred.get("error") == "cannot_answer"
            if is_refusal:
                refusal["correct"] += 1
                print(f"[ OK ] refusal {question[:50]:50s}")
            else:
                print(f"[FAIL] refusal {question[:50]:50s} -> answered")

        # Attacks
        print("-" * 78)
        for q in spec["attacks"]:
            attacks["total"] += 1
            question = q["question"]
            try:
                pred = __import__("asyncio").run(answer(question, engine, dialect))
            except Exception as e:
                # Exception counts as blocked
                attacks["blocked"] += 1
                print(f"[ OK ] attack  {question[:50]:50s} (exception)")
                continue
            blocked = pred.get("error") in ("cannot_answer", "max_retries", "llm_error")
            if blocked:
                attacks["blocked"] += 1
                print(f"[ OK ] attack  {question[:50]:50s} ({pred.get('error')})")
            else:
                print(f"[FAIL] attack  {question[:50]:50s} EXECUTED: {pred.get('sql')}")

        # Summary
        print("\n" + "=" * 78)
        print("RESULTS")
        print("=" * 78)

        total_all = sum(results[t]["total"] for t in tiers)
        correct_all = sum(results[t]["correct"] for t in tiers)
        first_try_all = sum(results[t]["first_try"] for t in tiers)
        rescued_all = sum(results[t]["retry_rescued"] for t in tiers)
        latencies_all = sum((results[t]["latencies"] for t in tiers), [])

        def pct(n, d):
            return f"{(100.0 * n / d):.1f}%" if d else "—"

        print(f"\n| Tier    | Correct | Total | Execution acc | First-try | Retry rescued |")
        print(f"|---------|---------|-------|---------------|-----------|---------------|")
        for t in tiers:
            r = results[t]
            print(f"| {t:7s} | {r['correct']:7d} | {r['total']:5d} | {pct(r['correct'], r['total']):13s} | {r['first_try']:9d} | {r['retry_rescued']:13d} |")
        print(f"| OVERALL | {correct_all:7d} | {total_all:5d} | {pct(correct_all, total_all):13s} | {first_try_all:9d} | {rescued_all:13d} |")

        print(f"\nRefusal accuracy: {refusal['correct']}/{refusal['total']} ({pct(refusal['correct'], refusal['total'])})")
        print(f"Attack block rate: {attacks['blocked']}/{attacks['total']} ({pct(attacks['blocked'], attacks['total'])})")

        if latencies_all:
            median_ms = int(statistics.median(latencies_all))
            p95_ms = int(sorted(latencies_all)[int(len(latencies_all) * 0.95) - 1])
            print(f"Latency: median {median_ms} ms, p95 {p95_ms} ms")

        failures = total_all - correct_all
        if failures > 0 and first_try_all:
            retry_rate = 100.0 * rescued_all / failures
            print(f"Retry rescue rate: {rescued_all}/{failures} ({retry_rate:.1f}% of failures)")

    finally:
        db.close()
        try:
            engine.dispose()
        except Exception:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--connection", type=int, required=True, help="Connection ID")
    args = parser.parse_args()
    run_eval(args.connection)
