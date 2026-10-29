
const comments = new Set();

function collectComments() {
    const elements = document.querySelectorAll(
        "ytd-comment-thread-renderer #content-text"
    );

    elements.forEach(element => {
        const comment = element.innerText.trim();

        if (comment && !comments.has(comment)) {
            comments.add(comment);
            console.log("Comment collected:", comment);
        }
    });
}

// Collect comments already on the page.
collectComments();

// Keep checking for comments loaded later as you scroll.
setInterval(collectComments, 1000);

// Convert the collected comments into an array when needed.
function getComments() {
    return [...comments];
}

// Example: view all collected comments as an array.
console.log("Comments array:", getComments());
