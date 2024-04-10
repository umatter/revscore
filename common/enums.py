from enum import Enum


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