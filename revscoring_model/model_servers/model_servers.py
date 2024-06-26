import logging
import os
from typing import Any, Dict, Optional

import aiohttp
import kserve
import mwapi
from kserve.errors import InvalidInput
from revscoring.extractors import api
from revscoring.features import trim

import events, logging_utils
from common.constants import FEATURE_VAL_KEY, EXTENDED_OUTPUT_KEY, EVENT_KEY, EVENTGATE_URL, EVENTGATE_STREAM, \
    AIOHTTP_CLIENT_TIMEOUT, TLS_CERT_BUNDLE_PATH, WIKI_HOST_ENV_VAR, MISSING_REV_ID_ERR, INVALID_REV_ID_ERR
from common.utils import _get_wiki_url, get_model_path, score, load
from preprocess_utils import validate_json_input
import extractor_utils
from common.enums import RevscoringModelType
logging.basicConfig(level=kserve.constants.KSERVE_LOGLEVEL)


class RevscoringModel(kserve.Model):
    def __init__(self, name: str, model_kind: RevscoringModelType):
        super().__init__(name)
        self.name = name
        self.model_kind = model_kind
        self.ready = False
        self.wiki_url = _get_wiki_url()
        self.FEATURE_VAL_KEY = FEATURE_VAL_KEY
        self.EXTENDED_OUTPUT_KEY = EXTENDED_OUTPUT_KEY
        self.EVENT_KEY = EVENT_KEY
        self.EVENTGATE_URL = os.environ.get(EVENTGATE_URL)
        self.EVENTGATE_STREAM = os.environ.get(EVENTGATE_STREAM)
        self.AIOHTTP_CLIENT_TIMEOUT = os.environ.get(AIOHTTP_CLIENT_TIMEOUT, 5)
        self.CUSTOM_UA = f"WMF ML Team {model_kind.value} model svc"
        # Deployed via the wmf-certificates package
        self.TLS_CERT_BUNDLE_PATH = TLS_CERT_BUNDLE_PATH
        self._http_client_session = {}
        if model_kind in [
            RevscoringModelType.EDITQUALITY_DAMAGING,
            RevscoringModelType.EDITQUALITY_GOODFAITH,
            RevscoringModelType.EDITQUALITY_REVERTED,
            RevscoringModelType.DRAFTQUALITY,
        ]:
            self.extra_mw_api_calls = True
        else:
            self.extra_mw_api_calls = False
        self.model_path = get_model_path(model_kind=self.model_kind)
        self.model = load(self.model_kind, self.model_path)
        self.ready = True
        self.prediction_results = None
        # FIXME: this may not be needed, in theory we could simply rely on
        # kserve.constants.KSERVE_LOGLEVEL (passing KSERVE_LOGLEVEL as env var)
        # but it doesn't seem to work.
        logging_utils.set_log_level()

    @staticmethod
    def fetch_features(rev_id, features, extractor, cache):
        return extractor_utils.fetch_features(rev_id, features, extractor, cache)

    def get_http_client_session(self, endpoint):
        """Returns a aiohttp session for the specific endpoint passed as input.
        We need to do it since sharing a single session leads to unexpected
        side effects (like sharing headers, most notably the Host one)."""
        timeout = aiohttp.ClientTimeout(total=self.AIOHTTP_CLIENT_TIMEOUT)
        if (
            self._http_client_session.get(endpoint, None) is None
            or self._http_client_session[endpoint].closed
        ):
            logging.info(f"Opening a new Asyncio session for {endpoint}.")
            self._http_client_session[endpoint] = aiohttp.ClientSession(
                timeout=timeout, raise_for_status=True
            )
        return self._http_client_session[endpoint]




    async def get_extractor(self, inputs, rev_id):
        # The postprocess() function needs to parse the revision_create_event
        # given as input (if any).
        self.revision_create_event = self.get_revision_event(inputs, self.EVENT_KEY)
        if self.revision_create_event:
            inputs["rev_id"] = rev_id
        wiki_host = os.environ.get(WIKI_HOST_ENV_VAR)

        # This is a workaround to allow the revscoring's extractor to leverage
        # aiohttp/asyncio HTTP calls. We inject a MW API cache later on in
        # the extractor, that in turn will not make any (blocking, old style)
        # HTTP calls via libs like requests.
        mw_http_cache = await extractor_utils.get_revscoring_extractor_cache(
            rev_id,
            self.CUSTOM_UA,
            self.get_http_client_session("mwapi"),
            wiki_url=self.wiki_url,
            wiki_host=wiki_host,
            fetch_extra_info=self.extra_mw_api_calls,
        )

        # Create the revscoring's extractor with the MWAPICache built above.
        return api.Extractor(
            mwapi.Session(self.wiki_url, user_agent=self.CUSTOM_UA),
            http_cache=mw_http_cache,
        )

    async def preprocess(self, inputs: Dict, headers: Dict[str, str] = None) -> Dict:
        """Use MW API session and Revscoring API to extract feature values
        of edit text based on its revision id"""
        inputs = validate_json_input(inputs)

        rev_id = self.get_rev_id(inputs, self.EVENT_KEY)
        extended_output = inputs.get("extended_output", False)
        extractor = await self.get_extractor(inputs, rev_id)

        # The idea of this cache variable is to avoid extra cpu-bound
        # computations when executing fetch_features in the extended_output
        # branch. Revscoring allows to pass a cache parameter to save
        # info about { rev-id -> features } for subsequent calls.
        # We pass 'cache' for reference, so that fetch_features can populate/use
        # it if needed. This sadly doesn't work with a process pool, since
        # behind the scenes the work is done in another Python process
        # (and input/output is pickled/unpickled). The reference doesn't work
        # of course, and any attempt to return it from fetch_features led to
        # pickling errors. For the moment, until we solve the pickling errors
        # in revscoring (not sure if we want to do it), enabling extended_output
        # and using a process pool will mean recomputing fetch_features.
        cache = {}

        inputs[self.FEATURE_VAL_KEY] = self.fetch_features(
            rev_id, self.model.features, extractor, cache
        )

        if extended_output:
            bare_model_features = list(trim(self.model.features))
            base_feature_values = self.fetch_features(
                rev_id, bare_model_features, extractor, cache
            )
            inputs[self.EXTENDED_OUTPUT_KEY] = {
                str(f): v for f, v in zip(bare_model_features, base_feature_values)
            }
        return inputs

    def get_revision_score_event(self, rev_create_event: Dict[str, Any]) -> Dict:
        return events.generate_revision_score_event(
            rev_create_event,
            self.EVENTGATE_STREAM,
            self.model.version,
            self.prediction_results,
            self.model_kind.value,
        )

    def get_output(self, request: Dict, extended_output: bool):
        wiki_db, model_name = self.name.split("-")
        rev_id = request.get("rev_id")
        output = {
            wiki_db: {
                "models": {model_name: {"version": self.model.version}},
                "scores": {rev_id: {model_name: {"score": self.prediction_results}}},
            }
        }
        if extended_output:
            # add extended output to reach feature parity with ORES, like:
            # https://ores.wikimedia.org/v3/scores/enwiki/186357639/goodfaith?features
            # If only rev_id is given in input.json, only the prediction results
            # will be present in the response. If the extended_output flag is true,
            # features output will be included in the response.
            output[wiki_db]["scores"][rev_id][model_name]["features"] = extended_output
        return output

    async def send_event(self) -> None:
        # Send a revision-score event to EventGate, generated from
        # the revision-create event passed as input.
        if self.revision_create_event:
            revision_score_event = self.get_revision_score_event(
                self.revision_create_event
            )
            await events.send_event(
                revision_score_event,
                self.EVENTGATE_URL,
                self.TLS_CERT_BUNDLE_PATH,
                self.CUSTOM_UA,
                self.get_http_client_session("eventgate"),
            )
    @staticmethod
    def get_revision_event(inputs: Dict, event_input_key) -> Optional[str]:
        try:
            return inputs[event_input_key]
        except KeyError:
            return None
    @staticmethod
    def get_rev_id(inputs: Dict, event_input_key) -> Dict:
        """Get a revision id from the inputs provided.
        The revision id can be contained into an event dict
        or passed directly as value.
        """
        try:
            # If a revision event is passed as input,
            # its rev-id is considerate the one to score.
            # Otherwise, we look for a specific "rev_id" input.
            if event_input_key in inputs:
                if inputs[event_input_key]["$schema"].startswith(
                    "/mediawiki/revision/create/1"
                ) or inputs[event_input_key]["$schema"].startswith(
                    "/mediawiki/revision/create/2"
                ):
                    rev_id = inputs[event_input_key]["rev_id"]
                elif inputs[event_input_key]["$schema"].startswith(
                    "/mediawiki/page/change/1"
                ):
                    rev_id = inputs[event_input_key]["revision"]["rev_id"]
                else:
                    raise InvalidInput(
                        f"Unsupported event of schema {inputs[event_input_key]['$schema']}, "
                        "the rev_id value cannot be determined."
                    )
            else:
                rev_id = inputs["rev_id"]
        except KeyError:
            logging.error(MISSING_REV_ID_ERR)
            raise InvalidInput(MISSING_REV_ID_ERR)
        if not isinstance(rev_id, int):
            logging.error(INVALID_REV_ID_ERR)
            raise InvalidInput(INVALID_REV_ID_ERR)
        return rev_id

    async def predict(self, request: Dict, headers: Dict[str, str] = None) -> Dict:
        feature_values = request.get(self.FEATURE_VAL_KEY)
        extended_output = request.get(self.EXTENDED_OUTPUT_KEY)
        self.prediction_results = score(self.model, feature_values)
        output = self.get_output(request, extended_output)
        await self.send_event()
        return output
