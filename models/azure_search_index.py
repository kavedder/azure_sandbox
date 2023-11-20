import json
import os

from azure.search.documents.indexes.models import (
    ComplexField,
    SimpleField,
    SearchableField,
    SearchFieldDataType, SearchIndex,
    CorsOptions
)

BASE = os.path.dirname(os.path.join('..', os.path.realpath(__file__)))
FIELD_TYPES = {
    "SimpleField": SimpleField,
    "SearchableField": SearchableField,
    "ComplexField": ComplexField
}

# TODO add more of these
DATA_TYPES = {
    "string": SearchFieldDataType.String,
    "double": SearchFieldDataType.Double,
    "datetime_offset": SearchFieldDataType.DateTimeOffset,
    "boolean": SearchFieldDataType.Boolean
}


def build_fields(json_fields):
    fields = []
    for field in json_fields:
        field_type_name = FIELD_TYPES[json_fields['field_type']]
        if field_type_name == 'ComplexField':
            field['fields'] = build_fields(field['fields'])

        field_type = FIELD_TYPES[field_type_name]
        if field.get('type'):
            field['type'] = DATA_TYPES[field['type']]

        fields.append(field_type(**field))

    return fields


def get_field_names(json_fields, prefix='', sep='/'):
    field_names = [sep.join([prefix, f['name']]).strip(sep) for f in json_fields
                   if f['field_type'] != 'ComplexField']
    for f in json_fields:
        if f['field_type'] == 'ComplexField':
            base_name = sep.join([prefix, f['name']]).strip(sep)
            subfields = get_field_names(f['fields'], base_name)
            field_names.extend(subfields)

    return field_names


class AzureSearchIndex:
    def __init__(self, index_name):
        self.index_name = index_name

        index_file = os.path.join(BASE, 'indexes', self.index_name)
        with open(index_file) as infi:
            self.index_json = json.load(infi)

        self.cors_options = self.build_cors_options()

        self.scoring_profiles = self.index_json['scoring_profiles'] or []
        self.suggesters = self.index_json['suggesters'] or []

        self.fields = build_fields(self.index_json['fields'])
        self.field_names = get_field_names(self.index_json['fields'])

        self.index = SearchIndex(
            name=self.index_name,
            fields=self.fields,
            scoring_profiles=self.scoring_profiles,
            suggesters=self.suggesters,
            cors_options=self.cors_options)

    def build_cors_options(self):
        return CorsOptions(allowed_origins=self.index_json.get('allowed_origin') or ["*"],
                           max_age_in_seconds=self.index_json.get('max_age_in_seconds') or 60)
