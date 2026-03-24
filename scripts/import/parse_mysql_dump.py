#!/usr/bin/env python3
"""
Parse MySQL dump file and extract table data.

Usage:
    python parse_mysql_dump.py --sql path/to/dump.sql --output raw/
    python parse_mysql_dump.py --sql path/to/dump.sql  # prints summary
"""
import re
import json
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Tables we care about
TABLES_OF_INTEREST = {
    "career_levels",
    "careerlevel_funding",
    "careerlevel_travelgrant",
    "funder_funding",
    "funder_travelgrant",
    "funders",
    "funding_purposes",
    "fundingpurpose_funding",
    "fundings",
    "resource_categories",
    "resource_category_resource",
    "resources",
    "subject_funding",
    "subject_travelgrant",
    "subjects",
    "travel_grants",
    "travel_purposes",
    "travelpurpose_travelgrant",
}


def unescape_mysql_string(s: str) -> str:
    """
    Unescape MySQL string escape sequences.

    MySQL escapes: \\', \\\\, \\n, \\r, \\t, \\0, \\Z, \\b
    """
    result = []
    i = 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            next_ch = s[i + 1]
            if next_ch == "'":
                result.append("'")
            elif next_ch == '\\':
                result.append('\\')
            elif next_ch == 'n':
                result.append('\n')
            elif next_ch == 'r':
                result.append('\r')
            elif next_ch == 't':
                result.append('\t')
            elif next_ch == '0':
                result.append('\x00')
            elif next_ch == 'Z':
                result.append('\x1a')
            elif next_ch == 'b':
                result.append('\b')
            else:
                # Unknown escape — keep as-is
                result.append(s[i + 1])
            i += 2
        else:
            result.append(s[i])
            i += 1
    return ''.join(result)


def tokenize_values_clause(text: str) -> List[List[Any]]:
    """
    Parse MySQL VALUES clause containing one or more row tuples.

    Handles:
    - Quoted strings with embedded escaped quotes and backslashes
    - NULL (unquoted)
    - Numeric values (int, float)
    - Binary/blob data (hex strings like 0x...)
    - Multi-row inserts: (v1,v2,...),(v3,v4,...)
    - Strings with embedded newlines

    Returns a list of rows, each row is a list of Python values.
    """
    rows: List[List[Any]] = []
    current_row: List[Any] = []
    i = 0
    n = len(text)

    # State: 'between_rows' | 'in_row' | 'after_value'
    state = 'between_rows'

    while i < n:
        ch = text[i]

        if state == 'between_rows':
            if ch == '(':
                state = 'in_row'
                current_row = []
                i += 1
            elif ch in (' ', '\t', '\n', '\r', ','):
                i += 1
            elif ch == ';':
                break
            else:
                i += 1

        elif state == 'in_row':
            # Skip whitespace before a value
            if ch in (' ', '\t', '\n', '\r'):
                i += 1
                continue

            if ch == ')':
                # End of this row
                rows.append(current_row)
                current_row = []
                state = 'between_rows'
                i += 1
                continue

            if ch == ',':
                # Between values in a row — skip
                i += 1
                continue

            # Parse a value
            value, i = parse_value(text, i, n)
            current_row.append(value)

        else:
            i += 1

    # Handle unclosed row (shouldn't happen in well-formed dumps)
    if current_row:
        rows.append(current_row)

    return rows


def parse_value(text: str, i: int, n: int) -> Tuple[Any, int]:
    """
    Parse a single MySQL value starting at position i.

    Returns (value, new_position).
    """
    ch = text[i]

    # NULL
    if text[i:i+4].upper() == 'NULL' and (i + 4 >= n or not text[i+4].isalnum()):
        return None, i + 4

    # Quoted string
    if ch == "'":
        return parse_quoted_string(text, i, n)

    # Hex blob: 0x...
    if text[i:i+2].lower() == '0x':
        j = i + 2
        while j < n and text[j] in '0123456789abcdefABCDEF':
            j += 1
        # Return None for binary blobs (cannot safely represent as text)
        return None, j

    # Numeric (int or float, possibly negative)
    if ch in '-+' or ch.isdigit():
        j = i
        if text[j] in '-+':
            j += 1
        while j < n and (text[j].isdigit() or text[j] == '.'):
            j += 1
        # Check for scientific notation
        if j < n and text[j].lower() == 'e':
            j += 1
            if j < n and text[j] in '-+':
                j += 1
            while j < n and text[j].isdigit():
                j += 1
        raw = text[i:j]
        if '.' in raw or 'e' in raw.lower():
            try:
                return float(raw), j
            except ValueError:
                return raw, j
        else:
            try:
                return int(raw), j
            except ValueError:
                return raw, j

    # Unquoted keyword values (TRUE, FALSE)
    if text[i:i+4].upper() == 'TRUE':
        return True, i + 4
    if text[i:i+5].upper() == 'FALSE':
        return False, i + 5

    # Default: consume until comma, closing paren, or end
    j = i
    while j < n and text[j] not in (',', ')'):
        j += 1
    return text[i:j].strip(), j


