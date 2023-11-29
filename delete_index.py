import argparse
import os
import sys
import time

from models.azure_search_client import AzureSearchClient


class ArgParser:
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            prog='delete_index',
            description='Delete an index',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        self.parser.add_argument('-i', '--index', help='Name of index', required=True)

    def parse(self):
        return self.parser.parse_args()


if __name__ == '__main__':
    BASE = os.path.dirname(os.path.join('..', os.path.dirname(os.path.realpath(__file__))))

    parser = ArgParser()
    args = parser.parse()

    client = AzureSearchClient(args.index)
    client.delete_index()