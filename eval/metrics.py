"""Compare decision fields against the supplied labels."""
FIELDS = ("action", "language", "category", "priority")


def summarize(results: list[dict]) -> dict:
    total = len(results)
    correct = {field: sum(
        not row.get("error")
        and row["prediction"][field] == row["expected"][field]
        for row in results) for field in FIELDS}
    return {
        "cases": total,
        "correct": correct,
        "accuracy": {field: count / total if total else 0 for field, count in correct.items()},
        "all_fields_correct": sum(
            not row.get("error")
            and all(row["prediction"][f] == row["expected"][f] for f in FIELDS)
            for row in results),
        "errors": sum(bool(row.get("error")) for row in results),
    }
