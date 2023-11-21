import argparse
import os

from models.azure_search_client import AzureSearchClient


class ArgParser:
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            prog='index',
            description='Add documents to an index',
        )
        self.parser.add_argument('-i', '--index', help='Name of index', required=True)
        self.parser.add_argument('-d', '--docs', help='Path to JSON file containing documents'
                                                      '(defaults to ../documents/<index>.json)')
        self.parser.add_argument('-s', '--schema', help='Path to JSON file containing index schema'
                                                        '(defaults to ../indexes/<index>.json)')
        self.parser.add_argument('-r', '--reindex', help='If specified, delete the index and recreate it',
                                 action='store_true')

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
            client.create_index()

    # if we don't chunk up the indexing, we fail with a completely unhelpful error message
    # this may be related to the fact that we have limited storage on the free tier, and actually
    # nothing to do with chunking?
    # NOTE: if get an out-of-storage message, and delete/recreate the index, wait a bit before trying
    # to index documents again for the dust to settle
    client.index_docs_chunked(args.docs, chunk_size=10000)

