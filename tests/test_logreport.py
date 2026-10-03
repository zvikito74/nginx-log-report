import unittest

from logreport import build_report, format_report, parse_line

GOOD = '203.0.113.7 - - [03/Oct/2026:14:02:11 +0400] "GET /index.html?ref=1 HTTP/1.1" 200 5123 "-" "Mozilla/5.0"'
NOT_FOUND = '198.51.100.4 - - [03/Oct/2026:14:05:40 +0400] "GET /wp-login.php HTTP/1.1" 404 153 "-" "curl/8.0"'
NO_SIZE = '203.0.113.7 - - [03/Oct/2026:15:10:00 +0400] "GET /style.css HTTP/1.1" 304 - "-" "Mozilla/5.0"'


class ParseLineTests(unittest.TestCase):
    def test_parses_fields(self):
        entry = parse_line(GOOD)
        self.assertEqual(entry["ip"], "203.0.113.7")
        self.assertEqual(entry["method"], "GET")
        self.assertEqual(entry["status"], 200)
        self.assertEqual(entry["size"], 5123)
        self.assertEqual(entry["time"].hour, 14)

    def test_strips_query_string(self):
        self.assertEqual(parse_line(GOOD)["path"], "/index.html")

    def test_dash_size_counts_as_zero(self):
        self.assertEqual(parse_line(NO_SIZE)["size"], 0)

    def test_invalid_line_returns_none(self):
        self.assertIsNone(parse_line("this is not a log line"))

    def test_bad_date_returns_none(self):
        self.assertIsNone(parse_line(GOOD.replace("03/Oct/2026", "99/Xyz/2026")))


class BuildReportTests(unittest.TestCase):
    def setUp(self):
        self.report = build_report([GOOD, GOOD, NOT_FOUND, NO_SIZE, "garbage", ""])

    def test_counts_requests_and_skips_bad_lines(self):
        self.assertEqual(self.report["total_requests"], 4)
        self.assertEqual(self.report["skipped_lines"], 1)

    def test_error_rate(self):
        self.assertEqual(self.report["error_requests"], 1)
        self.assertEqual(self.report["error_rate_percent"], 25.0)

    def test_status_codes(self):
        self.assertEqual(self.report["status_codes"], {200: 2, 304: 1, 404: 1})

    def test_top_lists(self):
        self.assertEqual(self.report["top_paths"][0], ("/index.html", 2))
        self.assertEqual(self.report["top_ips"][0], ("203.0.113.7", 3))
        self.assertEqual(self.report["top_errors"], [("404 /wp-login.php", 1)])

    def test_busiest_hours(self):
        self.assertEqual(self.report["busiest_hours"][0], ("2026-10-03 14:00", 3))

    def test_total_bytes(self):
        self.assertEqual(self.report["total_bytes"], 5123 * 2 + 153)

    def test_top_limit(self):
        self.assertEqual(len(build_report([GOOD, NOT_FOUND, NO_SIZE], top=1)["top_paths"]), 1)

    def test_empty_input(self):
        report = build_report([])
        self.assertEqual(report["total_requests"], 0)
        self.assertEqual(report["error_rate_percent"], 0.0)
        self.assertIn("(none)", format_report(report))


if __name__ == "__main__":
    unittest.main()
