from flask import Flask, redirect, render_template, request, url_for, session
from uuid import uuid1

from models.azure_search_client import AzureSearchClient
import os
import math

app = Flask(__name__)
SECRET_KEY = os.urandom(32)
app.config["SECRET_KEY"] = SECRET_KEY


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.route("/search/")
def search():
    client = AzureSearchClient()
    existing_indexes = client.list_indexes()
    return render_template("sandbox_search.jinja2", indexes=existing_indexes)


@app.route("/search/<index_name>", methods=["POST", "GET"])
def search_index(index_name, term=None, page=None):
    client = AzureSearchClient(index_name)
    existing_indexes = client.list_indexes()
    
    if request.method == 'POST':
      new_term = request.form['term']
      session_id = uuid1()
      session['session_id'] = session_id
      return redirect(url_for('search_index', index_name=index_name, term=new_term, page=1))
    else:
        new_term = request.args.get('term')
        page = request.args.get('page') or 1
        session_id = session.get('session_id') or uuid1()
        skip = (int(page)-1) * 10
        search_results = client.search_with_highlight(
            search_text=new_term, top=10, skip=skip, session_id=session_id,
            highlight_pre_tag='<mark>',
            highlight_post_tag='</mark>')

        # replace fields with highlights with the highlighted fields
        results = list(search_results)
        for res in results:
            for h_field, h_text in res.get('@search.highlights', {}).items():
                res[h_field] = h_text

        total_count = search_results.get_count()
        pages = math.ceil(total_count / 10)
        return render_template(
            "sandbox_search.jinja2",
            indexes=existing_indexes,
            current_idx=index_name,
            search_results=results,
            search_term=new_term,
            count=total_count,
            pages=pages,
            page=int(page)
    )
