var return_to_top = document.getElementById("return-to-top");
var sonarr_get_shows_button = document.getElementById('sonarr-get-shows-button');
var start_stop_button = document.getElementById('start-stop-button');
var sonarr_status = document.getElementById('sonarr-status');
var sonarr_spinner = document.getElementById('sonarr-spinner');
var sonarr_item_list = document.getElementById("sonarr-item-list");
var sonarr_select_all_checkbox = document.getElementById("sonarr-select-all");
var sonarr_select_all_container = document.getElementById("sonarr-select-all-container");
var config_modal = document.getElementById('config-modal');
var sonarr_sidebar = document.getElementById('sonarr-sidebar');
var save_message = document.getElementById("save-message");
var save_changes_button = document.getElementById("save-changes-button");
const sonarr_address = document.getElementById("sonarr-address");
const sonarr_api_key = document.getElementById("sonarr-api-key");
const root_folder_path = document.getElementById("root-folder-path");
const tvdb_api_key = document.getElementById("tvdb-api-key");
const tmdb_api_key = document.getElementById("tmdb-api-key");
var sonarr_items = [];
var socket = io();

function check_if_all_selected() {
    var checkboxes = document.querySelectorAll('input[name="sonarr-item"]');
    var all_checked = true;
    for (var i = 0; i < checkboxes.length; i++) {
        if (!checkboxes[i].checked) {
            all_checked = false;
            break;
        }
    }
    sonarr_select_all_checkbox.checked = all_checked;
}

function load_sonarr_data(response) {
    var every_check_box = document.querySelectorAll('input[name="sonarr-item"]');
    if (response.Running) {
        start_stop_button.classList.remove('btn-success');
        start_stop_button.classList.add('btn-warning');
        start_stop_button.textContent = "Stop";
        every_check_box.forEach(item => {
            item.disabled = true;
        });
        sonarr_select_all_checkbox.disabled = true;
        sonarr_get_shows_button.disabled = true;
    } else {
        start_stop_button.classList.add('btn-success');
        start_stop_button.classList.remove('btn-warning');
        start_stop_button.textContent = "Start";
        every_check_box.forEach(item => {
            item.disabled = false;
        });
        sonarr_select_all_checkbox.disabled = false;
        sonarr_get_shows_button.disabled = false;
    }
    check_if_all_selected();
}

function append_shows(shows) {
    var show_row = document.getElementById('show-row');
    var template = document.getElementById('show-template');
    shows.forEach(function (show) {
        var clone = document.importNode(template.content, true);
        var show_col = clone.querySelector('#show-column');

        show_col.querySelector('.card-title').textContent = `${show.Name} (${show.Year})`;
        show_col.querySelector('.genre').textContent = show.Genre;
        if (show.Img_Link) {
            show_col.querySelector('.card-img-top').src = show.Img_Link;
            show_col.querySelector('.card-img-top').alt = show.Name;
        } else {
            show_col.querySelector('.show-img-container').removeChild(show_col.querySelector('.card-img-top'));
        }
        show_col.querySelector('.add-to-sonarr-btn').addEventListener('click', function () {
            var add_button = this;
            add_button.disabled = true;
            add_to_sonarr(show.Name, show.Year);
        });
        show_col.querySelector('.get-overview-btn').addEventListener('click', function () {
            overview_req(show);
        });
        show_col.querySelector('.votes').textContent = show.Votes;
        show_col.querySelector('.rating').textContent = show.Rating;

        var add_button = show_col.querySelector('.add-to-sonarr-btn');
        if (show.Status === "Added" || show.Status === "Already in Sonarr") {
            show_col.querySelector('.card-body').classList.add('status-green');
            add_button.classList.remove('btn-primary');
            add_button.classList.add('btn-secondary');
            add_button.disabled = true;
            add_button.textContent = show.Status;
        } else if (show.Status === "Failed to Add" || show.Status === "Invalid Path") {
            show_col.querySelector('.card-body').classList.add('status-red');
            add_button.classList.remove('btn-primary');
            add_button.classList.add('btn-danger');
            add_button.disabled = true;
            add_button.textContent = show.Status;
        } else {
            show_col.querySelector('.card-body').classList.add('status-blue');
        }
        show_row.appendChild(clone);
    });
}

function add_to_sonarr(show_name, show_year) {
    if (socket.connected) {
        socket.emit('adder', [encodeURIComponent(show_name), show_year]);
    }
    else {
        show_toast("Connection Lost", "Please reload to continue.");
    }
}

