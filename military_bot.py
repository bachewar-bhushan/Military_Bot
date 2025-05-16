from flask import Flask, Response, render_template_string, request
import cv2
import threading
import time
import os
from ultralytics import YOLO
from queue import Queue
import RPi.GPIO as GPIO
from picamera2 import Picamera2



app = Flask(__name__)
picam2 = Picamera2()

# Camera configuration
video_config = picam2.create_video_configuration(
    main={"size": (320, 240)},
    controls={"FrameRate": 30}
)
picam2.configure(video_config)
picam2.preview_configuration.main.format = "RGB888"
picam2.configure("preview")

buzzer = 23
#picam2.set_controls({
 #   "AwbMode": 1,
  #  "Brightness": 0.0,
   # "Contrast": 1.2,
  #  "Saturation": 1.3,
   # "Sharpness": 1.0
#})

GPIO.setmode(GPIO.BCM)
GPIO.setup(buzzer, GPIO.OUT)
for i in range (3):
    GPIO.output(buzzer, GPIO.HIGH)
    time.sleep(0.2)
    GPIO.output(buzzer, GPIO.LOW)
    time.sleep(0.2)

picam2.start()

frame_lock = threading.Lock()
latest_frame = None

frame_queue = Queue(maxsize=1)
detected_frame = None
detected_lock = threading.Lock()

detected_frame = None
detected_lock = threading.Lock()

detected_objects = []
detected_objects_lock = threading.Lock()

# High Alert Classes
HIGH_ALERT_CLASSES = [
    "Storage box", "Microphone", "Backpack", "Knife", "Machinery Vehicle",
    "Surveillance Camera", "Gun", "Fire Hydrant", "Fire Extinguisher",
    "Hammer", "Recorder", "Lighter", "Tank"
]

model = YOLO("yolov8n-oiv7.pt")

def capture_frames():
    global latest_frame
    while True:
        frame = picam2.capture_array()
        with frame_lock:
            latest_frame = frame
        if not frame_queue.full():
            frame_queue.put(frame)
        time.sleep(0.1)

def detection_worker():
    global detected_frame
    while True:
        try:
            frame = frame_queue.get(timeout=1)
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            results = model.predict(source=frame_bgr, stream=False, verbose=False)
            result_frame = results[0].plot()
            detected_labels = results[0].names
            class_ids = results[0].boxes.cls.tolist()
            object_names = [detected_labels[int(cls)] for cls in class_ids]
            with detected_lock:
                detected_frame = result_frame
            with detected_objects_lock:
                detected_objects.clear()
                detected_objects.extend(object_names)
        except:
            continue

