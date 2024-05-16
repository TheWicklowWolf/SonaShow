import json
import time
import logging
import os
import random
import threading
import urllib.parse
from flask import Flask, render_template
from flask_socketio import SocketIO
import requests
from thefuzz import fuzz
from unidecode import unidecode
import re
from iso639 import Lang


class DataHandler:
    def __init__(self):
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        self.sonashow_logger = logging.getLogger()
        self.search_in_progress_flag = False
        self.new_found_shows_counter = 0
        self.clients_connected_counter = 0
        self.config_folder = "config"
        self.similar_shows = []
        self.sonarr_items = []
        self.cleaned_sonarr_items = []
        self.stop_event = threading.Event()
        self.stop_event.set()
        if not os.path.exists(self.config_folder):
            os.makedirs(self.config_folder)
        self.load_environ_or_config_settings()

    def load_environ_or_config_settings(self):
        # Defaults
        default_settings = {
            "sonarr_address": "http://192.168.1.2:8989",
            "sonarr_api_key": "",
            "root_folder_path": "/data/media/shows/",
            "tvdb_api_key": "",
            "tmdb_api_key": "",
            "fallback_to_top_result": False,
            "sonarr_api_timeout": 120.0,
            "quality_profile_id": 1,
            "metadata_profile_id": 1,
            "search_for_missing_episodes": False,
            "dry_run_adding_to_sonarr": False,
            "minimum_rating": 5.5,
            "minimum_votes": 50,
            "language_choice": "all",
        }

        # Load settings from environmental variables (which take precedence) over the configuration file.
        self.sonarr_address = os.environ.get("sonarr_address", "")
        self.sonarr_api_key = os.environ.get("sonarr_api_key", "")
        self.root_folder_path = os.environ.get("root_folder_path", "")
        self.tvdb_api_key = os.environ.get("tvdb_api_key", "")
        self.tmdb_api_key = os.environ.get("tmdb_api_key", "")
        fallback_to_top_result = os.environ.get("fallback_to_top_result", "")
        self.fallback_to_top_result = fallback_to_top_result.lower() == "true" if fallback_to_top_result != "" else ""
        sonarr_api_timeout = os.environ.get("sonarr_api_timeout", "")
        self.sonarr_api_timeout = float(sonarr_api_timeout) if sonarr_api_timeout else ""
        quality_profile_id = os.environ.get("quality_profile_id", "")
        self.quality_profile_id = int(quality_profile_id) if quality_profile_id else ""
        metadata_profile_id = os.environ.get("metadata_profile_id", "")
        self.metadata_profile_id = int(metadata_profile_id) if metadata_profile_id else ""
        search_for_missing_episodes = os.environ.get("search_for_missing_episodes", "")
        self.search_for_missing_episodes = search_for_missing_episodes.lower() == "true" if search_for_missing_episodes != "" else ""
        dry_run_adding_to_sonarr = os.environ.get("dry_run_adding_to_sonarr", "")
        self.dry_run_adding_to_sonarr = dry_run_adding_to_sonarr.lower() == "true" if dry_run_adding_to_sonarr != "" else ""
        minimum_rating = os.environ.get("minimum_rating", "")
        self.minimum_rating = float(minimum_rating) if minimum_rating else ""
        minimum_votes = os.environ.get("minimum_votes", "")
        self.minimum_votes = int(minimum_votes) if minimum_votes else ""
        self.language_choice = os.environ.get("language_choice", "")

        # Load variables from the configuration file if not set by environmental variables.
        try:
            self.settings_config_file = os.path.join(self.config_folder, "settings_config.json")
            if os.path.exists(self.settings_config_file):
                self.sonashow_logger.info(f"Loading Config via file")
                with open(self.settings_config_file, "r") as json_file:
                    ret = json.load(json_file)
                    for key in ret:
                        if getattr(self, key) == "":
                            setattr(self, key, ret[key])
        except Exception as e:
            self.sonashow_logger.error(f"Error Loading Config: {str(e)}")

        # Load defaults if not set by an environmental variable or configuration file.
        for key, value in default_settings.items():
            if getattr(self, key) == "":
                setattr(self, key, value)

        # Save config.
        self.save_config_to_file()

    def connection(self):
        if self.similar_shows:
            if self.clients_connected_counter == 0:
                if len(self.similar_shows) > 15:
                    self.similar_shows = random.sample(self.similar_shows, 15)
                else:
                    self.sonashow_logger.info(f"Shuffling Shows")
                    random.shuffle(self.similar_shows)
                self.raw_new_shows = []
            socketio.emit("more_shows_loaded", self.similar_shows)

        self.clients_connected_counter += 1

    def disconnection(self):
        self.clients_connected_counter = max(0, self.clients_connected_counter - 1)

    def start(self, data):
        try:
            socketio.emit("clear")
            self.new_found_shows_counter = 1
            self.raw_new_shows = []
            self.shows_to_use_in_search = []
            self.similar_shows = []

            for item in self.sonarr_items:
                item_name = item["name"]
                if item_name in data:
                    item["checked"] = True
                    self.shows_to_use_in_search.append(item_name)
                else:
                    item["checked"] = False

            if self.shows_to_use_in_search:
                self.stop_event.clear()
            else:
                self.stop_event.set()
                raise Exception("No Sonarr Shows Selected")

        except Exception as e:
            self.sonashow_logger.error(f"Startup Error: {str(e)}")
            self.stop_event.set()
            ret = {"Status": "Error", "Code": str(e), "Data": self.sonarr_items, "Running": not self.stop_event.is_set()}
            socketio.emit("sonarr_sidebar_update", ret)

        else:
            thread = threading.Thread(target=data_handler.find_similar_shows, name="Start_Finding_Thread")
            thread.daemon = True
            thread.start()

    def request_shows_from_sonarr(self):
        try:
            self.sonashow_logger.info(f"Getting Shows from Sonarr")
            self.sonarr_items = []
            endpoint = f"{self.sonarr_address}/api/v3/series"
            headers = {"X-Api-Key": self.sonarr_api_key}
            response = requests.get(endpoint, headers=headers, timeout=self.sonarr_api_timeout)

            if response.status_code == 200:
                self.full_sonarr_show_list = response.json()
                self.sonarr_items = [{"name": re.sub(r" \(\d{4}\)", "", unidecode(show["title"], replace_str=" ")), "checked": False} for show in self.full_sonarr_show_list]
                self.sonarr_items.sort(key=lambda x: x["name"].lower())
                self.cleaned_sonarr_items = [item["name"].lower() for item in self.sonarr_items]
                status = "Success"
                data = self.sonarr_items
            else:
                status = "Error"
                data = response.text

            ret = {"Status": status, "Code": response.status_code if status == "Error" else None, "Data": data, "Running": not self.stop_event.is_set()}

        except Exception as e:
            self.sonashow_logger.error(f"Getting Show Error: {str(e)}")
            ret = {"Status": "Error", "Code": 500, "Data": str(e), "Running": not self.stop_event.is_set()}

        finally:
            socketio.emit("sonarr_sidebar_update", ret)

    def request_show_id(self, show_name):
        url = f"https://api.themoviedb.org/3/search/tv"
        params = {"api_key": self.tmdb_api_key, "query": show_name}
        response = requests.get(url, params=params)
        data = response.json()
        if data:
            return data["results"][0]["id"]
        else:
            return None

    def request_similar_tv_shows(self, tv_show_id):
        url = f"https://api.themoviedb.org/3/tv/{tv_show_id}/recommendations"
        params = {"api_key": self.tmdb_api_key}
        response = requests.get(url, params=params)
        data = response.json()
        ret_list = []

        for show in data["results"]:
            if show.get("vote_average", 0) >= self.minimum_rating and show.get("vote_count", 0) >= self.minimum_votes:
                if show.get("original_language", "en") == self.language_choice or self.language_choice == "all":
                    ret_list.append(show)

        return ret_list

    def map_genre_ids_to_names(self, genre_ids):
        genre_mapping = {
            10759: "Action & Adventure",
            16: "Animation",
            35: "Comedy",
            80: "Crime",
            99: "Documentary",
            18: "Drama",
            10751: "Family",
            10762: "Kids",
            9648: "Mystery",
            10763: "News",
            10764: "Reality",
            10765: "Sci-Fi & Fantasy",
            10766: "Soap",
            10767: "Talk",
            10768: "War & Politics",
            37: "Western",
        }
        return [genre_mapping.get(genre_id, "Unknown") for genre_id in genre_ids]

    def find_similar_shows(self):
        if self.stop_event.is_set() or self.search_in_progress_flag:
            return
        elif self.new_found_shows_counter > 0:
            try:
                self.sonashow_logger.info(f"Searching for new shows")
                self.new_found_shows_counter = 0
                self.search_in_progress_flag = True
                random_shows = random.sample(self.shows_to_use_in_search, min(5, len(self.shows_to_use_in_search)))

                for show_name in random_shows:
                    if self.stop_event.is_set():
                        break
                    tv_show_id = self.request_show_id(show_name)
                    related_shows = self.request_similar_tv_shows(tv_show_id)
                    for show in related_shows:
                        if self.stop_event.is_set():
                            break
                        cleaned_show = unidecode(show["name"]).lower()
                        if cleaned_show not in self.cleaned_sonarr_items and not any(show["name"] == item["Name"] for item in self.raw_new_shows):
                            genres = ", ".join(self.map_genre_ids_to_names(show.get("genre_ids", [])))
                            overview = show.get("overview", "")
                            popularity = show.get("popularity", "")
                            original_language_code = show.get("original_language", "en")
                            original_language = Lang(original_language_code)
                            vote_count = show.get("vote_count", 0)
                            vote_avg = show.get("vote_average", 0)
                            img_link = show.get("poster_path", "")
                            date_string = show.get("first_air_date", "0000-01-01")
                            year = date_string.split("-")[0]
                            if img_link:
                                img_url = f"https://image.tmdb.org/t/p/original/{img_link}"
                            else:
                                img_url = "https://via.placeholder.com/300x200"

                            exclusive_show = {
                                "Name": show["name"],
                                "Year": year if year else "0000",
                                "Genre": genres,
                                "Status": "",
                                "Img_Link": img_url,
                                "Votes": f"Votes: {vote_count}",
                                "Rating": f"Rating: {vote_avg}",
                                "Overview": overview,
                                "Language": original_language.name,
                                "Popularity": popularity,
                                "Base_Show": show_name,
                            }
                            self.raw_new_shows.append(exclusive_show)
                            socketio.emit("more_shows_loaded", [exclusive_show])
                            self.new_found_shows_counter += 1

                if self.new_found_shows_counter == 0:
                    self.sonashow_logger.info("Search Exhausted - Try selecting more shows from existing Sonarr library")
                    socketio.emit("new_toast_msg", {"title": "Search Exhausted", "message": "Try selecting more shows from existing Sonarr library"})
                else:
                    self.similar_shows.extend(self.raw_new_shows)

            except Exception as e:
                self.sonashow_logger.error(f"TheMovieDB Error: {str(e)}")

            finally:
                self.search_in_progress_flag = False

        elif self.new_found_shows_counter == 0:
            try:
                self.search_in_progress_flag = True
                self.sonashow_logger.info("Search Exhausted - Try selecting more shows from existing Sonarr library")
                socketio.emit("new_toast_msg", {"title": "Search Exhausted", "message": "Try selecting more shows from existing Sonarr library"})
                time.sleep(2)

            except Exception as e:
                self.sonashow_logger.error(f"Search Exhausted Error: {str(e)}")

            finally:
                self.search_in_progress_flag = False

    def add_shows(self, data):
        try:
            raw_show_name, show_year = data
            show_name = urllib.parse.unquote(raw_show_name)
            show_folder = show_name.replace("/", " ")
            tvdb_id = self.request_tvdb_id(show_name, show_year)
            if tvdb_id:
                sonarr_url = f"{self.sonarr_address}/api/v3/series"
                headers = {"X-Api-Key": self.sonarr_api_key}
                payload = {
                    "title": show_name,
                    "qualityProfileId": self.quality_profile_id,
                    "metadataProfileId": self.metadata_profile_id,
                    "titleSlug": show_name.lower().replace(" ", "-"),
                    "rootFolderPath": self.root_folder_path,
                    "tvdbId": tvdb_id,
                    "seasonFolder": True,
                    "monitored": True,
                    "addOptions": {
                        "monitor": "all",
                        "searchForMissingEpisodes": self.search_for_missing_episodes,
                    },
                }
                if self.dry_run_adding_to_sonarr:
                    response = requests.Response()
                    response.status_code = 201
                else:
                    response = requests.post(sonarr_url, headers=headers, json=payload)

                if response.status_code == 201:
                    self.sonashow_logger.info(f"Show '{show_name}' added successfully to Sonarr.")
                    status = "Added"
                    self.sonarr_items.append({"name": show_name, "checked": False})
                    self.cleaned_sonarr_items.append(unidecode(show_name).lower())
                else:
                    self.sonashow_logger.error(f"Failed to add show '{show_name}' to Sonarr.")
                    error_data = json.loads(response.content)
                    error_message = error_data[0].get("errorMessage", "Unknown Error")
                    self.sonashow_logger.error(error_message)
                    if "already exists in the database" in error_message:
                        status = "Already in Sonarr"
                        self.sonashow_logger.info(f"Show '{show_name}' is already in Sonarr.")
                    elif "configured for an existing show" in error_message:
                        status = "Already in Sonarr"
                        self.sonashow_logger.info(f"'{show_folder}' folder already configured for an existing show.")
                    elif "Invalid Path" in error_message:
                        status = "Invalid Path"
                        self.sonashow_logger.info(f"Path: {os.path.join(self.root_folder_path, show_folder, '')} not valid.")
                    elif "series with this ID was not found" in error_message:
                        status = "Invalid Series ID"
                        self.sonashow_logger.info(f"ID: {tvdb_id} for '{show_folder}' not correct")
                    else:
                        status = "Failed to Add"

            else:
                status = "Failed to Add"
                self.sonashow_logger.info(f"No Matching Show for: '{show_name}' in The Movie Database.")
                socketio.emit("new_toast_msg", {"title": "Failed to add Show", "message": f"No Matching Show for: '{show_name}' in The Movie Database."})

            for item in self.similar_shows:
                if item["Name"] == show_name:
                    item["Status"] = status
                    socketio.emit("refresh_show", item)
                    break

        except Exception as e:
            self.sonashow_logger.error(f"Adding Show Error: {str(e)}")

    def request_bearer_token(self):
        login_url = "https://api4.thetvdb.com/v4/login"
        headers = {"Content-Type": "application/json"}
        login_data = {"apikey": self.tvdb_api_key}
        response = requests.post(login_url, headers=headers, json=login_data)
        response.raise_for_status()
        token = response.json()["data"]["token"]
        return token

    def request_tvdb_id(self, show_name, show_year):
        tvdb_id = None
        cleaned_show_name = urllib.parse.quote_plus(show_name)
        tvdb_url = f"https://api4.thetvdb.com/v4/search?query={cleaned_show_name}"
        bearer_token = self.request_bearer_token()
        headers = {"Authorization": f"Bearer {bearer_token}"}
        response = requests.get(tvdb_url, headers=headers)
        response.raise_for_status()
        if response.status_code == 200:
            tvdb_data = response.json()
            if "data" in tvdb_data:
                shows = tvdb_data["data"]
                for show in shows:
                    match_ratio = fuzz.ratio(f"{show_name.lower()} ({show_year})", show["name"].lower())
                    decoded_match_ratio = fuzz.ratio(unidecode(show_name.lower()), unidecode(show["name"].lower()))
                    if match_ratio > 90 or decoded_match_ratio > 90 and show_year == show["year"]:
                        tvdb_id = show["tvdb_id"]
                        self.sonashow_logger.info(f"Show '{show_name}' matched '{show['name']}' with TVDB_ID: {tvdb_id}  Match Ratio: {max(match_ratio, decoded_match_ratio)}")
                        break
                else:
                    if self.fallback_to_top_result and shows:
                        top_match_ratio = fuzz.ratio(show_name.lower(), shows[0]["name"].lower())
                        top_decoded_match_ratio = fuzz.ratio(unidecode(show_name.lower()), unidecode(shows[0]["name"].lower()))
                        tvdb_id = shows[0]["tvdb_id"]
                        self.sonashow_logger.info(f"Show '{show_name}' matched '{shows[0]['name']}' with TVDB_ID: {tvdb_id}  Match Ratio: {max(top_match_ratio, top_decoded_match_ratio)}")

        return tvdb_id

    def load_settings(self):
        try:
            data = {
                "sonarr_address": self.sonarr_address,
                "sonarr_api_key": self.sonarr_api_key,
                "root_folder_path": self.root_folder_path,
                "tvdb_api_key": self.tvdb_api_key,
                "tmdb_api_key": self.tmdb_api_key,
            }
            socketio.emit("settingsLoaded", data)
        except Exception as e:
            self.sonashow_logger.error(f"Failed to load settings: {str(e)}")

    def update_settings(self, data):
        try:
            self.sonarr_address = data["sonarr_address"]
            self.sonarr_api_key = data["sonarr_api_key"]
            self.root_folder_path = data["root_folder_path"]
            self.tvdb_api_key = data["tvdb_api_key"]
            self.tmdb_api_key = data["tmdb_api_key"]
        except Exception as e:
            self.sonashow_logger.error(f"Failed to update settings: {str(e)}")

    def save_config_to_file(self):
        try:
            with open(self.settings_config_file, "w") as json_file:
                json.dump(
                    {
                        "sonarr_address": self.sonarr_address,
                        "sonarr_api_key": self.sonarr_api_key,
                        "root_folder_path": self.root_folder_path,
                        "tvdb_api_key": self.tvdb_api_key,
                        "tmdb_api_key": self.tmdb_api_key,
                        "fallback_to_top_result": self.fallback_to_top_result,
                        "sonarr_api_timeout": float(self.sonarr_api_timeout),
                        "quality_profile_id": self.quality_profile_id,
                        "metadata_profile_id": self.metadata_profile_id,
                        "search_for_missing_episodes": self.search_for_missing_episodes,
                        "dry_run_adding_to_sonarr": self.dry_run_adding_to_sonarr,
                        "minimum_rating": self.minimum_rating,
                        "minimum_votes": self.minimum_votes,
                        "language_choice": self.language_choice,
                    },
                    json_file,
                    indent=4,
                )

        except Exception as e:
            self.sonashow_logger.error(f"Error Saving Config: {str(e)}")


