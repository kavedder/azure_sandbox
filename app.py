from flask import Flask, redirect, render_template, request, url_for, session
from uuid import uuid1

from models.azure_search_client import AzureSearchClient
import os
import math
import re

app = Flask(__name__)
SECRET_KEY = os.urandom(32)
app.config["SECRET_KEY"] = SECRET_KEY

metadata_field_sort = {
    'enron': [
        'Score',
        'Username',
        'Folder',
        'Is Deleted',
        'Original Message Id',
        'Message Id'
    ],
    'hotels-quickstart': [
        'Score',
        'Hotel Id',
        'Last Renovation Date'
    ]
}

field_sort = {
    'enron': [
        'From Email',
        'To Email',
        'Cc Email',
        'Bcc Email',
        'Send Date',
        'Subject',
        'Body',
        'Thread'
    ],
    'hotels-quickstart': [
        'Hotel Name',
        'Category',
        'Tags',
        'Description',
        'Description fr',
        'Address',
        'Rating'
    ]
}


def is_a_number(s):
    return s.replace('.', '').replace(',', '').replace(' ', '').strip().isdigit()


def is_boolean(s):
    return s.lower() == 'true' or s.lower() == 'false'


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.route("/search/")
def search():
    client = AzureSearchClient()
    existing_indexes = client.list_indexes()
    return render_template("sandbox_search.jinja2", indexes=existing_indexes)


@app.route("/search/<index_name>", methods=["POST", "GET"])
def search_index(index_name, term=None, order_by=None, order_dir=None, boolean_filter_by=None,
                 boolean_filter_exp=None, boolean_filter_val=None, page=None):
    client = AzureSearchClient(index_name)
    existing_indexes = client.list_indexes()

    if request.method == 'POST':
        term = request.form['term']
        order_by = request.form['order_by']
        order_dir = request.form['order_dir']
        boolean_filter_by = request.form['boolean_filter_by']
        boolean_filter_exp = 'eq' # request.form['boolean_filter_exp']
        boolean_filter_val = request.form['boolean_filter_val']
        session_id = uuid1()
        session['session_id'] = session_id
        return redirect(url_for('search_index', index_name=index_name, term=term, order_by=order_by,
                                order_dir=order_dir, boolean_filter_by=boolean_filter_by, 
                                boolean_filter_exp=boolean_filter_exp, boolean_filter_val=boolean_filter_val,
                                page=1))
    else:
        term = request.args.get('term')
        page = request.args.get('page') or 1
        order_by = request.args.get('order_by')
        order_dir = request.args.get('order_dir')
        boolean_filter_by = request.args.get('boolean_filter_by')
        boolean_filter_exp = 'eq' # request.args.get('boolean_filter_exp')
        boolean_filter_val = request.args.get('boolean_filter_val')
        session_id = session.get('session_id') or uuid1()
        skip = (int(page) - 1) * 10

        kwargs = {
            'search_text': term, 'top': 10, 'skip': skip, 'session_id': session_id,
            'highlight_pre_tag': '<mark>',
            'highlight_post_tag': '</mark>'
        }
        if order_by and order_dir:
            kwargs['order_by'] = f'{order_by} {order_dir}'
        if boolean_filter_by and boolean_filter_exp and boolean_filter_val:
            # if not is_a_number(boolean_filter_val) and not is_boolean(boolean_filter_val):
            #     boolean_filter_val = f"'{boolean_filter_val}'"
            kwargs['filter'] = f'{boolean_filter_by} {boolean_filter_exp} {boolean_filter_val}'

        print(kwargs)
        search_results = client.search_with_highlight(**kwargs)

        # replace fields with highlights with the highlighted fields
        results = list(search_results)
        for res in results:
            highlights = res.get('@search.highlights') or {}  # the key always exists but is sometimes None
            for h_field, h_text in highlights.items():
                res[h_field] = h_text
            res.pop('@search.highlights')
            res['Score'] = res['@search.score']
            res.pop('@search.score')

            # TODO: this should be recursive
            # some more field name mucking
            # maybe store this in an explicit dict or something, but this works for cases we have now
            for k in list(res.keys()):
                v = res[k]
                split_k = re.sub(r'([a-z])([A-Z])', r'\1 \2', k)
                split_k = re.sub(r'([a-zA-Z])_([a-zA-Z])', r'\1 \2', split_k)
                res[split_k] = v
                if k != split_k:
                    res.pop(k)

        #print([set(client.index.get_fields_by_datatype(dt) for dt in ['int32', 'int64', 'double', 'single'])])
        numeric_fields = set.union(*[set(client.index.get_fields_by_datatype(dt)) for dt in ['int32', 'int64', 'double', 'single']])

        total_count = search_results.get_count()
        pages = math.ceil(total_count / 10)
        return render_template(
            "sandbox_search.jinja2",
            indexes=existing_indexes,
            current_idx=index_name,
            search_results=results,
            search_term=term,
            count=total_count,
            pages=pages,
            page=int(page),
            f_sort=field_sort[index_name],
            md_f_sort=metadata_field_sort[index_name],
            sortable_fields=client.index.get_fields_by_ability('sortable'),
            boolean_filterable_fields=set(client.index.get_fields_by_ability('filterable')
                                          ).intersection(set(client.index.get_fields_by_datatype('boolean'))),
            date_filterable_fields=set(client.index.get_fields_by_ability('filterable')
                                          ).intersection(set(client.index.get_fields_by_datatype('datetime_offset'))),
            string_filterable_fields=set(client.index.get_fields_by_ability('filterable')
                                          ).intersection(set(client.index.get_fields_by_datatype('string'))),
            numeric_filterable_fields=set(client.index.get_fields_by_ability('filterable')
                                          ).intersection(numeric_fields)
        )
