import bz2
import os
from enum import Enum
from typing import Dict

import mwapi
from revscoring import Model
from revscoring.extractors.api import Extractor


class RevscoringModelType(Enum):
    ARTICLEQUALITY = "articlequality"
    ARTICLETOPIC = "articletopic"
    DRAFTQUALITY = "draftquality"
    DRAFTTOPIC = "drafttopic"
    EDITQUALITY_DAMAGING = "damaging"
    EDITQUALITY_GOODFAITH = "goodfaith"
    EDITQUALITY_REVERTED = "reverted"
    ITEMQUALITY = "itemquality"
    ITEMTOPIC = "itemtopic"

    @classmethod
    def get_model_type(cls, inference_name: str):
        """
        Lookup function that searches for the model type value in the inference service name.
        e.g. searches for 'articlequality` in `enwiki-articlequality`
        """
        for _, model in cls.__members__.items():
            if model.value in inference_name:
                return model
        raise LookupError(
            f"INFERENCE_NAME '{inference_name}' could not be matched to a revscoring model type."
        )


class ScriptRevscoringModel:
    def __init__(self, name: str, model_kind: RevscoringModelType):
        self.name = name
        self.model_kind = model_kind
        self.model_path = self.get_model_path()
        self.model = self.load()

    def score(self, feature_values):
        return self.model.score(feature_values)

    @staticmethod
    def _get_wiki_url():
        if "WIKI_URL" not in os.environ:
            raise ValueError(
                "The environment variable WIKI_URL is not set. Please set it before running the server."
            )
        wiki_url = os.environ.get("WIKI_URL")
        return wiki_url

    def get_model_path(self):
        if "MODEL_PATH" in os.environ:
            model_path = os.environ["MODEL_PATH"]
        elif self.model_kind == RevscoringModelType.DRAFTQUALITY:
            model_path = "/mnt/models/model.bz2"
        else:
            model_path = "/mnt/models/model.bin"
        return model_path

    def fetch_features(self, rev_id, features):
        extractor = Extractor(mwapi.Session(host=self._get_wiki_url(),
                                            user_agent="revscoring demo"))
        return list(extractor.extract(rev_id, features))

    def load(self):
        if self.model_kind == RevscoringModelType.DRAFTQUALITY:
            with bz2.open(self.model_path) as f:
                return Model.load(f)
        else:
            with open(self.model_path) as f:
                return Model.load(f)

    def get_output(self, rev_id, extended_output: bool, results: dict):
        wiki_db, _, model_name_partition = self.name.partition("-")
        model_name = model_name_partition if model_name_partition else wiki_db
        output = {
            wiki_db: {
                "models": {model_name: {"version": self.model.version}},
                "scores": {rev_id: {model_name: {"score": results}}},
            }
        }
        if extended_output:
            output[wiki_db]["scores"][rev_id][model_name]["features"] = extended_output
        return output

    async def predict(self, rev_id, features) -> Dict:
        feature_values = self.fetch_features(rev_id=rev_id, features=features)
        output = self.get_output(rev_id, True, results=(self.score(feature_values)))
        return output
