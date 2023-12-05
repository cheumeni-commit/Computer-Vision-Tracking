import json


def create_category_index(categories):
    """Creates dictionary of COCO compatible categories keyed by category id.

  Args:
    categories: a list of dicts, each of which has the following keys:
      'id': (required) an integer id uniquely identifying this category.
      'name': (required) string representing category name
        e.g., 'cat', 'dog', 'pizza'.

  Returns:
    category_index: a dict containing the same entries as categories, but keyed
      by the 'id' field of each category.
  """
    category_index = {k: v for k, v in categories.items()}
    return category_index


def load_labelmap(path):
    """Loads label map json.

  Args:
    path: path to json file.
  Returns:
    a dictionnary 
  """
    with open(path, "r") as fp:
        label_map = json.loads(fp.read())

    return label_map
