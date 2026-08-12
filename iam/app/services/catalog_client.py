from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from flask import current_app


class CatalogClient:
    @staticmethod
    def plantel_exists(id_plantel):
        api_url = current_app.config.get('CATALOG_API_BASE_URL')
        if not api_url:
            raise RuntimeError('CATALOG_API_BASE_URL no está configurado.')

        url = f"{api_url.rstrip('/')}/planteles/{id_plantel}"
        request = Request(url, headers={'Accept': 'application/json'})

        try:
            with urlopen(request, timeout=5) as response:
                return response.getcode() == 200
        except HTTPError as exc:
            if exc.code == 404:
                return False
            raise
        except URLError:
            raise
