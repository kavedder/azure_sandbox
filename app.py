from flask import Flask, redirect, render_template

from models.azure_search_client import AzureSearchClient
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import os

app = Flask(__name__)
SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


class BasicForm(FlaskForm):
    search_term = StringField("search_term", validators=[DataRequired()])


@app.route("/search")
def search():
    client = AzureSearchClient()
    existing_indexes = client.list_indexes()
    return render_template('sandbox_search.html', indexes=existing_indexes)


@app.route("/search/<index_name>", methods=['POST', 'GET'])
def search_index(index_name):
    client = AzureSearchClient(index_name)
    existing_indexes = client.list_indexes()
    form = BasicForm()
    if form.validate_on_submit():
        term = form.search_term.data
        print(term)
        return redirect(f'/search/{index_name}/{term}')

    search_results = client.search(search_text='*', top=10)

    return render_template('sandbox_search.html', indexes=existing_indexes,
                           current_idx = index_name,
                           search_results=search_results, form=form)


@app.route("/search/<index_name>/<term>", methods=['POST', 'GET'])
def search_index_term(index_name, term):
    client = AzureSearchClient(index_name)
    existing_indexes = client.list_indexes()
    form = BasicForm()
    if form.validate_on_submit():
        term = form.search_term.data
        print(term)
        return redirect(f'/search/{index_name}/{term}')

    search_results = client.search(search_text='*', top=10)

    return render_template('sandbox_search.html', indexes=existing_indexes,
                           current_idx = index_name,
                           search_results=search_results, form=form, term=term)
