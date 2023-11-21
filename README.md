# azure-sandbox

Models, convenience scripts, and bits and bobs of testing (under `tutorial`) for
Azure Cognitive (Azure AI) Search.

## Usage

# creds
Requires the existence of a toplevel `creds.<env>.yml` file. Currently the only `env` is `dev` (i.e. `creds.dev.yml`)

# setup
Set up a virtual environment if you'd like (you should like).
```
pip install -r requirements.txt
```
(Currently this only includes requirements for Azure Search and other libs for running models
and scripts, not for running the Jupyter notebook).