import os
import yaml
from pathlib import Path


class DatasetLoader(object):

    @staticmethod
    def read_dataset(dataset_id):
        my_dir = Path(__file__).resolve().parents[1]

        print("my_dir", my_dir)

        dataset_path = os.path.join(str(my_dir), 'datasets/' + dataset_id)

        with open(dataset_path, 'r') as file:
            dataset = yaml.safe_load(file)

        return dataset