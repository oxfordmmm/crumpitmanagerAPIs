#! /usr/bin/python3

#Functionality to for reading and using config file
#
#Author: Jez Swann
#Date: May 2019

import os
import subprocess
import pathlib
import shlex
import datetime

import yaml
import cerberus

class validateYAML:
    def validate_yaml(self, schemaFile: str, yamlFile: str):
        schema = eval(open(schemaFile, 'r').read())
        v = cerberus.Validator(schema)
        doc = yaml.safe_load(open(yamlFile, 'r').read())
        r = v.validate(doc, schema)
        return r, v.errors
class Config:
    """
    Configuration parsed directly from a YAML file
    """
    def __init__(self):
        self.config = None

    def load(self, config_file: str):
        try:
            validator = validateYAML()
            ok, errs = validator.validate_yaml('configs/schema.yaml', config_file)
            if ok:
                print(config_file, "validated")
                with open(config_file, 'r') as stream:
                    self.config = yaml.safe_load(stream)
            else:
                print(config_file, "validation failed")
                print(errs)
            
        except Exception as e:
            print('ERROR: Couldn\'t setup config parameters')
            print(e)

    def load_str(self, config_str: str):
        self.config = yaml.load(config_str)

    def get(self, field: str):
        return self.config[field]
