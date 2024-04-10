from typing import Dict
import mwapi
import pandas as pd
from revscoring.extractors.api import Extractor
from common.enums import RevscoringModelType
from common.constants import API_USER_AGENT
from common.utils import get_model_path, _get_wiki_url, convert, score, load


class ScriptRevscoringModel:
    def __init__(self, name: str, model_kind: RevscoringModelType):
        self.name = name
        self.model_kind = model_kind
        self.model_path = get_model_path(self.model_kind)
        self.model = load(self.model_kind, self.model_path)

    @staticmethod
    async def fetch_features(rev_id, features, path_to_save: str) -> None:
        """
        Asynchronously fetches specified features for a given revision ID and saves them to a CSV file.

        This static method uses the MediaWiki API to extract features for a specific revision ID.
        The extracted features are then saved to a CSV file at the specified path. The method
        creates a DataFrame to organize the features before saving, ensuring the CSV file contains
        a header row with feature names and a single row of values corresponding to the revision ID.

        Parameters:
        - rev_id: The revision ID for which to fetch features. The type of this parameter
                  depends on how the revision ID is represented in the caller's context.
        - features: A collection of features to be extracted for the revision ID. The type
                    and structure of this parameter should match what the Extractor expects,
                    typically a list or similar iterable of feature identifiers.
        - path_to_save (str): The file path where the extracted features should be saved as a CSV.
                              The method will overwrite any existing file at this path.

        Returns:
        - None: This method does not return a value. Its primary effect is the side effect of
                writing to a file system.

        Notes:
        - This method is asynchronous and should be awaited when called.
        - It relies on the `Extractor` class from a library designed to interact with the
          MediaWiki API, which must be properly initialized with a session including the
          target wiki URL and a user agent string.
        - The caller is responsible for ensuring that the `path_to_save` directory exists
          and is writable.
        """
        extractor = Extractor(mwapi.Session(host=_get_wiki_url(),
                                            user_agent=API_USER_AGENT))

        values = extractor.extract(rev_id, features)
        df = pd.DataFrame([values], columns=[str(f) for f in features])
        df.to_csv(path_to_save, index=False)

    def get_output(self, rev_id, extended_output: bool, results: dict):
        """
        Formats model scoring results for a revision ID into a structured output.

        Constructs a dictionary containing the model's version and scores for the specified revision ID.
        If `extended_output` is True, includes additional details in the output.

        Parameters:
        - rev_id: The revision ID being scored.
        - extended_output (bool): Flag to include extra information in the output.
        - results (dict): The scoring results for `rev_id`.

        Returns:
        - dict: A structured dictionary with the model scores and, optionally, extra details.
        """
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

    async def predict(self, rev_id, path_to_features: str) -> Dict:
        """
       Asynchronously predicts and formats the model's output for a given revision ID.

       Reads features from a CSV file, converts these features, and then uses them to
       score using the model. The scores are formatted into a structured output.

       Parameters:
       - rev_id: The revision ID for which to predict scores.
       - path_to_features (str): The path to the directory containing features CSV files.

       Returns:
       - Dict: A dictionary containing the formatted prediction output, including scores and,
               if enabled, additional details.
       """
        df = pd.read_csv(f"{path_to_features}/{rev_id}.csv", header=None)
        converted_list_of_features = [convert(value) for value in df.values[1]]
        output = self.get_output(rev_id, True, results=(score(self.model, converted_list_of_features)))
        return output
