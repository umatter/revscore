import os

from revscoring_model.model_servers.model_servers import RevscoringModelType
from revscoring_model.model_servers.preprocess_utils import _get_wiki_url

from revscoring.extractors.api import Extractor
import mwapi


def fetch_features(rev_id, features):
    extractor = Extractor(mwapi.Session(host=_get_wiki_url(),
                                        user_agent="revscoring demo"))
    return list(extractor.extract(rev_id, features))


def get_model_path(model_kind: RevscoringModelType):
    if "MODEL_PATH" in os.environ:
        model_path = os.environ["MODEL_PATH"]
    elif model_kind == RevscoringModelType.DRAFTQUALITY:
        model_path = "/mnt/models/model.bz2"
    else:
        model_path = "/mnt/models/model.bin"
    return model_path