#include <SPI.h>
#include <LoRa.h>
#include <Wire.h>
#include <Adafruit_ADS1X15.h>

Adafruit_ADS1115 ads;

// Lora Pins
#define NSS 10
#define RST 9
#define DIO0 2

// UNO potentiometer pins
#define potBase A2      // camera base
#define potShoulder A3  // camera shoulder

// ADC potentiometer pins
#define potSpeed 2  // ADC A2 // speed

// UNO joystick pins
#define controlJoystickVertical A0
#define controlJoystickHorizontal A1

int joystick_vertical = 900;
int joystick_horizontal = 900;

int pot_reading_base = 0;
int pot_reading_shoulder = 0;
int pot_reading_speed = 0;

// Pin Definitions
const int button1 = 0;  // automatic camera
const int button2 = 1;  // manual camera
const int button3 = 4;  // start/stop BOT
const int button4 = 6;  // on/off LED

const int led1 = 5;  // automatic & manual camera
const int led2 = 7;  // start/stop BOT
const int led3 = 8;  // on/off LED

// Mode states
bool mode1 = false;  // automatic camera
bool mode2 = false;  // manual camera
bool mode3 = false;  // start/stop BOT
bool mode4 = false;  // on/off LED

// Button states
bool buttonState1 = false;  // automatic camera
bool buttonState2 = false;  // manual camera
bool buttonState3 = false;  // start/stop BOT
bool buttonState4 = false;  // on/off LED

unsigned long previousMillis = 0;  // Timer variable
const long interval = 100;         // Interval in milliseconds

bool waitForAckWithHello(unsigned long interval = 1000, unsigned long timeout = 500) {
  while (true) {
    // Send HELLO
    Serial.println("Sending HELLO...");
    LoRa.beginPacket();
    LoRa.write(25);
    LoRa.endPacket();

    unsigned long startTime = millis();
    bool ackReceived = false;

    // Wait for ACK within timeout
    while (millis() - startTime < timeout) {
      int packetSize = LoRa.parsePacket();
      if (packetSize > 0) {
        int incoming = 0;
        if (LoRa.available()) {
          incoming = LoRa.read();
        }
        if (incoming == 35) {
          Serial.println("ACK received!");
          ackReceived = true;
          break;
        } else {
          Serial.print("Unexpected reply: ");
          Serial.println(incoming);
        }
      }
    }

    if (ackReceived) {
      return true;  // Exit loop if ACK received
    }

    Serial.println("No ACK. Retrying in 1 second...");
    delay(interval);  // Wait before resending HELLO
  }
}


void setup() {
  Serial.begin(9600);
  pinMode(button1, INPUT_PULLUP);
  pinMode(button2, INPUT_PULLUP);
  pinMode(button3, INPUT_PULLUP);
  pinMode(button4, INPUT_PULLUP);

  pinMode(led1, OUTPUT);
  pinMode(led2, OUTPUT);
  pinMode(led3, OUTPUT);

  pinMode(controlJoystickVertical, INPUT);
  pinMode(controlJoystickHorizontal, INPUT);

  if (!ads.begin()) {
    Serial.println("Failed to initialize ADS.");
    while (1)
      ;
  }

  Serial.println("ADS initialized");

  LoRa.setPins(NSS, RST, DIO0);

  if (!LoRa.begin(433E6)) {
    Serial.println("Starting LoRa failed!");
    while (1)
      ;
  }
  if (!waitForAckWithHello()) {
    Serial.println("Handshake failed.");
    while (1)
      ;  // Should never happen due to infinite retry
  }
  Serial.println("Handshake successful. Continuing setup...");
  resetModes();

    for (int i = 0; i <= 3; i++) {
    digitalWrite(led1, HIGH);
    delay(200);
    digitalWrite(led1, LOW);
    delay(200);
    
  }
}

int applyLowPassFilter(int previousValue, int newValue, float alpha) {
  return (int)(alpha * newValue + (1.0 - alpha) * previousValue);
}


