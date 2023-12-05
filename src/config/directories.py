from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class _Directories:

    def __init__(self):
       
        self.root_dir = Path(__file__).resolve(strict=True).parents[2]
        
        self.dir_config = self.root_dir / "config/"
        self.dir_data = self.root_dir / "data/"
        self.dir_project = self.root_dir / "src/"
        self.dir_raw = self.dir_data / "raw/"
        self.dir_video = self.dir_data / "saveVideos/"
        self.dir_labels = self.dir_data / "labels/"
        self.dir_model = self.dir_data / "artefacts/"
        
        
        for dir_path in vars(self).values():
            try:
                dir_path.mkdir(exist_ok=True, parents=True)
            except:
                logger.info("Error when we are build a {} directory".format(dir_path))
        
        
directories = _Directories()
       
