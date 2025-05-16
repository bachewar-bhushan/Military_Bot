#include <SPI.h>
#include <LoRa.h>
#include <AFMotor.h>
#include <Adafruit_PWMServoDriver.h>
#include <Wire.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

#define NSS 22
#define RST 23
#define DIO0 18

AF_DCMotor motor1(3);
AF_DCMotor motor2(1);
AF_DCMotor motor3(2);
AF_DCMotor motor4(4);

int mode1 = 0;
int mode2 = 0;
int led_switch = 0;
int set_position = 0;
bool var = true;
int temp_speed = 0;



int joystick_vertical = 900;
int joystick_horizontal = 900;
int led = 39;

int camera_pan = 710;
int camera_tilt = 567;
float filtered_pan = 710;
float filtered_tilt = 567;
float alpha = 0.2;

bool loraInitialized = false;


const int servoMin_pan = 304;
const int servoMax_pan = 530;

const int servoMin_tilt = 150;
const int servoMax_tilt = 502;

const int servoPanChannel = 0;
const int servoTiltChannel = 1;

int pan_pulse = 0;
int tilt_pulse = 0;

int speed = 0;
int prev_speed = -1;
//int led_brightness = 0;

int buzzer = 37;
char current_state = 's';

bool handshake_success = false;


unsigned long previousMillis = 0;  // Timer variable
const long interval = 100;         // Interval in milliseconds



void setup() {
  Serial.begin(115200);
  pinMode(buzzer, OUTPUT);
  pinMode(led, OUTPUT);
  pwm.begin();
  pwm.setPWMFreq(60);  // 50 Hz for servos
  delay(10);
  while (!Serial)
    ;
  LoRa.setPins(NSS, RST, DIO0);

  if (!LoRa.begin(433E6)) {
    Serial.println("Starting LoRa failed!");
    while (1)
      ;
  }
  Serial.println("Lora initialized");
  delay(1000);

  // Set initial position for servos
  camera_pan = 710;  // Mid-point value (0 to 1023)
  camera_tilt = 566;

  pan_pulse = map(camera_pan, 0, 1023, servoMin_pan, servoMax_pan);
  tilt_pulse = map(camera_tilt, 0, 1023, servoMin_tilt, servoMax_tilt);

  pwm.setPWM(servoPanChannel, 0, pan_pulse);
  pwm.setPWM(servoTiltChannel, 0, tilt_pulse);
  // Beep 3 times at startup
  delay(500);

  while (handshake_success == false) {
    int packetSize = LoRa.parsePacket();
    if (packetSize > 0) {

      int incoming = 0;
      if (LoRa.available()) {

        incoming = LoRa.read();
      }

      if (incoming == 25) {

        Serial.println("Got HELLO! Communication OK.");

        // sending ACK
        for (int i = 0; i <= 3; i++) {
          Serial.println("Sending ACK...");
          LoRa.beginPacket();
          LoRa.write(35);
          LoRa.endPacket();
          delay(500);
        }
        handshake_success = true;
        // You can blink an LED or respond back if needed
      }
    }
  }
  for (int i = 0; i < 3; i++) {
    digitalWrite(buzzer, HIGH);
    delay(100);
    digitalWrite(buzzer, LOW);
    delay(100);
  }
  delay(200);
  digitalWrite(buzzer, HIGH);
  delay(500);
  digitalWrite(buzzer, LOW);
  delay(500);
}


void move_forward() {
  motor1.run(BACKWARD);
  motor2.run(BACKWARD);
  motor3.run(BACKWARD);
  motor4.run(BACKWARD);
}

void move_backward() {
  motor1.run(FORWARD);
  motor2.run(FORWARD);
  motor3.run(FORWARD);
  motor4.run(FORWARD);
}

void move_left() {
  motor1.run(BACKWARD);
  motor2.run(FORWARD);
  motor3.run(FORWARD);
  motor4.run(BACKWARD);
}

void move_right() {
  motor1.run(FORWARD);
  motor2.run(BACKWARD);
  motor3.run(BACKWARD);
  motor4.run(FORWARD);
}

void stop() {
  motor1.run(RELEASE);
  motor2.run(RELEASE);
  motor3.run(RELEASE);
  motor4.run(RELEASE);
}


