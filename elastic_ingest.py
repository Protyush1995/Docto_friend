import pandas as pd
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

def ingest_csv_to_es(csv_file, index_name="medicines"):
    # Connect to Elasticsearch (adjust host/port if needed)
    es = Elasticsearch("http://localhost:9200")

    # Load the merged CSV
    df = pd.read_csv(csv_file)

    # Prepare documents for bulk ingestion
    actions = [
        {
            "_index": index_name,
            "_source": {
                "name": row["name"],
                "brand": row["brand"],
                "salt_composition": row["salt_composition"],
                "is_discontinued": row["Is_discontinued"]
            }
        }
        for _, row in df.iterrows()
    ]

    # Bulk insert into Elasticsearch
    bulk(es, actions)
    print(f"Ingested {len(actions)} records into index '{index_name}'")

if __name__ == "__main__":
    # Example usage: ingest merged.csv into Elasticsearch
    ingest_csv_to_es("merged.csv", "medicines")
