![Build Status](https://github.com/TheWicklowWolf/RadaRec/actions/workflows/main.yml/badge.svg)
![Docker Pulls](https://img.shields.io/docker/pulls/thewicklowwolf/radarec.svg)



<img src="/src/static/radarec.png" alt="image">


Web GUI for finding similar movies to selected Radarr movies.


## Run using docker-compose

```yaml
services:
  radarec:
    image: thewicklowwolf/radarec:latest
    container_name: radarec
    volumes:
      - /path/to/config:/radarec/config
      - /etc/localtime:/etc/localtime:ro
    ports:
      - 5000:5000
    restart: unless-stopped
```

## Configuration via environment variables

Certain values can be set via environment variables:

* __PUID__: The user ID to run the app with. Defaults to `1000`. 
* __PGID__: The group ID to run the app with. Defaults to `1000`.
* __radarr_address__: The URL for Radarr. Defaults to `http://192.168.1.2:8686`.
* __radarr_api_key__: The API key for Radarr. Defaults to ``.
* __root_folder_path__: The root folder path for Movies. Defaults to `/data/media/movies/`.
* __tmdb_api_key__: The API key for TMDB. Defaults to ``.
* __fallback_to_top_result__: Whether to use the top result if no match is found. Defaults to `False`.
* __radarr_api_timeout__: Timeout duration for Radarr API calls. Defaults to `120`.
* __quality_profile_id__: Quality profile ID in Radarr. Defaults to `1`.
* __metadata_profile_id__: Metadata profile ID in Radarr. Defaults to `1`
* __search_for_movie__: Whether to start searching for movie when adding. Defaults to `False`
* __dry_run_adding_to_radarr__: Whether to run without adding artists in Radarr. Defaults to `False`
* __minimum_rating__: Minimum Movie Rating. Defaults to `5.5`.
* __minimum_votes__: Minimum Vote Count. Defaults to `50`.
* __language_choice__: Chosen Language in ISO-639 two letter format. Defaults to `all`.
* __auto_start__: Whether to run automatically at startup. Defaults to `False`.
* __auto_start_delay__: Delay duration for Auto Start in Seconds (if enabled). Defaults to `60`.

---


<img src="/src/static/light.png" alt="image">



<img src="/src/static/dark.png" alt="image">

---

https://hub.docker.com/r/thewicklowwolf/radarec
