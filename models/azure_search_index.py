import json
import os

from azure.search.documents.indexes.models import (
    ComplexField,
    CorsOptions,
    SimpleField,
    SearchableField,
    SearchFieldDataType,
    SearchIndex
)

BASE = os.path.dirname(os.path.join('..', os.path.dirname(os.path.realpath(__file__))))

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
        field_type_name = field['field_type']
        if field_type_name == 'ComplexField':
            field['fields'] = build_fields(field['fields'])

        field_type = FIELD_TYPES[field_type_name]
        # ComplexFields don't have a `type`
        if field.get('type'):
            field['type'] = DATA_TYPES[field['type']]

        fields.append(field_type(**field))

    return fields


# only `SearchableField`s can be highlighted
def get_field_names(json_fields, prefix='', sep='/', only_highlightable=False):
    field_names = []
    for f in json_fields:
        base_name = sep.join([prefix, f['name']]).strip(sep)
        if f['field_type'] == 'ComplexField':
            subfields = get_field_names(f['fields'], base_name)
            field_names.extend(subfields)
        else:
            if only_highlightable:
                if f['field_type'] == 'SearchableField':
                    field_names.append(base_name)
            else:
                field_names.append(base_name)

    return field_names


class AzureSearchIndex:
    def __init__(self, index_name, index_file=None):
        self.index_name = index_name

        index_file = index_file or os.path.join(BASE, 'indexes', f'{self.index_name}.json')
        with open(index_file) as infi:
            self.index_json = json.load(infi)

        self.cors_options = self.build_cors_options()

        self.scoring_profiles = self.index_json['scoring_profiles'] or []
        self.suggesters = self.index_json['suggesters'] or []

        self.field_names = get_field_names(self.index_json['fields'])
        self.highlightable_fields = get_field_names(self.index_json['fields'], only_highlightable=True)
        self.fields = build_fields(self.index_json['fields'])

        self.index = SearchIndex(
            name=self.index_name,
            fields=self.fields,
            scoring_profiles=self.scoring_profiles,
            suggesters=self.suggesters,
            cors_options=self.cors_options)

    def build_cors_options(self):
        return CorsOptions(allowed_origins=self.index_json.get('allowed_origin') or ["*"],
                           max_age_in_seconds=self.index_json.get('max_age_in_seconds') or 60)
