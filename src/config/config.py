from dataclasses import dataclass
import logging
import yaml

from src.config.directories import directories as dirs
from src.constants import (C_YML,
                           C_PARAMETER
                          )


logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class Config:
    color: list
    barcode: list
    confBay: dict


def load_config():

    try:
        with open(dirs.dir_config / C_YML, 'r') as fp:
                read_data = yaml.safe_load(fp)
    except:
        logger.info("yml file is corrupted")

    return read_data


def get_config(env: str) -> Config:
    
    config = load_config()[C_PARAMETER]
    return Config(**config)

