# Hatespeech Filter browser extension

This browser extension checks visible page text with the prediction server and hides text of which the returned score is above a threshold set by the user.

## What the user experiences

1. When a website opens, the extension finds the text on this page and temporarily hides it while it requests scores.
2. The page stays covered until the first scan and scoring request finish. If a request is still pending after the set wait time, the extension shows a warning and a "Show page anyway" button.
3. When scores arrive, text with a score greater than the selected threshold is hidden. Other scored text is shown.
4. If the server is unavailable or returns an error, after which the user manually has to acknowledge wanting to still see the page. 
5. Text added later by a dynamic page (such as with an infinine feed on Twitter/X or Instagram) is also scanned and scored.

## Using the popup

The popup's main view contains a "Hide above confidence" slider ranging from 0 to 1. The selected threshold is saved locally and can be applied to the active page immediately; the user does not need to refresh the page.

Open settings to configure:
- Server URL: the full URL the extension should POST predictions to, including the API path.
- Wait before warning: how long a scoring request may take before the extension warns that the server is slow.
- Sites to exclude: one domain per line

## Connect to the backend

The extension sends `POST` requests with `Content-Type: application/json`. The body maps generated text IDs to text, for example:

```json
{
  "b1021fa0-...": "A paragraph from the page",
  "64a23cdd-...": "Another text block"
}
```

## Installation for local development

The supplied manifest is a Manifest V2 WebExtension and includes a Firefox extension ID. To try it locally in Firefox, open `about:debugging`, choose "This Firefox", select "Load Temporary Add-on", and choose `Frontend/manifest.json`.

## User data and scope

Page text selected for scoring is sent to the server configured in Settings. The extension stores its threshold, server URL, wait time, and excluded-domain list in local browser extension storage.

The extension filters ordinary text nodes. It skips scripts, form controls, media, embedded content, editable regions, and other excluded elements defined by the implementation. It does not block page navigation or remove content from the source; it hides matching page elements in the browser. Users can reveal the page when a slow or failed request triggers a warning.