import logging
import yaml


logger = logging.getLogger(__name__)


def load_yml_file(file):
    logger.info("load yml file")
    with open(file, 'r') as fp:
         config_file = yaml.safe_load(fp)
    logger.info("end of load yml file")
    return config_file