def parse_quoted_string(text: str, i: int, n: int) -> Tuple[str, int]:
    """
    Parse a MySQL single-quoted string starting at position i (the opening quote).

    Handles:
    - Escaped quotes: \\'  or ''  (doubled-quote style)
    - All other MySQL escape sequences

    Returns (unescaped_string, position_after_closing_quote).
    """
    assert text[i] == "'"
    i += 1  # Skip opening quote
    result = []

    while i < n:
        ch = text[i]

        if ch == '\\':
            # Escape sequence
            if i + 1 < n:
                next_ch = text[i + 1]
                if next_ch == "'":
                    result.append("'")
                elif next_ch == '\\':
                    result.append('\\')
                elif next_ch == 'n':
                    result.append('\n')
                elif next_ch == 'r':
                    result.append('\r')
                elif next_ch == 't':
                    result.append('\t')
                elif next_ch == '0':
                    result.append('\x00')
                elif next_ch == 'Z':
                    result.append('\x1a')
                elif next_ch == 'b':
                    result.append('\b')
                else:
                    result.append(next_ch)
                i += 2
            else:
                result.append(ch)
                i += 1
        elif ch == "'":
            # Check for doubled-quote (SQL standard escaping: '' → ')
            if i + 1 < n and text[i + 1] == "'":
                result.append("'")
                i += 2
            else:
                # End of string
                i += 1
                break
        else:
            result.append(ch)
            i += 1

    return ''.join(result), i


def extract_column_names_from_create(create_stmt: str) -> List[str]:
    """
    Extract ordered column names from a CREATE TABLE statement.

    Handles backtick-quoted column names.
    """
    columns = []
    # Match lines like: `col_name` type ...
    for match in re.finditer(r'^\s*`([^`]+)`\s+\S', create_stmt, re.MULTILINE):
        col = match.group(1)
        columns.append(col)
    return columns


