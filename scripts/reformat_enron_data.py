"""
Outputs to ../documents/enron.json
(follows schema in ../indexes/enron.json, which was hand-written)

TODO:
- separate indexes for users (email + name) and emails
- attempt to match up email w/user via To/From fields and X-To/X-From fields (a little squidgy it seems?)
"""
import argparse
import datetime
import glob
import os
import re
import sys
import tarfile

import chardet
import dateparser
import json

BASE = os.path.dirname(os.path.join('..', os.path.dirname(os.path.realpath(__file__))))


def extract_tarball(fipath, outdir=None):
    assert fipath.endswith('.tar.gz'), f'{fipath} is not a gzipped tarball'
    out = outdir or fipath.rstrip('.tar.gz')
    with tarfile.open(fipath) as fi:
        print(f'Extracting tarfile {fipath} to {out}...')
        fi.extractall(out)
        print(f'Extracted {fipath} to {out}')
    return out


def sub_header_line(sub_s, line, split=False):
    stripped = re.sub(rf'{sub_s}: *', '', line).strip()
    if split:
        split_items = [e.strip() for e in stripped.split(',') if e.strip()]
        return split_items
    return stripped


# TODO: needs some at least basic error handling
# TODO: Some redundancy can be factored out
def parse_email(raw, username, folder, path):
    is_deleted = 'deleted' in folder.lower()
    doc = {'Username': username, 'Folder': folder, 'IsDeleted': is_deleted, '@search.action': 'upload'}
    thread = []
    body = []
    begin_body = False
    begin_thread = False
    prev_field = None
    for line in raw:
        if not line.strip():
            # the first blank newline signals we've entered the body
            begin_body = True
            continue
        elif line.strip().startswith('----'):
            # a line surrounded by ---- indicates we're in the trailing thread, eg. fwd/reply
            # don't `continue` because the info in the --- line might be helpful
            begin_thread = True

        if begin_body:
            if begin_thread:
                thread.append(line.rstrip())
            else:
                body.append(line.rstrip())

        else:
            # still in the header
            if line.startswith('\t') or line.startswith(' '):
                # continuation of a previous line (To, Cc, Bcc)
                prev = doc[prev_field]
                if isinstance(prev, list):
                    prev.extend(sub_header_line('', line, split=True))
                else:
                    prev += ' ' + line.strip()
                doc[prev_field] = prev
            elif line.startswith('Message-ID:'):
                original_message_id = re.search(r'Message-ID: *<([^>]*)>', line).group(1)
                # keys can only contain a-zA-Z0-9_-=
                message_id = re.sub(r'[^a-zA-Z0-9_\-=]+', '-', original_message_id)
                doc['MessageId'] = message_id
                doc['OriginalMessageId'] = original_message_id
            elif line.startswith('Date:'):
                date = sub_header_line('Date', line)
                date = re.sub(r'\(\w\wT\)', '', date).strip()  # dateparser doesn't like eg. (PST)
                parsed_date = dateparser.parse(date)
                if parsed_date:
                    parsed_date_utc = parsed_date.astimezone(datetime.timezone.utc)
                    doc['SendDate'] = parsed_date_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
                else:
                    print(f'Unable to parse date {date} in file {path}')
                prev_field = 'SendDate'
            elif line.startswith('From: '):
                doc['FromEmail'] = sub_header_line('From', line)
                prev_field = 'FromEmail'
            elif line.startswith('To: '):
                doc['ToEmail'] = sub_header_line('To', line, True)
                prev_field = 'ToEmail'
            # Different capitalizations of Bcc and Cc occur in emails, but not in the header
            elif line.startswith('Cc: '):
                doc['CcEmail'] = sub_header_line('Cc', line, True)
                prev_field = 'CcEmail'
            elif line.startswith('Bcc: '):
                doc['BccEmail'] = sub_header_line('Bcc', line, True)
                prev_field = 'BccEmail'
            elif line.startswith('Subject: '):
                doc['Subject'] = sub_header_line('Subject', line)
                prev_field = 'Subject'

    doc['Body'] = '\n'.join(body)
    doc['Thread'] = '\n'.join(thread)

    for k in list(doc.keys()):
        v = doc[k]
        if v is None or v == "" or v == []:
            doc.pop(k)

    return doc


def walk_emails(email_dir, limit):
    docs = []
    root = os.path.join(email_dir, 'maildir')
    last_user = None
    user_count = 0
    emails_processed = 0
    num_users = len(os.listdir(root))
    try:
        # assumes all email files end in `.` eg. /path/to/file/13.
        for fi in glob.iglob(f'{root}/**/*.', recursive=True):
            if emails_processed > limit:
                break
            pathdirs = fi.split('/')
            base_idx = pathdirs.index('maildir')
            username = pathdirs[base_idx + 1]
            folder = '/'.join(pathdirs[base_idx + 2:-1])
            if username != last_user:
                # print(f'Processing emails for {username}')
                user_count += 1
                if user_count % 10 == 0:
                    print(f'User {user_count}/{num_users}...')
                last_user = username
            with open(fi) as infi:
                try:
                    lines = infi.readlines()
                    docs.append(parse_email(lines, username, folder, infi.name))
                except UnicodeDecodeError:
                    print(f'Unable to read file {fi} as unicode')
                    with open(fi, 'rb') as raw_binary:
                        encoding = chardet.detect(raw_binary.read())
                        print(f'Detected encoding {encoding["encoding"]} with confidence {encoding["confidence"]}')
                    with open(fi, encoding=encoding['encoding']) as infi_decoded:
                        try:
                            lines = infi_decoded.readlines()
                            docs.append(parse_email(lines, username, folder, infi.name))
                        except Exception as e2:
                            f'Still unable to read {fi}, giving up'
                            print(e2)
                emails_processed += 1
    except Exception as e:
        print('Whoops! Dumping!')
        print(e)

    with open(os.path.join(BASE, 'documents', 'enron.json'), 'w') as outfi:
        json.dump(docs, outfi, indent=2, sort_keys=True)


class ArgParser:
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            prog='reformat_enron_data',
            description='''Optionally unzips Enron data downloaded from https://www.cs.cmu.edu/~enron/
            and rewrites the resultant data into a JSON file at ../documents/enron.json''',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        self.parser.add_argument('-t', '--tarfile', help='Path to .tar.gz file to unzip')
        self.parser.add_argument('-d', '--directory', help='Output dir if -t specified, else input data dir'
                                                           '(defaults to same dir as tarfile if specified')
        self.parser.add_argument('-l', '--limit', default=sys.maxsize, type=int, help='Number of documents '
                                                                                      'process')

    def parse(self):
        return self.parser.parse_args()


if __name__ == '__main__':
    parser = ArgParser()
    args = parser.parse()
    assert args.tarfile or args.directory, 'At least of -t or -d is required'

    if args.tarfile:
        args.directory = extract_tarball(args.tarfile, args.directory)

    walk_emails(args.directory, args.limit)
