# azure-sandbox

Models, convenience scripts, and bits and bobs of testing (under `tutorial` and `scripts/noodlin.py`) for
Azure AI (fka Azure Cognitive) Search.

## Usage

### creds
Requires the existence of a toplevel `creds.<env>.yml` file. Currently the only `env` is `dev` (i.e. `creds.dev.yml`) that 
should have at least the following:
```yml
primary_admin: <primary-admin-key>
service_name: <service-name>
```

The `service_name` is part of your Azure search service URL: `https://<service_name>.search.windows.net`

You can find your `primary_admin` key under `Settings > Keys` while viewing your search service (click the `Copy to clipboard` button)

### setup
Set up a virtual environment if you'd like (you should like).
```
pip install -r requirements.txt
```
(Includes requirements for Azure APIs and other stuff, as well as Jupyter notebook)

NOTE: After deleting a full index, or removing docs from an index, wait for Azure to catch up to the fact
that the index is not full if you're running up against a usage quota. It seems this can take a few minutes.
The `index.py` script includes an optional `-w` parameter for a wait time in seconds to pause
after deleting an index.

#### Enron data

1. Download raw Enron data from https://www.cs.cmu.edu/~enron/
   - [tarball](https://www.cs.cmu.edu/~enron/enron_mail_20150507.tar.gz)
2. Process data into JSON documents
```
python scripts/reformat_enron_data.py -t /path/to/enron_mail_20150507.tar.gz
```
3. Upload data to `enron` index (run script with `-h` for more options)
```
python index.py -i enron -r
```

### NYT data

1. Unzip `documents/authors_article_text_sample.csv.bz2`
```
bzip2 -d -k authors_article_text_sample.csv.bz2 [-f]
```
2. Process data into JSON documents
```
python scripts/reformat_nyt_data.py -c /path/to/authors_article_text_sample.csv
```
3. Upload data to `nyt` index (run script with `-h` for more options)
```
python index.py -i nyt -r
```

### usage

Run the frontend like
```
flask run --debug
```
and head over to `http://127.0.0.1:5000/`