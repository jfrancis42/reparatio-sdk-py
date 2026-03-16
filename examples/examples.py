"""
Reparatio Python SDK — runnable examples.

Each example is a self-contained function.  Run the whole file:

    python examples/examples.py

Or run a single example:

    python -c "from examples.examples import ex_inspect_csv; ex_inspect_csv()"

These examples require a valid REPARATIO_API_KEY environment variable.
"""

import io
import json
import os
import sys
import tempfile
import zipfile

from reparatio import (
    Reparatio,
    AuthenticationError,
    InsufficientPlanError,
    FileTooLargeError,
    ParseError,
    APIError,
)

# ── Shared configuration ───────────────────────────────────────────────────────

API_KEY  = os.getenv("REPARATIO_API_KEY",  "EXAMPLE-EXAMPLE-EXAMPLE")

def _client() -> Reparatio:
    return Reparatio(api_key=API_KEY)

def _sep(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print('─' * 60)

# ── Example 1: formats() — list supported formats (no key required) ───────────

def ex_formats() -> None:
    _sep("1. formats() — list supported input/output formats")

    with Reparatio() as client:  # no key needed
        f = client.formats()

    print(f"Input formats  ({len(f.input)}): {', '.join(f.input[:8])} …")
    print(f"Output formats ({len(f.output)}): {', '.join(f.output[:8])} …")
    assert "csv" in f.input
    assert "parquet" in f.output
    print("PASS")


# ── Example 2: me() — account info ────────────────────────────────────────────

def ex_me() -> None:
    _sep("2. me() — account / subscription details")

    with _client() as client:
        me = client.me()

    print(f"Email:      {me.email}")
    print(f"Plan:       {me.plan}")
    print(f"Active:     {me.active}")
    print(f"API access: {me.api_access}")
    assert me.active
    assert me.api_access
    print("PASS")


# ── Example 3: inspect() — file metadata from inline bytes ────────────────────

def ex_inspect_csv() -> None:
    _sep("3. inspect() — CSV from inline bytes")

    csv_bytes = b"country,county\nEngland,Kent\nEngland,Essex\nWales,Gwent\n"
    with _client() as client:
        result = client.inspect(csv_bytes, filename="counties.csv")

    print(f"Filename:  {result.filename}")
    print(f"Rows:      {result.rows}")
    print(f"Encoding:  {result.detected_encoding}")
    print(f"Columns ({len(result.columns)}):")
    for col in result.columns:
        print(f"  {col.name:<25} {col.dtype:<15} nulls={col.null_count}")
    print(f"Preview row 0: {result.preview[0]}")
    assert result.rows > 0
    assert len(result.columns) > 0
    print("PASS")


# ── Example 4: inspect() — pass raw bytes with explicit filename ──────────────

def ex_inspect_bytes() -> None:
    _sep("4. inspect() — raw bytes (in-memory CSV)")

    csv_bytes = b"id,name,score\n1,Alice,95\n2,Bob,87\n3,Carol,92\n"
    with _client() as client:
        result = client.inspect(csv_bytes, filename="scores.csv")

    print(f"Rows:    {result.rows}")
    print(f"Columns: {[c.name for c in result.columns]}")
    print(f"Preview: {result.preview}")
    assert result.rows == 3
    assert [c.name for c in result.columns] == ["id", "name", "score"]
    print("PASS")


# ── Example 5: inspect() — TSV bytes ─────────────────────────────────────────

def ex_inspect_tsv() -> None:
    _sep("5. inspect() — TSV from inline bytes")

    tsv_bytes = b"name\tage\tcity\nAlice\t30\tBoston\nBob\t25\tChicago\nCarol\t35\tDenver\n"
    with _client() as client:
        result = client.inspect(tsv_bytes, filename="people.tsv")

    print(f"Filename: {result.filename}")
    print(f"Rows:     {result.rows}")
    print(f"Columns:  {[c.name for c in result.columns]}")
    assert result.rows > 0
    print("PASS")


# ── Example 6: convert() — CSV → Parquet ─────────────────────────────────────

def ex_convert_csv_to_parquet() -> None:
    _sep("6. convert() — CSV → Parquet")

    csv_bytes = b"country,county\nEngland,Kent\nEngland,Essex\nWales,Gwent\n"
    with _client() as client:
        out = client.convert(csv_bytes, "parquet", filename="counties.csv")

    print(f"Output filename: {out.filename}")
    print(f"Output size:     {len(out.content):,} bytes")
    assert out.filename.endswith(".parquet")
    assert len(out.content) > 0
    # Parquet magic bytes: PAR1
    assert out.content[:4] == b"PAR1", "Not a valid Parquet file"
    print("PASS")


# ── Example 7: convert() — CSV → JSON Lines ──────────────────────────────────

def ex_convert_csv_to_jsonl() -> None:
    _sep("7. convert() — CSV → JSON Lines")

    csv_bytes = (
        b"id,product,price\n"
        b"1,Widget,9.99\n"
        b"2,Gadget,19.99\n"
        b"3,Doohickey,4.99\n"
    )
    with _client() as client:
        out = client.convert(csv_bytes, "jsonl", filename="products.csv")

    lines = [l for l in out.content.decode().splitlines() if l.strip()]
    print(f"Output filename: {out.filename}")
    print(f"Lines:           {len(lines)}")
    print(f"First record:    {lines[0]}")
    assert out.filename.endswith(".jsonl")
    assert len(lines) > 0
    assert json.loads(lines[0])  # valid JSON
    print("PASS")


# ── Example 8: convert() — select + rename columns, compress output ───────────

def ex_convert_select_columns() -> None:
    _sep("8. convert() — select columns, rename, and gzip")

    csv_bytes = b"region,product,revenue,quantity\nNorth,Widget,100,5\nSouth,Gadget,200,3\n"

    # First inspect to see available columns
    with _client() as client:
        info = client.inspect(csv_bytes, filename="sales.csv")
        col_names = [c.name for c in info.columns]
        print(f"Available columns: {col_names}")

        # Take first two columns and rename them
        selected = col_names[:2]
        renamed  = ["ColA", "ColB"]
        out = client.convert(
            csv_bytes,
            "csv.gz",
            filename="sales.csv",
            select_columns=selected,
            columns=renamed,
        )

    print(f"Output filename: {out.filename}")
    print(f"Output size:     {len(out.content):,} bytes (compressed)")
    assert out.filename.endswith(".csv.gz")
    assert len(out.content) > 0
    print("PASS")


# ── Example 9: convert() — deduplicate and sample ────────────────────────────

def ex_convert_deduplicate_sample() -> None:
    _sep("9. convert() — deduplicate rows + 50% sample")

    # Build a CSV with deliberate duplicates
    rows = ["name,value"] + ["Alice,1", "Alice,1", "Bob,2", "Bob,2"] * 10
    csv_bytes = "\n".join(rows).encode()

    with _client() as client:
        # First confirm raw row count
        info = client.inspect(csv_bytes, filename="dupes.csv")
        print(f"Raw rows (with dupes): {info.rows}")

        out = client.convert(
            csv_bytes,
            "csv",
            filename="dupes.csv",
            deduplicate=True,
            sample_frac=0.5,
        )

    result_rows = [l for l in out.content.decode().splitlines() if l.strip()]
    print(f"After dedup+sample:    {len(result_rows) - 1} data rows")
    assert len(result_rows) > 1  # header + at least one data row
    print("PASS")


# ── Example 10: convert() — cast column types ────────────────────────────────

def ex_convert_cast_columns() -> None:
    _sep("10. convert() — override column types with cast_columns")

    csv_bytes = (
        b"id,amount,event_date\n"
        b"1,19.99,2025-01-15\n"
        b"2,34.50,2025-02-20\n"
        b"3,7.00,2025-03-01\n"
    )

    with _client() as client:
        out = client.convert(
            csv_bytes,
            "parquet",
            filename="sales.csv",
            cast_columns={
                "id":         {"type": "Int32"},
                "amount":     {"type": "Float64"},
                "event_date": {"type": "Date", "format": "%Y-%m-%d"},
            },
        )

    print(f"Output filename: {out.filename}")
    print(f"Output size:     {len(out.content):,} bytes")
    assert out.content[:4] == b"PAR1"

    # Round-trip inspect to verify types were applied
    with _client() as client:
        info = client.inspect(out.content, filename=out.filename)
    type_map = {c.name: c.dtype for c in info.columns}
    print(f"Column types: {type_map}")
    # Int32 is widened to Int64 by the server; both are acceptable.
    assert type_map["id"] in ("Int32", "Int64")
    assert type_map["amount"] == "Float64"
    # Parquet stores Date as an integer with metadata; Polars may read it back
    # as Date or as String depending on schema inference depth.
    assert type_map["event_date"] in ("Date", "String")
    print("PASS")


# ── Example 11: query() — SQL against a CSV ───────────────────────────────────

def ex_query() -> None:
    _sep("11. query() — SQL aggregation against a CSV file")

    csv_bytes = (
        b"region,product,revenue\n"
        b"North,Widget,100\n"
        b"South,Widget,200\n"
        b"North,Gadget,150\n"
        b"South,Gadget,300\n"
        b"North,Widget,120\n"
    )

    with _client() as client:
        out = client.query(
            csv_bytes,
            "SELECT region, SUM(revenue) AS total FROM data GROUP BY region ORDER BY total DESC",
            filename="sales.csv",
            target_format="json",
        )

    result = json.loads(out.content)
    print(f"Query result: {result}")
    assert len(result) == 2
    # South should have the higher total (500 vs 370)
    assert result[0]["region"] == "South"
    assert result[0]["total"] == 500
    print("PASS")


# ── Example 12: append() — stack multiple CSVs ───────────────────────────────

def ex_append() -> None:
    _sep("12. append() — stack multiple CSVs vertically")

    # Three monthly sales files with matching columns
    jan = b"date,region,revenue\n2025-01-01,North,100\n2025-01-02,South,200\n"
    feb = b"date,region,revenue\n2025-02-01,North,150\n2025-02-02,South,180\n"
    mar = b"date,region,revenue\n2025-03-01,North,120\n2025-03-02,South,210\n"

    with _client() as client:
        out = client.append(
            [jan, feb, mar],
            "csv",
            filenames=["jan.csv", "feb.csv", "mar.csv"],
        )

    lines = [l for l in out.content.decode().splitlines() if l.strip()]
    print(f"Output filename: {out.filename}")
    print(f"Total rows (incl. header): {len(lines)}")
    print(f"Header: {lines[0]}")
    assert len(lines) == 7  # 1 header + 6 data rows across 3 files
    print("PASS")


# ── Example 13: merge() — join two files on a key column ─────────────────────

def ex_merge_join() -> None:
    _sep("13. merge() — inner join two CSVs on a key column")

    orders_csv = (
        b"order_id,customer_id,amount\n"
        b"1001,C1,50.00\n"
        b"1002,C2,75.00\n"
        b"1003,C1,30.00\n"
        b"1004,C3,90.00\n"
    )
    customers_csv = (
        b"customer_id,name,city\n"
        b"C1,Alice,Boston\n"
        b"C2,Bob,Chicago\n"
    )

    with _client() as client:
        out = client.merge(
            orders_csv,
            customers_csv,
            operation="inner",
            target_format="csv",
            filename1="orders.csv",
            filename2="customers.csv",
            join_on="customer_id",
        )

    lines = [l for l in out.content.decode().splitlines() if l.strip()]
    print(f"Output filename: {out.filename}")
    print(f"Result rows (incl. header): {len(lines)}")
    print(f"Header: {lines[0]}")
    for row in lines[1:]:
        print(f"  {row}")
    # C3 has no matching customer so inner join yields 3 rows (orders C1, C2, C1)
    assert len(lines) == 4  # header + 3 matched rows
    print("PASS")


# ── Example 14: batch_convert() — ZIP of CSVs → ZIP of Parquets ──────────────

def ex_batch_convert() -> None:
    _sep("14. batch_convert() — ZIP of CSVs → ZIP of Parquet files")

    # Build a ZIP in memory with two small CSVs
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("sales_jan.csv", "date,amount\n2025-01-01,100\n2025-01-02,200\n")
        zf.writestr("sales_feb.csv", "date,amount\n2025-02-01,150\n2025-02-02,180\n")
    zip_bytes = buf.getvalue()

    with _client() as client:
        out = client.batch_convert(zip_bytes, "parquet", filename="monthly.zip")

    # Unpack the returned ZIP and verify each file
    with zipfile.ZipFile(io.BytesIO(out.content)) as zf:
        names = zf.namelist()
        print(f"Output files: {names}")
        for name in names:
            data = zf.read(name)
            assert data[:4] == b"PAR1", f"{name} is not a valid Parquet file"
            print(f"  {name}: {len(data):,} bytes — valid Parquet")

    if out.warning:
        print(f"Warnings: {out.warning}")

    assert len(names) == 2
    print("PASS")


# ── Example 15: error handling ────────────────────────────────────────────────

def ex_error_handling() -> None:
    _sep("15. error handling — bad key, bad file, unsupported format")

    # Bad API key → AuthenticationError
    with Reparatio(api_key="rp_invalid") as bad_client:
        try:
            bad_client.convert(b"a,b\n1,2\n", "parquet", filename="test.csv")
            assert False, "Should have raised"
        except (AuthenticationError, InsufficientPlanError) as e:
            print(f"Bad key caught:        {type(e).__name__}: {e}")

    # Unparseable file → ParseError
    with _client() as client:
        try:
            client.convert(b"\x00\x01\x02\x03garbage", "csv", filename="bad.parquet")
            assert False, "Should have raised"
        except (ParseError, APIError) as e:
            print(f"Bad file caught:       {type(e).__name__}: {e}")

    print("PASS")


# ── Runner ────────────────────────────────────────────────────────────────────

_EXAMPLES = [
    ex_formats,
    ex_me,
    ex_inspect_csv,
    ex_inspect_bytes,
    ex_inspect_tsv,
    ex_convert_csv_to_parquet,
    ex_convert_csv_to_jsonl,
    ex_convert_select_columns,
    ex_convert_deduplicate_sample,
    ex_convert_cast_columns,
    ex_query,
    ex_append,
    ex_merge_join,
    ex_batch_convert,
    ex_error_handling,
]

if __name__ == "__main__":
    passed, failed = 0, []
    for fn in _EXAMPLES:
        try:
            fn()
            passed += 1
        except Exception as exc:
            failed.append((fn.__name__, exc))
            print(f"  FAIL: {exc}")

    _sep(f"Results: {passed}/{len(_EXAMPLES)} passed")
    if failed:
        for name, exc in failed:
            print(f"  FAIL  {name}: {exc}")
        sys.exit(1)
    else:
        print("  All examples passed.")
