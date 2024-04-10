import argparse
import logging

from script_revscoring_model import ScriptRevscoringModel, RevscoringModelType

import asyncio
import pandas as pd
import os
import json


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')


async def fetch_revision_data(rev_id: int, data_dir: str) -> None:
    file_path = os.path.join(os.path.join(data_dir, "inferences"), f"{rev_id}.json")
    path_to_features = os.path.join(os.path.join(data_dir, "features"))
    if not os.path.exists(file_path):
        try:
            await model.fetch_features(rev_id=rev_id, features=model.model.features,
                                                       path_to_save=os.path.join(path_to_features, f"{rev_id}.csv"))
            data = await model.predict(rev_id=rev_id, path_to_features=path_to_features)
            with open(file_path, 'w') as f:
                json.dump(data, f)
            logging.info(f"Data for revision ID {rev_id} saved successfully.")
        except Exception as e:
            logging.error(f"Error fetching data for revision ID {rev_id}: {str(e)}")


async def main(csv_path: str, data_dir: str) -> None:
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Revscoring Data Fetcher")
    parser.add_argument('--csv_path', type=str, default='revision_ids.csv',
                        help='Path to the CSV file with revision IDs')
    parser.add_argument('--data_dir', type=str, default='data', help='Directory to store the fetched data')
    parser.add_argument('--model_name', type=str, required=True, help='Name of the model')
    parser.add_argument('--model_type', type=str, required=True, choices=[e.value for e in RevscoringModelType],
                        help='Type of the model')

    args = parser.parse_args()
    model_kind = args.model_type
    model = ScriptRevscoringModel(args.model_name, model_kind)
    asyncio.run(main(args.csv_path, args.data_dir))