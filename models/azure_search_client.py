import json
import os

import yaml
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient

from models.azure_search_index import AzureSearchIndex

BASE = os.path.dirname(os.path.join('..', os.path.realpath(__file__)))
VALID_ENVS = ['dev']


class AzureSearchClient:
    def __init__(self, index_name, env='dev'):
        assert env in VALID_ENVS, f'{env} is not a valid env; valid envs are {VALID_ENVS}'

        self.index_name = index_name
        self.creds_file = os.path.join(BASE, f'creds.{env}.yml')
        creds = self.get_creds()
        self.service_name = creds['service_name']
        self.admin_key = creds['primary_admin']
        self.endpoint = self.build_endpoint()

        self.search_client = self.build_client(SearchClient)
        self.admin_client = self.build_client(SearchIndexClient)

        self.index = AzureSearchIndex(self.index_name)

    def get_creds(self):
        with open(self.creds_file) as credsfi:
            return yaml.safe_load(credsfi)

    def build_endpoint(self):
        return f'https://{self.service_name}.search.windows.net/'

    def build_client(self, client_type):
        return client_type(endpoint=self.endpoint,
                           index_name=self.index_name,
                           credential=AzureKeyCredential(self.admin_key))

    def delete_index(self):
        self.admin_client.delete_index(self.index_name)
        print(f'Index {self.index_name} Deleted')

    def create_index(self):
        result = self.admin_client.create_index(self.index)
        print(f'Index {result.name} created')

    # TODO: does this need error handling? The tutorial includes it but it seems like we could just let ourselves
    # fail normally here
    def index_docs(self):
        docsfi = os.path.join(BASE, 'documents', f'{self.index_name}.json')
        with open(docsfi) as infi:
            documents = json.load(infi)
        result = self.search_client.upload_documents(documents=documents)
        print("Upload of new {} document(s) succeeded: {}".format(len(documents), result[0].succeeded))

    # TODO: this is where any preprocessing of args would take place
    def search(self, **kwargs):
        return self.search_client.search(**kwargs)

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
                              **kwargs):
        highlight_fields = highlight_fields or self.index.field_names
        return self.search_client.search(highlight_fields,
                                         highlight_pre_tag,
                                         highlight_post_tag,
                                         highlight_fields,
                                         **kwargs)

