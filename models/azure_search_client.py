import json
import os
import traceback

import yaml
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient

from models.azure_search_index import AzureSearchIndex

BASE = os.path.dirname(os.path.join('..', os.path.dirname(os.path.realpath(__file__))))
VALID_ENVS = ['dev']


class AzureSearchClient:
    """
    Class that holds both an indexing client (build and delete indexes)
    and search client (search/autocomplete/etc).

    Tied to a single index, or no index at all
    """

    def __init__(self, index_name=None, env='dev', index_file=None):
        assert env in VALID_ENVS, f'{env} is not a valid env; valid envs are {VALID_ENVS}'

        self.index_name = index_name

        self.creds_file = os.path.join(BASE, f'creds.{env}.yml')
        creds = self.get_creds()
        self.service_name = creds['service_name']
        self.admin_key = creds['primary_admin']
        self.endpoint = self.build_endpoint()

        # TODO: separate these into different models?
        # Only some of the methods on this class work without being tied to an index
        if self.index_name:
            self.search_client = SearchClient(endpoint=self.endpoint,
                                              credential=AzureKeyCredential(self.admin_key),
                                              index_name=index_name)
            self.index = AzureSearchIndex(self.index_name, index_file)
        self.admin_client = SearchIndexClient(endpoint=self.endpoint,
                                              credential=AzureKeyCredential(self.admin_key))

    def get_creds(self):
        with open(self.creds_file) as credsfi:
            return yaml.safe_load(credsfi)

    def build_endpoint(self):
        return f'https://{self.service_name}.search.windows.net/'

    def list_indexes(self):
        result = self.admin_client.list_index_names()
        return list(result)

    def delete_index(self):
        self.admin_client.delete_index(self.index_name)
        print(f'Index {self.index_name} deleted')

    def get_document_count(self):
        return self.search_client.get_document_count()

    def create_index(self):
        result = self.admin_client.create_index(self.index.index)
        print(f'Index {result.name} created')

    # TODO: does this need error handling? The tutorial includes it but it seems like we could just let ourselves
    # fail normally here
    def index_docs(self, documents_file=None):
        docsfi = documents_file or os.path.join(BASE, 'documents', f'{self.index_name}.json')
        with open(docsfi) as infi:
            documents = json.load(infi)
        print(f'Uploading {len(documents)} documents...')
        result = self.search_client.upload_documents(documents=documents)
        print(f'Upload of new {len(documents)} document(s) succeeded: {result[0].succeeded}')
        docs_in_index = self.get_document_count()
        print(f'{docs_in_index} now exist in index {self.index_name}')
        return len(documents)

    def index_docs_chunked(self, documents_file=None, chunk_size=100):
        docsfi = documents_file or os.path.join(BASE, 'documents', f'{self.index_name}.json')
        oneline = docsfi.replace('.json', '.oneline')
        with open(docsfi) as infi:
            documents = json.load(infi)
            num_docs = len(documents)
        print(f'Rewriting {num_docs} documents into one-object-per-line in {oneline}')
        with open(oneline, 'w') as outfi:
            for doc in documents:
                outfi.write(json.dumps(doc) + '\n')
        del documents
        print(f'Uploading {num_docs} documents in chunks of {chunk_size}...')
        with open(oneline) as infi:
            chunk = []
            completed = 0
            line = infi.readline()
            while line:
                j = json.loads(line)
                chunk.append(j)
                if len(chunk) > chunk_size - 1:
                    completed += chunk_size
                    try:
                        result = self.search_client.upload_documents(documents=chunk)
                    except HttpResponseError as e:
                        if "Storage quota has been exceeded for this service" in e.message:
                            print(e.message)
                            break
                        else:
                            print(traceback.print_exc())
                            exit(420)
                    success = 'success' if result[0].succeeded else 'failure'
                    print(f'{(completed / num_docs) * 100:.1f}% done: {success}')
                    chunk = []
                line = infi.readline()
        os.remove(oneline)
        docs_in_index = self.get_document_count()
        print(f'{docs_in_index} now exist in index {self.index_name}')
        return docs_in_index

    # TODO: this is where any preprocessing of args would take place
    def search(self, include_total_count=True, **kwargs):
        kwargs['include_total_count'] = include_total_count
        return self.search_client.search(**kwargs)

    def get_document(self, key):
        return self.search_client.get_document(key=key)

    def autocomplete(self, **kwargs):
        return self.search_client.autocomplete(**kwargs)

    # By default, returns highlights found in all fields
    # If we've limited `search_fields` and `highlight_fields`, and the `search_text` was found in
    # a `search_field` but NOT a `highlight_field`, then result.@search_highlights will be None
    # (but won't throw a KeyError exception)
    def search_with_highlight(self,
                              highlight_fields=None,
                              highlight_pre_tag='<i>',
                              highlight_post_tag='</i>',
                              include_total_count=True,
                              **kwargs):
        highlight_fields = highlight_fields or self.index.highlightable_fields
        new_kwargs = {**kwargs,
                      **{'highlight_fields': ','.join(highlight_fields),
                         'highlight_pre_tag': highlight_pre_tag,
                         'highlight_post_tag': highlight_post_tag,
                         'include_total_count': include_total_count}}
        return self.search(**new_kwargs)