@app.route('/')
def index():
    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>MilitaryBot</title>
      <style>
        html, body {
          height: 100%;
          margin: 0;
          padding: 0;
        }

        body {
          background-image: url('/static/home.jpg');
          background-size: cover;
          background-position: center;
          background-repeat: no-repeat;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          font-family: Arial, sans-serif;
          color: black;
        }

        .container {
          display: flex;
          justify-content: center;
          gap: 40px;
          margin-top: 40px;
        }

        button {
          padding: 15px 30px;
          font-size: 18px;
          cursor: pointer;
          border: none;
          background-color: #007bff;
          color: white;
          border-radius: 6px;
          transition: background-color 0.3s ease;
        }

        button:hover {
          background-color: #0056b3;
        }

        .shutdown {
          background-color: #dc3545;
          margin-bottom: 20px;
        }

        .shutdown:hover {
          background-color: #a71d2a;
        }
        .page-heading {
            width: 100%;
            text-align: center;
            margin-bottom: 20px;
            font-size: 24px;
            color: white;
            font-weight: bold;
            font-style: italic;
            z-index: 1001;
        }

      </style>
    </head>



    <body>
    <h1 class="page-heading">Ground Bot for Military Reconnaissance</h1>
    <form action="/shutdown" method="POST">
        <button class="shutdown" type="submit">Shutdown Raspberry Pi</button>
      </form>
      <div class="container">
        <button onclick="location.href='/video_feed'">Live Stream</button>
        <button onclick="location.href='/object_detection'">Object Detection</button>
      </div>
    </body>
    </html>
    '''
    return render_template_string(html)
@app.route('/video_feed')
def video_feed():
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Live Stream</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
        <style>
            html, body {
                    background-image: url('/static/como.jpg');
                   .home-button {
                    position: absolute;
                    top: 10px;
                    right: 10px;
                    padding: 10px 15px;
                    background: rgba(255, 255, 255, 0.85);
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 16px;
                    font-weight: bold;
                    z-index: 1001;
                }

                .home-button:hover {
                    background: rgba(200, 200, 200, 0.95);
                }
                margin: 0;
                padding: 0;
                height: 100%;
                background-color: black;
                display: flex;
                justify-content: center;
                align-items: center;
            }

            #video-container {
              position: relative;
              border-radius: 25px;
                width: 100%;
                height: 100%;
                background-color: black;
                display: flex;
                justify-content: center;
                align-items: center;
            }

            #stream {
                max-width: 100%;
                max-height: 100%;
                object-fit: contain;
                display: block;
            }

            .fullscreen-button {
                position: absolute;
                top: 10px;
                left: 50%;
                transform: translateX(-50%);
                padding: 10px 15px;
                background: rgba(255, 255, 255, 0.8);
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                font-weight: bold;
                z-index: 1000;
            }

            .fullscreen-button:hover {
                background: rgba(200, 200, 200, 0.9);
            }

            #map {
                position: absolute;
                top: 10px;
                left: 10px;
                width: 250px;
                height: 200px;
                z-index: 999;
                border: 2px solid #007bff;
                border-radius: 10px;
            }
        </style>
    </head>
    <body>
     <div id="map"></div>
        <div id="video-container">
            <img id="stream" src="/video_feed/stream" alt="Live Feed">
            <button class="fullscreen-button" onclick="goFullscreen()">🔲 Full Screen</button>
            <button class="home-button" onclick="location.href='/'">Home</button>

        </div>

        <script>
            function goFullscreen() {
                const container = document.getElementById("video-container");
                if (container.requestFullscreen) {
                    container.requestFullscreen();
                } else if (container.webkitRequestFullscreen) {
                    container.webkitRequestFullscreen(); // Safari
                } else if (container.msRequestFullscreen) {
                    container.msRequestFullscreen(); // IE11
                }
            }

            document.addEventListener("fullscreenchange", () => {
                const img = document.getElementById("stream");
                if (document.fullscreenElement) {
                    img.style.width = "100%";
                    img.style.height = "100%";
                } else {
                    img.style.width = "";
                    img.style.height = "";
                }
            });

            // Leaflet map logic
            const map = L.map('map').setView([18.46374, 73.86834], 13); // 🔁 Replace with your lat, lon
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; OpenStreetMap contributors'
            }).addTo(map);
            L.marker([18.46374, 73.86834]) // 🔁 Replace with your lat, lon
                .addTo(map)
                .bindPopup('Bot Location')
                .openPopup();
        </script>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route('/object_detection')
def object_detection_feed():
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Live Stream</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
        <style>
            html, body {
                    background-image: url('/static/como.jpg');
                   .home-button {
                    position: absolute;
                    top: 10px;
                    right: 10px;
                    padding: 10px 15px;
                    background: rgba(255, 255, 255, 0.85);
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 16px;
                    font-weight: bold;
                    z-index: 1001;
                }

                .home-button:hover {
                    background: rgba(200, 200, 200, 0.95);
                }
                margin: 0;
                padding: 0;
                height: 100%;
                background-color: black;
                display: flex;
                justify-content: center;
                align-items: center;
            }

            #video-container {
                    border-radius: 25px;
                    position: relative;
                    width: 100%;
                    height: 100%;
                    background-color: black;
                    display: flex;
                    justify-content: center;
                    align-items: center;
            }

            #stream {
                max-width: 100%;
                max-height: 100%;
                object-fit: contain;
                display: block;
            }

            .fullscreen-button {
                position: absolute;
                top: 10px;
                left: 50%;
                transform: translateX(-50%);
                padding: 10px 15px;
                background: rgba(255, 255, 255, 0.8);
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                font-weight: bold;
                z-index: 1000;
            }

            .fullscreen-button:hover {
                background: rgba(200, 200, 200, 0.9);
            }

            #map {
                position: absolute;
                top: 10px;
                left: 10px;
                width: 300px;
                height: 250px;
                z-index: 999;
                border: 2px solid #007bff;
                border-radius: 10px;
            }

            #alert-container {
            position: absolute;
            top: 100px;
            right: 20px;
            width: 250px;
            display: flex;
            flex-direction: column;
            gap: 20px;
            z-index: 999;
            }

            .alert-box {
                padding: 10px;
                background: rgba(255, 255, 255, 0.85);
                border-radius: 10px;
                border: 2px solid black;
                font-size: 16px;
                font-weight: bold;
                max-height: 200px;
                overflow-y: auto;
            }

            .alert-high {
                border-color: red;
                color: red;
            }

            .alert-normal {
                border-color: green;
                color: green;
            }
        </style>
    </head>
    <body>
     <div id="map"></div>
        <div id="video-container">
            <img id="stream" src="/object_detection/stream" alt="Live Feed">
            <button class="fullscreen-button" onclick="goFullscreen()">🔲 Full Screen</button>
            <button class="home-button" onclick="location.href='/'">Home</button>

        </div>
        <div id="alert-container">
            <div class="alert-box alert-high">
                High Alert:
                <ul id="high-alert-list"></ul>
            </div>
            <div class="alert-box alert-normal">
                Normal:
                <ul id="normal-list"></ul>
            </div>
        </div>

        <script>
            function goFullscreen() {
                const container = document.getElementById("video-container");
                if (container.requestFullscreen) {
                    container.requestFullscreen();
                } else if (container.webkitRequestFullscreen) {
                    container.webkitRequestFullscreen(); // Safari
                } else if (container.msRequestFullscreen) {
                    container.msRequestFullscreen(); // IE11
                }
            }

            document.addEventListener("fullscreenchange", () => {
                const img = document.getElementById("stream");
                if (document.fullscreenElement) {
                    img.style.width = "100%";
                    img.style.height = "100%";
                } else {
                    img.style.width = "";
                    img.style.height = "";
                }
            });

            // Leaflet map logic
            const map = L.map('map').setView([18.46374, 73.86834], 13); // 🔁 Replace with your lat, lon
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; OpenStreetMap contributors'
            }).addTo(map);
            L.marker([18.46374, 73.86834]) // 🔁 Replace with your lat, lon
                .addTo(map)
                .bindPopup('Bot Location')
                .openPopup();

            setInterval(() => {
                fetch('/object_detection/objects')
                    .then(res => res.json())
                    .then(data => {
                        const high = document.getElementById('high-alert-content');
                        const normal = document.getElementById('normal-content');
                        high.innerHTML = "";
                        normal.innerHTML = "";

                        const seen = new Set();

                        data.objects.forEach(obj => {
                            if (seen.has(obj)) return;
                            seen.add(obj);
                            const div = document.createElement('div');
                            div.textContent = obj;
                            if (data.high_alert.includes(obj)) {
                                high.appendChild(div);
                            } else {
                                normal.appendChild(div);
                            }
                        });

                        if (high.innerHTML === "") high.innerHTML = "None";
                        if (normal.innerHTML === "") normal.innerHTML = "None";
                    });
            }, 1000);
        </script>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route('/object_detection/objects')
def object_list():
    with detected_objects_lock:
        objs = list(set(detected_objects))  # remove duplicates
    return {
        "objects": objs,
        "high_alert": list(HIGH_ALERT_CLASSES)
    }

@app.route('/object_detection/stream')
def object_detection():
    def generate():
        while True:
            with detected_lock:
                if detected_frame is None:
                    time.sleep(0.01)
                    continue
                ret, jpeg = cv2.imencode('.jpg', detected_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if not ret:
                    continue
                frame = jpeg.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.01)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed/stream')
def video_feed_stream():
    def generate():
        while True:
            with frame_lock:
                if latest_frame is None:
                    continue
                ret, jpeg = cv2.imencode('.jpg', latest_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if not ret:
                    continue
                frame = jpeg.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.005)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/set_control', methods=['POST'])
def set_control():
    data = request.json
    control = data.get('control')
    value = data.get('value')
    try:
        picam2.set_controls({control: value})
        return {'status': 'success'}
    except Exception as e:
        print(f"Error setting {control}: {e}")
        return {'status': 'error', 'message': str(e)}, 400

@app.route('/shutdown', methods=['POST'])
def shutdown():
    try:
        picam2.stop()
        GPIO.output(buzzer, GPIO.HIGH)
        time.sleep(0.2)
        GPIO.output(buzzer, GPIO.LOW)
        time.sleep(0.2)
    except Exception as e:
        print("Camera stop error:", e)

    shutdown_func = request.environ.get('werkzeug.server.shutdown')
    GPIO.output(buzzer, GPIO.HIGH)
    time.sleep(0.8)
    GPIO.output(buzzer, GPIO.LOW)
    time.sleep(0.2)
    if shutdown_func:
        shutdown_func()


    threading.Thread(target=lambda: os.system("sudo shutdown now")).start()
    return "Shutting down..."

if __name__ == '__main__':
    threading.Thread(target=capture_frames, daemon=True).start()
    threading.Thread(target=detection_worker, daemon=True).start()
    app.run(host='0.0.0.0', port=8000)