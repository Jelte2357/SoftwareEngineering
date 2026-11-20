# Hatespeech Filter

Hatespeech Filter is a small browser extension and prediction backend that helps users limit exposure to hatespeech (such as negative comments) online. The extension sends text to the server, which scores it, and then hides text above the user's set threshold. 

This repository has the browser client, two backend implementations (Flask-Only & RabbitMQ), and model-related code.

- [Frontend: browser extension](Frontend/README.md): user behavior, settings, installation
- [Backend: RabbitMQ service](Backend/Backend%20(RabbitMQ)/README.md): architecture, setup, API

The extension needs a compatible running prediction API. Configure its Server URL with the full `/api/predict` route. See the frontend guide for the included Flask and RabbitMQ endpoint examples.

###### Note: Github copilot is labled as a contributor only because one merge conflict was automatically resolved.
