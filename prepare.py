from urllib.parse import urljoin
import requests


def download_ltr_resource(resource):
    ltr_domain = 'http://es-learn-to-rank.labs.o19s.com/'
    resource_url = urljoin(ltr_domain, resource)
    with open(resource, 'wb') as file:
        print("GET %s" % resource_url)
        resp = requests.get(resource_url, stream=True)
        for chunk in resp.iter_content(chunk_size=1024):
            if chunk:
                file.write(chunk)


if __name__ == "__main__":
    download_ltr_resource('tmdb.json')
    download_ltr_resource('RankLib-2.8.jar')