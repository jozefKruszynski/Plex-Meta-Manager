import logging
from modules import util
from modules.util import Failed
from plexapi.exceptions import BadRequest, NotFound

logger = logging.getLogger("Plex Meta Manager")

builders = ["tautulli_popular", "tautulli_watched"]

class Tautulli:
    def __init__(self, config, params):
        self.config = config
        self.url = params["url"]
        self.apikey = params["apikey"]
        try:
            response = self._request(f"{self.url}/api/v2?apikey={self.apikey}&cmd=get_library_names")
        except Exception:
            util.print_stacktrace()
            raise Failed("Tautulli Error: Invalid url")
        if response["response"]["result"] != "success":
            raise Failed(f"Tautulli Error: {response['response']['message']}")

    def get_rating_keys(self, library, params):
        query_size = int(params["list_size"]) + int(params["list_buffer"])
        logger.info(f"Processing Tautulli Most {params['list_type'].capitalize()}: {params['list_size']} {'Movies' if library.is_movie else 'Shows'}")
        response = self._request(f"{self.url}/api/v2?apikey={self.apikey}&cmd=get_home_stats&time_range={params['list_days']}&stats_count={query_size}")
        stat_id = f"{'popular' if params['list_type'] == 'popular' else 'top'}_{'movies' if library.is_movie else 'tv'}"

        items = None
        for entry in response["response"]["data"]:
            if entry["stat_id"] == stat_id:
                items = entry["rows"]
                break
        if items is None:
            raise Failed("Tautulli Error: No Items found in the response")

        section_id = self._section_id(library.name)
        rating_keys = []
        count = 0
        for item in items:
            if item["section_id"] == section_id and count < int(params['list_size']):
                try:
                    library.fetchItem(int(item["rating_key"]))
                    rating_keys.append(item["rating_key"])
                except (BadRequest, NotFound):
                    new_item = library.exact_search(item["title"], year=item["year"])
                    if new_item:
                        rating_keys.append(new_item[0].ratingKey)
                    else:
                        logger.error(f"Plex Error: Item {item} not found")
                        continue
                count += 1
        logger.debug("")
        logger.debug(f"{len(rating_keys)} Keys Found: {rating_keys}")
        return rating_keys

    def _section_id(self, library_name):
        response = self._request(f"{self.url}/api/v2?apikey={self.apikey}&cmd=get_library_names")
        section_id = None
        for entry in response["response"]["data"]:
            if entry["section_name"] == library_name:
                section_id = entry["section_id"]
                break
        if section_id:              return section_id
        else:                       raise Failed(f"Tautulli Error: No Library named {library_name} in the response")

    def _request(self, url):
        logger.debug(f"Tautulli URL: {url.replace(self.apikey, '###############')}")
        return self.config.get_json(url)
