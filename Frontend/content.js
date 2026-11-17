(() => {
    const default_settings = {
        threshold: 0.5,
        server_url: "http://127.0.0.1:4352/",
        wait_seconds: 2,
        non_block_sites: ["127.0.0.1", "localhost"],
        settings_version: 3
    };

    const ignored_tags = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE", "SVG", "CANVAS", "TEXTAREA", "INPUT", "OPTION", "SELECT", "BUTTON", "IFRAME", "OBJECT", "EMBED", "VIDEO", "AUDIO", "MATH", "IMG", "PICTURE", "SOURCE", "TRACK", "MAP", "AREA", "BR", "HR", "LINK", "META", "HEAD", "TITLE", "BASE", "COL", "COLGROUP", "FRAMESET", "FRAME", "NOFRAMES", "PARAM", "WBR", "DETAILS", "SUMMARY", "MARK", "TIME", "PROGRESS", "METER", "DATALIST", "KEYGEN", "OUTPUT"]);
    const block_tags = new Set(["P", "LI", "BLOCKQUOTE", "H1", "H2", "H3", "H4", "H5", "H6"]);

    const scores = new Map();
    const original_display = new WeakMap();
    const pending_spans = new Set();
    const slow_requests = new Set();
    const active_requests = new Set();
    let hidden_elements = new Set();
    let settings;
    let threshold = default_settings.threshold;
    let warning_acknowledged = false;
    let gate;
    let gate_message;
    let document_ready = document.readyState !== "loading";
    let initial_scan_done = false;

    // The stylesheet hides glyphs while preserving page layout and images.
    document.addEventListener("DOMContentLoaded", () => { // This is great because it will also run on new content added into a page.
        document_ready = true;
        maybe_release_gate();
    }, { once: true });

    async function load_settings() {
        const saved = await browser.storage.local.get(null);
        const values = {
            threshold: saved.threshold ?? default_settings.threshold,
            server_url: saved.server_url ?? saved.serverUrl ?? default_settings.server_url,
            wait_seconds: saved.wait_seconds ?? default_settings.wait_seconds,
            non_block_sites: saved.non_block_sites ?? default_settings.non_block_sites,
            settings_version: saved.settings_version ?? default_settings.settings_version
        };

        return values;
    }

    function set_gate_message(message) {
        if (!document.documentElement) {
            if (document.readyState === "loading") {
                document.addEventListener("DOMContentLoaded", () => set_gate_message(message), { once: true });
            }
            return;
        }

        if (!gate) {
            gate = document.createElement("div");
            gate.dataset.textFilterGate = "";
            gate.style.cssText = [ // CSS was written in normal file and re-formatted using GenAI
                "all:initial!important", "position:fixed!important", "inset:0!important",
                "z-index:2147483647!important", "display:grid!important", "place-items:center!important",
                "background:rgb(0 0 0 / 55%)!important", "color:#202124!important", "visibility:visible!important"
            ].join(";");
            const shadow = gate.attachShadow({ mode: "open" });
            shadow.innerHTML = `
                <style>
                    main {
                        width: min(420px, calc(100vw - 40px)); box-sizing: border-box; padding: 22px;
                        border: 1px solid #d8dee8; border-radius: 12px; background: #fff;
                        color: #202124; box-shadow: 0 8px 36px #0002; font: 15px/1.5 system-ui, sans-serif;
                    }
                    p { margin: 0 0 16px; }
                    button { padding: 8px 12px; border: 0; border-radius: 6px; background: #245bd6;
                        color: #fff; font: inherit; cursor: pointer; }
                </style>
                <main role="status" aria-live="polite"><p></p><button type="button">Show page anyway</button></main>`;
            gate_message = shadow.querySelector("p");
            shadow.querySelector("button").addEventListener("click", acknowledge_gate);
            document.documentElement.append(gate);
        }
        gate_message.textContent = message;
    }

    function acknowledge_gate() {
        // Late results will still hide text but user will see page even with warning.
        warning_acknowledged = true;
        for (const request of active_requests) request.acknowledged = true;
        slow_requests.clear();
        reveal_pending_text();
        release_gate();
    }

    function release_gate() {
        if (document.documentElement) document.documentElement.dataset.textFilterReady = "";
        if (gate) {
            gate.remove();
        }
        gate = null;
    }

    function maybe_release_gate() {
        // The initial page is released only when parsing and scoring have both finished.
        if (document_ready && initial_scan_done && slow_requests.size === 0) release_gate();
    }

    function is_excluded_site() {
        const hostname = location.hostname.toLowerCase();
        return settings.non_block_sites.some((site) => hostname === site || hostname.endsWith(`.${site}`));
    }

    function should_ignore(node) {
        const parent = node.parentElement;
        if (!parent || parent.closest("[data-text-filter-wrapper]")) return true;
        if (!node.nodeValue || !node.nodeValue.trim()) return true;
        for (let element = parent; element; element = element.parentElement) {
            if (ignored_tags.has(element.tagName) || element.isContentEditable) return true;
        }
        return false;
    }

    function find_text_nodes(root) {
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
            acceptNode(node) { return should_ignore(node) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT; }
        });
        const nodes = [];
        while (walker.nextNode()) nodes.push(walker.currentNode);
        return nodes;
    }

    function wrap_text(node) {
        const span = document.createElement("span");
        span.dataset.textFilterWrapper = "";
        span.dataset.textFilterId = crypto.randomUUID(); // https://www.uuidgenerator.net/dev-corner/javascript
        span.style.setProperty("visibility", "hidden", "important"); // Hide text until scored
        span.textContent = node.nodeValue;
        node.parentNode.replaceChild(span, node); // basically, we put all text into another element where we can set the status to hidden - we don't remove it off of the webpage entirely. (also makes it re-identifiable by uuid4)
        pending_spans.add(span);
        return span;
    }

    function find_hide_target(span) {
        for (let element = span.parentElement;
            element && element !== document.body && element !== document.documentElement;
            element = element.parentElement) {
            if (block_tags.has(element.tagName)) return element;
            // Only hide a div when it has one scored text block and no other direct text. (extra cool thing suggested by GenAI). Basically if there is something which only has the text inside of it, remove that thing entirely - otherwise just remove the text.
            if (element.tagName === "DIV" && element.querySelectorAll("[data-text-filter-wrapper]").length === 1) {
                const has_direct_text = [...element.childNodes].some((child) =>
                    child.nodeType === Node.TEXT_NODE && child.nodeValue.trim()
                );
                if (!has_direct_text) return element;
            }
        }
        return span;
    }

    function set_hidden(element) {
        if (!original_display.has(element)) {
            original_display.set(element, {
                value: element.style.getPropertyValue("display"),
                priority: element.style.getPropertyPriority("display")
            });
        }
        element.style.setProperty("display", "none", "important");
    }

    function restore(element) {
        const original = original_display.get(element);
        if (!original || !element.isConnected) return;
        if (original.value) element.style.setProperty("display", original.value, original.priority);
        else element.style.removeProperty("display");
    }

    function apply_scores() {
        // Recompute all targets so moving the popup slider also restores newly allowed text.
        const should_hide = new Set();

        for (const [span, score] of scores) {
            if (!span.isConnected) scores.delete(span); 
            else if (score > threshold) should_hide.add(find_hide_target(span));
        }
        for (const element of hidden_elements) if (!should_hide.has(element)) restore(element);
        for (const element of should_hide) set_hidden(element);
        hidden_elements = should_hide;
    }

    function reveal_pending_text(spans = pending_spans) {
        for (const span of spans) {
            if (span.isConnected) span.style.removeProperty("visibility");
            pending_spans.delete(span);
        }
    }

    function clear_slow_warnings() {
        // One good 200 response resolves the current warning and stops old timers reopening it.
        for (const request of active_requests) request.acknowledged = true;
        slow_requests.clear();
        warning_acknowledged = false;
    }

    async function score_spans(spans, is_initial = false) { // Main scoring function
        const request = { acknowledged: warning_acknowledged };
        active_requests.add(request);

        const text_by_id = Object.fromEntries(spans.map((span) => [span.dataset.textFilterId, span.textContent]));
        let complete = false;

        const timer = setTimeout(() => { // Only after the settings wait_seconds show thing
            if (complete || request.acknowledged || warning_acknowledged) return;
            slow_requests.add(request);
            set_gate_message(`The server is taking longer than ${settings.wait_seconds} seconds. The page is still covered until you choose to show it or a response arrives.`);
        }, Math.max(0, Number(settings.wait_seconds)) * 1000); 

        try {
            const result = await browser.runtime.sendMessage({
                type: "score-text", server_url: settings.server_url, text_by_id
            });
            complete = true;
            clearTimeout(timer);
            active_requests.delete(request);

            if (result?.ok) {
                for (const span of spans) {
                    const score = result.scores?.[span.dataset.textFilterId];
                    if (typeof score === "number" && Number.isFinite(score)) scores.set(span, score);
                }
                reveal_pending_text(spans);
                apply_scores();
                clear_slow_warnings();
            } else {
                reveal_pending_text(spans);
                if (!request.acknowledged) {
                    slow_requests.add(request);
                    set_gate_message(`Server error: ${result?.error || "No valid response."} Acknowledge to show the page.`);
                }
            }
        } catch (error) {
            complete = true;
            clearTimeout(timer);
            active_requests.delete(request);
            reveal_pending_text(spans);
            if (!request.acknowledged) {
                slow_requests.add(request);
                set_gate_message(`Server error: ${error.message || "Unknown request error"} Acknowledge to show the page.`);
            }
        }

        if (is_initial) initial_scan_done = true;
        maybe_release_gate();
    }

    function process_text_nodes(nodes, is_initial = false) {
        const spans = nodes.filter((node) => node.isConnected && !should_ignore(node)).map(wrap_text);
        if (!spans.length) {
            if (is_initial) initial_scan_done = true;
            maybe_release_gate();
            return;
        }
        score_spans(spans, is_initial);
    }

    function observe_dynamic_text() { 
        const observer = new MutationObserver((mutations) => {
            // The complete initial scan at DOMContentLoaded covers parser-created text.
            if (!document_ready) return;
            const added_text = new Set();
            for (const mutation of mutations) {
                for (const added of mutation.addedNodes) {
                    if (added.nodeType === Node.TEXT_NODE) added_text.add(added);
                    else if (added.nodeType === Node.ELEMENT_NODE && !added.matches("[data-text-filter-wrapper]")) {
                        find_text_nodes(added).forEach((node) => added_text.add(node));
                    }
                }
            }
            if (added_text.size) process_text_nodes([...added_text]);
        });
        observer.observe(document.documentElement, { childList: true, subtree: true });
    }

    browser.runtime.onMessage.addListener((message) => {
        if (message.type !== "set-threshold" || !Number.isFinite(Number(message.threshold))) return undefined;
        threshold = Number(message.threshold);
        apply_scores();
        return undefined;
    }); // reload page with the new threshold when the user changes it in the popup.

    function scan_initial_page() {
        process_text_nodes(find_text_nodes(document.documentElement), true);
    }

    load_settings().then((loaded) => {
        settings = loaded;
        threshold = Number(settings.threshold);
        if (is_excluded_site()) {
            initial_scan_done = true;
            release_gate();
            return;
        }
        observe_dynamic_text();
        if (document_ready) scan_initial_page();
        else document.addEventListener("DOMContentLoaded", scan_initial_page, { once: true });
    }).catch((error) => {
        set_gate_message(`Could not load settings: ${error.message || "Unknown error"} Acknowledge to show the page.`);
    });
})();