def parse_mysql_dump(sql_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parse a MySQL dump file and return a dict of table_name → list of row dicts.

    Only returns data for tables listed in TABLES_OF_INTEREST.

    Args:
        sql_path: Path to the MySQL .sql dump file.

    Returns:
        Dict mapping table name to list of row dicts.
    """
    path = Path(sql_path)
    if not path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")

    # Read the file, handling encoding issues gracefully
    try:
        text = path.read_text(encoding='utf-8', errors='replace')
    except Exception as e:
        raise RuntimeError(f"Failed to read SQL file: {e}")

    # result storage
    result: Dict[str, List[Dict[str, Any]]] = {t: [] for t in TABLES_OF_INTEREST}
    # Map from table name to list of column names (populated from CREATE TABLE)
    table_columns: Dict[str, List[str]] = {}

    # -------------------------------------------------------------------------
    # Phase 1: Extract CREATE TABLE statements to get column names
    # -------------------------------------------------------------------------
    # Match full CREATE TABLE blocks (from CREATE TABLE to the closing ");")
    create_pattern = re.compile(
        r'CREATE\s+TABLE\s+`([^`]+)`\s*\((.*?)\)\s*(?:ENGINE|DEFAULT|CHARSET|;)',
        re.IGNORECASE | re.DOTALL
    )
    for m in create_pattern.finditer(text):
        table_name = m.group(1)
        if table_name in TABLES_OF_INTEREST:
            create_body = m.group(0)
            columns = extract_column_names_from_create(create_body)
            table_columns[table_name] = columns

    # -------------------------------------------------------------------------
    # Phase 2: Extract INSERT INTO statements
    # -------------------------------------------------------------------------
    # We need to handle INSERT statements that may span many lines.
    # Strategy: find all INSERT INTO `table` (optionally with column list) VALUES ...;
    # We split on INSERT INTO boundaries, then parse each chunk.

    # Find all INSERT INTO positions
    insert_pattern = re.compile(
        r'INSERT\s+INTO\s+`([^`]+)`(?:\s*\([^)]*\))?\s+VALUES\s*',
        re.IGNORECASE
    )

    for m in insert_pattern.finditer(text):
        table_name = m.group(1)
        if table_name not in TABLES_OF_INTEREST:
            continue

        # Get column list from the INSERT header if present (rare in mysqldump)
        header_col_match = re.match(
            r'INSERT\s+INTO\s+`[^`]+`\s*\(([^)]+)\)\s+VALUES\s*',
            m.group(0),
            re.IGNORECASE
        )
        if header_col_match:
            cols_str = header_col_match.group(1)
            columns = [c.strip().strip('`') for c in cols_str.split(',')]
        else:
            columns = table_columns.get(table_name, [])

        if not columns:
            print(f"  Warning: no column info for table '{table_name}', skipping INSERT")
            continue

        # The VALUES clause starts right after the match
        values_start = m.end()

        # Find the end of this INSERT statement.
        # We scan forward looking for a semicolon that is NOT inside a string.
        values_text, end_pos = extract_statement_values(text, values_start)

        # Parse the values
        try:
            rows = tokenize_values_clause(values_text)
        except Exception as e:
            print(f"  Warning: failed to parse INSERT for '{table_name}': {e}")
            continue

        # Map rows to dicts
        for row in rows:
            if len(row) != len(columns):
                # Try to handle mismatches gracefully
                if len(row) < len(columns):
                    row = row + [None] * (len(columns) - len(row))
                else:
                    row = row[:len(columns)]
            row_dict = dict(zip(columns, row))
            result[table_name].append(row_dict)

    return result


def extract_statement_values(text: str, start: int) -> Tuple[str, int]:
    """
    Starting at `start` (just after 'VALUES '), scan forward to find the
    complete VALUES clause ending with ';'.

    Returns (values_text, end_position).
    Handles quoted strings so semicolons inside strings don't terminate early.
    """
    n = len(text)
    i = start
    in_string = False
    escape_next = False

    while i < n:
        ch = text[i]

        if escape_next:
            escape_next = False
            i += 1
            continue

        if in_string:
            if ch == '\\':
                escape_next = True
                i += 1
            elif ch == "'":
                # Check for doubled quote
                if i + 1 < n and text[i + 1] == "'":
                    i += 2
                else:
                    in_string = False
                    i += 1
            else:
                i += 1
        else:
            if ch == "'":
                in_string = True
                i += 1
            elif ch == ';':
                # End of statement
                return text[start:i], i + 1
            else:
                i += 1

    # No semicolon found — return everything
    return text[start:], n


def print_summary(data: Dict[str, List[Dict[str, Any]]]) -> None:
    """Print a summary of parsed tables."""
    print("\nParsed table row counts:")
    print("-" * 40)
    for table in sorted(TABLES_OF_INTEREST):
        count = len(data.get(table, []))
        print(f"  {table:<40} {count:>6} rows")
    print()


def save_output(data: Dict[str, List[Dict[str, Any]]], output_dir: str) -> None:
    """Save each table's data as a JSON file in output_dir."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    for table_name, rows in data.items():
        if not rows:
            continue
        file_path = out_path / f"{table_name}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(rows, f, ensure_ascii=False, indent=2, default=str)
        print(f"  Saved {len(rows)} rows → {file_path}")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Parse MySQL dump file and extract table data.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--sql', required=True, help='Path to MySQL .sql dump file')
    parser.add_argument(
        '--output', default=None,
        help='Directory to save raw JSON files (default: print summary only)'
    )
    args = parser.parse_args()

    print(f"Parsing MySQL dump: {args.sql}")
    data = parse_mysql_dump(args.sql)
    print_summary(data)

    if args.output:
        print(f"Saving raw JSON to: {args.output}")
        save_output(data, args.output)
        print("Done.")


if __name__ == '__main__':
    main()