app = Flask(__name__)
app.secret_key = "secret_key"
socketio = SocketIO(app)
data_handler = DataHandler()


@app.route("/")
def home():
    return render_template("base.html")


@socketio.on("side_bar_opened")
def side_bar_opened():
    if data_handler.sonarr_items:
        ret = {"Status": "Success", "Data": data_handler.sonarr_items, "Running": not data_handler.stop_event.is_set()}
        socketio.emit("sonarr_sidebar_update", ret)


@socketio.on("get_sonarr_shows")
def get_sonarr_shows():
    thread = threading.Thread(target=data_handler.request_shows_from_sonarr, name="Sonarr_Thread")
    thread.daemon = True
    thread.start()


@socketio.on("adder")
def add_shows(data):
    thread = threading.Thread(target=data_handler.add_shows, args=(data,), name="Add_Shows_Thread")
    thread.daemon = True
    thread.start()


@socketio.on("connect")
def connection():
    data_handler.connection()


@socketio.on("disconnect")
def disconnection():
    data_handler.disconnection()


@socketio.on("load_settings")
def load_settings():
    data_handler.load_settings()


@socketio.on("update_settings")
def update_settings(data):
    data_handler.update_settings(data)
    data_handler.save_config_to_file()


@socketio.on("start_req")
def starter(data):
    data_handler.start(data)


@socketio.on("stop_req")
def stopper():
    data_handler.stop_event.set()


@socketio.on("load_more_shows")
def load_more_shows():
    thread = threading.Thread(target=data_handler.find_similar_shows, name="Find_Similar")
    thread.daemon = True
    thread.start()


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
