# nginx-log-report

A small command-line tool that summarises an Nginx access log: how many requests there
were, how many failed, which pages and visitors were most active, and which hours were
busiest. Written in Python with no dependencies outside the standard library.

## Use it

```bash
python logreport.py sample/access.log
python logreport.py /var/log/nginx/access.log --top 5
python logreport.py access.log --json > report.json
cat access.log | python logreport.py -
```

Example output:

```text
Nginx access log report
=======================
Requests:      20
Errors (4xx/5xx): 6 (30.0%)
Data sent:     255.9 KB
Skipped lines: 1

Status codes
  200: 13
  304: 1
  404: 5
  405: 1

Top pages
       5  /
       3  /style.css
       2  /app.js
```

## Options

| Option | Meaning |
| --- | --- |
| `logfile` | Path to the log, or `-` to read from standard input |
| `--top N` | Rows to show in each list (default 10) |
| `--json` | Print the report as JSON, for use by other scripts |

## How it works

- Each line is matched against a regular expression for Nginx's default `combined`
  log format, which pulls out the visitor IP, time, method, path, status code and
  response size.
- Lines that do not match are counted as skipped instead of stopping the program, so
  one corrupted line does not break the report.
- Query strings are removed from paths, so `/?utm_source=a` and `/` count as one page.
- Counting is done with `collections.Counter`, in a single pass over the file, so the
  log is never loaded into memory in full.
- Status codes of 400 and above count as errors.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Why it is useful

A quick look at "top errors" and "top visitors" shows things like bots scanning for
`/wp-login.php` or `/.env`, broken links returning 404, or a single address making
most of the requests.
