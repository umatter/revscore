import bz2
import os
from revscoring import Model
from common.constants import MODEL_PATH_ENV_VAR, MODEL_PATH_FOR_DRAFT_QUALITY_MODEL_TYPE, DEFAULT_MODEL_PATH, \
    WIKI_URL_ENV_VAR, WIKI_URL_NOT_FOUND_IN_ENV_ERR
from common.enums import RevscoringModelType


def get_model_path(model_kind: RevscoringModelType):
    """
    Determines the path to a model file based on the model kind and environment variables.

    Checks for a model path in the MODEL_PATH_ENV_VAR environment variable; if not found, it
    selects a default path based on the model kind. Supports custom paths for different types
    of models.

    Parameters:
    - model_kind (RevscoringModelType): The kind of model, affecting the default path selection.

    Returns:
    - str: The determined path to the model file.
    """
    if MODEL_PATH_ENV_VAR in os.environ:
        model_path = os.environ[MODEL_PATH_ENV_VAR]
    elif model_kind == RevscoringModelType.DRAFTQUALITY:
        model_path = MODEL_PATH_FOR_DRAFT_QUALITY_MODEL_TYPE
    else:
        model_path = DEFAULT_MODEL_PATH
    return model_path


def _get_wiki_url():
    """
    Fetches the wiki URL from an environment variable.

    Raises a ValueError if the WIKI_URL_ENV_VAR is not set in the environment, indicating
    that the wiki URL is required but not provided.

    Returns:
    - str: The wiki URL retrieved from the environment variable.
    """
    if WIKI_URL_ENV_VAR not in os.environ:
        raise ValueError(
            WIKI_URL_NOT_FOUND_IN_ENV_ERR
        )
    wiki_url = os.environ.get(WIKI_URL_ENV_VAR)
    return wiki_url


def score(model, feature_values):
    """
    Scores a set of feature values using a given model.

    Parameters:
    - model: The model used for scoring.
    - feature_values: A list of feature values to be scored by the model.

    Returns:
    - dict: The scoring result returned by the model.
    """
    return model.score(feature_values)


def load(model_kind: RevscoringModelType, model_path: str):
    """
    Loads a model from a specified path, handling different types of model files.

    If the model kind is DRAFTQUALITY, the model file is assumed to be compressed with bz2.
    Otherwise, it is loaded directly from a standard file.

    Parameters:
    - model_kind (RevscoringModelType): The kind of the model, which determines how to load it.
    - model_path (str): The path to the model file.

    Returns:
    - The loaded model object.
    """
    if model_kind == RevscoringModelType.DRAFTQUALITY:
        with bz2.open(model_path) as f:
            return Model.load(f)
    else:
        with open(model_path) as f:
            return Model.load(f)


def convert(value):
    """
    Converts a string value to a boolean or float for feature value processing.

    Parameters:
    - value (str): The value to convert, expected to be 'True', 'False', or a string
                   representation of a float.

    Returns:
    - Union[bool, float]: The converted value as either a boolean or float.
    """
    if value == 'True':
        return True
    elif value == 'False':
        return False
    return float(value)


