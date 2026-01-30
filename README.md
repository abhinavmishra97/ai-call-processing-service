# AI Call Processing Service

A high-performance, async-first backend service designed to simulate a call center environment. This service handles real-time call packet ingestion, state management, and orchestrates background AI processing with robust retry mechanisms.

---

## 1. Methodology

The approach to this project focuses on **non-blocking concurrency** and **system resilience**.

*   **Ingestion**: The primary goal is to accept high-velocity data packets from streaming calls without latency. We utilize **FastAPI** with Python's `asyncio` to ensure the intake endpoint returns immediately (sub-50ms) while persisting data to the database.
*   **State Management**: A formal State Machine guides the call lifecycle from `IN_PROGRESS` to `ARCHIVED`. This ensures data integrity and predictable transitions.
*   **Background Orchestration**: Computationally expensive tasks (like AI analysis) are decoupled from the ingestion layer. They run in background tasks to prevent blocking the real-time stream.
*   **Resilience**: We assume external dependencies (like AI APIs) are unreliable. The system implements chaos engineering principles by simulating failures and handling them with exponential backoff retries.

---

## 2. Technical Details

### Architecture & Choices
*   **FastAPI**: Chosen for its native asynchronous capabilities and automatic OpenAPI documentation. It allows handling thousands of concurrent connections efficiently.
*   **Async SQLAlchemy**: We use the asynchronous engine to interact with the database, ensuring that database I/O does not block the main event loop.
    *   *Note*: The project is configured to use **SQLite (async)** by default for easy local testing, but it is production-ready for **PostgreSQL**.
*   **Robust Error Handling**:
    *   **Concurrency Control**: The ingestion endpoint handles **Race Conditions** (e.g., simultaneous packet arrivals) using database unique constraints and integrity error handling.
    *   **Retry Strategy**: The "Flaky" AI service is wrapped with the `tenacity` library, implementing **Exponential Backoff** ($2^n$ seconds) to gracefully handle ephemeral failures (503s) and network latency.
*   **Validation**: The system accepts packets out-of-order and logs warnings, adhering to the requirement of "accept first, validate later" to prioritize system availability.

### Key Components
1.  **Call Stream API**: `POST /v1/call/stream/{call_id}` - Accepts packets ~20ms response time.
2.  **Supervisor WebSocket**: `ws://.../stream/ws/supervisor` - Broadcasts real-time state changes to dashboards.
3.  **Mock AI Service**: Simulates a 25% failure rate and variable latency (1-3s) to test system robustness.

---

## 3. Setup Instructions

Follow these steps to run the project locally.

### Prerequisites
*   Python 3.9+
*   (Optional) Docker for PostgreSQL

### Installation

1.  **Clone the repository**:
    ```bash
    git clone <repository_url>
    cd ai-call-processing-service
    ```

2.  **Create a Virtual Environment**:
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\Activate

    # Mac/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

### Running the Application

1.  **Start the Server**:
    ```bash
    uvicorn app.main:app --reload
    ```
    The API will be available at: `http://127.0.0.1:8000`

2.  **Explore the API**:
    Open your browser to the **Interactive Documentation**:
    [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

    You can manually test endpoints here:
    *   **Ingest Packet**: `POST /v1/call/stream/{call_id}`
    *   **End Call**: `POST /v1/call/{call_id}/end` (Triggers background AI)

### Running Tests

We have dedicated scripts to simulate real-world chaos and concurrency issues.

#### 1. Race Condition Visualization
**Purpose:** To demonstrate how the system handles simultaneous packet arrivals. This script fires 5 requests for the *same new call* at the exact same millisecond.

**Run the test:**
```bash
python tests/visualize_race.py
```

**What to expect:**
1.  **Client Output:** You will see a list of 5 status codes: `['202', '202', '202', '202', '202']`. This proves *zero* requests failed.
2.  **Server Logs:** In your `uvicorn` terminal, you will see a warning:
    ```text
    WARNING: ... >>> RACE CONDITION CAUGHT! handling concurrency for ... <<<
    ```
    This confirms the database successfully blocked the duplicate creation and the API recovered gracefully.

#### 2. Standard Integration Tests
Run the standard pytest suite to verify general logic:
```bash
python -m pytest tests/
```
