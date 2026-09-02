"""Map a PyPI distribution name to the top-level module name(s) it's
actually imported as.

Most packages import as a name that's a trivial transform of their
distribution name (``requests`` -> ``requests``, ``python-dateutil`` ->
... well, not that one). This module holds the trivial default guess plus
a hand-curated table of the common exceptions -- packages whose install
name and import name genuinely differ.
"""
from __future__ import annotations

from depdrift.manifest import normalize_name

# normalized distribution name -> set of top-level module names it may be
# imported as. Curated from the most commonly hit mismatches; not
# exhaustive, but covers the packages that show up in most Python projects.
KNOWN_IMPORT_NAMES: dict[str, set[str]] = {
    "pyyaml": {"yaml"},
    "beautifulsoup4": {"bs4"},
    "bs4": {"bs4"},
    "python-dateutil": {"dateutil"},
    "scikit-learn": {"sklearn"},
    "scikit-image": {"skimage"},
    "pillow": {"pil"},
    "opencv-python": {"cv2"},
    "opencv-python-headless": {"cv2"},
    "opencv-contrib-python": {"cv2"},
    "protobuf": {"google"},
    "grpcio": {"grpc"},
    "grpcio-tools": {"grpc_tools"},
    "python-dotenv": {"dotenv"},
    "pyjwt": {"jwt"},
    "pyopenssl": {"openssl", "ssl"},
    "pycrypto": {"crypto"},
    "pycryptodome": {"crypto", "cryptodome"},
    "msgpack-python": {"msgpack"},
    "pyzmq": {"zmq"},
    "psycopg2-binary": {"psycopg2"},
    "mysql-connector-python": {"mysql"},
    "mysqlclient": {"mysqldb"},
    "websocket-client": {"websocket"},
    "attrs": {"attr", "attrs"},
    "typing-extensions": {"typing_extensions"},
    "setuptools": {"setuptools", "pkg_resources"},
    "google-cloud-storage": {"google"},
    "google-cloud-bigquery": {"google"},
    "google-api-python-client": {"googleapiclient"},
    "google-auth": {"google"},
    "azure-storage-blob": {"azure"},
    "boto3": {"boto3"},
    "botocore": {"botocore"},
    "pyparsing": {"pyparsing"},
    "jsonschema": {"jsonschema"},
    "django-rest-framework": {"rest_framework"},
    "djangorestframework": {"rest_framework"},
    "flask-sqlalchemy": {"flask_sqlalchemy"},
    "flask-cors": {"flask_cors"},
    "flask-migrate": {"flask_migrate"},
    "python-jose": {"jose"},
    "python-multipart": {"multipart"},
    "uvloop": {"uvloop"},
    "gitpython": {"git"},
    "pywin32": {"win32api", "win32com", "win32con", "pythoncom"},
    "pynacl": {"nacl"},
    "pytest-cov": {"pytest_cov"},
    "pytest-mock": {"pytest_mock"},
    "pytest-asyncio": {"pytest_asyncio"},
    "sphinx-rtd-theme": {"sphinx_rtd_theme"},
    "ruamel.yaml": {"ruamel"},
    "importlib-metadata": {"importlib_metadata"},
    "importlib-resources": {"importlib_resources"},
    "backports.zoneinfo": {"backports"},
    "html5lib": {"html5lib"},
    "lxml": {"lxml"},
    "aiohttp-cors": {"aiohttp_cors"},
    "elasticsearch-dsl": {"elasticsearch_dsl"},
    "google-cloud-pubsub": {"google"},
    "google-cloud-firestore": {"google"},
    "toml": {"toml"},
    "tomli": {"tomli"},
    "tomli-w": {"tomli_w"},
    "types-requests": set(),  # stub-only package: never imported directly
    "types-pyyaml": set(),
    "types-setuptools": set(),
}


def default_guess(distribution_name: str) -> str:
    """The naive fallback: lowercase, hyphens -> underscores. Correct for
    the large majority of packages (requests, numpy, pandas, click, ...).
    """
    return normalize_name(distribution_name).replace("-", "_")


def import_names_for(distribution_name: str) -> set[str]:
    """Return every plausible top-level import name for a declared
    dependency: the curated override(s) if known, otherwise just the
    naive guess.
    """
    key = normalize_name(distribution_name)
    if key in KNOWN_IMPORT_NAMES:
        return set(KNOWN_IMPORT_NAMES[key])
    return {default_guess(distribution_name)}
