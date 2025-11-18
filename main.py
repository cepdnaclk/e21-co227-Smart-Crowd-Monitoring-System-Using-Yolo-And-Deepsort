# main_threaded_reconnect.py
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
import cv2
from db_handler import CrowdDatabase
import threading
import time
import json
import sys
import os
import time

import sys
import os
import json

if getattr(sys, "frozen", False):
    # Running as .exe
    config_path = os.path.join(os.path.dirname(sys.executable), "config.json")
else:
    # Running as script
    config_path = os.path.join(os.path.dirname(__file__), "config.json")

print("Loading config from:", config_path)
with open(config_path, "r") as f:
    config = json.load(f)

buildings = {int(k): v for k, v in config["buildings"].items()}



# YOLO model
yolo_cfg = config.get("yolo", {})
model_path = yolo_cfg.get("model_path", "yolov8n.pt")
device = yolo_cfg.get("device", "cuda")  # set to "cpu" if no GPU

model = YOLO(model_path)
if device == "cuda":
    model.to("cuda")
else:
    model.to("cpu")

# -------------------- DATABASE --------------------
db_cfg = config.get("database", {})
db_host = db_cfg.get("host", "localhost")
db_port = db_cfg.get("port", 5432)
db_name = db_cfg.get("database", "crowd_monitor")
db_user = db_cfg.get("user", "postgres")
db_pass = db_cfg.get("password", "111@Postgres")

db = CrowdDatabase(
    host=db_host,
    database=db_name,
    user=db_user,
    password=db_pass,
    update_interval=config.get("update_interval", 10),
)

# Counting line positions
# line_y_in = 240
# line_y_out = 240

