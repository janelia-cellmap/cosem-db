import argparse
from sheetscrape.scraper import GoogleSheetScraper
from sheetscrape.parsers import TrainingData
import pandas as pd
from pymongo import MongoClient
import yaml
import time
import logging

logger = logging.getLogger(__name__)
c_handler = logging.StreamHandler()
c_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
c_handler.setFormatter(c_formatter)
logger.addHandler(c_handler)
logger.setLevel(logging.INFO)
def getpasswd():
    import sys
    import getpass

    print("Enter mongo credentials")
    username = input("Username: ")
    password = getpass.getpass("Password: ")
    return username, password


def parse_jobfile(path):
    with open(path, 'rb') as fh:
        jobparams = yaml.load(fh, Loader=yaml.FullLoader)
    return jobparams


def parse_worksheet(keyfile_path, doc_name, worksheet_title):
    doc = GoogleSheetScraper(keyfile_path).client.open(doc_name)
    worksheets = list(filter(lambda v: v.title == worksheet_title, doc.worksheets()))

    ws = None

    if len(worksheets) > 1:
        raise ValueError(f'Multiple worksheets found named \'{worksheet_title}\'')
    elif len(worksheets) == 0:
        raise ValueError(f'No worksheets found named \'{worksheet_title}\'')
    else:
        ws = worksheets[0]

    df = pd.DataFrame(ws.get_all_values())

    # put in a unique ID for each element
    parsed = TrainingData.parse(df)
    for p in parsed:
        p._id = f'{p.biotype}_crop{int(p.number)}'
    parsed = [p.todict() for p in parsed]

    return parsed


def update_collection(collection, to_insert):
    logger.info(f'Preparing to update {collection} with {len(to_insert)} entries.')
    k = '_id'
    try:
        ids = [t['_id'] for t in to_insert]
    except KeyError:
        raise KeyError('Each entry in `to_insert` must have an `_id` key')

    # remove old entries
    for current in collection.find():
        cid = current[k]
        removed = 0
        if cid not in ids:
            print(f'Removing {cid} from the database')
            collection.delete_one({k: cid})
            removed += 1
    logger.info(f'Removed {removed} stale entries from the database.')
    # add / update data to database

    for t in to_insert:
        collection.find_one_and_replace({k: t[k]}, t, upsert=True)
    return 0


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Update a MongoDB collection from data stored in a spreadsheet on google drive")
    
    parser.add_argument("-j", "--jobfile",help="Path to a .yml file that defines what data should be taken from google drive, "
                                              "and where that data should be stored", required=True)

    parser.add_argument('-i', '--interval',help="The interval in minutes between executions of this script. Valid values are "
                                                "-1 (the default) to run just once, and any integer in the range [1, 60]", default=-1)

    args = parser.parse_args()
    jobfile = args.jobfile
    interval = int(args.interval)
    if interval not in set([-1, *range(1, 61)]):
        raise ValueError('Interval must be -1 or an integer in the range [1, 60]')


    # maybe make this a command line argument
    jobName = 'getTrainingData'
    jobSpec = parse_jobfile(jobfile)
    inputSpec = jobSpec['jobs']['getTrainingData']['input']
    outputSpec = jobSpec['jobs']['getTrainingData']['output']
    src = inputSpec['origin']
    dest = outputSpec['destination']

    if dest == 'mongodb':
        mongo_username, mongo_password = getpasswd()
        client = MongoClient(outputSpec['url'],
                             username=mongo_username,
                             password=mongo_password)

        collection = client[outputSpec['database']][outputSpec['collection']]

        if src == 'googleDrive':
            while True:
                to_insert = parsed = parse_worksheet(inputSpec['auth'], inputSpec['document'], inputSpec['worksheet'])
                update_collection(collection, to_insert)
                try:
                    time.sleep(60 * interval)
                except ValueError:
                    break
        else:
            raise NotImplementedError(f'Destination {dest} not supported.')

    else:
        raise NotImplementedError(f'Destination {dest} not supported.')

