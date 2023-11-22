from flask import Flask, redirect, render_template, request, url_for

from models.azure_search_client import AzureSearchClient
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import os
import math

app = Flask(__name__)
SECRET_KEY = os.urandom(32)
app.config["SECRET_KEY"] = SECRET_KEY


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


# class BasicForm(FlaskForm):
#     search_term = StringField("search_term", validators=[DataRequired()])


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
      return redirect(url_for('search_index', index_name=index_name, term=new_term, page=1))
    else:
        new_term = request.args.get('term')
        page = request.args.get('page')
        skip = int(page) * 10
        search_results = client.search(search_text=new_term, top=10, skip=skip)
        total_count = search_results.get_count()
        pages = math.ceil(total_count / 10)
        return render_template(
            "sandbox_search.jinja2",
            indexes=existing_indexes,
            current_idx=index_name,
            search_results=search_results,
            search_term=new_term,
            count=total_count,
            pages=pages,
            page=page
    )
