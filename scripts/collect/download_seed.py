import os
import gzip
import requests
from tqdm.auto import tqdm
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from common import DATA_PATH

# Seed repository list from GitHub Search, MIT-licensed (see DATA_LICENSE)
# https://github.com/seart-group/ghs
url = "https://seart-ghs.si.usi.ch/api/r/download/csv?nameEquals=false&sort=name%2Casc"
output_path = DATA_PATH / "seed_repositories.csv.gz"
extract_path = DATA_PATH / "seed_repositories.csv"

os.makedirs("data", exist_ok=True)

with requests.get(url, stream=True, verify=False) as r:
    r.raise_for_status()

    total = int(r.headers.get("content-length", 0))

    with open(output_path, "wb") as f, tqdm(
        total=total,
        unit="B",
        unit_scale=True,
        desc="Downloading",
    ) as pbar:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
                pbar.update(len(chunk))

with gzip.open(output_path, "rb") as src, open(extract_path, "wb") as dst, tqdm(
    unit="B",
    unit_scale=True,
    desc="Extracting",
) as pbar:
    while chunk := src.read(1024 * 1024):
        dst.write(chunk)
        pbar.update(len(chunk))

print(f"Extracted to {extract_path}")