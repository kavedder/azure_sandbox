import argparse
import os
import sys
import time

from models.azure_search_client import AzureSearchClient


class ArgParser:
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            prog='index',
            description='Add documents to an index',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        self.parser.add_argument('-i', '--index', help='Name of index', required=True)
        self.parser.add_argument('-d', '--docs', help='Path to JSON file containing documents'
                                                      '(defaults to ../documents/<index>.json)')
        self.parser.add_argument('-s', '--schema', help='Path to JSON file containing index schema'
                                                        '(defaults to ../indexes/<index>.json)')
        self.parser.add_argument('-r', '--reindex', help='If specified, delete the index and recreate it',
                                 action='store_true')
        self.parser.add_argument('-c', '--chunk_size', default=10000, type=int, help='Chunk of documents to '
                                                                                     'upload at a time')
        self.parser.add_argument('-l', '--limit', default=sys.maxsize, type=int, help='Number of documents '
                                                                                      'to upload total')
        self.parser.add_argument('-w', '--wait', type=int, help='Time (in seconds) to wait after deleting an index before reindexing')

    def parse(self):
        return self.parser.parse_args()


if __name__ == '__main__':
    BASE = os.path.dirname(os.path.join('..', os.path.dirname(os.path.realpath(__file__))))

    parser = ArgParser()
    args = parser.parse()

    client = AzureSearchClient(args.index, index_file=args.schema)
    existing_indexes = client.list_indexes()

    if args.index not in existing_indexes:
        client.create_index()
    else:
        if args.reindex:
            client.delete_index()
            if args.wait:
                print(f'Waiting {args.wait} seconds before continuing...')
                time.sleep(args.wait)
                print('And here we go!')
            client.create_index()

    # Can't upload all documents at once
    # NOTE: if get an out-of-storage message, and delete/recreate the index, wait a bit before trying
    # to index documents again for the dust to settle
    client.index_docs_chunked(args.docs, chunk_size=args.chunk_size, limit=args.limit)