function show_toast(header, message) {
    var toast_container = document.querySelector('.toast-container');
    var toast_template = document.getElementById('toast-template').cloneNode(true);
    toast_template.classList.remove('d-none');

    toast_template.querySelector('.toast-header strong').textContent = header;
    toast_template.querySelector('.toast-body').textContent = message;
    toast_template.querySelector('.text-muted').textContent = new Date().toLocaleString();

    toast_container.appendChild(toast_template);
    var toast = new bootstrap.Toast(toast_template);
    toast.show();
    toast_template.addEventListener('hidden.bs.toast', function () {
        toast_template.remove();
    });
}

return_to_top.addEventListener("click", function () {
    window.scrollTo({ top: 0, behavior: "smooth" });
});

sonarr_select_all_checkbox.addEventListener("change", function () {
    var is_checked = this.checked;
    var checkboxes = document.querySelectorAll('input[name="sonarr-item"]');
    checkboxes.forEach(function (checkbox) {
        checkbox.checked = is_checked;
    });
});

sonarr_get_shows_button.addEventListener('click', function () {
    sonarr_get_shows_button.disabled = true;
    sonarr_spinner.classList.remove('d-none');
    sonarr_status.textContent = "Accessing Sonarr API";
    sonarr_item_list.innerHTML = '';
    socket.emit("get_sonarr_shows");
});

start_stop_button.addEventListener('click', function () {
    var running_state = start_stop_button.textContent.trim() === "Start" ? true : false;
    if (running_state) {
        start_stop_button.classList.remove('btn-success');
        start_stop_button.classList.add('btn-warning');
        start_stop_button.textContent = "Stop";
        var checked_items = Array.from(document.querySelectorAll('input[name="sonarr-item"]:checked'))
            .map(item => item.value);
        document.querySelectorAll('input[name="sonarr-item"]').forEach(item => {
            item.disabled = true;
        });
        sonarr_get_shows_button.disabled = true;
        sonarr_select_all_checkbox.disabled = true;
        socket.emit("start_req", checked_items);
        if (checked_items.length > 0) {
            show_toast("Loading new shows");
        }
    }
    else {
        start_stop_button.classList.add('btn-success');
        start_stop_button.classList.remove('btn-warning');
        start_stop_button.textContent = "Start";
        document.querySelectorAll('input[name="sonarr-item"]').forEach(item => {
            item.disabled = false;
        });
        sonarr_get_shows_button.disabled = false;
        sonarr_select_all_checkbox.disabled = false;
        socket.emit("stop_req");
    }
});

save_changes_button.addEventListener("click", () => {
    socket.emit("update_settings", {
        "sonarr_address": sonarr_address.value,
        "sonarr_api_key": sonarr_api_key.value,
        "root_folder_path": root_folder_path.value,
        "tvdb_api_key": tvdb_api_key.value,
        "tmdb_api_key": tmdb_api_key.value,
    });
    save_message.style.display = "block";
    setTimeout(function () {
        save_message.style.display = "none";
    }, 1000);
});

config_modal.addEventListener('show.bs.modal', function (event) {
    socket.emit("load_settings");

    function handle_settings_loaded(settings) {
        sonarr_address.value = settings.sonarr_address;
        sonarr_api_key.value = settings.sonarr_api_key;
        root_folder_path.value = settings.root_folder_path;
        tvdb_api_key.value = settings.tvdb_api_key;
        tmdb_api_key.value = settings.tmdb_api_key;
        socket.off("settingsLoaded", handle_settings_loaded);
    }
    socket.on("settingsLoaded", handle_settings_loaded);
});

sonarr_sidebar.addEventListener('show.bs.offcanvas', function (event) {
    socket.emit("side_bar_opened");
});

window.addEventListener('scroll', function () {
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight) {
        socket.emit('load_more_shows');
    }
});

window.addEventListener('touchmove', function () {
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight) {
        socket.emit('load_more_shows');
    }
});

window.addEventListener('touchend', () => {
    const { scrollHeight, scrollTop, clientHeight } = document.documentElement;
    if (Math.abs(scrollHeight - clientHeight - scrollTop) < 1) {
        socket.emit('load_more_shows');
    }
});

