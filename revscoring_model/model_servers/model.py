import os
from distutils.util import strtobool

import enchant
import kserve
from pyenchant_utils import EnchantStr, UTF16EnchantStr

from model_servers import (
    RevscoringModel,
    RevscoringModelType
)
from model_server_mp import RevscoringModelMP


# monkey patching enchant to support older binaries. There are some older models
# which have been trained with older enchant binaries. By including additional classes from v2.0.0
# of the pyenchant library (the pyenchant_utils.py file), we allow these models to be loaded and used.
enchant.utils.UTF16EnchantStr = UTF16EnchantStr
enchant.utils.EnchantStr = EnchantStr

if __name__ == "__main__":
    inference_name = os.environ.get("INFERENCE_NAME")
    model_type = RevscoringModelType.get_model_type(inference_name)
    mp = strtobool(os.environ.get("ASYNCIO_USE_PROCESS_POOL", "False"))
    if mp:
        model = RevscoringModelMP(inference_name, model_type)
    else:
        model = RevscoringModel(inference_name, model_type)
    kserve.ModelServer(workers=1).start([model])
