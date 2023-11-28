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
    "ComplexField": ComplexField,
}

# TODO add more of these
DATA_TYPES = {
    "string": SearchFieldDataType.String,
    "double": SearchFieldDataType.Double,
    "datetime_offset": SearchFieldDataType.DateTimeOffset,
    "boolean": SearchFieldDataType.Boolean,
    "geography_point": SearchFieldDataType.GeographyPoint,  # A geographic point type.
    "int32": SearchFieldDataType.Int32,  # An Int32 type, or something that can convert to an Int32.
    "int64": SearchFieldDataType.Int64,  # An Int64 type, or something that can convert to an Int64.
    "single": SearchFieldDataType.Single,  # A single type. (smaller than a double -- when would we ever use this)
}


def build_fields_from_json(json_fields):
    fields = []
    for field in json_fields:
        field_type_name = field['field_type']
        if field_type_name == 'ComplexField':
            field['fields'] = build_fields_from_json(field['fields'])

        field_type = FIELD_TYPES[field_type_name]
        # ComplexFields don't have a `type`
        if field.get('type'):
            field['type'] = DATA_TYPES[field['type']]

        fields.append(field_type(**field))

    return fields


def get_simplified_fields(json_fields, prefix='', sep='/'):
    field_names = {}
    for f in json_fields:
        base_name = sep.join([prefix, f['name']]).strip(sep)
        if f['field_type'] == 'ComplexField':
            subfields = get_simplified_fields(f['fields'], base_name)
            field_names = {**field_names, **subfields}
        else:
            field_names[base_name] = {k: f.get(k, False) for k in ['facetable', 'sortable', 'filterable']}
            field_names[base_name]['data_type'] = f['type']
            # only `SearchableField`s can be highlighted
            if f['field_type'] == 'SearchableField':
                field_names[base_name]['highlightable'] = True

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

        self.simplified_fields = get_simplified_fields(self.index_json['fields'])
        self.fields = build_fields_from_json(self.index_json['fields'])

        self.index = SearchIndex(
            name=self.index_name,
            fields=self.fields,
            scoring_profiles=self.scoring_profiles,
            suggesters=self.suggesters,
            cors_options=self.cors_options)

    def build_cors_options(self):
        return CorsOptions(allowed_origins=self.index_json.get('allowed_origin') or ["*"],
                           max_age_in_seconds=self.index_json.get('max_age_in_seconds') or 60)

    # NOTE only goes one level deep
    def get_fields_by_datatype(self, datatype):
        return [f for f, v in self.simplified_fields.items() if v['data_type'] == datatype]

    def get_fields_by_ability(self, ability):
        return [f for f, v in self.simplified_fields.items() if v.get(ability)]
