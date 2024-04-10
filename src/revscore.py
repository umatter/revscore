import argparse
import logging
from common.enums import RevscoringModelType
from script_revscoring_model import ScriptRevscoringModel

import asyncio
import pandas as pd
import os
import json


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')


async def fetch_revision_data(rev_id: int, data_dir: str) -> None:
    """
    Asynchronously fetches and saves revision data for a given revision ID.

    This function first checks if the data for the specified revision ID already exists.
    If not, it proceeds to fetch feature data for that revision and uses it to
    make a prediction. The prediction data is then saved as a JSON file. If the
    data already exists or an error occurs during data fetching or file saving,
    appropriate logging is performed.

    Parameters:
    - rev_id (int): The revision ID for which data needs to be fetched and saved.
    - data_dir (str): The directory path where the data files are stored. This
                      path is used to construct the paths for saving the inference
                      data and the features data.

    Returns:
    - None: This function does not return anything. It saves the prediction data
            to a file and logs messages indicating the success or failure of
            data fetching and saving operations.

    Raises:
    - Exception: Catches and logs any exceptions that occur during the data
                 fetching and saving process, including errors in file handling
                 and issues encountered while fetching features or making predictions.
    """
    file_path = os.path.join(os.path.join(data_dir, "inferences"), f"{rev_id}.json")
    path_to_features = os.path.join(os.path.join(data_dir, "features"))
    if not os.path.exists(file_path):
        try:
            await model.fetch_features(rev_id=rev_id, features=model.model.features,
                                 path_to_save=os.path.join(path_to_features, f"{rev_id}.csv")
                                 )
            data = await model.predict(rev_id=rev_id, path_to_features=path_to_features)
            with open(file_path, 'w') as f:
                json.dump(data, f)
            logging.info(f"Data for revision ID {rev_id} saved successfully.")
        except Exception as e:
            logging.error(f"Error fetching data for revision ID {rev_id}: {str(e)}")


async def main(csv_path: str, data_dir: str) -> None:
    """
    Asynchronously processes revision IDs from a CSV file to fetch and save their data.

    This function reads revision IDs from a specified CSV file and asynchronously
    fetches and saves data for each revision ID. It ensures the necessary directories
    exist for storing the fetched data and logs the creation of any new directories.
    If the specified CSV file does not exist or other file operations fail, appropriate
    logging is performed. The function handles creating both 'inferences' and 'features'
    directories under the specified data directory if they do not already exist.

    Parameters:
    - csv_path (str): The file path to the CSV file containing revision IDs under
                      the column 'rev_id'.
    - data_dir (str): The base directory path where the fetched data (inferences and
                      features) should be stored. This function ensures this directory
                      and its subdirectories ('inferences', 'features') exist.

    Returns:
    - None: This function does not return any value. It primarily focuses on side effects
            including reading from a CSV file, creating directories, and initiating
            asynchronous data fetching and saving operations for multiple revision IDs.

    Notes:
    - The function relies on the `fetch_revision_data` asynchronous function to process
      each revision ID found in the CSV file.
    - It uses asynchronous IO operations to improve efficiency when handling multiple
      revision IDs.
    - The function creates the necessary data directories if they do not exist, to ensure
      there is a structured place to save the fetched data.
    - Logging is used to provide feedback on the process's progress and to report any
      issues encountered during execution.
    """
    if not os.path.isfile(csv_path):
        logging.error(f"CSV file not found at {csv_path}")
        return

    df = pd.read_csv(csv_path)

    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        logging.info(f"Created directory {data_dir}")

    for dir in [os.path.join(data_dir, "inferences"), os.path.join(data_dir, "features")]:
        if not os.path.exists(dir):
            os.makedirs(dir)
            logging.info(f"Created directory {dir}")

    tasks = [fetch_revision_data(rev_id, data_dir) for rev_id in df['rev_id']]
    await asyncio.gather(*tasks)

# This script is a Revscoring Data Fetcher. It reads revision IDs from a CSV file,
# fetches and saves data for each revision ID using a specified model. The script
# allows customization of the CSV file path, data directory, model name, and model type
# through command-line arguments.

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Revscoring Data Fetcher")
    parser.add_argument('--csv_path', type=str, default='revision_ids.csv',
                        help='Path to the CSV file with revision IDs')
    parser.add_argument('--data_dir', type=str, default='data', help='Directory to store the fetched data')
    parser.add_argument('--model_name', type=str, required=True, help='Name of the model')
    parser.add_argument('--model_type', type=str, required=True, choices=[e.value for e in RevscoringModelType],
                        help='Type of the model')
    # Parse the command-line arguments.
    args = parser.parse_args()

    # Initialize the model and start the main asynchronous operation.
    model_kind = args.model_type
    model = ScriptRevscoringModel(args.model_name, model_kind)
    asyncio.run(main(args.csv_path, args.data_dir))