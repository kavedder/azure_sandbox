# azure-sandbox

Models, convenience scripts, and bits and bobs of testing (under `tutorial` and `scripts/noodlin.py`) for
Azure Cognitive (Azure AI) Search.

## Usage

### creds
Requires the existence of a toplevel `creds.<env>.yml` file. Currently the only `env` is `dev` (i.e. `creds.dev.yml`) that 
should have at least the following:
```yml
primary_admin: <primary-admin-key>
service_name: <service-name>
```

### setup
Set up a virtual environment if you'd like (you should like).
```
pip install -r requirements.txt
```
(Includes requirements for Azure APIs and other stuff, as well as Jupyter notebook)

### usage

#### Enron data

1. Download raw Enron data from https://www.cs.cmu.edu/~enron/
   1. [tarball](https://www.cs.cmu.edu/~enron/enron_mail_20150507.tar.gz)
2. Process data into JSON documents
```
python scripts/reformat_enron_data.py -t /path/to/enron_mail_20150507.tar.gz
```
3. Upload data to `enron` index (run script with `-h` for more options)
```
python index.py -i enron -r
```