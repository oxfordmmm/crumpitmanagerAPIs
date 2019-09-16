#! /usr/bin/python3

#Functionality to validate YAML
#
#Author: Jez Swann
#Date: May 2019

import cerberus
import yaml

class validateYAML:
    def validate_yaml(self, schemaFile: str, yamlFile: str):
        schema = eval(open(schemaFile, 'r').read())
        v = cerberus.Validator(schema)
        doc = yaml.safe_load(open(yamlFile, 'r').read())
        r = v.validate(doc, schema)
        return r, v.errors
