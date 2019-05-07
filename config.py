import os
import subprocess
import pathlib
import shlex
import datetime

import yaml
import validateYAML

class Config:
    """
    Configuration parsed directly from a YAML file
    """
    def __init__(self):
        self.config = None

    def load(self, config_file: str):
        try:
            validator = validateYAML.validateYAML()
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
