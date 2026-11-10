"""Create a repeatable retail fixture with duplicates and a few bad records."""
import csv
from datetime import datetime, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from retail.model import COLUMNS


def rows():
    products = [("P01", "Desk lamp", "Home", "24.50"),
                ("P02", "Notebook", "Stationery", "5.00"),
                ("P03", "Headphones", "Electronics", "49.95"),
                ("P04", "Travel mug", "Home", "12.00")]
    result = []
    for i in range(1200):
        order = i // 2
        pid, name, category, price = products[(order + i % 2) % 4]
        timestamp = datetime(2026, 1, 1, 12) + timedelta(days=order % 60)
        cid = f"C{order % 80:03}"
        result.append(dict(zip(COLUMNS, [
            f"O{order:05}", str(i % 2 + 1), timestamp.isoformat(" "), cid,
            f"{cid.lower()}@example.invalid", pid, name, category,
            ["East", "West", "North", "South"][order % 4],
            str(i % 3 + 1), price, "0.1000" if order % 5 == 0 else "0",
            "cancelled" if order % 17 == 0 else "returned" if order % 23 == 0 else "completed",
            timestamp.isoformat(" "), "USD",
        ])))
    # Replay one line, then correct another with a later timestamp.
    result.append(result[0].copy())
    result.append({**result[1], "quantity": "4", "updated_at": "2026-04-01 12:00:00"})
    # This broken correction should quarantine the key, not restore its older value.
    result.append({**result[2], "quantity": "oops", "updated_at": "2026-04-02 12:00:00"})
    for n, changes in enumerate([
        {"quantity": "oops"}, {"order_ts": "bad-date"}, {"quantity": "-1"},
        {"discount_pct": "1.5"}, {"currency": "EUR"}, {"quantity": "1.5"},
        {"customer_id": ""}, {"unit_price": "-2"},
    ]):
        result.append({**result[10 + n], "order_id": f"BAD{n}", **changes})
    return result


if __name__ == "__main__":
    target = ROOT / "data" / "sample_orders.csv"
    target.parent.mkdir(exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows())
    print(f"Wrote {len(rows())} fictional source rows to {target}")