# -------------------- BUILDING THREAD FUNCTION --------------------
def process_building(building_id, feeds, shared_counters, lock):
    tracker_in = DeepSort(max_age=30)
    tracker_out = DeepSort(max_age=30)

    # Normalize feed entries (support string or dict in config)
    def normalize_feed_entry(entry):
        if isinstance(entry, str):
            return {"url": entry, "line": None}
        if isinstance(entry, dict):
            url = entry.get("url") or entry.get("rtsp") or entry.get("feed")
            return {
                "url": url,
                "line": entry.get("line")  # full line object
            }
        return {"url": None, "line": None}


    entrance_cfg = normalize_feed_entry(feeds.get("entrance"))
    exit_cfg = normalize_feed_entry(feeds.get("exit"))

    entrance_url = entrance_cfg["url"]
    exit_url = exit_cfg["url"]

    counters = {
        "entrance_count": 0,
        "exit_count": 0,
        # memory maps tid -> {"cx": int, "cy": int}
        "memory_in": {},
        "memory_out": {},
        # store frame id when we last counted that tid to avoid duplicate counts
        "last_count_frame_in": {},
        "last_count_frame_out": {},
    }
    frame_id = {"entrance": 0, "exit": 0} #Keeps track of the frame number for both cameras.

    # helper: open VideoCapture with retries
    def open_capture(url):
        cap = cv2.VideoCapture(url) #Tries to open the camera stream or video file at the given UR
        retry = 0
        while not cap.isOpened():
            print(f"[Building {building_id}] Failed to open {url}. Retrying in 5 seconds...")
            time.sleep(5)
            cap = cv2.VideoCapture(url)
            retry += 1
            if retry > 12:
                print(f"[Building {building_id}] Could not open {url} after multiple attempts.")
                return None
        return cap

    cap_in = open_capture(entrance_url) #Tries to open the entrance camera stream or video file.
    cap_out = None
    # Only open exit capture if exit feed is provided
    if "exit" in feeds:
        cap_out = open_capture(exit_cfg["url"])

    # If both streams failed to open, exit thread
    if cap_in is None and cap_out is None:
        print(f"[Building {building_id}] Streams not available. Exiting thread.")
        return

    # helper: convert normalized or pixel spec -> pixel coordinate for this frame size
    def spec_to_pixel(spec, length):
        if spec is None:
            return None
        # Tries to convert spec into a floating-point number.
        try:
            v = float(spec) 
        except Exception: 
            return None
        if 0.0 <= v <= 1.0: #If the given value is between 0 and 1, it’s treated as a normalized ratio.
            return int(v * length)
        return int(v) #Otherwise, treat it as a raw pixel value.

    while True:
        # --- Entrance ---
        if not cap_in.isOpened():
            print(f"[Building {building_id}] Entrance stream lost. Reconnecting...")
            cap_in.release() #Releases the current VideoCapture object.
            cap_in = open_capture(entrance_url)
            if cap_in is None:
                time.sleep(5)
                continue

        ret_in, frame_in = cap_in.read() #Reads one frame from the entrance video feed.
        # If reading fails, try to reconnect.
        if not ret_in:
            print(f"[Building {building_id}] Entrance read failed. Reconnecting...")
            cap_in.release()
            cap_in = open_capture(entrance_url)
            continue
        

        frame_id["entrance"] += 1 #
        if frame_id["entrance"] % 3 == 0:
            frame_in = cv2.resize(frame_in, (640, 480))
            h_in, w_in = frame_in.shape[:2] 

            # compute pixel line positions for this resolution
            line_cfg = entrance_cfg.get("line") #Gets the line configuration for the entrance camera.
            hline_in, vline_in = None, None #Initializes horizontal and vertical line positions to None.
            enter_dir_in = None
            if line_cfg:
                enter_dir_in = line_cfg.get("enter_direction")  # 'down'|'up' for horizontal, 'right'|'left' for vertical
                if line_cfg["type"] == "horizontal":
                    hline_in = line_cfg["coords"][1]
                elif line_cfg["type"] == "vertical":
                    vline_in = line_cfg["coords"][0]

            
            results_in = model(frame_in, conf=0.4, verbose=False)
            # extract person detections
            detections_in = [
                ([int(r.xyxy[0][0]), int(r.xyxy[0][1]),
                  int(r.xyxy[0][2] - r.xyxy[0][0]),
                  int(r.xyxy[0][3] - r.xyxy[0][1])],
                 float(r.conf[0]), int(r.cls[0]))
                for r in results_in[0].boxes if model.names[int(r.cls[0])] == "person"
            ]

            # deep sort tracking
            tracks_in = tracker_in.update_tracks(detections_in, frame=frame_in) 
            #Updates the tracker with the new detections for the current frame.
            for track in tracks_in:
                if not track.is_confirmed():
                    continue
                tid = track.track_id #Gets the unique track ID for the current tracked object.
                x1, y1, x2, y2 = map(int, track.to_ltrb()) #Gets the bounding box coordinates for the tracked object.
                cx, cy = (x1 + x2)//2, (y1 + y2)//2 #Calculates the center coordinates of the bounding box.

                # only for one direction
                # prev = counters["memory_in"].get(tid)
                # counted = False
                # # simple debounce: ignore if we counted this tid in last 5 frames
                # last_frame = counters["last_count_frame_in"].get(tid, -9999)
                # if prev is not None and (frame_id["entrance"] - last_frame) > 5:
                #     prev_cx, prev_cy = prev["cx"], prev["cy"]
                #     # horizontal crossing (downwards)
                #     if hline_in is not None and prev_cy < hline_in <= cy:
                #         counters["entrance_count"] += 1
                #         counted = True
                #     # vertical crossing (rightwards) - only count if not already counted this update
                #     if (not counted) and vline_in is not None and prev_cx < vline_in <= cx:
                #         counters["entrance_count"] += 1
                #         counted = True
                #     if counted:
                #         counters["last_count_frame_in"][tid] = frame_id["entrance"]
                
                prev = counters["memory_in"].get(tid) #Retrieves the previous position of the tracked object from memory.
                last_frame = counters["last_count_frame_in"].get(tid, -9999) #Gets the last frame number when this object was counted.
                # simple debounce: ignore if we counted this tid in last 5 frames
                if prev is not None and (frame_id["entrance"] - last_frame) > 5:
                    prev_cx, prev_cy = prev["cx"], prev["cy"] #Gets the previous center coordinates of the tracked object.

                    # Horizontal line logic
                    if hline_in is not None:
                        crossed_down = prev_cy < hline_in <= cy   # top -> bottom
                        crossed_up   = prev_cy > hline_in >= cy   # bottom -> top
                        if crossed_down or crossed_up:
                            # determine which direction counts as entrance
                            desired = enter_dir_in or "down"  # default old behavior
                            if (crossed_down and desired == "down") or (crossed_up and desired == "up"):
                                counters["entrance_count"] += 1
                            else:
                                counters["exit_count"] += 1
                            counters["last_count_frame_in"][tid] = frame_id["entrance"]

                    # Vertical line logic
                    if vline_in is not None:
                        crossed_right = prev_cx < vline_in <= cx  # left -> right
                        crossed_left  = prev_cx > vline_in >= cx  # right -> left
                        if crossed_right or crossed_left:
                            desired = enter_dir_in or "right"
                            if (crossed_right and desired == "right") or (crossed_left and desired == "left"):
                                counters["entrance_count"] += 1
                            else:
                                counters["exit_count"] += 1
                            counters["last_count_frame_in"][tid] = frame_id["entrance"]


                # update memory
                counters["memory_in"][tid] = {"cx": cx, "cy": cy} #Updates the memory with the current position of the tracked object.

                # draw bbox + id
                cv2.rectangle(frame_in, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame_in, f"IN ID {tid}", (x1, y1-5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

            # draw lines if present
            if hline_in is not None:
                cv2.line(frame_in, (0, hline_in), (w_in, hline_in), (255,0,0), 2)
                cv2.putText(frame_in, f"H: {hline_in}", (10, max(20, hline_in-10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,0,0), 2)
            if vline_in is not None:
                cv2.line(frame_in, (vline_in, 0), (vline_in, h_in), (255,0,0), 2)
                cv2.putText(frame_in, f"V: {vline_in}", (min(w_in-80, vline_in+5), 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,0,0), 2)
            # draw counts
            cv2.putText(frame_in, f"Entrance: {counters['entrance_count']}", (20,40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
            cv2.imshow(f"Building {building_id} Entrance", frame_in)

        # --- Exit ---
        if cap_out is not None:
            ret_out, frame_out = cap_out.read()
            if ret_out:
        # your exit-processing code here
                if not cap_out.isOpened():
                    print(f"[Building {building_id}] Exit stream lost. Reconnecting...")
                    cap_out.release()
                    cap_out = open_capture(exit_url)
                    if cap_out is None:
                        time.sleep(5)
                        continue

                ret_out, frame_out = cap_out.read()
                if not ret_out:
                    print(f"[Building {building_id}] Exit read failed. Reconnecting...")
                    cap_out.release()
                    cap_out = open_capture(exit_url)
                    continue

                frame_id["exit"] += 1
                if frame_id["exit"] % 3 == 0:
                    frame_out = cv2.resize(frame_out, (640, 480))
                    h_out, w_out = frame_out.shape[:2]

                    line_cfg = exit_cfg.get("line")
                    hline_out, vline_out = None, None
                    enter_dir_out = None
                    if line_cfg:
                        enter_dir_out = line_cfg.get("enter_direction")
                        if line_cfg["type"] == "horizontal":
                            hline_out = line_cfg["coords"][1]
                        elif line_cfg["type"] == "vertical":
                            vline_out = line_cfg["coords"][0]


                    results_out = model(frame_out, conf=0.4, device=device)
                    detections_out = [
                        ([int(r.xyxy[0][0]), int(r.xyxy[0][1]),
                        int(r.xyxy[0][2] - r.xyxy[0][0]),
                        int(r.xyxy[0][3] - r.xyxy[0][1])],
                        float(r.conf[0]), int(r.cls[0]))
                        for r in results_out[0].boxes if model.names[int(r.cls[0])] == "person"
                    ]

                    tracks_out = tracker_out.update_tracks(detections_out, frame=frame_out)
                    for track in tracks_out:
                        if not track.is_confirmed():
                            continue
                        tid = track.track_id
                        x1, y1, x2, y2 = map(int, track.to_ltrb())
                        cx, cy = (x1 + x2)//2, (y1 + y2)//2

                        # One direction
                        # prev = counters["memory_out"].get(tid)
                        # counted = False
                        # last_frame = counters["last_count_frame_out"].get(tid, -9999)
                        # if prev is not None and (frame_id["exit"] - last_frame) > 5:
                        #     prev_cx, prev_cy = prev["cx"], prev["cy"]
                        #     # horizontal (downwards)
                        #     if hline_out is not None and prev_cy < hline_out <= cy:
                        #         counters["exit_count"] += 1
                        #         counted = True
                        #     # vertical (rightwards)
                        #     if (not counted) and vline_out is not None and prev_cx < vline_out <= cx:
                        #         counters["exit_count"] += 1
                        #         counted = True
                        #     if counted:
                        #         counters["last_count_frame_out"][tid] = frame_id["exit"]

                        prev = counters["memory_out"].get(tid)
                        last_frame = counters["last_count_frame_out"].get(tid, -9999)
                        if prev is not None and (frame_id["exit"] - last_frame) > 5:
                            prev_cx, prev_cy = prev["cx"], prev["cy"]

                            # Horizontal line logic
                            if hline_out is not None:
                                crossed_down = prev_cy < hline_out <= cy
                                crossed_up   = prev_cy > hline_out >= cy
                                if crossed_down or crossed_up:
                                    desired = enter_dir_out or "down"
                                    if (crossed_down and desired == "down") or (crossed_up and desired == "up"):
                                        counters["entrance_count"] += 1
                                    else:
                                        counters["exit_count"] += 1
                                    counters["last_count_frame_out"][tid] = frame_id["exit"]

                            # Vertical line logic
                            if vline_out is not None:
                                crossed_right = prev_cx < vline_out <= cx
                                crossed_left  = prev_cx > vline_out >= cx
                                if crossed_right or crossed_left:
                                    desired = enter_dir_out or "right"
                                    if (crossed_right and desired == "right") or (crossed_left and desired == "left"):
                                        counters["entrance_count"] += 1
                                    else:
                                        counters["exit_count"] += 1
                                    counters["last_count_frame_out"][tid] = frame_id["exit"]


                        counters["memory_out"][tid] = {"cx": cx, "cy": cy}

                        cv2.rectangle(frame_out, (x1, y1), (x2, y2), (0, 0, 255), 2)
                        cv2.putText(frame_out, f"OUT ID {tid}", (x1, y1-5),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 2)

                    if hline_out is not None:
                        cv2.line(frame_out, (0, hline_out), (w_out, hline_out), (255,0,0), 2)
                        cv2.putText(frame_out, f"H: {hline_out}", (10, max(20, hline_out-10)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,0,0), 2)
                    if vline_out is not None:
                        cv2.line(frame_out, (vline_out, 0), (vline_out, h_out), (255,0,0), 2)
                        cv2.putText(frame_out, f"V: {vline_out}", (min(w_out-80, vline_out+5), 20),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,0,0), 2)

                    cv2.putText(frame_out, f"Exit: {counters['exit_count']}", (20,40),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
                    cv2.imshow(f"Building {building_id} Exit", frame_out)

        # Update shared counters
        crowd_inside = max(0, counters["entrance_count"] - counters["exit_count"])
        # lock ensures that only one thread updates shared_counters at a time
        with lock:
            shared_counters[building_id] = crowd_inside
        #print(f"Building {building_id} Inside: {crowd_inside}")

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    # Cleanup        
    cap_in.release()
    cap_out.release()


# -------------------- START THREADS --------------------
shared_counters = {} # building_id -> current count inside
lock = threading.Lock() # to protect shared_counters access
threads = [] # list of building threads

# Start a Thread for Each Building
for building_id, feeds in buildings.items():
    t = threading.Thread(target=process_building, args=(building_id, feeds, shared_counters, lock))
    t.start()
    threads.append(t)

# Background thread for DB updates every 1 second
def db_updater():
    while True:
        with lock:
            db.insert_multiple_counts(shared_counters)
        time.sleep(1)

db_thread = threading.Thread(target=db_updater, daemon=True) #Daemon thread will exit when main program exits
db_thread.start()

# Wait for all building threads to finish
for t in threads:
    t.join()

# Cleanup
cv2.destroyAllWindows()
db.close()