void loop() {

  unsigned long currentMillis = millis();
  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;
    // Read button states
    bool btn1 = digitalRead(button1) == LOW;
    bool btn2 = digitalRead(button2) == LOW;
    bool btn3 = digitalRead(button3) == LOW;
    bool btn4 = digitalRead(button4) == LOW;

    if (btn1 && !buttonState1) {
      if (mode1) {
        mode1 = false;  // If already ON, turn it OFF
      } else {
        resetModes();
        mode1 = true;  // Otherwise, turn it ON
      }
      buttonState1 = true;
    } else if (!btn1) {
      buttonState1 = false;
    }

    if (btn2 && !buttonState2) {
      if (mode2) {
        mode2 = false;
      } else {
        resetModes();
        mode2 = true;
      }
      buttonState2 = true;
    } else if (!btn2) {
      buttonState2 = false;
    }

    if (btn3 && !buttonState3) {
      if (mode3) {
        mode3 = false;
      } else {
        resetModes();
        mode3 = true;
      }
      buttonState3 = true;
    } else if (!btn3) {
      buttonState3 = false;
    }

    if (btn4 && !buttonState4) {
      if (mode4) {
        mode4 = false;
      } else {
        resetModes();
        mode4 = true;
      }
      buttonState4 = true;
    } else if (!btn4) {
      buttonState4 = false;
    }

    // LED control based on modes
    if (mode1) {
      digitalWrite(led1, HIGH);
    } else if (mode2) {
      digitalWrite(led1, millis() % 500 < 250 ? HIGH : LOW);
    } else {
      digitalWrite(led1, LOW);
    }

    digitalWrite(led2, mode3 ? HIGH : LOW);
    digitalWrite(led3, mode4 ? HIGH : LOW);

    joystick_vertical = analogRead(controlJoystickVertical);
    joystick_horizontal = analogRead(controlJoystickHorizontal);
    pot_reading_base = analogRead(potBase);
    pot_reading_shoulder = analogRead(potShoulder);

    // ADC potentiometer reading
    pot_reading_speed = ads.readADC_SingleEnded(potSpeed);

    int mapped_base = map(pot_reading_base, 0, 860, 0, 1023);
    int mapped_shoulder = map(pot_reading_shoulder, 0, 860, 0, 1023);
    int mapped_speed = map(pot_reading_speed, 0, 22560, 0, 1023);

    int mapped_horizontal = map(joystick_horizontal, 0, 851, 0, 1023);
    int mapped_vertical = map(joystick_vertical, 0, 851, 0, 1023);

    LoRa.beginPacket();
    LoRa.write((byte)mode1);
    LoRa.write((byte)mode2);
    LoRa.write((byte)mode3);
    LoRa.write((byte)mode4);
    LoRa.write(highByte(mapped_vertical));
    LoRa.write(lowByte(mapped_vertical));
    LoRa.write(highByte(mapped_horizontal));
    LoRa.write(lowByte(mapped_horizontal));
    LoRa.write(highByte(mapped_base));
    LoRa.write(lowByte(mapped_base));
    LoRa.write(highByte(mapped_shoulder));
    LoRa.write(lowByte(mapped_shoulder));
    LoRa.write(highByte(mapped_speed));
    LoRa.write(lowByte(mapped_speed));
    LoRa.endPacket();

    // Serial.print("route: ");
    // Serial.print(mode1);
    // Serial.print("\t");
    // Serial.print("irrigation: ");
    // Serial.print(mode2);
    // Serial.print("\t");
    // Serial.print("manual: ");
    // Serial.print(mode3);
    // Serial.print("\t");
    // Serial.print("weed: ");
    // Serial.print(mode4);
    // Serial.print("\t");
    // Serial.print("joystick vertical: ");
    // Serial.print(mapped_vertical);
    // Serial.print("\t");
    // Serial.print("joystick horizontal: ");
    // Serial.print(mapped_horizontal);
    // Serial.print("\t");
    // Serial.print("base: ");
    // Serial.print(mapped_base);
    // Serial.print("\t");
    // Serial.print("shoulder: ");
    // Serial.print(mapped_shoulder);
    // Serial.print("\t");
    // Serial.print("speed: ");
    // Serial.println(mapped_speed);
  }
}

// Function to reset all modes before enabling a new one
void resetModes() {
  mode1 = false;
  mode2 = false;
}