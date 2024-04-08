import bz2
from typing import Dict

from revscoring import Model

from revscoring_model.model_servers.model_servers import RevscoringModelType
from src.preprocess_utils import fetch_features, get_model_path


class ScriptRevscoringModel:
    def __init__(self, name: str, model_kind: RevscoringModelType):
        self.name = name
        self.model_kind = model_kind
        self.model_path = get_model_path(self.model_kind)
        self.model = self.load()

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
        feature_values = fetch_features(rev_id=rev_id, features=features)
        output = self.get_output(rev_id, True, results=(self.model.score(feature_values)))
        return output
