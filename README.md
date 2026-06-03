# Here are your Instructions


```bash
docker run -d -p 27017:27017 --name lioncity-mongo mongo:7
```

### Backend
```python
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`
```bash
MONGO_URL=mongodb://localhost:27017
DB_NAME=lioncity
CORS_ORIGINS=http://localhost:3000
LTA_ACCOUNT_KEY=oEZSvJLqSK6RZe+qNpeK9A==
OSRM_BASE_URL=https://router.project-osrm.org
```

```python
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend
```python
cd frontend
yarn install
```

Create `frontend/.env`
```bash
REACT_APP_BACKEND_URL=http://localhost:8001
WDS_SOCKET_PORT=3000
```

```python
yarn start
```