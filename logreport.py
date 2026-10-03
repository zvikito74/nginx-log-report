#!/usr/bin/env python3
"""Summarise an Nginx access log.

Reads a log in Nginx's default "combined" format and prints the number of
requests, the share of errors, the busiest hours, and the most requested
pages, most active visitors and most common failing URLs.

Examples:
    logreport.py /var/log/nginx/access.log
    logreport.py access.log --top 5 --json
    cat access.log | logreport.py -
"""

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime

# 203.0.113.7 - - [03/Oct/2026:14:02:11 +0400] "GET /index.html HTTP/1.1" 200 5123 "-" "Mozilla/5.0"
LINE_PATTERN = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<path>\S+)[^"]*" '
    r'(?P<status>\d{3}) (?P<size>\d+|-)'
)
TIME_FORMAT = "%d/%b/%Y:%H:%M:%S %z"


def parse_line(line):
    """Return a dict for one log line, or None if the line is not valid."""
    match = LINE_PATTERN.match(line)
    if not match:
        return None
    try:
        time = datetime.strptime(match["time"], TIME_FORMAT)
    except ValueError:
        return None
    return {
        "ip": match["ip"],
        "time": time,
        "method": match["method"],
        "path": match["path"].split("?")[0],
        "status": int(match["status"]),
        "size": 0 if match["size"] == "-" else int(match["size"]),
    }


def build_report(lines, top=10):
    """Read log lines and return the summary as a dict."""
    total = skipped = total_bytes = 0
    statuses, paths, ips, hours, error_paths = Counter(), Counter(), Counter(), Counter(), Counter()

    for line in lines:
        if not line.strip():
            continue
        entry = parse_line(line)
        if entry is None:
            skipped += 1
            continue

        total += 1
        total_bytes += entry["size"]
        statuses[entry["status"]] += 1
        paths[entry["path"]] += 1
        ips[entry["ip"]] += 1
        hours[entry["time"].strftime("%Y-%m-%d %H:00")] += 1
        if entry["status"] >= 400:
            error_paths[f'{entry["status"]} {entry["path"]}'] += 1

    errors = sum(count for status, count in statuses.items() if status >= 400)
    return {
        "total_requests": total,
        "skipped_lines": skipped,
        "total_bytes": total_bytes,
        "error_requests": errors,
        "error_rate_percent": round(100 * errors / total, 2) if total else 0.0,
        "status_codes": dict(sorted(statuses.items())),
        "top_paths": paths.most_common(top),
        "top_ips": ips.most_common(top),
        "top_errors": error_paths.most_common(top),
        "busiest_hours": hours.most_common(top),
    }


def format_report(report):
    """Turn the summary dict into readable text."""
    out = [
        "Nginx access log report",
        "=======================",
        f'Requests:      {report["total_requests"]}',
        f'Errors (4xx/5xx): {report["error_requests"]} ({report["error_rate_percent"]}%)',
        f'Data sent:     {report["total_bytes"] / 1024:.1f} KB',
        f'Skipped lines: {report["skipped_lines"]}',
        "",
        "Status codes",
    ]
    out += [f"  {status}: {count}" for status, count in report["status_codes"].items()]

    sections = [
        ("Top pages", "top_paths"),
        ("Top visitors", "top_ips"),
        ("Top errors", "top_errors"),
        ("Busiest hours", "busiest_hours"),
    ]
    for title, key in sections:
        out += ["", title]
        out += [f"  {count:>6}  {name}" for name, count in report[key]] or ["  (none)"]
    return "\n".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Summarise an Nginx access log.")
    parser.add_argument("logfile", help='path to the access log, or "-" to read standard input')
    parser.add_argument("--top", type=int, default=10, help="rows to show in each list (default: 10)")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)

    if args.top < 1:
        parser.error("--top must be at least 1")

    try:
        if args.logfile == "-":
            report = build_report(sys.stdin, args.top)
        else:
            with open(args.logfile, encoding="utf-8", errors="replace") as log:
                report = build_report(log, args.top)
    except OSError as error:
        print(f"ERROR: cannot read {args.logfile}: {error.strerror}", file=sys.stderr)
        return 1

    print(json.dumps(report, indent=2) if args.json else format_report(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
