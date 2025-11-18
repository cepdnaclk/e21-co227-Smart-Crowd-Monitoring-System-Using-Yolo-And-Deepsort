# Smart Crowd Monitoring System Using YOLO and Deepsort

## Team
- E/21/124, Ekanayake E.M.D.A., e21124@eng.pdn.ac.lk
- E/21/361, Sasindu K.T., e21361@eng.pdn.ac.lk
- E/21/371, SENAWIRATHNE D.M.W.J.I., e21371@eng.pdn.ac.lk
- E/21/433, WICKRAMANAYAKA N.S., e21433@eng.pdn.ac.lk

## Supervisor
- Ms. Yasodha Vimukthi, yasodhav@eng.pdn.ac.lk

## Table of Contents
- [Introduction](#introduction)
- [System Architecture](#system-architecture)
- [Features](#features)
- [Technology and Implementation](#technology-and-implementation)
- [Links](#links)

## Introduction
Real-time people counting and crowd monitoring using YOLOv8 + DeepSort for multi-camera feeds. Counts are persisted in PostgreSQL and exposed via a FastAPI backend. An optional React (Vite) frontend can visualize live status and history.

## System Architecture
```
main.py (processing threads) --> PostgreSQL <-- api.py (FastAPI) <-- React frontend (Vite or static build)
```
- `main.py`: loads config, starts one thread per building/feed, tracks objects, updates counts.
- `db_handler.py`: resilient inserts to PostgreSQL.
- `api.py`: serves latest counts and (optionally) the built frontend from `frontend/dist`.

## Features
- Person detection (YOLOv8) and multi-object tracking (DeepSort)
- Entrance/exit line crossing with direction-aware counting
- Threaded processing for multiple buildings/feeds
- PostgreSQL persistence of counts (per-building historical records)
- FastAPI JSON endpoints (`/crowd`, `/crowd/history`) + optional static frontend
- React dashboard (Chart.js) consuming API
- Config-driven feed lines & thresholds (`config.json`)

## Technology and Implementation
- Backend: FastAPI, Uvicorn
- Processing: YOLOv8 (Ultralytics), DeepSort, OpenCV
- Database: PostgreSQL (with indexes for latest-per-building queries)
- Frontend (optional): React + Vite (Chart.js for charts)
- Config: JSON file and environment overrides

## Links
- Project Repository: https://github.com/Anji-001/Project_CCTV
- Department of Computer Engineering: https://www.ce.pdn.ac.lk/
- University of Peradeniya: https://www.pdn.ac.lk/



