# Revscore ML Models (based on Wikimedia Inference Services)

(based on https://github.com/wikimedia/machinelearning-liftwing-inference-services/tree/main)

## Preparatory steps and prerequisites for running the revscoring model server

The following steps are necessary to run the revscoring model server locally:

```
# install pyenv
curl https://pyenv.run | bash
echo 'export PATH="$HOME/.pyenv/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init --path)"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc

# install python 3.8.10
pyenv install 3.8.10
pyenv global 3.8.10

# set up the virtual environment
python3.8 -m venv revscore_env
source revscore_env/bin/activate

# install the requirements
pip install --upgrade pip setuptools wheel
pip install -r python/requirements.txt
pip install -r revscoring_model/requirements.txt

# download the models
mkdir models
cd models
mkdir goodfaith
cd goodfaith
wget -m -np -nH --cut-dirs=3 -R "index.html*" https://analytics.wikimedia.org/published/wmf-ml-models/goodfaith/enwiki/20220214192144/
wget -m -np -nH --cut-dirs=3 -R "index.html*" https://analytics.wikimedia.org/published/wmf-ml-models/goodfaith/ruwiki/20220214192253/

# Set environment variables
export INFERENCE_NAME='enwiki-goodfaith'
export MODEL_URL='goodfaith/enwiki/20220214192144/model.bin'
export MODEL_PATH='models/goodfaith/enwiki/20220214192144/model.bin'
export WIKI_URL='https://en.wikipedia.org'


```
*NOTE: set the WIKI_URL such that it is consistent with the language version of the model!*


## Running the revscoring model server

Once the above steps are completed, you can start the server by running the following command:

```

python3.8 revscoring_model/model_servers/model.py
```

This will start the server on port 8080. You should see output like this:

```
2024-04-03 06:51:36.869 uvicorn.error INFO:     Started server process [131806]
2024-04-03 06:51:36.869 uvicorn.error INFO:     Waiting for application startup.
2024-04-03 06:51:36.873 131806 kserve INFO [start():62] Starting gRPC server on [::]:8081
2024-04-03 06:51:36.873 uvicorn.error INFO:     Application startup complete.
2024-04-03 06:51:36.873 uvicorn.error INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

Then run queries like this

```
curl localhost:8080/v1/models/enwiki-goodfaith:predict -X POST -d '{"rev_id": 12345}' -H "Content-type: application/json"

```

which should return a response like this:

```
{"enwiki":{"models":{"goodfaith":{"version":"0.5.1"}},"scores":{"345":{"goodfaith":{"score":{"prediction":true,"probability":{"false":0.07060893127590206,"true":0.9293910687240979}}}}}}
```

## Running the Script

To execute the script from the project's root directory, use the command:

```bash
python3.8 src/revscore.py --model_name <your_model_name> --model_type <model_type>
```

Required Parameters:

```
--model_name: The name you wish to assign to your model. You are free to choose any name.
--model_type: The type of AI model you wish to use, selected from a predefined list of enums. Available options are articlequality, articletopic, draftquality, drafttopic, damaging, goodfaith,
```

Optional Parameters:

```
--csv_path: The path to the CSV file containing rev_ids. By default, the script searches for a CSV file in the root directory unless another path is specified.
--data_dir: The directory where inferences for rev_id from the CSV are saved. If not specified, the script defaults to a data folder in the project's root directory.
```

Functionality

 - Reads all rev_id identifiers from the specified CSV file.
 - For each rev_id, if there is no existing file in the results directory (rev_id.json), the script fetches the inference for that rev_id and saves it.
 - Fetching the inference requires sending a request to an API to obtain features for the AI model, which is accomplished through the fetch_features method.
 - Once the features are retrieved, the script can load the AI model locally and use these features to generate an inference locally, saving the result in the designated directory (default is /data) in JSON format.
 - The script includes try-except blocks to catch and handle errors, ensuring smooth execution.