void loop() {

  unsigned long currentMillis = millis();
  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;
    int packetSize = LoRa.parsePacket();
    if (packetSize > 0) {
      if (LoRa.available()) {

        mode1 = LoRa.read();
        mode2 = LoRa.read();
        led_switch = LoRa.read();
        set_position = LoRa.read();
        byte highByte_joystick_vertical = LoRa.read();
        byte lowByte_joystick_vertical = LoRa.read();
        joystick_vertical = word(highByte_joystick_vertical, lowByte_joystick_vertical);

        byte highByte_joystick_horizontal = LoRa.read();
        byte lowByte_joystick_horizontal = LoRa.read();
        joystick_horizontal = word(highByte_joystick_horizontal, lowByte_joystick_horizontal);

        byte highByte_pan = LoRa.read();
        byte lowByte_pan = LoRa.read();
        camera_pan = word(highByte_pan, lowByte_pan);

        byte highByte_tilt = LoRa.read();
        byte lowByte_tilt = LoRa.read();
        camera_tilt = word(highByte_tilt, lowByte_tilt);

        byte highByte_speed = LoRa.read();
        byte lowByte_speed = LoRa.read();
        speed = word(highByte_speed, lowByte_speed);
        speed = map(speed, 0, 1023, 0, 255);

        if (led_switch == 1) {
          digitalWrite(led, HIGH);
          delay(10);
        } else {
          digitalWrite(led, LOW);
          delay(10);
        }
 loraInitialized = true;

        if (loraInitialized) {
          camera_pan = constrain(camera_pan, 0, 1009);
// LOW-PASS filter
          filtered_pan = alpha * camera_pan + (1 - alpha) * filtered_pan;
  
          pan_pulse = map(filtered_pan, 0, 1009, servoMin_pan, servoMax_pan);
    
          pwm.setPWM(servoPanChannel, 0, pan_pulse);


          camera_tilt = constrain(camera_tilt, 0, 1009);
   
          filtered_tilt = alpha * camera_tilt + (1 - alpha) * filtered_tilt;

          tilt_pulse = map(filtered_tilt, 0, 1009, servoMin_tilt, servoMax_tilt);
    
          pwm.setPWM(servoTiltChannel, 0, tilt_pulse);
        }
      }
      if (joystick_vertical < 0 || joystick_vertical > 1023) {

        stop();
      }

      if (joystick_horizontal < 0 || joystick_horizontal > 1023) {
        stop();
      }

      if (camera_pan < 0 || camera_pan > 1023) {
        camera_pan = 512;
      }

      if (camera_tilt < 0 || camera_tilt > 1023) {
        camera_tilt = 512;
      }

      if (speed < 0 || speed > 1023) {
        speed = 0;
      }
    }



    if (set_position == 1) {
      // Maintain last known direction using current_state
      for (int i = 0; i < 3; i++) {

        pinMode(buzzer, HIGH);
        delay(100);
        pinMode(buzzer, LOW);
        delay(100);
      }
      if (current_state == 'f') {
        move_forward();
      } else if (current_state == 'b') {
        move_backward();
      } else if (current_state == 'l') {
        move_left();
      } else if (current_state == 'r') {
        move_right();
      } else {
        stop();
      }
    } else {
      // Live joystick control

      if (current_state == 'l' || current_state == 'r') {

        temp_speed = speed;  // Save current speed
        speed = 190;
        var = false;

      } else if ((current_state == 'f' || current_state == 'b') && var == false) {
        speed = temp_speed;  // Restore speed
        var = true;
      }

      // keep speed track
      if (speed != prev_speed) {
        motor1.setSpeed(speed);
        motor2.setSpeed(speed);
        motor3.setSpeed(speed);
        motor4.setSpeed(speed);
        prev_speed = speed;
      }
      if (joystick_vertical > 600) {
        current_state = 'f';
        move_forward();
      } else if (joystick_vertical < 300) {
        current_state = 'b';
        move_backward();
      } else if (joystick_horizontal < 300) {
        current_state = 'l';
        move_left();
      

      } else if (joystick_horizontal > 600) {
        current_state = 'r';
        move_right();


      } else {
        current_state = 's';  // stop state
        stop();
      }
    }
  }
}