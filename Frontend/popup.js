const default_settings = {
    threshold: 0.5,
    server_url: "http://127.0.0.1:4352/",
    wait_seconds: 2,
    non_block_sites: [],
    settings_version: 3
};

const controls = { // Incredibly shitty way of doing this but it works I guess.
    threshold: document.getElementById("threshold"),
    threshold_value: document.getElementById("threshold_value"),
    server_url: document.getElementById("server_url"),
    wait_seconds: document.getElementById("wait_seconds"),
    non_block_sites: document.getElementById("non_block_sites"),
    status: document.getElementById("status"),
    main_view: document.getElementById("main_view"),
    settings_view: document.getElementById("settings_view")
};

let save_timer = null;

function show_settings(show) {
    controls.main_view.hidden = show;
    controls.settings_view.hidden = !show;
}

function update_threshold_label() {
    controls.threshold_value.value = Number(controls.threshold.value).toFixed(2); // 2 Decimal places for the threshold value label so it doesnt go to like 0.300000000004 cause floating point math sucks *ss.
}

async function apply_threshold_to_active_tab(value) {
    const [active_tab] = await browser.tabs.query({ active: true, currentWindow: true });
    if (!active_tab?.id) return;

    try { // https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/tabs/sendMessage
        await browser.tabs.sendMessage(active_tab.id, { type: "set-threshold", threshold: value });
    } catch {
        // Idk why this crashes but it happens but it only crashes on like non-important sites so just ignore it.
    }
}

function parse_excluded_sites(text) { // basically just removes https and stuff so we can block sites.
    return [...new Set(text.split(/[\r\n,]+/)
        .map((site) => site.trim().toLowerCase().replace(/^https?:\/\//, "").replace(/\/$/, ""))
        .filter(Boolean))];
}

function read_server_url() {
    let server_url;
    try {
        server_url = new URL(controls.server_url.value);
    } catch {
        throw new Error("Enter a valid server URL, including http:// or https://.");
    }
    if (!["http:", "https:"].includes(server_url.protocol)) {
        throw new Error("The server URL must use HTTP or HTTPS.");
    }
    return server_url.href;
}

async function save_settings() {
    const wait_seconds = Number(controls.wait_seconds.value);
    if (!Number.isFinite(wait_seconds) || wait_seconds < 0 || wait_seconds > 30) {
        throw new Error("Wait time must be between 0 and 30 seconds.");
    }

    await browser.storage.local.set({
        threshold: Number(controls.threshold.value),
        server_url: read_server_url(),
        wait_seconds,
        non_block_sites: parse_excluded_sites(controls.non_block_sites.value),
        settings_version: default_settings.settings_version
    });
    controls.status.textContent = "Saved. Reload open pages to apply these settings.";
}

function schedule_settings_save() { // Save a bit after user stops typing instead of at back button cause I've quit out of the menu like 500 times without the back button and it got annoying.
    clearTimeout(save_timer);
    save_timer = setTimeout(() => {
        save_settings().catch((error) => {
            controls.status.textContent = error.message;
        });
    }, 250);
}

async function load_settings() {

    const saved = await browser.storage.local.get(null);
    const settings = {
        threshold: saved.threshold ?? default_settings.threshold,
        server_url: saved.server_url ?? default_settings.server_url,
        wait_seconds: saved.wait_seconds ?? default_settings.wait_seconds,
        non_block_sites: saved.non_block_sites ?? default_settings.non_block_sites,
        settings_version: saved.settings_version ?? default_settings.settings_version
    };

    controls.threshold.value = settings.threshold;
    controls.server_url.value = settings.server_url;
    controls.wait_seconds.value = settings.wait_seconds;
    controls.non_block_sites.value = settings.non_block_sites.join("\n");
    update_threshold_label();
    await apply_threshold_to_active_tab(Number(settings.threshold));
}

document.getElementById("show_settings").addEventListener("click", () => show_settings(true)); // Once again, incredible code quality here.
document.getElementById("back_button").addEventListener("click", () => show_settings(false));


controls.threshold.addEventListener("input", () => {
    const value = Number(controls.threshold.value);
    update_threshold_label();
    browser.storage.local.set({ threshold: value });
    apply_threshold_to_active_tab(value);
});
controls.server_url.addEventListener("change", schedule_settings_save);
controls.wait_seconds.addEventListener("change", schedule_settings_save);
controls.non_block_sites.addEventListener("change", schedule_settings_save);

load_settings().catch((error) => {
    controls.status.textContent = `Could not load settings: ${error.message}`;
});
