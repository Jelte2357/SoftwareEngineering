// Greatest hackaround - because you cant request the server from the content, you just run something else in the background that just does the request for you.
// (This is absolutely no good code)
browser.runtime.onMessage.addListener((message) => {
    if (message.type !== "score-text") return undefined;
    return score_text(message);
});

async function score_text(message) {
    try {
        const response = await fetch(message.server_url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(message.text_by_id)
        });

        if (!response.ok) {
            return { ok: false, error: `Server returned HTTP ${response.status} ${response.statusText}` };
        }

        return { ok: true, scores: await response.json() };
    } catch (error) {
        return { ok: false, error: error.message || "Could not reach the server" };
    }
}

function processElement(targetElementId, selectionText) {
    if (selectionText) {
        return selectionText;
    }
    else {
        return browser.menus.getTargetElement(targetElementId).parentElement.innerText;
    }
}

// browser.menus.create({
//     id: "re-score-hatespeech",
//     title: "Re-score hatespeech",
//     contexts: ["page", "selection"],

//     onclick: async function (info, tab) {
//         const result = await browser.scripting.executeScript({
//             target: {
//                 tabId: tab.id,
//                 frameIds: [info.frameId]
//             },
//             func: processElement,
//             args: [info.targetElementId, info.selectionText]
//         });
//         const text = result[0].result;

//         console.log(text);
//     }
// });