import logging
import yaml


logger = logging.getLogger(__name__)


def load_yml_file(file, default=None):
     try:
        with open(file, 'r') as fp:
          config_file = yaml.safe_load(fp)
        return config_file
     except KeyError:
          if default is None:
               default = {}
          return default

