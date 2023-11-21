from time import sleep

from models.azure_search_client import AzureSearchClient

if __name__ == '__main__':
    index_name = 'hotels-quickstart'

    client = AzureSearchClient(index_name)

    client.delete_index()
    client.create_index()

    docs_indexed = client.index_docs()
    # if you don't hang on a sec, searches fail
    # cool cool cool...
    while client.get_document_count() < docs_indexed:
        sleep(1)

    # res = client.search(search_text='*', include_total_count=True)
    res = client.search_with_highlight(search_text='hotel', include_total_count=True)
    print(res.get_count())
    for r in res:
        print(r['HotelName'], r['@search.highlights'])

