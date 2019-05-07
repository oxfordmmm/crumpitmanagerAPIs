import cerberus
import yaml

class validateYAML:
    def validate_yaml(self, schemaFile: str, yamlFile: str):
        schema = eval(open(schemaFile, 'r').read())
        v = cerberus.Validator(schema)
        doc = yaml.safe_load(open(yamlFile, 'r').read())
        r = v.validate(doc, schema)
        return r, v.errors
