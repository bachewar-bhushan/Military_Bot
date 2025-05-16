from flask import Flask, Response, render_template_string, request
import cv2
import threading
import time
import os
from ultralytics import YOLO
from queue import Queue

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

#picam2.set_controls({
 #   "AwbMode": 1,
  #  "Brightness": 0.0,
   # "Contrast": 1.2,
  #  "Saturation": 1.3,
   # "Sharpness": 1.0
#})

picam2.start()

frame_lock = threading.Lock()
latest_frame = None

frame_queue = Queue(maxsize=1)
detected_frame = None
detected_lock = threading.Lock()

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
            with detected_lock:
                detected_frame = result_frame
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
      <title>Stream Options</title>
      <style>
                  background-image: url('/static/background.jpg');  /* Put your image in the same directory with this name */
          background-size: cover;
          background-position: center;
          background-repeat: no-repeat;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          font-family: Arial, sans-serif;
          color: white;

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
      </style>
    </head>
    <body>
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

@app.route('/object_detection')
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

@app.route('/shutdown', methods=['POST'])
def shutdown():
    try:
        picam2.stop()
    except Exception as e:
        print("Camera stop error:", e)

    shutdown_func = request.environ.get('werkzeug.server.shutdown')
    if shutdown_func:
        shutdown_func()

    threading.Thread(target=lambda: os.system("sudo shutdown now")).start()
    return "Shutting down..."

if __name__ == '__main__':
    threading.Thread(target=capture_frames, daemon=True).start()
    threading.Thread(target=detection_worker, daemon=True).start()
    app.run(host='0.0.0.0', port=8000)
