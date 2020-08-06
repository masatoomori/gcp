import os
import re
from io import StringIO

from google.cloud import storage        # pip install google-cloud-storage
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = 'horse-race-263506-744e3e1e7e55.json'


def list_blobs(bucket_name, prefix=None):
    """Lists all the blobs in the bucket."""
    storage_client = storage.Client()

    # Note: Client.list_blobs requires at least package version 1.17.0.
    blobs = storage_client.list_blobs(bucket_name, prefix=prefix)

    return blobs


def blob_exists(blob_name, bucket_name):
    for b in list_blobs(bucket_name):
        if b.name == blob_name:
            return True
    return False


def upload_file(source_file, destination_file, bucket_name, content_type='application/vnd.ms-excel'):
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    blob = bucket.blob(destination_file)
    blob.upload_from_filename(filename=source_file, content_type=content_type)


def upload_dataframe(df, destination_file, bucket_name, index=False, content_type='application/vnd.ms-excel'):
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    blob = bucket.blob(destination_file)

    if content_type in ['csv', 'application/vnd.ms-excel']:
        bytes_to_write = df.to_csv(None, index=index).encode()
        blob.upload_from_string(bytes_to_write, content_type=content_type)
    elif content_type in ['parquet']:
        # pyarrowのTableに変換
        table = pa.Table.from_pandas(df)

        # Bufferにテーブルを書き込み
        buf = pa.BufferOutputStream()
        pq.write_table(table, buf, compression=None)

        blob.upload_from_string(data=buf.getvalue().to_pybytes())
    else:
        print('invalid content_type selected')


def download_dataframe(source_file, bucket_name, encodings, skip_rows=0, line_feed_code='\n', dtype=object):
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    if encodings:
        for encoding in encodings:
            try:
                content = bucket.get_blob(source_file).download_as_string().decode(encoding)
                lines = re.split(line_feed_code, content)

                buff = list()
                for i, line in enumerate(lines):
                    if i >= skip_rows:
                        buff.append(line)
                content = '{}'.format(line_feed_code).join(buff)

                df = pd.read_csv(StringIO(content), dtype=dtype)

                return df
            except Exception as e:
                print(e)
                continue
    else:
        print('ERROR: download_dataframe({s}, {b}). Specify at least on encoding'.format(s=source_file, b=bucket))
        exit()
    return pd.DataFrame()


def main():
    bucket_name = '<bucket name>'
    gcs_source_file = '<file name in GCS>'
    gcs_destination_file = '<file name in GCS>'
    local_source_file = '<path to data>.csv'

    # ファイルをアップロードする
    upload_file(source_file=local_source_file, destination_file=gcs_destination_file, bucket_name=bucket_name,
                content_type='application/vnd.ms-excel')

    # DataFrameをアップロードする
    df = pd.DataFrame()
    upload_dataframe(df, destination_file=gcs_destination_file, bucket_name=bucket_name,
                     content_type='application/vnd.ms-excel')

    # DataFrameにダウンロードする
    df = download_dataframe(source_file=gcs_source_file, bucket_name=bucket_name, encodings=['utf8'])
    print(df)


if __name__ == '__main__':
    main()