import datetime
import math
import os
import re
from uuid import uuid1

import dateparser
import yaml
from flask import Flask, redirect, render_template, request, session, url_for

from models.azure_search_client import AzureSearchClient

app = Flask(__name__)
SECRET_KEY = os.urandom(32)
app.config["SECRET_KEY"] = SECRET_KEY

with open(os.path.join("app_config", "field_sorts.yml")) as config_file:
    config = yaml.safe_load(config_file)


def is_a_number(s):
    return s.replace(".", "").replace(",", "").replace(" ", "").strip().isdigit()


def is_boolean(s):
    return s.lower() == "true" or s.lower() == "false"


def format_dt_offset(s):
    parsed_date = dateparser.parse(s)
    parsed_date_utc = parsed_date.astimezone(datetime.timezone.utc)
    return parsed_date_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.route("/search/")
def search():
    client = AzureSearchClient()
    existing_indexes = client.list_indexes()
    return render_template("sandbox_search.jinja2", indexes=existing_indexes)


@app.route("/search/<index_name>", methods=["POST", "GET"])
def search_index(
    index_name, term=None, order_by=None, order_dir=None, filters=None, page=None
):
    client = AzureSearchClient(index_name)
    existing_indexes = client.list_indexes()

    if request.method == "POST":
        term = request.form.get("term")
        order_by = request.form.get("order_by")
        order_dir = request.form.get("order_dir")
        filters = []
        for filter_type in ("boolean", "datetime", "string", "numeric"):
            f = []
            for field_type in ("by", "exp", "val"):
                v = f"{filter_type}_filter_{field_type}"
                val = request.form.get(v)
                if len(f) > 0 and not val:
                    val = "eq"
                if val:
                    if "date" in filter_type and field_type == "val":
                        val = format_dt_offset(val)
                    f.append(val)
            if len(f) > 1:
                filters.append(" ".join(f))

        session_id = uuid1()
        session["session_id"] = session_id
        return redirect(
            url_for(
                "search_index",
                index_name=index_name,
                term=term,
                order_by=order_by,
                order_dir=order_dir,
                filters=filters,
                page=1,
            )
        )
    else:
        term = request.args.get("term")
        page = request.args.get("page") or 1
        order_by = request.args.get("order_by")
        order_dir = request.args.get("order_dir")
        filters = request.args.get("filters", [])
        session_id = session.get("session_id") or uuid1()
        session["session_id"] = session_id
        skip = (int(page) - 1) * 10

        kwargs = {
            "search_text": term,
            "top": 10,
            "skip": skip,
            "session_id": session_id,
            "highlight_pre_tag": "<mark>",
            "highlight_post_tag": "</mark>",
        }
        if order_by and order_dir:
            kwargs["order_by"] = f"{order_by} {order_dir}"

        filter_string = " AND ".join(filters) if isinstance(filters, list) else filters

        kwargs["filter"] = filter_string

        search_results = client.search_with_highlight(**kwargs)

        # replace fields with highlights with the highlighted fields
        results = list(search_results) # can't modify the iterator
        for res in results:
            highlights = (
                res.get("@search.highlights") or {}
            )  # the key always exists but is sometimes None
            for h_field, h_text in highlights.items():
                res[h_field] = h_text
            res.pop("@search.highlights")
            res["Score"] = res["@search.score"]
            res.pop("@search.score")

            # TODO: this should be recursive
            # some more field name mucking
            # maybe store this in an explicit dict or something, but this works for cases we have now
            for k in list(res.keys()):
                v = res[k]
                split_k = re.sub(r"([a-z])([A-Z])", r"\1 \2", k)
                split_k = re.sub(r"([a-zA-Z])_([a-zA-Z])", r"\1 \2", split_k)
                res[split_k] = v
                if k != split_k:
                    res.pop(k)

        filterable_fields = set(client.index.get_fields_by_ability("filterable"))
        boolean_fields = set(client.index.get_fields_by_datatype("boolean"))
        date_fields = set(client.index.get_fields_by_datatype("datetime_offset"))
        string_fields = set(client.index.get_fields_by_datatype("string"))
        numeric_fields = set.union(
            *[
                set(client.index.get_fields_by_datatype(dt))
                for dt in ["int32", "int64", "double", "single"]
            ]
        )

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
            f_sort=config["field_sort"][index_name],
            md_f_sort=config["metadata_field_sort"][index_name],
            sortable_fields=client.index.get_fields_by_ability("sortable"),
            boolean_filterable_fields=filterable_fields.intersection(boolean_fields),
            datetime_filterable_fields=filterable_fields.intersection(date_fields),
            string_filterable_fields=filterable_fields.intersection(string_fields),
            numeric_filterable_fields=filterable_fields.intersection(numeric_fields),
        )
