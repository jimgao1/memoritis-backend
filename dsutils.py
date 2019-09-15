from google.cloud import storage

class GoogleDatastore:
    def __init__(self):
        self.client = storage.Client()
        self.bucket = self.client.get_bucket('htn19videos')

    def upload(self, source_name, target_name):
        blob = self.bucket.blob(target_name)
        blob.upload_from_filename(source_name)

    def grab(self, blob_name, file_name):
        blob = self.bucket.blob(blob_name)
        blob.download_to_filename('files/%s' % file_name)
