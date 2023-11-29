import argparse
import csv
import datetime
import json
import os
import sys
import re

csv.field_size_limit(sys.maxsize)
BASE = os.path.dirname(os.path.join("..", os.path.dirname(os.path.realpath(__file__))))
BEGIN_QUOTE_RE = re.compile(r'\\"(\w)')
END_QUOTE_RE = re.compile(r'\\"([^\w])')


rename_fields = {
    "article_id": "ArticleId",
    "content_id": "ContentId",
    "author_id": "AuthorId",
    "hl_main": "HeadlineMain",
    "hl_kicker": "HeadlineKicker",
    "hl_print_headline": "PrintHeadline",
    "pub_date": "PubDate",
    "first_name": "AuthorFirstName",
    "last_name": "AuthorLastName",
    "middle_name": "AuthorMiddleName",
    "title": "AuthorTitle",
    "full_name": "AuthorFullName",
    "text_array": "Text",
}


def format_dt_offset(s):
    try:
        parsed_date = datetime.datetime.strptime(s + '00', '%Y-%m-%d %H:%M:%S%z')
        if not parsed_date:
            return 
    except ValueError:
        return
    parsed_date_utc = parsed_date.astimezone(datetime.timezone.utc)
    return parsed_date_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def split_pg_text_array(s):
    s = s.lstrip('{"').rstrip('"}')
    return s.split('","')


def fix_quotes(s):
    s = BEGIN_QUOTE_RE.sub(r"“\1", s)
    s = END_QUOTE_RE.sub(r"”\1", s)
    return s

class ArgParser:
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            prog="reformat_nyt_data",
            description="""Rewrites a CSV dump from a SQL database into a JSON file at ../documents/nyt.json""",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        self.parser.add_argument("-c", "--csvfile", help="Path to .csv file to parse")
        self.parser.add_argument(
            "-l",
            "--limit",
            default=sys.maxsize,
            type=int,
            help="Number of documents to process",
        )

    def parse(self):
        return self.parser.parse_args()


if __name__ == "__main__":
    parser = ArgParser()
    args = parser.parse()

    JSONFILE = os.path.join(BASE, "documents", "nyt.json")

    with open(args.csvfile) as csvfile:
        reader = csv.DictReader(csvfile)
        i = 0
        docs = []
        for row in reader:
            if i % 10000 == 0:
                print(i)
            j = {}
            text = row["text_array"]
            row["text_array"] = fix_quotes('\n'.join(split_pg_text_array(text)))

            full_name = " ".join([row.get(n) for n in ('title', 'first_name', 'middle_name', 'last_name') if row.get(n)])
            row['full_name'] = full_name

            row['pub_date'] = format_dt_offset(row['pub_date'])

            for k, v in row.items():
                j[rename_fields[k]] = v
            j["@search.action"] = "upload"
            docs.append(j)
            i += 1
            if i > args.limit:
                break

    with open(os.path.join(BASE, "documents", "nyt.json"), "w") as outfi:
        json.dump(docs, outfi, indent=2, sort_keys=True)
        print(outfi.name)
