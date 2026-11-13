http://localhost:15672/#/

Docker Server:
```powershell
docker run -d --name rabbitmq-poc `
  -p 5672:5672 `
  -p 15672:15672 `
  rabbitmq:4-management
```

```powershell
docker start rabbitmq-poc
```

Orchestrator:
```powershell
python orchestrator.py
```

Worker 1:

```powershell
$env:WORKER_ID = "worker-1"
$env:PORT = "4352"
$env:DB_PATH = "$PWD\worker1.db"
python app.py
```

Worker 2:

```powershell
$env:WORKER_ID = "worker-2"
$env:PORT = "4353"
$env:DB_PATH = "$PWD\worker2.db"
python app.py
```

Test Orchestrator:

```powershell
python TEST_ORCHESTRATOR.py
```