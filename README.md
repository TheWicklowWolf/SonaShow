![Build Status](https://github.com/TheWicklowWolf/SonaShow/actions/workflows/main.yml/badge.svg)
![Docker Pulls](https://img.shields.io/docker/pulls/thewicklowwolf/sonashow.svg)



<img src="/src/static/sonashow.png" alt="image">


Web GUI for finding similar shows to selected Sonarr shows.


## Run using docker-compose

```yaml
services:
  sonashow:
    image: thewicklowwolf/sonashow:latest
    container_name: sonashow
    volumes:
      - /path/to/config:/sonashow/config
      - /etc/localtime:/etc/localtime:ro
    ports:
      - 5000:5000
    restart: unless-stopped
```

## Configuration via environment variables

Certain values can be set via environment variables:

* __sonarr_address__: The URL for Sonarr. Defaults to `http://192.168.1.2:8686`.
* __sonarr_api_key__: The API key for Sonarr. Defaults to ``.
* __root_folder_path__: The root folder path for TV Shows. Defaults to `/data/media/shows/`.
* __tvdb_api_key__: The API key for TVDB. Defaults to ``.
* __tmdb_api_key__: The API key for TMDB. Defaults to ``.
* __fallback_to_top_result__: Whether to use the top result if no match is found. Defaults to `False`.
* __sonarr_api_timeout__: Timeout duration for Sonarr API calls. Defaults to `120`.
* __quality_profile_id__: Quality profile ID in Sonarr. Defaults to `1`.
* __metadata_profile_id__: Metadata profile ID in Sonarr. Defaults to `1`
* __search_for_missing_episodes__: Whether to start searching for missing episodes when adding shows. Defaults to `False`
* __dry_run_adding_to_sonarr__: Whether to run without adding artists in Sonarr. Defaults to `False`
* __minimum_rating__: Minimum Show Rating. Defaults to `5.5`.
* __minimum_votes__: Minimum Vote Count. Defaults to `50`.
* __language_choice__: Chosen Language in ISO-639 two letter format. Defaults to `all`.

---


<img src="/src/static/light.png" alt="image">



<img src="/src/static/dark.png" alt="image">

---

https://hub.docker.com/r/thewicklowwolf/sonashow
