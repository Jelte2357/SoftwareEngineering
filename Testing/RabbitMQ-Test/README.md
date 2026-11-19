# RabbitMQ-Test

## Download & Setup

### Docker + WSL

1. Install Docker Desktop and WSL, following the instructios from the announcement on the Software Engineering Canvas page.
2. Open PowerShell: Press Windows + R, type `powershell` and press Enter.
3. Check Docker by entering these commands, one at a time:

   ```powershell
   docker --version
   docker compose version
   docker run --rm hello-world
   ```

### RabbitMQ

1. In PowerShell, enter the following:

   ```powershell
   docker run -d --name hate-speech-rabbitmq -p 127.0.0.1:5672:5672 -p 127.0.0.1:15672:15672 -e RABBITMQ_DEFAULT_USER=se_user -e RABBITMQ_DEFAULT_PASS=dev_only_change_this rabbitmq:4-management
   ```

2. Check if it's running:

   ```powershell
   docker ps
   docker logs hate-speech-RabbitMQ
   ```

3. Go to http://localhost:15672 in your browser, and enter the following credentials:

   - **Username:** `se_user`
   - **Password:** `dev_only_change_this`

   This opens the RabbitMQ dashboard. The dashboard lets you monitor RabbitMQ and inspect its messaging infrastructure, including queues, exchanges, connections, and message activity. You can also check whether messages are waiting in a queue, being delivered, or being acknowledged.

4. Go to the tab **Queues and Streams**.

### VScode

1. Download this entire folder.
2. Download the distilBERT model from SoftwareEngineering > Model (PyTorch) > LINK.txt, and then pasting the https://jelte2357.nl/distilbert_classifier.zip into the search bar of your browser. This will download the model for you (the model was too big to upload to GitHub, so Jelte made a download link).
3. Unzip everything.
4. Set up the right folder structure as follows:

   ```text
   RabbitMQ-Test/
   ├── consumer.py
   ├── orchestrator.py
   ├── producer.py
   ├── README.md
   ├── requirements.txt
   └── distilbert_classifier/
       ├── config.json
       ├── model.safetensors
       ├── tokenizer.json
       └── tokenizer_config.json
   ```

5. In Powershell open the folder with the following command prompt:

   ```powershell
   Set-Location "C:\path\to\RabbitMQ-Test"
   ```

   Replace `C:\path\to\RabbitMQ-Test` with the actual path to the folder.

6. Create a new environment inside the folder:

   ```powershell
   py -3.14 -m venv .venv
   ```

7. Install all libraries listed in the requirements.txt:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

## Running the Program

1. Try a test run, to see if everything works. In VScode (or any other code-editor) open the RabbitMQ-Test folder and check if it automatically catches the right environment. Otherwise, you can activate the environment in each terminal by running the following in the terminal:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

2. open three separate terminals and run the following, in this exact order:

   **Terminal 1:**

   ```powershell
   python consumer.py
   ```

   **Terminal 2:**

   ```powershell
   python orchestrator.py
   ```

   **Terminal 3:**

   ```powershell
   python producer.py
   ```

After activating *all* terminals, this should give the following output:

**Terminal 1:**

```text
Loading DistilBERT model...
Loading weights: 100%|███████████████████████████████████████████| 104/104 [00:00<00:00, 885.24it/s]
DistilBERT model loaded successfully!
Waiting for requests...

Received a request!
Request ID: 1
Text: I really dislike this person.
Prediction: Not hate speech
Confidence: 0.9798
Response sent!

Received a request!
Request ID: 2
Text: You are an idiot.
Prediction: Hate speech
Confidence: 0.9646
Response sent!

Received a request!
Request ID: 3
Text: Have a wonderful day!
Prediction: Not hate speech
Confidence: 0.9991
Response sent!
```

**Terminal 2:**

```text
Orchestrator is running...
Waiting for incoming requests...

Received a request from the interface.
RabbitMQ confirmed the message.
Original request acknowledged.

Received a request from the interface.
RabbitMQ confirmed the message.
Original request acknowledged.

Received a request from the interface.
RabbitMQ confirmed the message.
Original request acknowledged.
```

**Terminal 3:**

```text
Sending requests...
Sent request 1
Sent request 2
Sent request 3

Waiting for responses...
Received response for: 1
Received response for: 2
Received response for: 3

Results:
```

```json
{
    "request_id": "1",
    "status": "success",
    "original_text": "I really dislike this person.",
    "predicted_class": 0,
    "classification": "Not hate speech",
    "confidence": 0.9798
}
```

```json
{
    "request_id": "2",
    "status": "success",
    "original_text": "You are an idiot.",
    "predicted_class": 1,
    "classification": "Hate speech",
    "confidence": 0.9646
}
```

```json
{
    "request_id": "3",
    "status": "success",
    "original_text": "Have a wonderful day!",
    "predicted_class": 0,
    "classification": "Not hate speech",
    "confidence": 0.9991
}
```

All requests received a response!

**RabbitMQ Queues and Streams:**

```text
ai_requests [running]
interface_requests [running]
```

**NOTE:** you can stop a terminal by entering ctrl + C in it (takes a few secs to process).

## Expanding the orchestrator

Currently, my work on the orchestrator follows this architecture:

- Flask handles the interface and orchestration.
- RabbitMQ handles communication between the orchestrator and AI server.
- DistilBERT handles hate-speech classification.

From what I understand, the only thing that still needs to happen is fully integrate the orchestrator with our existing software and end-to-end testing.

If you plan on using ChatGPT to work on this, I advise to

- explain our project idea and what we are working on
- upload the entire .zip of our repository
- explain that we have a locally, pre-trained distilBERT model and report its folder layout (or just upload the zip as well if you have the space)
- copy-paste the teacher's description of our current assignment
- upload / direct it to this README.md or this entire folder, so it can look into what needs to happen still

---

## Troubleshooting

- I somehow got issues importing torch when running it on 3.15, so I switched my environment to 3.14. This resolved the issue.

  If you already created a virtual environment with a different Python version, you cannot reliably change the Python version inside that existing environment. Deactivate it, create a new environment using Python 3.14, and activate the new environment:

  ```powershell
  deactivate
  py -3.14 --version
  py -3.14 -m venv .venv
  .\.venv\Scripts\Activate.ps1
  python --version
  ```

  The version check should report Python 3.14. If `py -3.14` is not recognised, install Python 3.14 first and make sure the Python launcher is available. Once the new environment is active, reinstall the project dependencies using `python -m pip install -r requirements.txt`.