socket.on("sonarr_sidebar_update", (response) => {
    if (response.Status == "Success") {
        sonarr_status.textContent = "Sonarr List Retrieved";
        sonarr_items = response.Data;
        sonarr_item_list.innerHTML = '';
        sonarr_select_all_container.classList.remove('d-none');

        for (var i = 0; i < sonarr_items.length; i++) {
            var item = sonarr_items[i];

            var div = document.createElement("div");
            div.className = "form-check";

            var input = document.createElement("input");
            input.type = "checkbox";
            input.className = "form-check-input";
            input.id = "sonarr-" + i;
            input.name = "sonarr-item";
            input.value = item.name;

            if (item.checked) {
                input.checked = true;
            }

            var label = document.createElement("label");
            label.className = "form-check-label";
            label.htmlFor = "sonarr-" + i;
            label.textContent = item.name;

            input.addEventListener("change", function () {
                check_if_all_selected();
            });

            div.appendChild(input);
            div.appendChild(label);

            sonarr_item_list.appendChild(div);
        }
    }
    else {
        sonarr_status.textContent = response.Code;
    }
    sonarr_get_shows_button.disabled = false;
    sonarr_spinner.classList.add('d-none');
    load_sonarr_data(response);
});

socket.on("refresh_show", (show) => {
    var show_cards = document.querySelectorAll('#show-column');
    show_cards.forEach(function (card) {
        var card_body = card.querySelector('.card-body');
        var card_show_name = card_body.querySelector('.card-title').textContent.trim();
        card_show_name = card_show_name.replace(/\s*\(\d{4}\)$/, "");
        if (card_show_name === show.Name) {
            card_body.classList.remove('status-green', 'status-red', 'status-blue');

            var add_button = card_body.querySelector('.add-to-sonarr-btn');

            if (show.Status === "Added" || show.Status === "Already in Sonarr") {
                card_body.classList.add('status-green');
                add_button.classList.remove('btn-primary');
                add_button.classList.add('btn-secondary');
                add_button.disabled = true;
                add_button.textContent = show.Status;
            } else if (show.Status === "Failed to Add" || show.Status === "Invalid Path" || show.Status === "Invalid Series ID") {
                card_body.classList.add('status-red');
                add_button.classList.remove('btn-primary');
                add_button.classList.add('btn-danger');
                add_button.disabled = true;
                add_button.textContent = show.Status;
            } else {
                card_body.classList.add('status-blue');
                add_button.disabled = false;
            }
            return;
        }
    });
});

socket.on('more_shows_loaded', function (data) {
    append_shows(data);
});

socket.on('clear', function () {
    clear_all();
});

socket.on("new_toast_msg", function (data) {
    show_toast(data.title, data.message);
});

socket.on("disconnect", function () {
    show_toast("Connection Lost", "Please refresh to continue.");
    clear_all();
});

function clear_all() {
    var show_row = document.getElementById('show-row');
    var show_cards = show_row.querySelectorAll('#show-column');
    show_cards.forEach(function (card) {
        card.remove();
    });
}

let overview_request_flag = false;
function overview_req(show) {
    if (!overview_request_flag) {
        overview_request_flag = true;
        show_overview_modal(show);
        setTimeout(() => {
            overview_request_flag = false;
        }, 1500);
    }
}

function show_overview_modal(show) {
    const scrollbar_width = window.innerWidth - document.documentElement.clientWidth;
    document.body.style.overflow = 'hidden';
    document.body.style.paddingRight = `${scrollbar_width}px`;

    var modal_title = document.getElementById('overview-modal-title');
    var modal_body = document.getElementById('modal-body');

    modal_title.textContent = show.Name;
    modal_body.innerHTML = `${show.Overview}<br><br>Language: ${show.Language}<br>Popularity: ${show.Popularity}<br><br>Comparable to: ${show.Base_Show}`;

    var overview_modal = new bootstrap.Modal(document.getElementById('overview-modal'));
    overview_modal.show();

    overview_modal._element.addEventListener('hidden.bs.modal', function () {
        document.body.style.overflow = 'auto';
        document.body.style.paddingRight = '0';
    });
}

const theme_switch = document.getElementById('theme-switch');
const saved_theme = localStorage.getItem('theme');
const saved_switch_position = localStorage.getItem('switch-position');

if (saved_switch_position) {
    theme_switch.checked = saved_switch_position === 'true';
}

if (saved_theme) {
    document.documentElement.setAttribute('data-bs-theme', saved_theme);
}

theme_switch.addEventListener('click', () => {
    if (document.documentElement.getAttribute('data-bs-theme') === 'dark') {
        document.documentElement.setAttribute('data-bs-theme', 'light');
    } else {
        document.documentElement.setAttribute('data-bs-theme', 'dark');
    }
    localStorage.setItem('theme', document.documentElement.getAttribute('data-bs-theme'));
    localStorage.setItem('switch_position', theme_switch.checked);
});
